# Dockerfile Multi-Stage — NVIDIA CUDA + AMD ROCm + CPU

Referencia completa para construir imágenes Docker que funcionen en cualquier
backend GPU (NVIDIA, AMD o CPU) usando un solo Dockerfile multi-stage.

---

## Estructura

El Dockerfile define 4 targets:

```
base  ← Dependencias comunes (Python, requirements, código)
  ├── cuda  ← NVIDIA CUDA (runtime nvidia + PyTorch CUDA)
  ├── rocm  ← AMD ROCm (dispositivos /dev/kfd + /dev/dri + PyTorch ROCm)
  └── cpu   ← CPU fallback (PyTorch CPU)
```

---

## Dockerfile Completo

```dockerfile
# ==============================================================================
# Dockerfile Multi-Stage — NVIDIA CUDA + AMD ROCm + CPU
# ==============================================================================
# Build:
#   docker build --target cuda -t munin/app:cuda .
#   docker build --target rocm -t munin/app:rocm .
#   docker build --target cpu  -t munin/app:cpu .
#
# Run:
#   # NVIDIA
#   docker run --runtime nvidia --gpus all munin/app:cuda
#
#   # AMD ROCm
#   docker run --device=/dev/kfd --device=/dev/dri --group-add=render munin/app:rocm
#
#   # CPU
#   docker run munin/app:cpu
# ==============================================================================

# ------------------------------------------------------------------------------
# STAGE 0: Base común
# ------------------------------------------------------------------------------
# Usamos Python 3.12-slim porque es requerido por vLLM ROCm y funciona
# en todos los backends.
FROM python:3.12-slim AS base

# Evitar que Python escriba bytecode y bufeé stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copiar solo requirements primero para aprovechar cache de Docker layers
COPY requirements.txt .

# Instalar dependencias base (sin PyTorch — se instala por backend)
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Entrypoint con detección automática de backend GPU
# (opcional — ver scripts/entrypoint.sh)
# COPY scripts/entrypoint.sh /entrypoint.sh
# RUN chmod +x /entrypoint.sh
# ENTRYPOINT ["/entrypoint.sh"]

CMD ["python", "run.py"]

# ------------------------------------------------------------------------------
# STAGE 1: Target NVIDIA CUDA
# ------------------------------------------------------------------------------
FROM base AS cuda

# Instalar PyTorch con CUDA 12.4
RUN pip install --no-cache-dir torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu124

# Variables de entorno CUDA
ENV CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:$PATH \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH \
    BACKEND=cuda

# Activar TF32 para NVIDIA Ampere+ (A100, H100, RTX 40xx)
RUN python3 -c "import torch; torch.backends.cuda.matmul.allow_tf32 = True; torch.backends.cudnn.allow_tf32 = True" 2>/dev/null || true

CMD ["python", "run.py"]

# ------------------------------------------------------------------------------
# STAGE 2: Target AMD ROCm
# ------------------------------------------------------------------------------
FROM base AS rocm

# Instalar PyTorch con ROCm 7.2.x
# Usar el índice oficial de PyTorch para ROCm
RUN pip install --no-cache-dir torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/rocm7.2

# Variables de entorno ROCm
ENV ROCM_HOME=/opt/rocm \
    HCC_HOME=/opt/rocm \
    PATH=/opt/rocm/bin:$PATH \
    LD_LIBRARY_PATH=/opt/rocm/lib:$LD_LIBRARY_PATH \
    HIPBLAS_WORKSPACE_CONFIG=:512:8 \
    BACKEND=rocm

# Verificar que PyTorch detecta el backend ROCm
RUN python3 -c "
import torch
if torch.cuda.is_available():
    hip_ver = torch.version.hip or 'desconocido'
    print(f'ROCm detectado: HIP {hip_ver}')
else:
    print('GPU no detectada en build time (normal en multi-stage)')
" 2>/dev/null || true

CMD ["python", "run.py"]

# ------------------------------------------------------------------------------
# STAGE 3: Target CPU Fallback
# ------------------------------------------------------------------------------
FROM base AS cpu

# Instalar PyTorch CPU-only (mucho más pequeño)
RUN pip install --no-cache-dir torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cpu

# Variables de entorno CPU
ENV BACKEND=cpu \
    OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4

CMD ["python", "run.py"]
```

---

## .dockerignore

Crear un `.dockerignore` en el mismo directorio para optimizar builds:

```dockerignore
# .dockerignore
.git/
.gitignore
*.md
__pycache__/
*.pyc
.env
.venv/
venv/
*.egg-info/
dist/
build/
.DS_Store
.vscode/
.idea/
*.log
*.tmp
tests/
test_*.py
notebooks/
data/
```

