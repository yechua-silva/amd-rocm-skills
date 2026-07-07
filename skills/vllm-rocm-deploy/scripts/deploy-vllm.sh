#!/bin/bash
# ============================================================
# deploy-vllm.sh — Deploy vLLM Server with Auto Backend Detection
# ============================================================
# Soporta: AMD ROCm, NVIDIA CUDA, CPU fallback
# Detección automática del backend GPU disponible.
# 
# Uso:
#   ./deploy-vllm.sh                          # Auto-detect + defaults
#   ./deploy-vllm.sh --model Qwen/Qwen2-VL-7B-Instruct
#   ./deploy-vllm.sh --backend cuda --port 8080
#   ./deploy-vllm.sh --backend rocm --gpu-memory-utilization 0.95
#   ./deploy-vllm.sh --backend cpu
# ============================================================

set -euo pipefail

# ─── Configuración por defecto ───────────────────────────────
MODEL="OpenGVLab/InternVL2-8B"
PORT=8000
HOST="0.0.0.0"
BACKEND="auto"
GPU_MEMORY_UTILIZATION="0.90"
MAX_MODEL_LEN="4096"
TENSOR_PARALLEL_SIZE="1"
MAX_NUM_SEQS="256"
CONTAINER_NAME="vllm"
DETACH=true
CUSTOM_ARGS=""

# ─── Colores ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }
header(){ echo -e "\n${CYAN}━━━ $1 ━━━${NC}"; }

# ─── Parseo de argumentos ────────────────────────────────────
usage() {
    cat <<EOF
Uso: $0 [OPCIONES]

Opciones:
  --model <nombre>            Modelo a servir (default: $MODEL)
  --port <puerto>             Puerto del servidor (default: $PORT)
  --host <dirección>          Host a escuchar (default: $HOST)
  --backend <auto|cuda|rocm|cpu>  Forzar backend (default: auto-detect)
  --gpu-memory-utilization <0-1>   Uso de VRAM (default: $GPU_MEMORY_UTILIZATION)
  --max-model-len <int>       Longitud máxima de contexto (default: $MAX_MODEL_LEN)
  --tensor-parallel-size <int>    Número de GPUs para TP (default: auto)
  --max-num-seqs <int>        Máximo de secuencias simultáneas (default: $MAX_NUM_SEQS)
  --name <string>             Nombre del contenedor (default: $CONTAINER_NAME)
  --no-detach                 Ejecutar en primer plano
  --dry-run                   Solo mostrar comando sin ejecutar
  --help, -h                  Mostrar ayuda

Ejemplos:
  $0                                                      # Auto-detect
  $0 --model Qwen/Qwen2-VL-7B-Instruct --backend rocm    # Forzar ROCm
  $0 --backend cuda --tensor-parallel-size 2             # NVIDIA multi-GPU
  $0 --backend cpu --max-model-len 2048                  # CPU fallback
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)                  MODEL="$2"; shift 2 ;;
        --port)                   PORT="$2"; shift 2 ;;
        --host)                   HOST="$2"; shift 2 ;;
        --backend)                BACKEND="$2"; shift 2 ;;
        --gpu-memory-utilization) GPU_MEMORY_UTILIZATION="$2"; shift 2 ;;
        --max-model-len)          MAX_MODEL_LEN="$2"; shift 2 ;;
        --tensor-parallel-size)   TENSOR_PARALLEL_SIZE="$2"; shift 2 ;;
        --max-num-seqs)           MAX_NUM_SEQS="$2"; shift 2 ;;
        --name)                   CONTAINER_NAME="$2"; shift 2 ;;
        --no-detach)              DETACH=false; shift ;;
        --dry-run)                DRY_RUN=true; shift ;;
        --help|-h)                usage ;;
        *)
            # Argumento sin flag = modelo
            if [[ "$1" != --* ]]; then
                MODEL="$1"
                shift
            else
                err "Argumento desconocido: $1"
                usage
            fi
            ;;
    esac
done

# ─── Banner ──────────────────────────────────────────────────
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  vLLM Deploy — Server Setup${NC}"
echo -e "${CYAN}============================================${NC}"
echo "  Modelo:       $MODEL"
echo "  Puerto:       $PORT"
echo "  Backend:      $BACKEND (auto-detect si 'auto')"
echo ""

# ─── Función: Detectar backend ───────────────────────────────
detect_backend() {
    # Detectar NVIDIA CUDA
    if command -v nvidia-smi &> /dev/null; then
        local gpu_count
        gpu_count=$(nvidia-smi -L 2>/dev/null | wc -l)
        if [[ "$gpu_count" -gt 0 ]]; then
            echo "cuda"
            return 0
        fi
    fi

    # Detectar AMD ROCm
    if command -v rocminfo &> /dev/null; then
        local gfx_arch
        gfx_arch=$(rocminfo 2>/dev/null | grep -oP 'gfx\w+' | head -1)
        if [[ -n "$gfx_arch" ]]; then
            echo "rocm"
            return 0
        fi
    fi

    # Detectar por dispositivos (alternative para ROCm sin rocminfo)
    if [[ -e /dev/kfd ]] || ls /dev/dri/render* &> /dev/null 2>&1; then
        echo "rocm"
        return 0
    fi

    # Fallback CPU
    echo "cpu"
}

