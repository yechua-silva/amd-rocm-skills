#!/bin/bash
# ============================================================
# rocm-monitor.sh — GPU Monitor for AMD ROCm / NVIDIA CUDA
#
# Monitoreo en tiempo real de GPU: clock, temperatura, power,
# VRAM, fan speed. Detecta automáticamente AMD vs NVIDIA.
#
# Usage:
#   bash rocm-monitor.sh                    # monitor every 2s
#   bash rocm-monitor.sh --interval 1       # monitor every 1s
#   bash rocm-monitor.sh --log output.log   # log to file
#   bash rocm-monitor.sh --json             # JSON-formatted output
#
# Exit: Ctrl+C to stop. Prints summary of peaks/averages.
# ============================================================

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────
INTERVAL=2
LOG_FILE=""
JSON_MODE=false
COLOR=true

# ── Parse arguments ──────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --log)
            LOG_FILE="$2"
            shift 2
            ;;
        --json)
            JSON_MODE=true
            shift
            ;;
        --no-color)
            COLOR=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--interval N] [--log FILE] [--json] [--no-color]"
            echo
            echo "  --interval N    Polling interval in seconds (default: 2)"
            echo "  --log FILE      Append timestamped data to log file"
            echo "  --json          Output in JSON format (one line per sample)"
            echo "  --no-color      Disable colored output"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ── Colors ───────────────────────────────────────────────
if [[ "$COLOR" == "true" ]] && [[ -t 1 ]]; then
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

# ── Detection ────────────────────────────────────────────
detect_backend() {
    if command -v rocm-smi &>/dev/null; then
        echo "rocm"
    elif command -v nvidia-smi &>/dev/null; then
        echo "nvidia"
    else
        echo "none"
    fi
}

BACKEND=$(detect_backend)

if [[ "$BACKEND" == "none" ]]; then
    echo -e "${RED}❌ No GPU monitoring tool found.${NC}"
    echo "  Install rocm-smi (AMD) or nvidia-smi (NVIDIA)"
    exit 2
fi

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     MUNIN — GPU Monitor (${BACKEND})   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo "  Interval: ${INTERVAL}s | Log: ${LOG_FILE:-stdout}"
echo "  Press Ctrl+C to stop and show summary"
echo

# ── Data collectors ──────────────────────────────────────
TEMP_SAMPLES=()
POWER_SAMPLES=()
CLOCK_SAMPLES=()
VRAM_SAMPLES=()
FAN_SAMPLES=()

SAMPLE_COUNT=0
START_TIME=$(date +%s)

# ── Sampling functions ──────────────────────────────────

sample_rocm() {
    local json_out
    json_out=$(rocm-smi --showtemp --showpower --showclk --showmeminfo vram --showfan --json 2>/dev/null || echo "{}")

    # Parse each card
    echo "$json_out" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
except:
    sys.exit(0)

cards = [k for k in data if k.startswith('card')]
if not cards:
    # Try 'list' key
    cards = data.get('list', [])
    if isinstance(cards, list):
        for c in cards:
            print(f'card|{c.get(\"card\",\"?\")}|{c.get(\"Temperature (Sensor edge) (C)\",\"N/A\")}|{c.get(\"Power Draw (W)\",\"N/A\")}|{c.get(\"sclk\",\"N/A\")}|{c.get(\"mclk\",\"N/A\")}|{c.get(\"VRAM Total (MB)\",\"N/A\")}|{c.get(\"VRAM Used (MB)\",\"N/A\")}|{c.get(\"Fan Speed (%)\",\"N/A\")}')
    sys.exit(0)

for card_key in cards:
    card = data[card_key]
    if not isinstance(card, dict):
        continue
    temp = card.get('Temperature (Sensor edge) (C)', 'N/A')
    power = card.get('Power Draw (W)', 'N/A')
    sclk = card.get('sclk', 'N/A')
    mclk = card.get('mclk', 'N/A')
    vram_total = card.get('VRAM Total (MB)', 'N/A')
    vram_used = card.get('VRAM Used (MB)', 'N/A')
    fan = card.get('Fan Speed (%)', 'Fan 0 Speed (%)', 'N/A')
    print(f'card|{card_key}|{temp}|{power}|{sclk}|{mclk}|{vram_total}|{vram_used}|{fan}')
" 2>/dev/null
}

