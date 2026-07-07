---
name: rocm-docker
description: >
  Configura y verifica Docker con soporte GPU AMD ROCm y NVIDIA CUDA.
  Realiza preflight checks, configura runtime para AMD (--device=/dev/kfd --device=/dev/dri --group-add=render)
  y NVIDIA (--runtime nvidia --gpus all), y valida que los contenedores detecten GPUs.
  Incluye docker-compose multi-perfil, entrypoint con detección automática de backend,
  y Dockerfile multi-stage para construir imágenes que funcionen en cualquier hardware.
  Usar cuando necesites ejecutar contenedores con GPU AMD o NVIDIA, configurar Docker para ROCm,
  verificar setup de Docker + GPU, o crear pipelines multi-backend.
  Keywords: docker, rocm, container, gpu, nvidia, amd, passthrough, preflight, cuda, hip,
  multi-gpu, compose, pytorch, vllm, mi300, mi250, instinct, radeon
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: "Munin Project"
  tags:
    - amd
    - rocm
    - docker
    - container
    - gpu
    - multi-gpu
    - nvidia
    - cuda
    - preflight
    - pytorch
    - vllm
compatibility:
  - claude-code
  - opencode
  - codex
  - cursor
  - "Requiere Docker Engine 24+ y Linux host con GPU."
---

# ROCm Docker Skill

Configuración completa de Docker con soporte GPU para **AMD ROCm** y **NVIDIA CUDA**.
Detección automática del backend, preflight checks, docker-compose multi-perfil,
y Dockerfile multi-stage para construir imágenes portables.

## Purpose

Proporciona un conjunto de scripts, referencias y documentación para:

- **Verificar** que Docker está correctamente configurado para usar GPUs AMD y/o NVIDIA
- **Ejecutar** contenedores con GPU passthrough para ambos backends
- **Detectar** automáticamente el backend GPU disponible dentro del contenedor
- **Construir** imágenes multi-stage que funcionen en NVIDIA, AMD o CPU
- **Orquestar** servicios con docker-compose usando perfiles específicos por backend
- **Diagnosticar** problemas comunes de GPU en contenedores

## When to Use

Usa esta skill cuando:

- "Set up Docker for AMD GPUs" / "Configurar Docker para GPUs AMD"
- "Configure Docker ROCm runtime" / "Configurar runtime ROCm en Docker"
- "Test GPU passthrough in Docker" / "Probar paso de GPU en Docker"
- "Run vLLM with ROCm in Docker" / "Ejecutar vLLM con ROCm en Docker"
- "Create multi-GPU Docker setup" / "Crear configuración Docker multi-GPU"
- "Docker compose with GPU profiles" / "Docker compose con perfiles de GPU"
- "Build multi-stage Dockerfile for AMD and NVIDIA"
- "Check if Docker can see my GPU" / "Verificar si Docker ve mi GPU"
- "Preflight check before running GPU containers"
- Keywords: docker, rocm, container, gpu passthrough, rocm-docker, multi-gpu, cuda

## Prerequisites

### Hardware
- **AMD**: GPU AMD con soporte ROCm (MI300X, MI250, MI100, RX 7900 XTX, etc.)
- **NVIDIA**: GPU NVIDIA con soporte CUDA (A100, H100, V100, RTX series, etc.)
- **CPU**: Fallback automático si no hay GPU

### Software Host
- **Docker Engine 24+** (verificar con `docker --version`)
- **Docker Compose V2+** (verificar con `docker compose version`)
- **ROCm** (para AMD): Instalado en host — verificar con `rocm-smi --showproductname`
- **NVIDIA Container Toolkit** (para NVIDIA): `nvidia-smi` debe funcionar

### Permisos de Usuario
- **AMD**: Usuario en grupos `video` y `render`
  ```bash
  sudo usermod -aG video,render $USER
  # Cerrar sesión y volver a entrar
  ```
- **NVIDIA**: Usuario en grupo `video`
  ```bash
  sudo usermod -aG video $USER
  ```

## Quickstart

### 1. Run Preflight Check

```bash
# Verificar todo el setup (AMD + NVIDIA)
bash scripts/docker-preflight.sh

# Opción JSON para parsear desde scripts
bash scripts/docker-preflight.sh --json
```

### 2. Test GPU en Contenedor

**AMD ROCm:**
```bash
docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  rocm/dev-ubuntu-22.04:latest \
  rocminfo | grep "Name:"
```

**NVIDIA CUDA:**
```bash
docker run --rm \
  --runtime nvidia \
  --gpus all \
  nvidia/cuda:12.6.3-runtime-ubuntu22.04 \
  nvidia-smi
```

### 3. Usar Entrypoint con Detección Automática

```bash
docker run --rm \
  --device=/dev/kfd --device=/dev/dri --group-add=render \
  -e BACKEND=auto \
  munin/app:latest
```

### 4. Docker Compose Multi-Perfil