# ─── Función: Obtener número de GPUs ─────────────────────────
get_gpu_count() {
    local backend="$1"
    case "$backend" in
        cuda)
            if command -v nvidia-smi &> /dev/null; then
                nvidia-smi -L 2>/dev/null | wc -l
            else
                echo "1"
            fi
            ;;
        rocm)
            if command -v rocm-smi &> /dev/null; then
                rocm-smi --json 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    devices = data.get('list', [])
    if not devices:
        devices = [k for k in data.keys() if k.startswith('card')]
    print(len(devices))
except:
    print('1')
" 2>/dev/null || echo "1"
            else
                echo "1"
            fi
            ;;
        cpu)
            echo "0"
            ;;
    esac
}

# ─── Función: Obtener dtype recomendado ──────────────────────
get_dtype() {
    local backend="$1"
    case "$backend" in
        rocm) echo "float16" ;;
        cuda) echo "bfloat16" ;;
        cpu)  echo "float32" ;;
    esac
}

# ─── Función: Imagen Docker ──────────────────────────────────
get_docker_image() {
    local backend="$1"
    case "$backend" in
        rocm) echo "vllm/vllm-openai-rocm:latest" ;;
        cuda) echo "vllm/vllm-openai:latest" ;;
        cpu)  echo "vllm/vllm-openai:latest" ;;
    esac
}

# ─── Función: Docker run flags por backend ──────────────────
get_docker_flags() {
    local backend="$1"
    local gpu_count="$2"
    local flags=""

    case "$backend" in
        rocm)
            flags="--device=/dev/kfd --device=/dev/dri --group-add=render"
            flags+=" --cap-add=SYS_PTRACE --security-opt seccomp=unconfined"
            flags+=" -e HSA_OVERRIDE_GFX_VERSION=9.4.2"
            flags+=" -e HIPBLAS_WORKSPACE_CONFIG=:512:8"
            ;;
        cuda)
            flags="--runtime nvidia --gpus all"
            flags+=" -e NVIDIA_DRIVER_CAPABILITIES=compute,utility"
            ;;
        cpu)
            flags=""
            flags+=" -e OMP_NUM_THREADS=$(nproc)"
            flags+=" -e MKL_NUM_THREADS=$(nproc)"
            ;;
    esac

    echo "$flags"
}

# ─── Ejecutar detección ──────────────────────────────────────
header "Detectando Backend"

if [[ "$BACKEND" == "auto" ]]; then
    DETECTED_BACKEND=$(detect_backend)
    info "Backend detectado: ${DETECTED_BACKEND^^}"
else
    DETECTED_BACKEND="$BACKEND"
    info "Backend forzado: ${DETECTED_BACKEND^^}"
fi

# Validar backend
case "$DETECTED_BACKEND" in
    cuda|rocm|cpu) ;;
    *)
        err "Backend inválido: $DETECTED_BACKEND (opciones: cuda, rocm, cpu)"
        exit 1
        ;;
esac

# Obtener número de GPUs
GPU_COUNT=$(get_gpu_count "$DETECTED_BACKEND")
if [[ "$DETECTED_BACKEND" != "cpu" ]]; then
    info "GPUs detectadas: $GPU_COUNT"
    # Ajustar tensor_parallel_size automáticamente si no se especificó
    if [[ "$TENSOR_PARALLEL_SIZE" == "1" && "$GPU_COUNT" -gt 1 ]]; then
        TENSOR_PARALLEL_SIZE="$GPU_COUNT"
        info "Tensor parallel size ajustado a: $TENSOR_PARALLEL_SIZE"
    fi
fi

# Obtener dtype
DTYPE=$(get_dtype "$DETECTED_BACKEND")
info "dtype recomendado: $DTYPE"

# Obtener imagen Docker
DOCKER_IMAGE=$(get_docker_image "$DETECTED_BACKEND")
info "Imagen Docker: $DOCKER_IMAGE"

# Obtener flags Docker
DOCKER_FLAGS=$(get_docker_flags "$DETECTED_BACKEND" "$GPU_COUNT")

# ─── Verificar Docker ────────────────────────────────────────
header "Verificando Docker"

if ! command -v docker &> /dev/null; then
    err "Docker no encontrado. Instala Docker primero."
    exit 1
fi
ok "Docker instalado"

# Probar permisos Docker
if ! docker info &> /dev/null; then
    err "No tienes permisos para ejecutar Docker. Agrega tu usuario al grupo docker: sudo usermod -aG docker \$USER"
    exit 1
fi
ok "Permisos Docker OK"

# Detener contenedor existente
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    warn "Contenedor '$CONTAINER_NAME' ya existe. Deteniendo y eliminando..."
    docker stop "$CONTAINER_NAME" &> /dev/null || true
    docker rm "$CONTAINER_NAME" &> /dev/null || true
fi

# ─── Construir comando Docker ────────────────────────────────
header "Comando de Despliegue"

