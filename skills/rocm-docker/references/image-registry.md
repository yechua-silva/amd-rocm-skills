# ROCm & CUDA Docker Image Registry

Catálogo completo de imágenes Docker oficiales para AMD ROCm y NVIDIA CUDA,
incluyendo imágenes de frameworks populares (PyTorch, vLLM) y las imágenes
específicas para tu proyecto.

---

## 1. Imágenes Oficiales AMD ROCm

### 1.1 ROCm Dev — Base System

Imágenes base con ROCm instalado, ideales para desarrollo y testing.

| Imagen | OS Base | Tag Recomendado | Tamaño Aprox | Descripción |
|--------|---------|-----------------|-------------|-------------|
| `rocm/dev-ubuntu-22.04` | Ubuntu 22.04 LTS | `latest` | ~4 GB | ROCm sobre Ubuntu 22.04. Máxima compatibilidad. |
| `rocm/dev-ubuntu-22.04` | Ubuntu 22.04 LTS | `complete` | ~8 GB | ROCm completo con todas las herramientas. |
| `rocm/dev-ubuntu-24.04` | Ubuntu 24.04 LTS | `latest` | ~4 GB | ROCm sobre Ubuntu 24.04. Python 3.12 nativo. |
| `rocm/dev-ubuntu-24.04` | Ubuntu 24.04 LTS | `complete` | ~8 GB | ROCm completo sobre Ubuntu 24.04. |
| `rocm/dev-centos-7` | CentOS 7 | `latest` | ~3.5 GB | ROCm sobre CentOS 7. En desuso, preferir Ubuntu. |

**Uso:**
```bash
# ROCm dev sobre Ubuntu 22.04
docker pull rocm/dev-ubuntu-22.04:latest

# ROCm dev sobre Ubuntu 24.04 (recomendado para vLLM)
docker pull rocm/dev-ubuntu-24.04:latest

# Ejecutar con GPU passthrough
docker run -it --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --group-add=render \
  rocm/dev-ubuntu-24.04:latest \
  /bin/bash

# Verificar instalación ROCm dentro del contenedor
docker run -it --rm \
  --device=/dev/kfd --device=/dev/dri --group-add=video \
  rocm/dev-ubuntu-22.04:latest \
  bash -c "rocminfo | grep 'Name:' && rocm-smi --showproductname"
```

### 1.2 ROCm PyTorch

Imágenes con PyTorch pre-instalado y optimizado para ROCm.

| Imagen | Tag Recomendado | ROCm | PyTorch | Python | Ubuntu | Tamaño |
|--------|----------------|:----:|:-------:|:------:|:------:|:------:|
| `rocm/pytorch` | `rocm7.2.4_ubuntu24.04_py3.12_pytorch_2.10.0` | 7.2.4 | 2.10.0 | 3.12 | 24.04 | ~8 GB |
| `rocm/pytorch` | `rocm7.2.4_ubuntu22.04_py3.11_pytorch_2.10.0` | 7.2.4 | 2.10.0 | 3.11 | 22.04 | ~8 GB |
| `rocm/pytorch` | `rocm6.3.3_ubuntu22.04_py3.11_pytorch_2.5.1` | 6.3.3 | 2.5.1 | 3.11 | 22.04 | ~8 GB |
| `rocm/pytorch` | `rocm6.2.4_ubuntu22.04_py3.11_pytorch_2.4.0` | 6.2.4 | 2.4.0 | 3.11 | 22.04 | ~7 GB |
| `rocm/pytorch` | `latest` | varía | varía | 3.11 | 22.04 | ~8 GB |

> **Nota:** vLLM ROCm requiere **Python 3.12**. Usa el tag `rocm7.2.4_ubuntu24.04_py3.12_pytorch_2.10.0` para compatibilidad máxima.

**Uso:**
```bash
# Descargar PyTorch ROCm (última versión estable)
docker pull rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_2.10.0

# Verificar PyTorch + GPU
docker run -it --rm \
  --device=/dev/kfd --device=/dev/dri --group-add=video \
  rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_2.10.0 \
  python3 -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'GPUs: {torch.cuda.device_count()}')
print(f'ROCm: {torch.version.hip}')
"

# Ejecutar training simple
docker run -it --rm \
  --device=/dev/kfd --device=/dev/dri --group-add=video \
  -v $(pwd):/workspace \
  rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_2.10.0 \
  python3 -c "
import torch
import torch.nn as nn
model = nn.Linear(100, 10).cuda()
x = torch.randn(32, 100).cuda()
print(model(x).shape)
"
```

