#!/bin/bash
# ============================================================
# quick-fix.sh — ROCm Quick Fix Script
#
# Soluciones rápidas para problemas comunes de ROCm.
# Sin -y: solo muestra lo que haría (dry-run)
# Con -y: ejecuta los cambios
#
# Usage:
#   bash quick-fix.sh --fix-kfd              # Dry-run: muestra qué haría
#   bash quick-fix.sh --fix-kfd -y           # Ejecuta
#   bash quick-fix.sh --fix-groups           # Dry-run
#   bash quick-fix.sh --fix-groups -y        # Ejecuta
#   bash quick-fix.sh --fix-hip-version      # Verifica match
#   bash quick-fix.sh --fix-docker           # Dry-run
#   bash quick-fix.sh --fix-docker -y        # Ejecuta
#   bash quick-fix.sh --all                  # Dry-run para todos
#   bash quick-fix.sh --all -y               # Ejecuta todos
# ============================================================

set -euo pipefail

# ── Config ──────────────────────────────────────────────────
EXECUTE=false
DO_KFD=false
DO_GROUPS=false
DO_HIP=false
DO_DOCKER=false

# ── Colors ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
INFO="${CYAN}ℹ️${NC}"
WARN="${YELLOW}⚠️${NC}"
PASS="${GREEN}✅${NC}"
FAIL="${RED}❌${NC}"

# ── Parse args ──────────────────────────────────────────────
while [ $# -gt 0 ]; do
    case "$1" in
        -y|--yes|--execute)
            EXECUTE=true
            shift
            ;;
        --fix-kfd)
            DO_KFD=true
            shift
            ;;
        --fix-groups)
            DO_GROUPS=true
            shift
            ;;
        --fix-hip-version)
            DO_HIP=true
            shift
            ;;
        --fix-docker)
            DO_DOCKER=true
            shift
            ;;
        --all)
            DO_KFD=true
            DO_GROUPS=true
            DO_HIP=true
            DO_DOCKER=true
            shift
            ;;
        -h|--help)
            echo "Usage: bash quick-fix.sh [FLAGS] [-y]"
            echo ""
            echo "Flags:"
            echo "  --fix-kfd             Reinstalar udev rules para /dev/kfd"
            echo "  --fix-groups          Agregar usuario a grupos video/render"
            echo "  --fix-hip-version     Verificar match ROCm vs PyTorch"
            echo "  --fix-docker          Reinstalar configuración ROCm Docker"
            echo "  --all                 Ejecutar todos los fixes"
            echo "  -y, --execute         Ejecutar cambios (sin -y: dry-run)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: bash quick-fix.sh [--fix-kfd|--fix-groups|--fix-hip-version|--fix-docker|--all] [-y]"
            exit 1
            ;;
    esac
done

if ! $DO_KFD && ! $DO_GROUPS && ! $DO_HIP && ! $DO_DOCKER; then
    echo "No fix specified. Usage: bash quick-fix.sh [--fix-kfd|--fix-groups|--fix-hip-version|--fix-docker|--all] [-y]"
    exit 1
fi

# ── Helper ──────────────────────────────────────────────────
action() {
    local desc="$1" cmd="$2"
    if $EXECUTE; then
        echo -e "  ${INFO} $desc"
        echo "    $ ${cmd}"
        if eval "$cmd"; then
            echo -e "  ${PASS} Done"
        else
            echo -e "  ${FAIL} Failed: $cmd"
            return 1
        fi
    else
        echo -e "  ${INFO} [DRY-RUN] $desc"
        echo "    Would execute: ${cmd}"
    fi
}

warn() { echo -e "  ${WARN} $1"; }
ok()   { echo -e "  ${PASS} $1"; }
info() { echo -e "  ${INFO} $1"; }

# ═══════════════════════════════════════════════════════════
# Banner
# ═══════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════╗"
echo "║    ROCm Quick Fix — AMD ROCm Troubleshoot   ║"
if $EXECUTE; then
    echo "║    Mode: EXECUTE (-y)                    ║"
else
    echo "║    Mode: DRY-RUN (add -y to execute)     ║"
fi
echo "╚══════════════════════════════════════════╝"
echo ""

