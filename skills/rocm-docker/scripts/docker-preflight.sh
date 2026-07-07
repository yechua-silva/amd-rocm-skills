#!/bin/bash
#===============================================================================
# Docker GPU Preflight Check — Multi-Backend (AMD ROCm + NVIDIA CUDA)
#===============================================================================
# Usage:
#   bash docker-preflight.sh          # Reporte legible
#   bash docker-preflight.sh --json   # Salida JSON parseable
#   bash docker-preflight.sh --quiet  # Solo exit code
#
# Exit codes:
#   0 = Todo OK — GPU(s) detectada(s) y funcionando
#   1 = Warnings — GPU detectada pero con advertencias
#   2 = Errors — No se pudo verificar GPU o Docker no disponible
#===============================================================================

set -e

# ── Config ────────────────────────────────────────────────────────────────────
MODE="${1:-normal}"  # normal, --json, --quiet
EXIT_CODE=0
REPORT_JSON='{"status":"ok","checks":[],"warnings":[],"errors":[],"backends":{}}'

# ── Helpers ───────────────────────────────────────────────────────────────────

log_info()    { [ "$MODE" != "--json" ] && echo -e "  $1"; }
log_ok()      { [ "$MODE" != "--json" ] && echo -e "  ✅ $1"; }
log_warn()    { [ "$MODE" != "--json" ] && echo -e "  ⚠️  $1"; EXIT_CODE=1; }
log_error()   { [ "$MODE" != "--json" ] && echo -e "  ❌ $1"; EXIT_CODE=2; }
log_header()  { [ "$MODE" != "--json" ] && echo -e "\n─── $1 ───"; }

