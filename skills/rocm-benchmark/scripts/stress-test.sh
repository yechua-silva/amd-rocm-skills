#!/bin/bash
# ============================================================
# stress-test.sh — GPU Stress Test for AMD ROCm / NVIDIA CUDA
#
# Carga sostenida de GPU con detección de thermal throttling.
# Usa PyTorch GEMM loop (recomendado) o rocblas-bench si está
# disponible. Detecta automáticamente AMD vs NVIDIA.
#
# Usage:
#   bash stress-test.sh                           # 60s default
#   bash stress-test.sh --duration 120            # 120 seconds
#   bash stress-test.sh --load 4096               # matrix size
#   bash stress-test.sh --monitor                 # with rocm-smi
#   bash stress-test.sh --threshold 10            # 10% clock drop
#
# Exit codes:
#   0 = stable (no throttling detected)
#   1 = throttling detected
#   2 = error (no GPU, no tools, etc.)
# ============================================================

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────
DURATION=60
MATRIX_SIZE=4096
THRESHOLD=5
MONITOR=false
INTERVAL=2
PYTHON_CMD=""

# ── Parse arguments ──────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --duration|-d)
            DURATION="$2"
            shift 2
            ;;
        --load|-l)
            MATRIX_SIZE="$2"
            shift 2
            ;;
        --threshold|-t)
            THRESHOLD="$2"
            shift 2
            ;;
        --monitor|-m)
            MONITOR=true
            shift
            ;;
        --interval|-i)
            INTERVAL="$2"
            shift 2
            ;;
        --python)
            PYTHON_CMD="$2"
            shift 2
            ;;
        -h|--help)
            echo "GPU Stress Test — AMD ROCm / NVIDIA CUDA"
            echo
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  --duration SECS    Test duration (default: 60)"
            echo "  --load N           GEMM matrix size (default: 4096)"
            echo "  --threshold PCT    Clock drop threshold %% (default: 5)"
            echo "  --monitor          Monitor with rocm-smi/nvidia-smi"
            echo "  --interval SECS    Monitor interval (default: 2)"
            echo "  --python PATH      Python interpreter path"
            echo
            echo "Exit codes:"
            echo "  0 = stable"
            echo "  1 = throttling detected"
            echo "  2 = error"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 2
            ;;
    esac
done

# ── Colors ───────────────────────────────────────────────
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    CYAN=''
    BOLD=''
    NC=''
fi

# ── Detect Python ────────────────────────────────────────
if [[ -z "$PYTHON_CMD" ]]; then
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    done
fi

if [[ -z "$PYTHON_CMD" ]]; then
    echo -e "${RED}❌ Python not found${NC}"
    exit 2
fi

# ── Detect GPU Backend ───────────────────────────────────
detect_gpu() {
    if command -v rocm-smi &>/dev/null; then
        echo "rocm"
    elif command -v nvidia-smi &>/dev/null; then
        echo "nvidia"
    else
        # Check via lspci
        if command -v lspci &>/dev/null; then
            if lspci | grep -qiE "amd|radeon" | grep -qiE "vga|3d|display" 2>/dev/null; then
                echo "rocm-no-tools"
            elif lspci | grep -qi nvidia | grep -qiE "vga|3d|display" 2>/dev/null; then
                echo "nvidia-no-tools"
            fi
        fi
        echo "none"
    fi
}

BACKEND=$(detect_gpu)
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     AMD ROCm — GPU Stress Test (${BACKEND})   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo "  Duration:     ${DURATION}s"
echo "  Matrix Size:  ${MATRIX_SIZE}x${MATRIX_SIZE}"
echo "  Threshold:    ${THRESHOLD}% clock drop"
echo "  Monitor:      ${MONITOR}"
echo

if [[ "$BACKEND" == "none" ]]; then
    echo -e "${RED}❌ No GPU detected${NC}"
    exit 2
fi