# ═══════════════════════════════════════════════════════════
# FIX: /dev/kfd udev rules
# ═══════════════════════════════════════════════════════════
if $DO_KFD; then
    echo "─── Fix: /dev/kfd udev Rules ───"

    if [ -e /dev/kfd ]; then
        ok "/dev/kfd ya existe"
    else
        warn "/dev/kfd no existe — cargando módulo amdgpu"
        action "Cargar módulo amdgpu" "sudo modprobe amdgpu"
    fi

    # Check udev rule
    UDEV_FILE="/etc/udev/rules.d/99-rocm.rules"
    if [ -f "$UDEV_FILE" ]; then
        ok "udev rule ya existe: ${UDEV_FILE}"
        info "Contenido: $(cat "$UDEV_FILE")"
    else
        warn "udev rule no encontrada — creando"
        action "Crear udev rule para /dev/kfd" \
            "echo 'KERNEL==\"kfd\", MODE=\"0666\", GROUP=\"render\"' | sudo tee $UDEV_FILE"
        action "Recargar udev rules" "sudo udevadm control --reload-rules && sudo udevadm trigger"
    fi

    # Check render group permissions for /dev/dri
    DRI_RENDER=$(ls /dev/dri/render* 2>/dev/null | head -1)
    if [ -n "$DRI_RENDER" ]; then
        RENDER_GROUP=$(stat -c "%G" "$DRI_RENDER" 2>/dev/null || echo "unknown")
        if [ "$RENDER_GROUP" != "render" ]; then
            warn "/dev/dri/render* no pertenece al grupo render (grupo: ${RENDER_GROUP})"
            action "Fix permisos /dev/dri/render*" \
                "sudo chgrp render /dev/dri/render* && sudo chmod 660 /dev/dri/render*"
        else
            ok "/dev/dri/render* pertenece al grupo render"
        fi
    fi

    echo ""
fi

# ═══════════════════════════════════════════════════════════
# FIX: User groups
# ═══════════════════════════════════════════════════════════
if $DO_GROUPS; then
    echo "─── Fix: User Groups ───"

    CURRENT_USER=${USER:-$(whoami)}
    info "Usuario actual: ${CURRENT_USER}"
    info "Grupos actuales: $(groups "$CURRENT_USER" 2>/dev/null || echo "N/A")"

    for g in video render; do
        if groups "$CURRENT_USER" 2>/dev/null | grep -q "\b${g}\b"; then
            ok "Usuario ya está en grupo '${g}'"
        else
            warn "Usuario NO está en grupo '${g}'"
            action "Agregar usuario a grupo '${g}'" "sudo usermod -a -G ${g} ${CURRENT_USER}"
        fi
    done

    if ! $EXECUTE; then
        warn "Los cambios de grupo requieren cerrar sesión y volver a entrar"
        info "  O ejecuta: newgrp video && newgrp render"
    else
        info "NOTA: Los grupos se actualizarán en el próximo inicio de sesión"
        info "  Para aplicar ahora: newgrp video && newgrp render"
    fi

    # Check if /etc/group has correct permissions
    GROUPS_AFTER=$(groups "$CURRENT_USER" 2>/dev/null || true)
    info "Grupos después del cambio: ${GROUPS_AFTER}"

    echo ""
fi

# ═══════════════════════════════════════════════════════════
# FIX: HIP/PyTorch version match
# ═══════════════════════════════════════════════════════════
if $DO_HIP; then
    echo "─── Fix: HIP/PyTorch Version Match ───"

    # Get ROCm version
    ROCM_VER=""
    if [ -f /opt/rocm/share/doc/rocm-version/version ]; then
        ROCM_VER=$(cat /opt/rocm/share/doc/rocm-version/version)
        ok "ROCm instalado: ${ROCM_VER}"
    elif command -v rocminfo &>/dev/null; then
        ROCM_VER=$(rocminfo 2>/dev/null | grep -i "rocminfo" | head -1 | grep -oP '\d+\.\d+\.\d+' || echo "unknown")
        ok "ROCm (rocminfo): ${ROCM_VER}"
    else
        warn "No se pudo determinar versión ROCm"
    fi

    # Get HIP version from torch
    if python3 -c "import torch; print(torch.__version__)" &>/dev/null; then
        TORCH_VER=$(python3 -c "import torch; print(torch.__version__)")
        HIP_VER=$(python3 -c "import torch; v=getattr(torch.version,'hip',None); print(v or 'none')" 2>/dev/null || echo "none")
        CUDA_VER=$(python3 -c "import torch; v=getattr(torch.version,'cuda',None); print(v or 'none')" 2>/dev/null || echo "none")

        ok "PyTorch: ${TORCH_VER}"
        info "  HIP: ${HIP_VER}"
        info "  CUDA: ${CUDA_VER}"

        if echo "$TORCH_VER" | grep -q "rocm"; then
            TORCH_ROCM_VER=$(echo "$TORCH_VER" | grep -oP 'rocm\d+\.\d+' || echo "")
            if [ -n "$TORCH_ROCM_VER" ] && [ -n "$ROCM_VER" ]; then
                ROCM_MAJOR=$(echo "$ROCM_VER" | cut -d. -f1)
                TORCH_ROCM_NUM=$(echo "$TORCH_ROCM_VER" | grep -oP '\d+\.\d+')
                TORCH_ROCM_MAJOR=$(echo "$TORCH_ROCM_NUM" | cut -d. -f1)
                if [ "$ROCM_MAJOR" = "$TORCH_ROCM_MAJOR" ] || \
                   [ "$((ROCM_MAJOR - 1))" = "$TORCH_ROCM_MAJOR" ]; then
                    ok "✅ ROCm (${ROCM_VER}) y PyTorch (${TORCH_ROCM_VER}) compatibles"
                else
                    warn "⚠️ ROCm v${ROCM_VER} y PyTorch ${TORCH_ROCM_VER} pueden ser incompatibles"
                    warn "  Ver tabla de compatibilidad en SKILL.md"
                    if ! $EXECUTE; then
                        info "  Para instalar versión correcta:"
                        info "    pip install torch --index-url https://download.pytorch.org/whl/rocm6.2"
                    fi
                fi
            fi
        else
            warn "PyTorch NO es rueda ROCm (probablemente CUDA: ${CUDA_VER})"
            if ! $EXECUTE; then
                info "  Para instalar rueda ROCm:"
                info "    pip uninstall torch torchvision torchaudio -y"
                info "    pip install torch --index-url https://download.pytorch.org/whl/rocm6.2"
            fi
        fi
    else
        warn "PyTorch no está instalado"
        if ! $EXECUTE; then
            info "  Para instalar PyTorch ROCm:"
            info "    pip install torch --index-url https://download.pytorch.org/whl/rocm6.2"
        fi
    fi

    echo ""
