#!/bin/bash
#===============================================================================
# AMD ROCm — Entrypoint con Detección Automática de Backend GPU
#===============================================================================
# Este script detecta automáticamente el backend GPU disponible dentro del
# contenedor y exporta BACKEND=cuda|rocm|cpu como variable de entorno.
#
# Orden de detección:
#   1. nvidia-smi → BACKEND=cuda (NVIDIA CUDA)
#   2. rocm-smi o /dev/kfd → BACKEND=rocm (AMD ROCm)
#   3. /dev/dri/render* (fallback sin rocm-smi) → BACKEND=rocm
#   4. Nada detectado → BACKEND=cpu
#
# Uso en Dockerfile:
#   COPY scripts/entrypoint.sh /entrypoint.sh
#   RUN chmod +x /entrypoint.sh
#   ENTRYPOINT ["/entrypoint.sh"]
#   CMD ["python", "run.py"]
#
# También se puede forzar un backend específico con:
#   docker run -e BACKEND=cuda ...
#   docker run -e BACKEND=rocm ...
#   docker run -e BACKEND=cpu ...
#===============================================================================

set -e

# ── Forzar backend desde variable de entorno ──────────────────────────────────
if [ -n "$BACKEND" ] && [ "$BACKEND" != "auto" ]; then
    case "$BACKEND" in
        cuda|rocm|cpu)
            echo "[AMD ROCm] Backend forzado: $BACKEND" >&2
            export BACKEND
            exec "$@"
            ;;
        *)
            echo "[AMD ROCm] ⚠️  BACKEND desconocido: '$BACKEND'. Procediendo con auto-detección." >&2
            ;;
    esac
fi

# ── Banner ────────────────────────────────────────────────────────────────────
echo "[AMD ROCm] ╔═══════════════════════════════════════════╗" >&2
echo "[AMD ROCm] ║   AMD ROCm — GPU Backend Detection          ║" >&2
echo "[AMD ROCm] ╚═══════════════════════════════════════════╝" >&2
echo "" >&2

# ── Nivel 1: Detectar NVIDIA CUDA ─────────────────────────────────────────────
echo "[AMD ROCm] 🔍 Detectando NVIDIA CUDA..." >&2

if command -v nvidia-smi &> /dev/null; then
    NVIDIA_OUTPUT=$(nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>/dev/null | head -3)
    NVIDIA_COUNT=$(echo "$NVIDIA_OUTPUT" | grep -c . 2>/dev/null || echo 0)

    if [ "$NVIDIA_COUNT" -gt 0 ]; then
        NVIDIA_NAME=$(echo "$NVIDIA_OUTPUT" | head -1 | cut -d, -f1 | xargs)
        NVIDIA_DRIVER=$(echo "$NVIDIA_OUTPUT" | head -1 | cut -d, -f2 | xargs)
        echo "[AMD ROCm] ✅ NVIDIA CUDA detectado: $NVIDIA_COUNT GPU(s) — $NVIDIA_NAME" >&2
        echo "[AMD ROCm]    Driver: $NVIDIA_DRIVER" >&2
        export BACKEND=cuda
        export NVIDIA_VISIBLE_DEVICES=${NVIDIA_VISIBLE_DEVICES:-all}
        export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}
        echo "[AMD ROCm] ✅ Backend configurado: BACKEND=$BACKEND" >&2
        exec "$@"
    else
        echo "[AMD ROCm] ⚠️  nvidia-smi encontrado pero sin GPUs detectadas" >&2
    fi
else
    echo "[AMD ROCm]    nvidia-smi no disponible" >&2
fi

# ── Nivel 2: Detectar AMD ROCm vía rocm-smi ──────────────────────────────────
echo "[AMD ROCm] 🔍 Detectando AMD ROCm..." >&2

ROCM_DETECTED=false

if command -v rocm-smi &> /dev/null; then
    ROCM_OUTPUT=$(rocm-smi --showproductname --json 2>/dev/null || echo "{}")
    ROCM_CARD_COUNT=$(echo "$ROCM_OUTPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    cards = [k for k in data if k.startswith('card')]
    print(len(cards))
except:
    print(0)
" 2>/dev/null || echo 0)

    if [ "$ROCM_CARD_COUNT" -gt 0 ]; then
        echo "[AMD ROCm] ✅ AMD ROCm detectado vía rocm-smi: $ROCM_CARD_COUNT GPU(s)" >&2
        ROCM_DETECTED=true
    else
        echo "[AMD ROCm] ⚠️  rocm-smi disponible pero sin GPUs reportadas" >&2
    fi
else
    echo "[AMD ROCm]    rocm-smi no disponible" >&2
fi

# ── Nivel 3: Detectar AMD ROCm vía dispositivos ──────────────────────────────
if ! $ROCM_DETECTED; then
    if [ -e /dev/kfd ]; then
        echo "[AMD ROCm] ✅ /dev/kfd presente — posible GPU AMD" >&2
        ROCM_DETECTED=true
    fi

    if ls /dev/dri/render* &> /dev/null 2>&1; then
        RENDER_COUNT=$(ls /dev/dri/render* 2>/dev/null | wc -l)
        echo "[AMD ROCm] ✅ /dev/dri/render* presente ($RENDER_COUNT nodos) — posible GPU AMD" >&2
        ROCM_DETECTED=true
    fi

    # Verificación adicional con rocminfo si está disponible
    if command -v rocminfo &> /dev/null; then
        ROCMINFO_GFX=$(rocminfo 2>/dev/null | grep -i 'gfx[0-9]' | head -1 | xargs || echo "")
        if [ -n "$ROCMINFO_GFX" ]; then
            echo "[AMD ROCm] ✅ rocminfo: arquitectura $ROCMINFO_GFX detectada" >&2
            ROCM_DETECTED=true
        fi
    fi
fi

# ── Si ROCm fue detectado, configurar ─────────────────────────────────────────
if $ROCM_DETECTED; then
    export BACKEND=rocm
    export ROCM_HOME=${ROCM_HOME:-/opt/rocm}
    export HIP_VISIBLE_DEVICES=${HIP_VISIBLE_DEVICES:-0}
    export ROCR_VISIBLE_DEVICES=${ROCR_VISIBLE_DEVICES:-0}

    echo "[AMD ROCm] ✅ Backend configurado: BACKEND=$BACKEND" >&2
    exec "$@"
fi

# ── Nivel 4: Fallback CPU ─────────────────────────────────────────────────────
echo "[AMD ROCm] ⚠️  No se detectó GPU — usando CPU fallback" >&2
export BACKEND=cpu

# Configurar optimal CPU threading
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-$(nproc 2>/dev/null || echo 4)}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-$OMP_NUM_THREADS}

echo "[AMD ROCm]    OMP_NUM_THREADS=$OMP_NUM_THREADS" >&2
echo "[AMD ROCm] ✅ Backend configurado: BACKEND=$BACKEND" >&2

exec "$@"