json_add_check() {
    local status="$1" name="$2" message="$3"
    REPORT_JSON=$(echo "$REPORT_JSON" | python3 -c "
import sys, json
report = json.load(sys.stdin)
report['checks'].append({'status': '$status', 'name': '$name', 'message': '$message'})
if '$status' == 'error': report['status'] = 'error'
elif '$status' == 'warning' and report['status'] != 'error': report['status'] = 'warning'
print(json.dumps(report))
" 2>/dev/null || echo "$REPORT_JSON")
}

json_set_backend() {
    local backend="$1" key="$2" value="$3"
    REPORT_JSON=$(echo "$REPORT_JSON" | python3 -c "
import sys, json
report = json.load(sys.stdin)
if '$backend' not in report['backends']:
    report['backends']['$backend'] = {}
report['backends']['$backend']['$key'] = '$value'
print(json.dumps(report))
" 2>/dev/null || echo "$REPORT_JSON")
}

json_add_error() {
    REPORT_JSON=$(echo "$REPORT_JSON" | python3 -c "
import sys, json
report = json.load(sys.stdin)
report['errors'].append('$1')
report['status'] = 'error'
print(json.dumps(report))
" 2>/dev/null || echo "$REPORT_JSON")
}

json_add_warning() {
    REPORT_JSON=$(echo "$REPORT_JSON" | python3 -c "
import sys, json
report = json.load(sys.stdin)
report['warnings'].append('$1')
if report['status'] != 'error': report['status'] = 'warning'
print(json.dumps(report))
" 2>/dev/null || echo "$REPORT_JSON")
}

# ── Main ──────────────────────────────────────────────────────────────────────

[ "$MODE" != "--json" ] && [ "$MODE" != "--quiet" ] && echo "
╔══════════════════════════════════════════════════════════╗
║     Munin — Docker GPU Preflight Check                  ║
║     AMD ROCm + NVIDIA CUDA + CPU fallback               ║
╚══════════════════════════════════════════════════════════╝
"

# ── 1. Docker Engine ──────────────────────────────────────────────────────────
log_header "Docker Engine"

DOCKER_OK=false
if command -v docker &> /dev/null; then
    DOCKER_VER=$(docker --version 2>/dev/null)
    log_ok "$DOCKER_VER"
    json_add_check "ok" "docker-engine" "$DOCKER_VER"
    DOCKER_OK=true
else
    log_error "Docker not found. Install Docker Engine first."
    json_add_error "Docker not found"
    DOCKER_OK=false
fi

# ── 2. Docker Compose ────────────────────────────────────────────────────────
log_header "Docker Compose"

if docker compose version &> /dev/null; then
    COMPOSE_VER=$(docker compose version 2>/dev/null)
    log_ok "$COMPOSE_VER"
    json_add_check "ok" "docker-compose" "$COMPOSE_VER"
else
    log_warn "Docker Compose v2 not found (docker compose). Install Docker Compose plugin."
    json_add_warning "Docker Compose v2 not found"
fi

# ── 3. User Groups ───────────────────────────────────────────────────────────
log_header "User Groups"

CURRENT_USER=${USER:-$(whoami)}

for g in video render; do
    if groups "$CURRENT_USER" 2>/dev/null | grep -q "\b$g\b"; then
        log_ok "User in '$g' group"
        json_add_check "ok" "group-$g" "User in $g group"
    else
        if [ "$g" = "render" ]; then
            log_warn "User NOT in '$g' group (AMD GPU access may be limited)"
            json_add_warning "User not in render group"
        else
            log_warn "User NOT in '$g' group (GPU access may be limited)"
            json_add_warning "User not in $g group"
        fi
    fi
done

# ── 4. NVIDIA Backend ────────────────────────────────────────────────────────
log_header "NVIDIA CUDA"

NVIDIA_FOUND=false
if command -v nvidia-smi &> /dev/null; then
    NVIDIA_OUTPUT=$(nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null | head -5)
    NVIDIA_COUNT=$(echo "$NVIDIA_OUTPUT" | grep -c . 2>/dev/null || echo 0)
    if [ "$NVIDIA_COUNT" -gt 0 ]; then
        NVIDIA_NAME=$(echo "$NVIDIA_OUTPUT" | head -1 | cut -d, -f1 | xargs)
        NVIDIA_DRIVER=$(echo "$NVIDIA_OUTPUT" | head -1 | cut -d, -f2 | xargs)
        log_ok "$NVIDIA_COUNT GPU(s) detectada(s): $NVIDIA_NAME"
        log_info "  Driver: $NVIDIA_DRIVER"
        json_set_backend "nvidia" "available" "true"
        json_set_backend "nvidia" "device_count" "$NVIDIA_COUNT"
        json_set_backend "nvidia" "device_name" "$NVIDIA_NAME"
        json_set_backend "nvidia" "driver_version" "$NVIDIA_DRIVER"
        json_add_check "ok" "nvidia-smi" "$NVIDIA_COUNT GPUs found: $NVIDIA_NAME"
        NVIDIA_FOUND=true
    else
        log_warn "nvidia-smi found but no GPUs reported"
        json_add_warning "nvidia-smi found but no GPUs"
    fi
elif [ -f /proc/driver/nvidia/version ] || lsmod 2>/dev/null | grep -q nvidia; then
    log_warn "NVIDIA driver module loaded but nvidia-smi not found"
    json_add_warning "NVIDIA driver loaded but nvidia-smi missing"
else
    log_info "No NVIDIA GPU detectada (no nvidia-smi, no driver)"
    json_set_backend "nvidia" "available" "false"
fi

# ── 5. AMD ROCm Backend ──────────────────────────────────────────────────────
log_header "AMD ROCm"

ROCM_FOUND=false

# 5a. Verificar dispositivos
KFD_EXISTS=false
DRI_EXISTS=false
[ -e /dev/kfd ] && KFD_EXISTS=true
[ -d /dev/dri ] && [ "$(ls -A /dev/dri/ 2>/dev/null)" ] && DRI_EXISTS=true

if $KFD_EXISTS; then
    log_ok "/dev/kfd exists"
    json_add_check "ok" "dev-kfd" "/dev/kfd exists"
else
    log_warn "/dev/kfd missing (ROCm kernel module not loaded)"
    json_add_warning "/dev/kfd missing"
fi

if $DRI_EXISTS; then
    RENDER_NODES=$(ls /dev/dri/render* 2>/dev/null | wc -l)
    log_ok "/dev/dri/ present ($RENDER_NODES render nodes)"
    json_add_check "ok" "dev-dri" "/dev/dri/ present with $RENDER_NODES render nodes"
else
    log_warn "/dev/dri/ missing"
    json_add_warning "/dev/dri/ missing"
fi

# 5b. Verificar rocm-smi
if command -v rocm-smi &> /dev/null; then
    ROCM_SMI_OUTPUT=$(rocm-smi --showproductname --json 2>/dev/null || echo "")
    if [ -n "$ROCM_SMI_OUTPUT" ]; then
        # Extraer número de GPUs del JSON
        ROCM_GPU_COUNT=$(echo "$ROCM_SMI_OUTPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    cards = [k for k in data if k.startswith('card')]
    print(len(cards))
except:
    print(0)
" 2>/dev/null || echo 0)
        if [ "$ROCM_GPU_COUNT" -gt 0 ]; then
            log_ok "rocm-smi: $ROCM_GPU_COUNT GPU(s) detectada(s)"
            json_set_backend "rocm" "available" "true"
            json_set_backend "rocm" "device_count" "$ROCM_GPU_COUNT"
            json_add_check "ok" "rocm-smi" "$ROCM_GPU_COUNT GPUs found via rocm-smi"
            ROCM_FOUND=true
        else
            log_warn "rocm-smi found but no GPUs detected"
            json_add_warning "rocm-smi found but no GPUs"
        fi
    else
        log_warn "rocm-smi available but no output"
        json_add_warning "rocm-smi no output"
    fi
else
    log_info "rocm-smi not found (ROCm tools may not be installed)"
    json_set_backend "rocm" "available" "false"
fi

# 5c. Verificar módulo amdgpu
if lsmod 2>/dev/null | grep -q amdgpu; then
    log_ok "Kernel module 'amdgpu' loaded"
    json_add_check "ok" "amdgpu-module" "amdgpu kernel module loaded"
else
    log_info "Kernel module 'amdgpu' not loaded (not an AMD system or driver not installed)"
fi

# 5d. Verificar arquitectura GFX via rocminfo
if command -v rocminfo &> /dev/null; then
    GFX_ARCH=$(rocminfo 2>/dev/null | grep -i 'gfx[0-9]' | head -1 | xargs || echo "")
    if [ -n "$GFX_ARCH" ]; then
        log_ok "Arquitectura GFX: $GFX_ARCH"
        json_set_backend "rocm" "gfx_arch" "$GFX_ARCH"
        json_add_check "ok" "gfx-arch" "GFX architecture: $GFX_ARCH"
    fi
fi

# ── 6. Test Container ────────────────────────────────────────────────────────
log_header "Docker GPU Test"

if $DOCKER_OK; then
    # 6a. Test NVIDIA
    if $NVIDIA_FOUND; then
        log_info "Testeando contenedor NVIDIA..."
        if docker run --rm --runtime nvidia --gpus all \
            nvidia/cuda:12.6.3-runtime-ubuntu22.04 \
            nvidia-smi --query-gpu=name --format=csv,noheader &> /tmp/munin-nvidia-test.log; then
            NVIDIA_TEST=$(cat /tmp/munin-nvidia-test.log | head -1)
            log_ok "Test NVIDIA OK: $NVIDIA_TEST"
            json_set_backend "nvidia" "container_test" "passed"
            json_add_check "ok" "nvidia-container-test" "NVIDIA container test passed: $NVIDIA_TEST"
        else
            log_error "Test NVIDIA FALLÓ. Log: /tmp/munin-nvidia-test.log"
            json_set_backend "nvidia" "container_test" "failed"
            json_add_error "NVIDIA container test failed"
        fi
    else
        log_info "Saltando test NVIDIA (no detectado)"
    fi

    # 6b. Test AMD ROCm
    if $ROCM_FOUND || $KFD_EXISTS; then
        log_info "Testeando contenedor AMD ROCm..."
        if docker run --rm --device=/dev/kfd --device=/dev/dri --group-add=video \
            rocm/dev-ubuntu-22.04:latest \
            rocminfo &> /tmp/munin-rocm-test.log; then
            ROCM_LINE=$(grep "Name:" /tmp/munin-rocm-test.log | head -1 | xargs || echo "GPU detectada")
            log_ok "Test ROCm OK: $ROCM_LINE"
            json_set_backend "rocm" "container_test" "passed"
            json_add_check "ok" "rocm-container-test" "ROCm container test passed"
        else
            log_error "Test ROCm FALLÓ. Log: /tmp/munin-rocm-test.log"
            json_set_backend "rocm" "container_test" "failed"
            json_add_error "ROCm container test failed"
        fi
    else
        log_info "Saltando test AMD (no detectado)"
    fi
else
    log_error "Docker no disponible — no se pueden ejecutar tests"
    json_add_error "Docker not available — cannot run container tests"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
log_header "Resumen"

if $NVIDIA_FOUND && $ROCM_FOUND; then
    log_ok "✅ Dual-backend: NVIDIA CUDA + AMD ROCm detectados y funcionando"
elif $NVIDIA_FOUND; then
    log_ok "✅ Backend NVIDIA CUDA detectado y funcionando"
elif $ROCM_FOUND; then
    log_ok "✅ Backend AMD ROCm detectado y funcionando"
elif $KFD_EXISTS || $DRI_EXISTS; then
    log_warn "⚠️  Dispositivos AMD detectados pero rocm-smi no disponible"
else
    log_warn "⚠️  No se detectó GPU — usando CPU fallback"
fi

if [ $EXIT_CODE -eq 0 ]; then
    [ "$MODE" != "--json" ] && [ "$MODE" != "--quiet" ] && echo -e "\n🎯 Todo OK — Docker listo para GPU workloads.\n"
elif [ $EXIT_CODE -eq 1 ]; then
    [ "$MODE" != "--json" ] && [ "$MODE" != "--quiet" ] && echo -e "\n⚠️  Completado con advertencias. Revisa los puntos marcados.\n"
else
    [ "$MODE" != "--json" ] && [ "$MODE" != "--quiet" ] && echo -e "\n❌ Errores encontrados. Corrige los problemas señalados.\n"
fi

# ── Salida JSON ───────────────────────────────────────────────────────────────
if [ "$MODE" = "--json" ]; then
    # Finalizar JSON con exit code y timestamp
    REPORT_JSON=$(echo "$REPORT_JSON" | python3 -c "
import sys, json, time
report = json.load(sys.stdin)
report['exit_code'] = $EXIT_CODE
report['timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
report['host'] = '$(hostname 2>/dev/null)'
print(json.dumps(report, indent=2))
" 2>/dev/null || echo "$REPORT_JSON")
    echo "$REPORT_JSON"
fi

exit $EXIT_CODE
