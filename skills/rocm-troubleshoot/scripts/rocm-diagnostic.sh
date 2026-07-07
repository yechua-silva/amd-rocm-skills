#!/bin/bash
# ============================================================
# rocm-diagnostic.sh — ROCm Master Diagnostic Script
#
# Ejecuta TODAS las verificaciones disponibles y produce un
# reporte completo del estado del sistema ROCm.
#
# Usage:
#   bash rocm-diagnostic.sh            # Reporte legible
#   bash rocm-diagnostic.sh --json     # Salida JSON parseable
#   bash rocm-diagnostic.sh --quiet    # Solo exit code
#
# Checks:
#   1. GPU física (lspci + nvidia-smi + rocminfo)
#   2. Kernel module (amdgpu)
#   3. Device nodes (/dev/kfd, /dev/dri/*)
#   4. ROCm tools (rocminfo, rocm-smi, hipconfig)
#   5. ROCm version (/opt/rocm/share/doc/rocm-version/version)
#   6. Docker (Engine, grupos, test container)
#   7. PyTorch (torch.cuda, torch.version.hip, torch.version.cuda)
#   8. vLLM (pip list, Python version)
#   9. Environment variables (ROCR_VISIBLE_DEVICES, HIP_VISIBLE_DEVICES,
#      HSA_OVERRIDE_GFX_VERSION, CUDA_VISIBLE_DEVICES)
#   10. GPU architecture (rocminfo | grep gfx)
#
# Exit codes:
#   0 = Todo OK
#   1 = Warnings (GPU detectada pero algo subóptimo)
#   2 = Errors (GPU no detectada o componentes críticos faltan)
# ============================================================

set -euo pipefail

# ── Constants ──────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
PASS="${GREEN}✅${NC}"
WARN="${YELLOW}⚠️${NC}"
FAIL="${RED}❌${NC}"
INFO="${CYAN}ℹ️${NC}"

EXIT=0
MODE="${1:-normal}"  # normal, --json, --quiet
REPORT_JSON='{"status":"ok","exit_code":0,"checks":[],"warnings":[],"errors":[],"system":{},"gpu":{},"rocm":{},"pytorch":{},"vllm":{},"docker":{},"env":{}}'

# ── Helpers ────────────────────────────────────────────────
log_info()    { [ "$MODE" != "--json" ] && echo -e "  ${INFO} $1"; }
log_ok()      { [ "$MODE" != "--json" ] && echo -e "  ${PASS} $1"; }
log_warn()    { [ "$MODE" != "--json" ] && echo -e "  ${WARN} $1"; [ "$EXIT" -eq 0 ] && EXIT=1; }
log_error()   { [ "$MODE" != "--json" ] && echo -e "  ${FAIL} $1"; EXIT=2; }
log_header()  { [ "$MODE" != "--json" ] && echo -e "\n─── $1 ───"; }