### 1.3 vLLM ROCm

Imágenes oficiales de vLLM con soporte AMD ROCm.

| Imagen | Tag Recomendado | ROCm | vLLM | Python | Descripción |
|--------|----------------|:----:|:----:|:------:|-------------|
| `vllm/vllm-openai-rocm` | `latest` | 7.2.x | última | 3.12 | vLLM con API OpenAI-compatible para ROCm |
| `vllm/vllm-openai-rocm` | `rocm7.2` | 7.2 | última | 3.12 | vLLM ROCm 7.2 estable |
| `vllm/vllm-openai-rocm` | `rocm6.3` | 6.3 | última | 3.12 | vLLM ROCm 6.3 estable |

> **Importante:** vLLM ROCm requiere Python 3.12. Verificar con `python3 --version` dentro del contenedor.

**Uso:**
```bash
# Descargar vLLM ROCm
docker pull vllm/vllm-openai-rocm:latest

# Verificar Python 3.12
docker run --rm --device=/dev/kfd --device=/dev/dri \
  vllm/vllm-openai-rocm:latest python3 --version

# Ejecutar servidor vLLM con ROCm
docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --group-add=render \
  --cap-add=SYS_PTRACE \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai-rocm:latest \
  --model mistralai/Mistral-7B-Instruct-v0.3 \
  --tensor-parallel-size 4

# Consultar la API
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "mistralai/Mistral-7B-Instruct-v0.3", "prompt": "Hello!", "max_tokens": 50}'
```

---

## 2. Imágenes Oficiales NVIDIA CUDA

### 2.1 CUDA Base

| Imagen | Tag Recomendado | CUDA | Ubuntu | Tamaño | Descripción |
|--------|----------------|:----:|:------:|:------:|-------------|
| `nvidia/cuda` | `12.6.3-runtime-ubuntu22.04` | 12.6.3 | 22.04 | ~1.5 GB | Runtime mínimo para ejecutar apps CUDA |
| `nvidia/cuda` | `12.6.3-devel-ubuntu22.04` | 12.6.3 | 22.04 | ~3.5 GB | Incluye herramientas de desarrollo CUDA |
| `nvidia/cuda` | `12.6.3-base-ubuntu22.04` | 12.6.3 | 22.04 | ~800 MB | Base mínima solo con librerías CUDA |

**Uso:**
```bash
# Verificar CUDA
docker run --rm --runtime nvidia --gpus all \
  nvidia/cuda:12.6.3-runtime-ubuntu22.04 \
  nvidia-smi

# Compilar código CUDA
docker run --rm --runtime nvidia --gpus all \
  nvidia/cuda:12.6.3-devel-ubuntu22.04 \
  nvcc --version
```

### 2.2 PyTorch NVIDIA

| Imagen | Tag Recomendado | CUDA | PyTorch | Descripción |
|--------|----------------|:----:|:-------:|-------------|
| `pytorch/pytorch` | `2.5.1-cuda12.4-cudnn9-runtime` | 12.4 | 2.5.1 | PyTorch + CUDA + cuDNN 9 |
| `pytorch/pytorch` | `2.4.0-cuda12.4-cudnn9-runtime` | 12.4 | 2.4.0 | PyTorch + CUDA + cuDNN 9 |
| `pytorch/pytorch` | `latest` | varía | última | Último release estable |

**Uso:**
```bash
docker run --rm --runtime nvidia --gpus all \
  pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime \
  python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPUs: {torch.cuda.device_count()}')"
```

### 2.3 vLLM NVIDIA

| Imagen | Tag Recomendado | vLLM | Descripción |
|--------|----------------|:----:|-------------|
| `vllm/vllm-openai` | `latest` | última | vLLM con API OpenAI-compatible |
| `vllm/vllm-openai` | `v0.6.3` | 0.6.3 | Versión específica estable |

**Uso:**
```bash
docker run --rm --runtime nvidia --gpus all \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model mistralai/Mistral-7B-Instruct-v0.3
```

---

## 3. Imágenes Personalizadas (Referencia)

Imágenes personalizadas para entornos con GPUs AMD.