sample_nvidia() {
    nvidia-smi \
        --query-gpu=index,name,temperature.gpu,power.draw,clocks.gr,clocks.mem,memory.used,memory.total,fan.speed \
        --format=csv,noheader,nounits 2>/dev/null | while IFS=',' read -r idx name temp power clock mem_clock mem_used mem_total fan; do
        # Trim whitespace
        idx=$(echo "$idx" | xargs)
        temp=$(echo "$temp" | xargs)
        power=$(echo "$power" | xargs)
        clock=$(echo "$clock" | xargs)
        mem_clock=$(echo "$mem_clock" | xargs)
        mem_used=$(echo "$mem_used" | xargs)
        mem_total=$(echo "$mem_total" | xargs)
        fan=$(echo "$fan" | xargs)
        echo "card|card${idx}|${temp}|${power}|${clock}|${mem_clock}|${mem_total}|${mem_used}|${fan}"
    done 2>/dev/null
}

# ── Output formatting ──────────────────────────────────

format_line() {
    local card_id="$1" temp="$2" power="$3" clock="$4" mem_clock="$5" vram_used="$6" vram_total="$7" fan="$8"
    local now
    now=$(date '+%H:%M:%S')

    # Color temperature
    local temp_display="$temp"
    if [[ "$COLOR" == "true" ]]; then
        if [[ "$temp" != "N/A" ]] && [[ "$temp" != "" ]]; then
            if (( $(echo "$temp >= 85" | bc -l 2>/dev/null) )); then
                temp_display="${RED}${temp}°C${NC}"
            elif (( $(echo "$temp >= 70" | bc -l 2>/dev/null) )); then
                temp_display="${YELLOW}${temp}°C${NC}"
            else
                temp_display="${GREEN}${temp}°C${NC}"
            fi
        fi
    else
        temp_display="${temp}°C"
    fi

    local power_display="N/A"
    if [[ "$power" != "N/A" ]] && [[ "$power" != "" ]]; then
        power_display="${power}W"
    fi

    local clock_display="N/A"
    if [[ "$clock" != "N/A" ]] && [[ "$clock" != "" ]]; then
        clock_display="${clock} MHz"
    fi

    local vram_display="N/A"
    if [[ "$vram_used" != "N/A" ]] && [[ "$vram_total" != "N/A" ]] && [[ "$vram_used" != "" ]] && [[ "$vram_total" != "" ]]; then
        vram_display="${vram_used}/${vram_total} MB"
    fi

    local fan_display="N/A"
    if [[ "$fan" != "N/A" ]] && [[ "$fan" != "" ]]; then
        fan_display="${fan}%"
    fi

    printf "  [${now}] GPU %-2s | %s | %s | %s MHz | %s | %s\n" \
        "$card_id" "$temp_display" "$power_display" "$clock_display" "$vram_display" "$fan_display"
}

format_json() {
    local card_id="$1" temp="$2" power="$3" clock="$4" mem_clock="$5" vram_used="$6" vram_total="$7" fan="$8"
    local now
    now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Sanitize values
    [[ "$temp" == "N/A" || "$temp" == "" ]] && temp="null"
    [[ "$power" == "N/A" || "$power" == "" ]] && power="null"
    [[ "$clock" == "N/A" || "$clock" == "" ]] && clock="null"
    [[ "$mem_clock" == "N/A" || "$mem_clock" == "" ]] && mem_clock="null"
    [[ "$vram_used" == "N/A" || "$vram_used" == "" ]] && vram_used="null"
    [[ "$vram_total" == "N/A" || "$vram_total" == "" ]] && vram_total="null"
    [[ "$fan" == "N/A" || "$fan" == "" ]] && fan="null"

    printf '{"timestamp":"%s","gpu_id":%d,"backend":"%s","temp_c":%s,"power_w":%s,"clock_mhz":%s,"mem_clock_mhz":%s,"vram_used_mb":%s,"vram_total_mb":%s,"fan_pct":%s}\n' \
        "$now" "$card_id" "$BACKEND" "$temp" "$power" "$clock" "$mem_clock" "$vram_used" "$vram_total" "$fan"
}

# ── Main loop ────────────────────────────────────────────