---

## Build Commands

### Build individual por target

```bash
# NVIDIA CUDA
docker build --target cuda -t munin/app:cuda .

# AMD ROCm
docker build --target rocm -t munin/app:rocm .

# CPU
docker build --target cpu -t munin/app:cpu .
```

### Build multi-arch (AMD ROCm solo x86_64 de momento)

```bash
# NVIDIA CUDA (x86_64 + arm64)
docker buildx build --platform linux/amd64,linux/arm64 \
  --target cuda -t munin/app:cuda --push .

# AMD ROCm (solo x86_64)
docker buildx build --platform linux/amd64 \
  --target rocm -t munin/app:rocm --push .
```

---

## Run Commands

### NVIDIA CUDA

```bash
# Básico
docker run --rm --runtime nvidia --gpus all munin/app:cuda

# Con todas las GPUs
docker run --rm --runtime nvidia --gpus all \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e CUDA_VISIBLE_DEVICES=0,1 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -p 8000:8000 \
  munin/app:cuda
```

### AMD ROCm

```bash
# Básico
docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --group-add=render \
  munin/app:rocm

# Con configuración completa
docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --group-add=render \
  --cap-add=SYS_PTRACE \
  -e HIP_VISIBLE_DEVICES=0,1 \
  -e ROCR_VISIBLE_DEVICES=0,1 \
  -e HSA_OVERRIDE_GFX_VERSION=11.0.0 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -p 8000:8000 \
  munin/app:rocm
```

### CPU

```bash
docker run --rm -p 8000:8000 munin/app:cpu
```

---

## Best Practices

### 1. Layer Caching — Copiar requirements primero

```dockerfile
# ✅ BUENO: Copiar solo requirements primero para cachear
COPY requirements.txt .
RUN pip install -r requirements.txt

# ❌ MALO: Copiar todo el proyecto antes de instalar
COPY . .
RUN pip install -r requirements.txt
```

### 2. Usar --no-cache-dir en pip

```dockerfile
RUN pip install --no-cache-dir torch
# Ahorra ~200 MB en la imagen final
```

### 3. Instalar solo lo necesario por backend

Cada target instala solo el PyTorch que necesita:

| Target | Comando pip | Tamaño Aprox |
|--------|-------------|:------------:|
| cuda | `--index-url https://download.pytorch.org/whl/cu124` | ~2.5 GB |
| rocm | `--index-url https://download.pytorch.org/whl/rocm7.2` | ~3 GB |
| cpu | `--index-url https://download.pytorch.org/whl/cpu` | ~800 MB |

### 4. Entrypoint con detección automática

Usar `scripts/entrypoint.sh` para detectar automáticamente el backend:

```dockerfile
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "run.py"]
```

```bash
# Ahora funciona en cualquier backend sin flags extra
docker run --runtime nvidia --gpus all munin/app  # detecta CUDA
docker run --device=/dev/kfd --device=/dev/dri munin/app  # detecta ROCm
docker run munin/app  # fallback CPU
```

### 5. Usar ARG para versiones

```dockerfile
ARG PYTORCH_VERSION=2.10.0
ARG CUDA_VERSION=124
ARG ROCM_VERSION=7.2

RUN pip install torch==${PYTORCH_VERSION} \
    --index-url https://download.pytorch.org/whl/cu${CUDA_VERSION}
```

### 6. Multi-arch builds

```bash
# Crear builder si no existe
docker buildx create --name mybuilder --use
docker buildx inspect --bootstrap

# Build multi-arch
docker buildx build --platform linux/amd64,linux/arm64 \
  --target cpu -t munin/app:cpu --push .
```

> **Nota:** ROCm solo está disponible para `linux/amd64`. No intentes builds multi-arch para el target `rocm`.

---

## Verificación Post-Build

```bash
# Verificar que la imagen CUDA funciona
docker run --rm --runtime nvidia --gpus all \
  munin/app:cuda \
  python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0)}')"

# Verificar que la imagen ROCm funciona
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add=video \
  munin/app:rocm \
  python3 -c "import torch; print(f'ROCm: {torch.cuda.is_available()}, HIP: {torch.version.hip}')"

# Verificar que la imagen CPU funciona
docker run --rm munin/app:cpu \
  python3 -c "import torch; print(f'CPU: {torch.cuda.is_available()}, Backend: cpu')"
```

---

## Referencias

- [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [PyTorch — Get Started Locally](https://pytorch.org/get-started/locally/)
- [ROCm — Docker](https://rocm.docs.amd.com/en/latest/deploy/docker.html)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