# ── Verify PyTorch ────────────────────────────────────────
echo -n "  Verifying PyTorch CUDA... "
PYTORCH_OK=$($PYTHON_CMD -c "
import torch
print(torch.cuda.is_available())
" 2>/dev/null || echo "False")

if [[ "$PYTORCH_OK" != "True" ]]; then
    echo -e "${RED}FAIL${NC}"
    echo "  ❌ torch.cuda.is_available() is False"
    echo "  Install PyTorch with ROCm/CUDA support"
    exit 2
fi
echo -e "${GREEN}OK${NC}"

DEVICE_NAME=$($PYTHON_CMD -c "
import torch
print(torch.cuda.get_device_name(0))
" 2>/dev/null || echo "Unknown")
echo "  GPU:          $DEVICE_NAME"
echo

# ── Monitor setup ────────────────────────────────────────
MONITOR_PID=""
if [[ "$MONITOR" == "true" ]]; then
    # Launch rocm-monitor in background
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -f "${SCRIPT_DIR}/rocm-monitor.sh" ]]; then
        bash "${SCRIPT_DIR}/rocm-monitor.sh" --interval "$INTERVAL" --no-color &
        MONITOR_PID=$!
    else
        # Fallback: inline monitoring with rocm-smi
        echo "  (monitor script not found, using inline rocm-smi)"
        MONITOR_PID="inline"
    fi
fi

# ── Initial metrics ──────────────────────────────────────
echo "  Collecting baseline metrics..."
BASELINE_TEMP=""
BASELINE_CLOCK=""