| Imagen | Base | Descripción | Estatus |
|--------|------|-------------|:-------:|
| `rocm-vllm` | `vllm/vllm-openai-rocm:latest` | vLLM + ROCm + configuraciones personalizadas | En desarrollo |
| `rocm-yolo` | `rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_2.10.0` | YOLOv8x + PyTorch ROCm para detección de objetos | En desarrollo |
| `rocm-app` | multi-stage (base/cuda/rocm/cpu) | App multi-backend | Planificado |

---

## 4. Tabla Comparativa por Framework

| Framework | Imagen NVIDIA | Imagen AMD ROCm |
|-----------|--------------|-----------------|
| **Base OS** | `nvidia/cuda:12.6.3-runtime-ubuntu22.04` | `rocm/dev-ubuntu-24.04:latest` |
| **PyTorch** | `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` | `rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_2.10.0` |
| **vLLM** | `vllm/vllm-openai:latest` | `vllm/vllm-openai-rocm:latest` |
| **Dev** | `nvidia/cuda:12.6.3-devel-ubuntu22.04` | `rocm/dev-ubuntu-24.04:complete` |

---

## 5. Docker Pull + Run — Cheatsheet

```bash
# ── AMD ROCm ──────────────────────────────────────────────────────────────────

# ROCm dev (Ubuntu 22.04)
docker pull rocm/dev-ubuntu-22.04:latest
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add=video \
  rocm/dev-ubuntu-22.04:latest rocminfo

# ROCm dev (Ubuntu 24.04 — Python 3.12)
docker pull rocm/dev-ubuntu-24.04:latest
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add=video \
  rocm/dev-ubuntu-24.04:latest rocminfo

# ROCm PyTorch (Python 3.12 para vLLM)
docker pull rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_2.10.0
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add=video \
  rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_2.10.0 \
  python3 -c "import torch; print(torch.cuda.is_available())"

# vLLM ROCm
docker pull vllm/vllm-openai-rocm:latest
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add=video \
  --group-add=render -p 8000:8000 \
  vllm/vllm-openai-rocm:latest \
  --model mistralai/Mistral-7B-Instruct-v0.3

# ── NVIDIA CUDA ───────────────────────────────────────────────────────────────

# CUDA runtime
docker pull nvidia/cuda:12.6.3-runtime-ubuntu22.04
docker run --rm --runtime nvidia --gpus all \
  nvidia/cuda:12.6.3-runtime-ubuntu22.04 nvidia-smi

# PyTorch NVIDIA
docker pull pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime
docker run --rm --runtime nvidia --gpus all \
  pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime \
  python3 -c "import torch; print(torch.cuda.is_available())"

# vLLM NVIDIA
docker pull vllm/vllm-openai:latest
docker run --rm --runtime nvidia --gpus all -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model mistralai/Mistral-7B-Instruct-v0.3
```

---

## 6. Notas Importantes

### Python 3.12 para vLLM ROCm

vLLM con soporte ROCm **requiere Python 3.12**. Al construir imágenes personalizadas:

```dockerfile
FROM rocm/dev-ubuntu-24.04:latest  # Ubuntu 24.04 trae Python 3.12
# ✅ OK — python3 --version mostrará 3.12.x
```

```dockerfile
FROM rocm/dev-ubuntu-22.04:latest  # Ubuntu 22.04 trae Python 3.10
# ⚠️ Necesitarás instalar Python 3.12 adicionalmente
```

### Tensor Parallelism

| Backend | Library | Comando Docker |
|---------|---------|----------------|
| NVIDIA | NCCL | `--tensor-parallel-size 4` |
| AMD ROCm | RCCL | `--tensor-parallel-size 4` (mismo flag) |

### GPU Memory Utilization

```bash
# Recomendado para ROCm — usar float16
docker run ... vllm/vllm-openai-rocm:latest \
  --model meta-llama/Llama-2-70b-hf \
  --dtype float16 \
  --gpu-memory-utilization 0.9

# Recomendado para NVIDIA — usar bfloat16 si soportado
docker run ... vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-70b-hf \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.9
```

---

## Referencias

- [ROCm Docker Hub](https://hub.docker.com/r/rocm/dev-ubuntu-22.04)
- [NVIDIA CUDA Docker Hub](https://hub.docker.com/r/nvidia/cuda)
- [PyTorch Docker Hub](https://hub.docker.com/r/pytorch/pytorch)
- [vLLM Docker Hub](https://hub.docker.com/r/vllm/vllm-openai)
- [ROCm Installation Guide](https://rocm.docs.amd.com/en/latest/deploy/docker.html)