```bash
# Con GPUs NVIDIA
docker compose --profile nvidia up

# Con GPUs AMD
docker compose --profile rocm up

# Sin GPU (CPU)
docker compose --profile cpu up
```

## Step-by-Step

### 1. Preflight Check

Ejecuta `scripts/docker-preflight.sh` para verificar:

| Check | Qué verifica | AMD | NVIDIA |
|-------|-------------|:---:|:------:|
| Docker Engine | `docker --version` | ✅ | ✅ |
| Docker Compose | `docker compose version` | ✅ | ✅ |
| User groups | `groups` contiene `video`/`render` | ✅ | ✅ |
| Device nodes | `/dev/kfd`, `/dev/dri/render*` | ✅ | ❌ |
| GPU driver | `rocm-smi` o `nvidia-smi` | ✅ | ✅ |
| Test container | Run + detect GPU | ✅ | ✅ |

**Exit codes:**
- `0`: Todo OK — GPU(s) detectada(s) y funcionando
- `1`: Warnings — GPU detectada pero con advertencias (ej. falta grupo render)
- `2`: Errors — No se pudo verificar GPU o Docker no disponible

### 2. Docker Run — AMD ROCm

Flags esenciales para AMD:

```bash
docker run \
  --device=/dev/kfd \          # Dispositivo KFD (Kernel Fusion Driver)
  --device=/dev/dri \          # Dispositivos DRM (Direct Rendering Manager)
  --group-add=video \          # Grupo video para acceso a /dev/dri
  --group-add=render \         # Grupo render para acceso a render nodes
  --cap-add=SYS_PTRACE \       # SYS_PTRACE para ROCm (recomendado)
  -v /opt/rocm:/opt/rocm:ro \  # Montar ROCm del host (opcional)
  <imagen> <comando>
```

**Ejemplo completo con vLLM:**
```bash
docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --group-add=render \
  --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai-rocm:latest \
  --model mistralai/Mistral-7B-Instruct-v0.3
```

**Variables de entorno para AMD ROCm:**

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `HIP_VISIBLE_DEVICES` | Selecciona GPUs AMD visibles | `0,1` |
| `ROCR_VISIBLE_DEVICES` | Alternativa a HIP_VISIBLE_DEVICES | `0,1` |
| `HSA_OVERRIDE_GFX_VERSION` | Override de arquitectura GFX | `11.0.0` |
| `HIPBLAS_WORKSPACE_CONFIG` | Configuración workspace HIPBLAS | `:512:8` |
| `ROCM_HOME` | Ruta home de ROCm | `/opt/rocm` |

### 3. Docker Run — NVIDIA CUDA

Flags esenciales para NVIDIA:

```bash
docker run \
  --runtime nvidia \            # Usar runtime NVIDIA
  --gpus all \                  # Pasar todas las GPUs
  -e NVIDIA_VISIBLE_DEVICES=all \ # Opcional, explícito
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \ # Capacidades
  <imagen> <comando>
```

**Ejemplo completo con vLLM:**
```bash
docker run --rm \
  --runtime nvidia \
  --gpus all \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model mistralai/Mistral-7B-Instruct-v0.3
```

**Variables de entorno para NVIDIA CUDA:**

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `CUDA_VISIBLE_DEVICES` | Selecciona GPUs NVIDIA visibles | `0,1,2,3` |
| `NVIDIA_VISIBLE_DEVICES` | GPUs visibles en contenedor Docker | `all` |
| `NVIDIA_DRIVER_CAPABILITIES` | Capacidades del driver | `compute,utility` |

### 4. Docker Compose Multi-Perfil

Usa `scripts/docker-compose.yml` para orquestar servicios con perfiles separados:

```bash
# AMD ROCm
docker compose --profile rocm up -d

# NVIDIA CUDA
docker compose --profile nvidia up -d

# CPU fallback
docker compose --profile cpu up -d

# Ver logs
docker compose logs -f

# Detener todo
docker compose down
```

### 5. Build Multi-Stage

Usa `references/multi-gpu-dockerfile.md` como referencia para construir imágenes:

```bash
# Construir para NVIDIA
docker build --target cuda -t munin-app:cuda .

# Construir para AMD
docker build --target rocm -t munin-app:rocm .

# Construir para CPU
docker build --target cpu -t munin-app:cpu .
```

### 6. Smoke Test

Verifica que los contenedores detectan correctamente la GPU:

```bash
# AMD — verificar rocminfo
docker run --rm --device=/dev/kfd --device=/dev/dri \
  --group-add=video rocm/dev-ubuntu-22.04:latest \
  bash -c "rocminfo 2>/dev/null | grep 'Name:' | head -5"

# AMD — verificar PyTorch detecta GPU
docker run --rm --device=/dev/kfd --device=/dev/dri \
  --group-add=video rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_2.10.0 \
  python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device count: {torch.cuda.device_count()}')"

# NVIDIA — verificar nvidia-smi
docker run --rm --runtime nvidia --gpus all \
  nvidia/cuda:12.6.3-runtime-ubuntu22.04 \
  nvidia-smi

# NVIDIA — verificar PyTorch
docker run --rm --runtime nvidia --gpus all \
  pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime \
  python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device count: {torch.cuda.device_count()}')"
```

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/image-registry.md](references/image-registry.md) | Catálogo completo de imágenes Docker ROCm y NVIDIA |
| [references/multi-gpu-dockerfile.md](references/multi-gpu-dockerfile.md) | Dockerfile multi-stage con targets cuda/rocm/cpu |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/docker-preflight.sh` | Preflight check multi-backend para Docker + GPU |
| `scripts/entrypoint.sh` | Entrypoint con detección automática de backend GPU |
| `scripts/docker-compose.yml` | Docker Compose multi-perfil (nvidia/rocm/cpu) |

## Common Issues

### Issue 1: Permission denied al acceder a /dev/kfd o /dev/dri

**Síntoma:** `docker: Error response from daemon: error gathering device information while adding custom device "/dev/kfd": permission denied`

**Causa:** El usuario no está en los grupos `video` y `render`.

**Solución:**
```bash
sudo usermod -aG video,render $USER
# Cerrar sesión y volver a entrar, o ejecutar:
newgrp video
newgrp render
```

### Issue 2: Docker no encuentra el runtime nvidia

**Síntoma:** `docker: Error response from daemon: unknown or invalid runtime name: nvidia`

**Causa:** NVIDIA Container Toolkit no está instalado o configurado.

**Solución:**
```bash
# Instalar NVIDIA Container Toolkit
sudo apt-get install -y nvidia-container-toolkit

# Configurar runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verificar
docker info | grep -i runtime
```

### Issue 3: ROCm no detecta GPU dentro del contenedor

**Síntoma:** `rocminfo` dentro del contenedor muestra 0 GPUs o "No AMD GPUs found".

**Causa:** Faltan flags `--device=/dev/kfd --device=/dev/dri --group-add=video` o el kernel module `amdgpu` no está cargado en el host.

**Solución:**
```bash
# Verificar en host que el módulo amdgpu está cargado
lsmod | grep amdgpu

# Verificar dispositivos en host
ls -la /dev/kfd /dev/dri/render*

# Re-ejecutar con todos los flags
docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --group-add=render \
  --cap-add=SYS_PTRACE \
  rocm/dev-ubuntu-22.04:latest \
  rocminfo
```

### Issue 4: vLLM ROCm se queja de Python 3.12

**Síntoma:** `Python version must be 3.12.x for ROCm` o error similar al iniciar vLLM.

**Causa:** vLLM ROCm requiere Python 3.12 específicamente.

**Solución:** Usar imágenes que ya incluyan Python 3.12:
```bash
docker pull vllm/vllm-openai-rocm:latest
docker run --rm --device=/dev/kfd --device=/dev/dri \
  vllm/vllm-openai-rocm:latest python3 --version
# Debe mostrar Python 3.12.x
```

O para imágenes PyTorch ROCm, usar el tag correcto:
```bash
docker pull rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_2.10.0
```

### Issue 5: Docker compose —profile no reconoce el perfil

**Síntoma:** `WARNING: Some services (munin-nvidia) use the 'deploy' key, which will be ignored. Compose does not support 'deploy' configuration.`

**Causa:** Usar `docker-compose` (v1) en lugar de `docker compose` (v2).

**Solución:** Usar siempre `docker compose` (v2):
```bash
# ✅ Correcto (v2)
docker compose --profile rocm up

# ❌ Incorrecto (v1)
docker-compose --profile rocm up
```

### Issue 6: OOM (Out of Memory) en contenedor GPU

**Síntoma:** El contenedor se mata con exit code 137 o error "Killed".

**Causa:** El contenedor no tiene límites de memoria y el host se queda sin RAM.

**Solución:**
```bash
# Limitar memoria del contenedor
docker run --rm \
  --memory=64g \
  --memory-swap=64g \
  --device=/dev/kfd --device=/dev/dri \
  --group-add=video \
  vllm/vllm-openai-rocm:latest \
  --model meta-llama/Llama-2-70b-hf \
  --gpu-memory-utilization 0.9

# Para NVIDIA también se puede limitar
docker run --rm \
  --runtime nvidia --gpus all \
  --memory=64g \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-70b-hf
```

### Issue 7: HIP_VISIBLE_DEVICES no tiene efecto

**Síntoma:** Se define `HIP_VISIBLE_DEVICES=0` pero el contenedor ve todas las GPUs.

**Causa:** Algunas versiones de ROCm usan `ROCR_VISIBLE_DEVICES` en lugar de `HIP_VISIBLE_DEVICES`.

**Solución:** Usar ambas variables para compatibilidad máxima:
```bash
docker run --rm \
  --device=/dev/kfd --device=/dev/dri \
  --group-add=video \
  -e HIP_VISIBLE_DEVICES=0 \
  -e ROCR_VISIBLE_DEVICES=0 \
  rocm/dev-ubuntu-22.04:latest \
  rocminfo
```