# Flags comunes
CMD_FLAGS="-d"
$DETACH || CMD_FLAGS="--rm"

DOCKER_CMD="docker run ${CMD_FLAGS} --name ${CONTAINER_NAME}"
DOCKER_CMD+=" ${DOCKER_FLAGS}"
DOCKER_CMD+=" -p ${HOST}:${PORT}:8000"
DOCKER_CMD+=" -v ~/.cache/huggingface:/root/.cache/huggingface"
DOCKER_CMD+=" --shm-size 16g"
DOCKER_CMD+=" ${DOCKER_IMAGE}"

# Argumentos vLLM
VLLM_ARGS=""
VLLM_ARGS+=" --model ${MODEL}"
VLLM_ARGS+=" --dtype ${DTYPE}"
VLLM_ARGS+=" --max-model-len ${MAX_MODEL_LEN}"
VLLM_ARGS+=" --gpu-memory-utilization ${GPU_MEMORY_UTILIZATION}"
VLLM_ARGS+=" --max-num-seqs ${MAX_NUM_SEQS}"

if [[ "$DETECTED_BACKEND" == "cpu" ]]; then
    VLLM_ARGS+=" --device cpu"
    VLLM_ARGS+=" --enforce-eager"
    VLLM_ARGS+=" --gpu-memory-utilization 0"
fi

if [[ "$DETECTED_BACKEND" == "cuda" ]]; then
    VLLM_ARGS+=" --enable-flash-attention"
fi

# Tensor parallelism (solo GPU)
if [[ "$DETECTED_BACKEND" != "cpu" && "$TENSOR_PARALLEL_SIZE" -gt 1 ]]; then
    VLLM_ARGS+=" --tensor-parallel-size ${TENSOR_PARALLEL_SIZE}"
fi

# Argumentos personalizados
if [[ -n "$CUSTOM_ARGS" ]]; then
    VLLM_ARGS+=" ${CUSTOM_ARGS}"
fi

# Para imagen ROCm: vllm-openai-rocm usa entrypoint que recibe args directamente
# Para imagen CUDA/CPU: vllm-openai también usa entrypoint openai
# Para CPU: necesitamos "vllm serve" explícito
if [[ "$DETECTED_BACKEND" == "cpu" ]]; then
    DOCKER_CMD+=" vllm serve ${VLLM_ARGS}"
else
    DOCKER_CMD+=" ${VLLM_ARGS}"
fi

echo ""
echo -e "${YELLOW}$DOCKER_CMD${NC}"
echo ""

# ─── Dry run ────────────────────────────────────────────────
if [[ "${DRY_RUN:-false}" == "true" ]]; then
    info "Dry-run mode. No se ejecutó el comando."
    exit 0
fi

# ─── Ejecutar ─────────────────────────────────────────────────
header "Desplegando vLLM"

eval "$DOCKER_CMD"

if $DETACH; then
    ok "Contenedor '$CONTAINER_NAME' iniciado en puerto $PORT"
else
    ok "Contenedor ejecutándose en primer plano"
fi

# ─── Health Check ─────────────────────────────────────────────
header "Health Check"

info "Esperando a que el servidor esté listo..."

# Polling hasta 120 segundos
MAX_RETRIES=30
RETRY_INTERVAL=4
READY=false

for i in $(seq 1 "$MAX_RETRIES"); do
    if curl -sf "http://localhost:${PORT}/v1/models" &> /dev/null; then
        READY=true
        break
    fi
    echo -n "."
    sleep "$RETRY_INTERVAL"
done
echo ""

if $READY; then
    ok "Servidor listo en http://localhost:${PORT}"
    echo ""
    echo -e "  ${CYAN}Endpoints:${NC}"
    echo "    GET  http://localhost:${PORT}/v1/models"
    echo "    POST http://localhost:${PORT}/v1/chat/completions"
    echo "    POST http://localhost:${PORT}/v1/completions"
    echo ""
    echo -e "  ${CYAN}Test rápido:${NC}"
    echo "    curl http://localhost:${PORT}/v1/models"
    echo ""
    echo -e "  ${CYAN}Logs:${NC}"
    echo "    docker logs -f $CONTAINER_NAME"
    echo ""
    echo -e "  ${CYAN}Detener:${NC}"
    echo "    docker stop $CONTAINER_NAME"
else
    warn "El servidor no respondió después de $((MAX_RETRIES * RETRY_INTERVAL)) segundos."
    warn "Revisa los logs: docker logs $CONTAINER_NAME"
    exit 1
fi

# ─── Resumen ──────────────────────────────────────────────────
header "Resumen del Despliegue"
echo "  Modelo:          $MODEL"
echo "  Backend:         ${DETECTED_BACKEND^^}"
echo "  GPUs:            $GPU_COUNT"
echo "  dtype:           $DTYPE"
echo "  TP size:         $TENSOR_PARALLEL_SIZE"
echo "  Puerto:          $PORT"
echo "  Max model len:   $MAX_MODEL_LEN"
echo "  GPU mem util:    $GPU_MEMORY_UTILIZATION"
echo "  Contenedor:      $CONTAINER_NAME"
echo ""
ok "Despliegue completado exitosamente."