cleanup() {
    echo
    echo
    echo -e "${CYAN}═══ Monitor Summary ═══${NC}"

    local duration=$(( $(date +%s) - START_TIME ))

    if [[ ${#TEMP_SAMPLES[@]} -gt 0 ]]; then
        local temp_min temp_max temp_avg
        temp_min=$(printf '%s\n' "${TEMP_SAMPLES[@]}" | sort -n | head -1)
        temp_max=$(printf '%s\n' "${TEMP_SAMPLES[@]}" | sort -n | tail -1)
        temp_avg=$(printf '%s\n' "${TEMP_SAMPLES[@]}" | awk '{sum+=$1; n++} END {printf "%.1f", sum/n}')
        echo -e "  Temperature:  min ${temp_min}°C  |  avg ${temp_avg}°C  |  max ${temp_max}°C"
    fi

    if [[ ${#POWER_SAMPLES[@]} -gt 0 ]]; then
        local power_min power_max power_avg
        power_min=$(printf '%s\n' "${POWER_SAMPLES[@]}" | sort -n | head -1)
        power_max=$(printf '%s\n' "${POWER_SAMPLES[@]}" | sort -n | tail -1)
        power_avg=$(printf '%s\n' "${POWER_SAMPLES[@]}" | awk '{sum+=$1; n++} END {printf "%.1f", sum/n}')
        echo -e "  Power:        min ${power_min}W  |  avg ${power_avg}W  |  max ${power_max}W"
    fi

    if [[ ${#CLOCK_SAMPLES[@]} -gt 0 ]]; then
        local clock_min clock_max clock_avg
        clock_min=$(printf '%s\n' "${CLOCK_SAMPLES[@]}" | sort -n | head -1)
        clock_max=$(printf '%s\n' "${CLOCK_SAMPLES[@]}" | sort -n | tail -1)
        clock_avg=$(printf '%s\n' "${CLOCK_SAMPLES[@]}" | awk '{sum+=$1; n++} END {printf "%.0f", sum/n}')
        echo -e "  Clock:        min ${clock_min} MHz  |  avg ${clock_avg} MHz  |  max ${clock_max} MHz"
    fi

    if [[ ${#VRAM_SAMPLES[@]} -gt 0 ]]; then
        local vram_min vram_max vram_avg
        vram_min=$(printf '%s\n' "${VRAM_SAMPLES[@]}" | sort -n | head -1)
        vram_max=$(printf '%s\n' "${VRAM_SAMPLES[@]}" | sort -n | tail -1)
        vram_avg=$(printf '%s\n' "${VRAM_SAMPLES[@]}" | awk '{sum+=$1; n++} END {printf "%.0f", sum/n}')
        echo -e "  VRAM Used:    min ${vram_min} MB  |  avg ${vram_avg} MB  |  max ${vram_max} MB"
    fi

    echo -e "  Duration:     ${duration}s (${SAMPLE_COUNT} samples)"
    echo -e "${CYAN}═════════════════════════════${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${BOLD}  Time       | Temp    | Power  | Clock     | VRAM           | Fan${NC}"
echo -e "${BOLD}  ──────────┼─────────┼────────┼───────────┼────────────────┼─────${NC}"

while true; do
    if [[ "$BACKEND" == "rocm" ]]; then
        LINES=$(sample_rocm)
    else
        LINES=$(sample_nvidia)
    fi

    IFS=$'\n'
    for line in $LINES; do
        IFS='|' read -r _ card_id temp power clock mem_clock vram_total vram_used fan <<< "$line"

        # Trim whitespace from each field
        card_id=$(echo "$card_id" | xargs)
        temp=$(echo "$temp" | xargs)
        power=$(echo "$power" | xargs)
        clock=$(echo "$clock" | xargs)
        mem_clock=$(echo "$mem_clock" | xargs)
        vram_used=$(echo "$vram_used" | xargs)
        vram_total=$(echo "$vram_total" | xargs)
        fan=$(echo "$fan" | xargs)

        # Extract just the card number from card_id (e.g., "card0" → "0")
        card_num="${card_id##card}"

        # Collect samples for summary
        if [[ "$temp" != "N/A" ]] && [[ "$temp" != "" ]]; then
            TEMP_SAMPLES+=("$temp")
        fi
        if [[ "$power" != "N/A" ]] && [[ "$power" != "" ]]; then
            POWER_SAMPLES+=("$power")
        fi
        if [[ "$clock" != "N/A" ]] && [[ "$clock" != "" ]]; then
            CLOCK_SAMPLES+=("$clock")
        fi
        if [[ "$vram_used" != "N/A" ]] && [[ "$vram_used" != "" ]]; then
            VRAM_SAMPLES+=("$vram_used")
        fi
        if [[ "$fan" != "N/A" ]] && [[ "$fan" != "" ]]; then
            FAN_SAMPLES+=("$fan")
        fi

        # Output
        if [[ "$JSON_MODE" == "true" ]]; then
            format_json "$card_num" "$temp" "$power" "$clock" "$mem_clock" "$vram_used" "$vram_total" "$fan"
        else
            format_line "$card_num" "$temp" "$power" "$clock" "$mem_clock" "$vram_used" "$vram_total" "$fan"
        fi

        # Log to file
        if [[ -n "$LOG_FILE" ]]; then
            format_json "$card_num" "$temp" "$power" "$clock" "$mem_clock" "$vram_used" "$vram_total" "$fan" >> "$LOG_FILE"
        fi
    done

    SAMPLE_COUNT=$((SAMPLE_COUNT + 1))
    sleep "$INTERVAL"
done