fi

# ═══════════════════════════════════════════════════════════
# FIX: Docker ROCm
# ═══════════════════════════════════════════════════════════
if $DO_DOCKER; then
    echo "─── Fix: Docker ROCm Configuration ───"

    if command -v docker &>/dev/null; then
        ok "Docker instalado: $(docker --version 2>/dev/null)"
    else
        warn "Docker no está instalado"
        if ! $EXECUTE; then
            info "  Instalar Docker: https://docs.docker.com/engine/install/ubuntu/"
        fi
    fi

    # Check docker group
    CURRENT_USER=${USER:-$(whoami)}
    if groups "$CURRENT_USER" 2>/dev/null | grep -q "\bdocker\b"; then
        ok "Usuario en grupo docker"
    else
        warn "Usuario NO en grupo docker"
        action "Agregar a grupo docker" "sudo usermod -a -G docker ${CURRENT_USER}"
    fi

    # Check NVIDIA container toolkit
    if command -v nvidia-smi &>/dev/null; then
        if docker info 2>/dev/null | grep -q "nvidia"; then
            ok "NVIDIA Container Toolkit configurado"
        else
            warn "NVIDIA Container Toolkit no configurado"
            if $EXECUTE; then
                info "  Instalando NVIDIA Container Toolkit..."
                action "Instalar nvidia-container-toolkit" "sudo apt-get install -y nvidia-container-toolkit"
                action "Configurar runtime" "sudo nvidia-ctk runtime configure --runtime=docker"
                action "Reiniciar Docker" "sudo systemctl restart docker"
            else
                info "  Para instalar: sudo apt-get install -y nvidia-container-toolkit"
                info "  Luego: sudo nvidia-ctk runtime configure --runtime=docker"
                info "  Luego: sudo systemctl restart docker"
            fi
        fi
    fi

    # Test AMD Docker
    if [ -e /dev/kfd ] && [ -d /dev/dri ]; then
        info "Probando Docker ROCm..."
        if docker run --rm --device=/dev/kfd --device=/dev/dri --group-add=video \
            rocm/dev-ubuntu-22.04:latest ls /dev/kfd &>/tmp/rocm-quick-docker-test.log; then
            ok "Docker ROCm test: OK"
        else
            warn "Docker ROCm test: FAILED"
            info "  Verificar: /dev/kfd existe? Permisos? amdgpu module cargado?"
            if ! $EXECUTE; then
                info "  Comando de prueba:"
                info "    docker run --rm --device=/dev/kfd --device=/dev/dri --group-add=video rocm/dev-ubuntu-22.04:latest rocminfo"
            fi
        fi
    else
        info "Saltando test Docker ROCm (no hay dispositivos AMD)"
    fi

    echo ""
fi

# ── Final ───────────────────────────────────────────────────
echo "══════════════════════════════════════════"
if $EXECUTE; then
    echo -e "  ${PASS} Quick fixes ejecutados"
else
    echo -e "  ${WARN} Dry-run completado. Ejecuta con -y para aplicar cambios."
fi
echo "══════════════════════════════════════════"