if [[ "$BACKEND" == "rocm" ]] || [[ "$BACKEND" == "rocm-no-tools" ]]; then
    if command -v rocm-smi &>/dev/null; then
        BASELINE_TEMP=$(rocm-smi --showtemp --json 2>/dev/null | $PYTHON_CMD -c "
import sys,json
try:
    d=json.load(sys.stdin)
    for k,v in d.items():
        if k.startswith('card') and isinstance(v,dict):
            t=v.get('Temperature (Sensor edge) (C)','')
            print(t); break
except: pass
" 2>/dev/null || echo "")
        BASELINE_CLOCK=$(rocm-smi --showclk --json 2>/dev/null | $PYTHON_CMD -c "
import sys,json
try:
    d=json.load(sys.stdin)
    for k,v in d.items():
        if k.startswith('card') and isinstance(v,dict):
            c=v.get('sclk',''); print(c); break
except: pass
" 2>/dev/null || echo "")
    fi
elif [[ "$BACKEND" == "nvidia" ]] || [[ "$BACKEND" == "nvidia-no-tools" ]]; then
    if command -v nvidia-smi &>/dev/null; then
        BASELINE_TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 || echo "")
        BASELINE_CLOCK=$(nvidia-smi --query-gpu=clocks.gr --format=csv,noheader,nounits 2>/dev/null | head -1 | awk '{print $1}' || echo "")
    fi
fi

echo "  Baseline temp: ${BASELINE_TEMP:-N/A}°C"
echo "  Baseline clock: ${BASELINE_CLOCK:-N/A} MHz"
echo

# ── Stress test (PyTorch GEMM loop) ──────────────────────
echo -e "${BOLD}  Running stress test...${NC}"

# Write a temporary Python stress script
STRESS_SCRIPT=$(mktemp /tmp/gpu-stress-XXXXXX.py)
cat > "$STRESS_SCRIPT" << PYEOF
import torch
import time
import sys
import json

device = "cuda:0"
n = $MATRIX_SIZE
duration = $DURATION
threshold = $THRESHOLD
backend = "$BACKEND"

# Create matrices
a = torch.randn(n, n, device=device)
b = torch.randn(n, n, device=device)

# Warmup
print(f"  Warming up ({n}x{n} GEMM)...")
for _ in range(20):
    c = torch.mm(a, b)
    torch.cuda.synchronize()

# Stress loop
start_time = time.time()
iter_count = 0
clock_samples = []
temp_samples = []

while time.time() - start_time < duration:
    # Run GEMM for ~1 second chunks
    chunk_start = time.time()
    while time.time() - chunk_start < 1.0:
        c = torch.mm(a, b)
        torch.cuda.synchronize()
        iter_count += 1

    # Report progress
    elapsed = time.time() - start_time
    pct = min(elapsed / duration * 100, 100)
    print(f"  \r  Progress: {pct:.0f}% | iterations: {iter_count}", end="")
    sys.stdout.flush()

print()
print(f"  Completed: {iter_count} iterations in {time.time() - start_time:.1f}s")
print(f"  Throughput: {iter_count / duration:.0f} GEMM/s")

# Signal completion
print("__STRESS_DONE__")
sys.stdout.flush()
PYEOF

# Run stress script and capture output
START_TIME=$(date +%s)
$PYTHON_CMD "$STRESS_SCRIPT" 2>&1
STRESS_EXIT=$?
rm -f "$STRESS_SCRIPT"

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo

# ── Final metrics ────────────────────────────────────────
echo "  Collecting final metrics..."
FINAL_TEMP=""
FINAL_CLOCK=""

if [[ "$BACKEND" == "rocm" ]] || [[ "$BACKEND" == "rocm-no-tools" ]]; then
    if command -v rocm-smi &>/dev/null; then
        FINAL_TEMP=$(rocm-smi --showtemp --json 2>/dev/null | $PYTHON_CMD -c "
import sys,json
try:
    d=json.load(sys.stdin)
    for k,v in d.items():
        if k.startswith('card') and isinstance(v,dict):
            t=v.get('Temperature (Sensor edge) (C)','')
            print(t); break
except: pass
" 2>/dev/null || echo "")
        FINAL_CLOCK=$(rocm-smi --showclk --json 2>/dev/null | $PYTHON_CMD -c "
import sys,json
try:
    d=json.load(sys.stdin)
    for k,v in d.items():
        if k.startswith('card') and isinstance(v,dict):
            c=v.get('sclk',''); print(c); break
except: pass
" 2>/dev/null || echo "")
    fi
elif [[ "$BACKEND" == "nvidia" ]] || [[ "$BACKEND" == "nvidia-no-tools" ]]; then
    if command -v nvidia-smi &>/dev/null; then
        FINAL_TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 || echo "")
        FINAL_CLOCK=$(nvidia-smi --query-gpu=clocks.gr --format=csv,noheader,nounits 2>/dev/null | head -1 | awk '{print $1}' || echo "")
    fi
fi

# ── Analyze ──────────────────────────────────────────────
echo
echo -e "${CYAN}═══ Stress Test Results ═══${NC}"
echo "  Duration:     ${ELAPSED}s (target: ${DURATION}s)"
echo "  Baseline temp: ${BASELINE_TEMP:-N/A}°C  →  Final temp: ${FINAL_TEMP:-N/A}°C"
echo "  Baseline clock: ${BASELINE_CLOCK:-N/A} MHz  →  Final clock: ${FINAL_CLOCK:-N/A} MHz"

# Throttling detection
if [[ -n "$BASELINE_CLOCK" && -n "$FINAL_CLOCK" ]] && \
   [[ "$BASELINE_CLOCK" != "N/A" && "$FINAL_CLOCK" != "N/A" ]] && \
   [[ "$BASELINE_CLOCK" =~ ^[0-9]+(\.[0-9]+)?$ && "$FINAL_CLOCK" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then

    CLOCK_DROP=$(echo "scale=2; (${BASELINE_CLOCK} - ${FINAL_CLOCK}) / ${BASELINE_CLOCK} * 100" | bc -l 2>/dev/null || echo "0")

    echo "  Clock drop:   ${CLOCK_DROP}%"

    if (( $(echo "$CLOCK_DROP >= $THRESHOLD" | bc -l 2>/dev/null) )); then
        echo -e "  Status:       ${RED}❌ THROTTLING DETECTED${NC}"
        echo
        echo -e "${YELLOW}  ⚠️  GPU clock dropped ${CLOCK_DROP}% (threshold: ${THRESHOLD}%)${NC}"
        echo "  Possible causes:"
        echo "    - Insufficient cooling (airflow, fans, thermal paste)"
        echo "    - Power supply limit (PSU wattage too low)"
        echo "    - Ambient temperature too high"
        echo "    - Power capping active (check: rocm-smi --showpowercap)"
        EXIT_CODE=1
    else
        echo -e "  Status:       ${GREEN}✅ STABLE${NC}"
        EXIT_CODE=0
    fi
else
    echo "  Clock data:   insufficient for throttle analysis"
    EXIT_CODE=0
fi

# Temperature warning
if [[ -n "$FINAL_TEMP" ]] && [[ "$FINAL_TEMP" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    if (( $(echo "$FINAL_TEMP >= 85" | bc -l 2>/dev/null) )); then
        echo -e "  ${YELLOW}⚠️  High temperature: ${FINAL_TEMP}°C (throttle threshold: ~85°C)${NC}"
    fi
fi

# ── Cleanup monitor ──────────────────────────────────────
if [[ -n "$MONITOR_PID" ]] && [[ "$MONITOR_PID" != "inline" ]]; then
    kill "$MONITOR_PID" 2>/dev/null || true
fi

echo
echo -e "${CYAN}═══════════════════════════════════════════${NC}"
echo -e "  Exit code: ${EXIT_CODE} ($([ "$EXIT_CODE" == 0 ] && echo 'stable' || echo 'throttling'))"
echo -e "${CYAN}═══════════════════════════════════════════${NC}"

exit $EXIT_CODE