json_add() {
    local key="$1" value="$2" section="${3:-checks}"
    REPORT_JSON=$(echo "$REPORT_JSON" | python3 -c "
import sys, json
r = json.load(sys.stdin)
if '$section' == 'checks':
    r['checks'].append({'name': '$key', 'status': 'ok', 'message': '$value'})
else:
    r['$section']['$key'] = '$value'
print(json.dumps(r))
" 2>/dev/null || echo "$REPORT_JSON")
}

json_warn() {
    local key="$1" value="$2"
    REPORT_JSON=$(echo "$REPORT_JSON" | python3 -c "
import sys, json
r = json.load(sys.stdin)
r['checks'].append({'name': '$key', 'status': 'warning', 'message': '$value'})
r['warnings'].append('$key: $value')
if r['status'] == 'ok': r['status'] = 'warning'
print(json.dumps(r))
" 2>/dev/null || echo "$REPORT_JSON")
}

json_error() {
    local key="$1" value="$2"
    REPORT_JSON=$(echo "$REPORT_JSON" | python3 -c "
import sys, json
r = json.load(sys.stdin)
r['checks'].append({'name': '$key', 'status': 'error', 'message': '$value'})
r['errors'].append('$key: $value')
r['status'] = 'error'
print(json.dumps(r))
" 2>/dev/null || echo "$REPORT_JSON")
}

# ── Banner ─────────────────────────────────────────────────
[ "$MODE" != "--json" ] && [ "$MODE" != "--quiet" ] && echo "
╔══════════════════════════════════════════════════════════╗
║      ROCm Master Diagnostic — Munin Troubleshoot        ║
║      GPU ROCm + NVIDIA CUDA + CPU fallback              ║
╚══════════════════════════════════════════════════════════╝
"

# ═══════════════════════════════════════════════════════════
# 1. SYSTEM INFO
# ═══════════════════════════════════════════════════════════
log_header "System Info"

SYS_KERNEL=$(uname -r 2>/dev/null || echo "unknown")
SYS_OS=""
if [ -f /etc/os-release ]; then
    SYS_OS=$(grep -E "^PRETTY_NAME=" /etc/os-release | cut -d= -f2 | tr -d '"')
fi
SYS_HOSTNAME=$(hostname 2>/dev/null || echo "unknown")
SYS_ARCH=$(uname -m 2>/dev/null || echo "unknown")
log_info "Host: ${SYS_HOSTNAME} | OS: ${SYS_OS} | Kernel: ${SYS_KERNEL} | Arch: ${SYS_ARCH}"
json_add "hostname" "$SYS_HOSTNAME" "system"
json_add "os" "$SYS_OS" "system"
json_add "kernel" "$SYS_KERNEL" "system"
json_add "arch" "$SYS_ARCH" "system"

# ═══════════════════════════════════════════════════════════
# 2. GPU DETECTION
# ═══════════════════════════════════════════════════════════
log_header "GPU Detection"

GPU_FOUND=false
GPU_BACKEND=""
GPU_COUNT=0
GPU_NAMES=""
GPU_GFX=""

# 2a. lspci
if command -v lspci &>/dev/null; then
    AMD_PCI=$(lspci 2>/dev/null | grep -iE "amd|radeon" | grep -iE "vga|display|3d" || true)
    NVIDIA_PCI=$(lspci 2>/dev/null | grep -i nvidia | grep -iE "vga|display|3d" || true)
    if [ -n "$AMD_PCI" ]; then
        GPU_FOUND=true
        GPU_BACKEND="rocm"
        log_ok "AMD GPU(s) en PCIe: $(echo "$AMD_PCI" | wc -l) dispositivo(s)"
        json_add "pci_amd" "$(echo "$AMD_PCI" | tr '\n' ';')" "gpu"
    fi
    if [ -n "$NVIDIA_PCI" ]; then
        GPU_FOUND=true
        GPU_BACKEND="nvidia"
        log_ok "NVIDIA GPU(s) en PCIe: $(echo "$NVIDIA_PCI" | wc -l) dispositivo(s)"
        json_add "pci_nvidia" "$(echo "$NVIDIA_PCI" | tr '\n' ';')" "gpu"
    fi
    if [ -z "$AMD_PCI" ] && [ -z "$NVIDIA_PCI" ]; then
        log_warn "No se encontraron GPUs via lspci"
        json_warn "pci_gpu" "No GPUs found via lspci"
    fi
else
    log_warn "lspci no disponible (instalar con: sudo apt install pciutils)"
    json_warn "lspci" "lspci not available"
fi

# 2b. nvidia-smi
if command -v nvidia-smi &>/dev/null; then
    NVIDIA_OUT=$(nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null | head -5 || true)
    NVIDIA_COUNT=$(echo "$NVIDIA_OUT" | grep -c . 2>/dev/null || echo 0)
    if [ "$NVIDIA_COUNT" -gt 0 ]; then
        GPU_FOUND=true
        GPU_BACKEND="nvidia"
        GPU_COUNT=$NVIDIA_COUNT
        GPU_NAMES=$(echo "$NVIDIA_OUT" | head -1 | cut -d, -f1 | xargs)
        log_ok "nvidia-smi: $NVIDIA_COUNT GPU(s) detectada(s): $GPU_NAMES"
        json_add "nvidia_count" "$NVIDIA_COUNT" "gpu"
        json_add "nvidia_names" "$GPU_NAMES" "gpu"
    fi
else
    log_info "nvidia-smi no disponible (esperado si no hay NVIDIA)"
fi

# 2c. rocminfo / rocm-smi
if command -v rocminfo &>/dev/null; then
    ROCM_GFX=$(rocminfo 2>/dev/null | grep -E "^\s*Name:\s+gfx" | head -5 || true)
    if [ -n "$ROCM_GFX" ]; then
        GPU_FOUND=true
        GPU_BACKEND="rocm"
        GPU_GFX=$(echo "$ROCM_GFX" | head -1 | xargs)
        log_ok "rocminfo: $(echo "$ROCM_GFX" | wc -l) agente(s) GFX detectado(s)"
        echo "$ROCM_GFX" | while read -r line; do
            [ "$MODE" != "--json" ] && echo "         $line"
        done
        json_add "rocm_gfx_agents" "$(echo "$ROCM_GFX" | tr '\n' ';')" "gpu"
    fi
else
    log_info "rocminfo no disponible (ROCm no instalado)"
fi

if command -v rocm-smi &>/dev/null; then
    ROCM_SMI_OUT=$(rocm-smi --showproductname 2>/dev/null | grep -E "^[0-9]+:" | head -5 || true)
    if [ -n "$ROCM_SMI_OUT" ]; then
        GPU_FOUND=true
        GPU_BACKEND="rocm"
        ROCM_SMI_COUNT=$(echo "$ROCM_SMI_OUT" | wc -l)
        [ "$GPU_COUNT" -eq 0 ] && GPU_COUNT=$ROCM_SMI_COUNT
        log_ok "rocm-smi: $ROCM_SMI_COUNT GPU(s)"
        json_add "rocm_smi_count" "$ROCM_SMI_COUNT" "gpu"
    fi
fi

# 2d. GPU architecture
if command -v rocminfo &>/dev/null; then
    GFX_ARCH=$(rocminfo 2>/dev/null | grep -oP 'gfx\d+' | sort -u | head -3 | tr '\n' ' ')
    if [ -n "$GFX_ARCH" ]; then
        log_ok "Arquitectura GFX: $GFX_ARCH"
        json_add "gfx_architecture" "$(echo "$GFX_ARCH" | xargs)" "gpu"
    fi
fi

# Summary
if ! $GPU_FOUND; then
    log_error "No se detectó ninguna GPU (checked: lspci, nvidia-smi, rocminfo, rocm-smi)"
    json_error "gpu_detection" "No GPU detected"
else
    log_ok "Backend: ${GPU_BACKEND} | GPUs: ${GPU_COUNT}"
    json_add "gpu_found" "true" "gpu"
    json_add "gpu_backend" "$GPU_BACKEND" "gpu"
    json_add "gpu_count" "$GPU_COUNT" "gpu"
fi

# ═══════════════════════════════════════════════════════════
# 3. KERNEL MODULE
# ═══════════════════════════════════════════════════════════
log_header "Kernel Module"

if lsmod 2>/dev/null | grep -q amdgpu; then
    log_ok "Módulo amdgpu cargado"
    json_add "amdgpu_module" "loaded" "gpu"
else
    log_warn "Módulo amdgpu NO cargado (AMD GPU no funcionará)"
    json_warn "amdgpu_module" "amdgpu module not loaded"
fi

if lsmod 2>/dev/null | grep -q nvidia; then
    log_ok "Módulo nvidia cargado"
    json_add "nvidia_module" "loaded" "gpu"
fi

# ═══════════════════════════════════════════════════════════
# 4. DEVICE NODES
# ═══════════════════════════════════════════════════════════
log_header "Device Nodes"

KFD_EXISTS=false
DRI_EXISTS=false

if [ -e /dev/kfd ]; then
    KFD_PERMS=$(ls -la /dev/kfd 2>/dev/null | awk '{print $1, $3, $4}')
    log_ok "/dev/kfd existe ($KFD_PERMS)"
    json_add "dev_kfd" "exists: $KFD_PERMS" "gpu"
    KFD_EXISTS=true
else
    log_error "/dev/kfd NO existe (amdgpu module no cargado o ROCm no instalado)"
    json_error "dev_kfd" "/dev/kfd does not exist"
fi

if [ -d /dev/dri ] && [ "$(ls -A /dev/dri/ 2>/dev/null)" ]; then
    RENDER_NODES=$(ls /dev/dri/render* 2>/dev/null | wc -l)
    CARD_NODES=$(ls /dev/dri/card* 2>/dev/null | wc -l)
    log_ok "/dev/dri/ presente ($RENDER_NODES render nodes, $CARD_NODES card nodes)"
    json_add "dev_dri" "present: ${RENDER_NODES} render, ${CARD_NODES} card" "gpu"
    DRI_EXISTS=true
else
    log_warn "/dev/dri/ no encontrado o vacío"
    json_warn "dev_dri" "/dev/dri not found or empty"
fi

# ═══════════════════════════════════════════════════════════
# 5. ROCm TOOLS & VERSION
# ═══════════════════════════════════════════════════════════
log_header "ROCm Tools & Version"

ROCM_VERSION=""
if [ -f /opt/rocm/share/doc/rocm-version/version ]; then
    ROCM_VERSION=$(cat /opt/rocm/share/doc/rocm-version/version)
    log_ok "ROCm version: ${ROCM_VERSION}"
    json_add "rocm_version" "$ROCM_VERSION" "rocm"
elif command -v dpkg &>/dev/null; then
    ROCM_DPKG=$(dpkg -l rocm-libs 2>/dev/null | grep rocm-libs | awk '{print $3}' || true)
    if [ -n "$ROCM_DPKG" ]; then
        ROCM_VERSION="${ROCM_DPKG}"
        log_ok "ROCm version (dpkg): ${ROCM_DPKG}"
        json_add "rocm_version" "$ROCM_DPKG" "rocm"
    else
        log_warn "No se pudo determinar versión ROCm"
        json_warn "rocm_version" "Could not determine ROCm version"
    fi
fi

for tool in rocminfo rocm-smi hipconfig; do
    if command -v "$tool" &>/dev/null; then
        log_ok "$tool disponible"
        json_add "tool_${tool}" "available" "rocm"
    else
        log_warn "$tool NO disponible (ROCm puede no estar completo)"
        json_warn "tool_${tool}" "$tool not found"
    fi
done

# hipconfig version
if command -v hipconfig &>/dev/null; then
    HIP_VER=$(hipconfig --version 2>/dev/null || echo "unknown")
    log_info "HIP version: ${HIP_VER}"
    json_add "hip_version" "$HIP_VER" "rocm"
fi

# ═══════════════════════════════════════════════════════════
# 6. DOCKER
# ═══════════════════════════════════════════════════════════
log_header "Docker"

DOCKER_OK=false
if command -v docker &>/dev/null; then
    DOCKER_VER=$(docker --version 2>/dev/null)
    log_ok "Docker: ${DOCKER_VER}"
    json_add "docker_version" "$DOCKER_VER" "docker"
    DOCKER_OK=true

    # User groups for Docker
    CURRENT_USER=${USER:-$(whoami)}
    DOCKER_GROUP_OK=false
    if groups "$CURRENT_USER" 2>/dev/null | grep -q "\bdocker\b"; then
        log_ok "Usuario en grupo docker"
        json_add "docker_group" "yes" "docker"
        DOCKER_GROUP_OK=true
    else
        log_warn "Usuario NO en grupo docker (necesario para Docker sin sudo)"
        json_warn "docker_group" "User not in docker group"
    fi

    # Groups for GPU
    for g in video render; do
        if groups "$CURRENT_USER" 2>/dev/null | grep -q "\b$g\b"; then
            log_ok "Usuario en grupo '$g'"
            json_add "group_${g}" "yes" "docker"
        else
            log_warn "Usuario NO en grupo '$g' (GPU access limitado)"
            json_warn "group_${g}" "User not in $g group"
        fi
    done

    # Test container (optional, may fail if no GPU)
    if $KFD_EXISTS && $DRI_EXISTS; then
        log_info "Ejecutando test de contenedor ROCm..."
        if docker run --rm --device=/dev/kfd --device=/dev/dri --group-add=video \
            rocm/dev-ubuntu-22.04:latest rocminfo &>/tmp/munin-diag-rocm-test.log; then
            log_ok "Test contenedor ROCm: OK"
            json_add "docker_rocm_test" "passed" "docker"
        else
            log_warn "Test contenedor ROCm falló (ver /tmp/munin-diag-rocm-test.log)"
            json_warn "docker_rocm_test" "ROCm container test failed"
        fi
    else
        log_info "Saltando test ROCm container (no hay dispositivos AMD)"
    fi
else
    log_warn "Docker no instalado"
    json_warn "docker" "Docker not installed"
fi

# ═══════════════════════════════════════════════════════════
# 7. PyTorch
# ═══════════════════════════════════════════════════════════
log_header "PyTorch"

PYTORCH_INSTALLED=false
if python3 -c "import torch; print(torch.__version__)" &>/dev/null; then
    PYTORCH_INSTALLED=true
    TORCH_VER=$(python3 -c "import torch; print(torch.__version__)")
    log_ok "PyTorch ${TORCH_VER} instalado"
    json_add "torch_version" "$TORCH_VER" "pytorch"

    # Check CUDA availability
    CUDA_AVAIL=$(python3 -c "import torch; print(torch.cuda.is_available())" 2>/dev/null || echo "error")
    if [ "$CUDA_AVAIL" = "True" ]; then
        log_ok "torch.cuda.is_available() = True"
        json_add "torch_cuda" "True" "pytorch"

        HIP_VER=$(python3 -c "import torch; v=getattr(torch.version,'hip',None); print(v or 'none')" 2>/dev/null || echo "none")
        CUDA_VER=$(python3 -c "import torch; v=getattr(torch.version,'cuda',None); print(v or 'none')" 2>/dev/null || echo "none")

        if [ "$HIP_VER" != "none" ]; then
            log_ok "Backend: ROCm (HIP ${HIP_VER})"
            json_add "torch_backend" "rocm" "pytorch"
            json_add "torch_hip" "$HIP_VER" "pytorch"
        elif [ "$CUDA_VER" != "none" ]; then
            log_ok "Backend: CUDA (CUDA ${CUDA_VER})"
            json_add "torch_backend" "cuda" "pytorch"
            json_add "torch_cuda_ver" "$CUDA_VER" "pytorch"
        fi

        DEV_COUNT=$(python3 -c "import torch; print(torch.cuda.device_count())" 2>/dev/null || echo "0")
        log_ok "Device count: ${DEV_COUNT}"
        json_add "torch_device_count" "$DEV_COUNT" "pytorch"

        for i in $(seq 0 $((DEV_COUNT - 1))); do
            DEV_NAME=$(python3 -c "import torch; print(torch.cuda.get_device_name($i))" 2>/dev/null || echo "unknown")
            log_ok "  [$i] ${DEV_NAME}"
        done

        # Check mem info
        FREE_MEM=$(python3 -c "import torch; f,t=torch.cuda.mem_get_info(); print(f'{f/1e9:.2f}')" 2>/dev/null || echo "unknown")
        TOTAL_MEM=$(python3 -c "import torch; f,t=torch.cuda.mem_get_info(); print(f'{t/1e9:.2f}')" 2>/dev/null || echo "unknown")
        log_info "VRAM: ${FREE_MEM} GB free / ${TOTAL_MEM} GB total"
        json_add "torch_vram_free" "$FREE_MEM" "pytorch"
        json_add "torch_vram_total" "$TOTAL_MEM" "pytorch"

    else
        log_error "torch.cuda.is_available() = False"
        json_error "torch_cuda" "torch.cuda.is_available() is False"

        # Determine why
        if [ "$GPU_BACKEND" = "rocm" ]; then
            log_warn "GPU AMD detectada pero PyTorch no la ve — ¿rueda CUDA instalada?"
            log_warn "Solución: pip install torch --index-url https://download.pytorch.org/whl/rocm6.2"
            json_warn "torch_cuda_fix" "Install PyTorch ROCm wheel"
        elif [ "$GPU_BACKEND" = "nvidia" ]; then
            log_warn "GPU NVIDIA detectada pero PyTorch no la ve"
            json_warn "torch_cuda_fix" "Reinstall PyTorch with CUDA support"
        fi

        TORCH_VERSION_STR=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null || echo "unknown")
        if echo "$TORCH_VERSION_STR" | grep -q "rocm"; then
            log_info "PyTorch tiene ROCm support pero no detecta GPU — probablemente permisos"
            json_warn "torch_rocm_no_gpu" "PyTorch has ROCm but GPU not detected (permissions?)"
        elif echo "$TORCH_VERSION_STR" | grep -q "cu"; then
            log_info "PyTorch es rueda CUDA — sistema AMD necesita rueda ROCm"
            json_warn "torch_cuda_wheel" "PyTorch is CUDA wheel, AMD needs ROCm wheel"
        fi
    fi
else
    log_warn "PyTorch no instalado"
    json_warn "pytorch" "PyTorch not installed"
fi

# ═══════════════════════════════════════════════════════════
# 8. vLLM
# ═══════════════════════════════════════════════════════════
log_header "vLLM"

# Python version
PYTHON_VER=$(python3 --version 2>/dev/null || echo "no python3")
log_info "Python: ${PYTHON_VER}"
json_add "python_version" "$PYTHON_VER" "vllm"

if pip3 list 2>/dev/null | grep -qi vllm; then
    VLLM_VER=$(pip3 list 2>/dev/null | grep -i vllm | awk '{print $1, $2}')
    log_ok "vLLM instalado: ${VLLM_VER}"
    json_add "vllm_installed" "$VLLM_VER" "vllm"

    # Check Python 3.12 for ROCm
    if echo "$PYTHON_VER" | grep -q "3\\.12"; then
        log_ok "Python 3.12 OK para vLLM ROCm"
        json_add "vllm_python_ok" "true" "vllm"
    else
        if [ "$GPU_BACKEND" = "rocm" ]; then
            log_warn "Python NO es 3.12 — vLLM ROCm requiere Python 3.12"
            json_warn "vllm_python" "Python not 3.12 (required for vLLM ROCm)"
        fi
    fi

    # Check if ROCm or CUDA wheel
    if pip3 list 2>/dev/null | grep -i vllm | grep -qi rocm; then
        log_ok "vLLM wheel: ROCm"
        json_add "vllm_wheel" "rocm" "vllm"
    elif pip3 list 2>/dev/null | grep -i vllm | grep -qi cuda; then
        log_info "vLLM wheel: CUDA"
        json_add "vllm_wheel" "cuda" "vllm"
    else
        log_info "vLLM wheel: genérica"
        json_add "vllm_wheel" "generic" "vllm"
    fi
else
    log_info "vLLM no instalado"
    json_add "vllm_installed" "false" "vllm"
fi

# ═══════════════════════════════════════════════════════════
# 9. ENVIRONMENT VARIABLES
# ═══════════════════════════════════════════════════════════
log_header "Environment Variables"

ENV_VARS_SET=0

if [ -n "${HIP_VISIBLE_DEVICES:-}" ]; then
    log_ok "HIP_VISIBLE_DEVICES = ${HIP_VISIBLE_DEVICES}"
    json_add "HIP_VISIBLE_DEVICES" "$HIP_VISIBLE_DEVICES" "env"
    ENV_VARS_SET=$((ENV_VARS_SET + 1))
fi

if [ -n "${ROCR_VISIBLE_DEVICES:-}" ]; then
    log_ok "ROCR_VISIBLE_DEVICES = ${ROCR_VISIBLE_DEVICES}"
    json_add "ROCR_VISIBLE_DEVICES" "$ROCR_VISIBLE_DEVICES" "env"
    ENV_VARS_SET=$((ENV_VARS_SET + 1))
fi

if [ -n "${CUDA_VISIBLE_DEVICES:-}" ]; then
    log_ok "CUDA_VISIBLE_DEVICES = ${CUDA_VISIBLE_DEVICES}"
    json_add "CUDA_VISIBLE_DEVICES" "$CUDA_VISIBLE_DEVICES" "env"
    ENV_VARS_SET=$((ENV_VARS_SET + 1))
fi

if [ -n "${HSA_OVERRIDE_GFX_VERSION:-}" ]; then
    log_warn "HSA_OVERRIDE_GFX_VERSION = ${HSA_OVERRIDE_GFX_VERSION} (override activo)"
    json_warn "HSA_OVERRIDE_GFX_VERSION" "Override active: ${HSA_OVERRIDE_GFX_VERSION}"

    # Validate override
    if [ -n "$GPU_GFX" ]; then
        GFX_NUM=$(echo "$GPU_GFX" | grep -oP 'gfx(\d+)' | head -1 | grep -oP '\d+')
        OVERRIDE_MAJOR=$(echo "${HSA_OVERRIDE_GFX_VERSION}" | cut -d. -f1)
        if [ -n "$GFX_NUM" ] && [ -n "$OVERRIDE_MAJOR" ]; then
            EXPECTED_MAJOR=$((GFX_NUM / 100))
            if [ "$OVERRIDE_MAJOR" -ne "$EXPECTED_MAJOR" ]; then
                log_warn "  ⚠ Posible mismatch: GPU gfx${GFX_NUM} → override major ${OVERRIDE_MAJOR}, esperado ~${EXPECTED_MAJOR}"
                json_warn "hsa_override_mismatch" "Override ${HSA_OVERRIDE_GFX_VERSION} may not match GPU gfx${GFX_NUM}"
            fi
        fi
    fi
fi

if [ -n "${ROCM_PATH:-}" ]; then
    log_ok "ROCM_PATH = ${ROCM_PATH}"
    json_add "ROCM_PATH" "$ROCM_PATH" "env"
fi

if [ -n "${ROCM_HOME:-}" ]; then
    log_ok "ROCM_HOME = ${ROCM_HOME}"
    json_add "ROCM_HOME" "$ROCM_HOME" "env"
fi

if [ -n "${HIPBLAS_WORKSPACE_CONFIG:-}" ]; then
    log_ok "HIPBLAS_WORKSPACE_CONFIG = ${HIPBLAS_WORKSPACE_CONFIG}"
    json_add "HIPBLAS_WORKSPACE_CONFIG" "$HIPBLAS_WORKSPACE_CONFIG" "env"
fi

if [ "$ENV_VARS_SET" -eq 0 ] && $GPU_FOUND; then
    log_info "No GPU visibility variables set (todas las GPUs serán usadas)"
    json_add "gpu_visibility_vars" "none" "env"
fi

# ═══════════════════════════════════════════════════════════
# 10. USER GROUPS
# ═══════════════════════════════════════════════════════════
log_header "User Groups"

CURRENT_USER=${USER:-$(whoami)}
USER_GROUPS=$(groups "$CURRENT_USER" 2>/dev/null || true)

for g in video render lp; do
    if echo "$USER_GROUPS" | grep -q "\b${g}\b"; then
        [ "$g" != "lp" ] && log_ok "Usuario en grupo '${g}'"
        json_add "group_${g}" "yes" "gpu"
    else
        if [ "$g" = "render" ]; then
            log_warn "Usuario NO en grupo '${g}' (GPU AMD puede no funcionar)"
            json_warn "group_${g}" "User not in ${g} group"
        fi
    fi
done

# ═══════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════
log_header "Summary"

[ "$MODE" != "--json" ] && [ "$MODE" != "--quiet" ] && echo ""
if [ "$EXIT" -eq 0 ]; then
    [ "$MODE" != "--json" ] && echo -e "  ${PASS} All checks passed — sistema ROCm OK"
elif [ "$EXIT" -eq 1 ]; then
    [ "$MODE" != "--json" ] && echo -e "  ${WARN} Completed with warnings — revisar puntos marcados"
else
    [ "$MODE" != "--json" ] && echo -e "  ${FAIL} Errors detected — corrigir problemas señalados"
fi

# ── JSON Output ────────────────────────────────────────────
if [ "$MODE" = "--json" ]; then
    REPORT_JSON=$(echo "$REPORT_JSON" | python3 -c "
import sys, json, time
r = json.load(sys.stdin)
r['exit_code'] = $EXIT
r['timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
r['host'] = '$(hostname 2>/dev/null)'
print(json.dumps(r, indent=2, ensure_ascii=False))
" 2>/dev/null || echo "$REPORT_JSON")
    echo "$REPORT_JSON"
fi

exit $EXIT
