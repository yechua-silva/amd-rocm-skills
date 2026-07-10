---
name: vllm-rocm-deploy
description: >
  Despliegue de vLLM para inferencia LLM/VLM en GPUs AMD ROCm o NVIDIA CUDA
  con detección automática de backend. Cubre instalación, configuración Docker,
  selección de modelos multimodales (InternVL2, Qwen2-VL, LLaVA), optimización
  de rendimiento y tests de inferencia. Útil cuando necesites servir LLMs o VLMs
  con cualquier GPU disponible, configurar vLLM para ROCm o CUDA, hacer inferencia
  multimodal, o desplegar servidores compatibles con OpenAI API.
  Keywords: vllm, rocm, cuda, amd, nvidia, llm, vlm, multimodal, internvl, qwen,
  llava, mi300, a100, h100, inference, deployment, openai-api, docker
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: "yechua-silva"
  tags:
    - amd
    - rocm
    - vllm
    - llm
    - vlm
    - multimodal
    - inference
    - nvidia
    - cuda
    - docker
    - python
    - gpu
compatibility: >
  Compatible with Claude Code, OpenCode, Codex, Cursor, Cline, Roo Code,
  Windsurf, Gemini CLI, and Kiro CLI. Requires Linux with AMD ROCm or
  NVIDIA CUDA GPU (CPU fallback supported).
---

# vLLM ROCm / CUDA Deploy

Despliegue de **vLLM** para servir modelos de lenguaje (LLM) y visión-lenguaje (VLM) con soporte para **AMD ROCm**, **NVIDIA CUDA** y **CPU fallback**. La skill detecta automáticamente el backend disponible y configura vLLM con los parámetros óptimos para cada plataforma.

## Purpose

- Servir modelos LLM/VLM con API compatible con OpenAI (`/v1/chat/completions`, `/v1/models`)
- Desplegar en **AMD ROCm** (MI300X, MI250, RX 7900) con float16
- Desplegar en **NVIDIA CUDA** (A100, H100, RTX 4090) con bfloat16 / TF32
- Fallback a **CPU** cuando no hay GPU disponible
- Inferencia multimodal (texto + imágenes) con modelos como InternVL2, Qwen2-VL, LLaVA
- Optimización de rendimiento: throughput, latencia, tensor parallelism

## When to Use / Cuándo Usar

- "Deploy vLLM on AMD GPU / Desplegar vLLM en GPU AMD"
- "Serve InternVL2 on ROCm / Servir InternVL2 en ROCm"
- "Configure vLLM for MI300X or A100 / Configurar vLLM para MI300X o A100"
- "Test multimodal inference on AMD / NVIDIA / Probar inferencia multimodal"
- "vLLM OpenAI API server deployment"
- Keywords: vllm, rocm, cuda, amd, nvidia, llm, vlm, multimodal, internvl, deploy, inference, docker

## Prerequisites

- [ ] **GPU compatible**: AMD ROCm (MI300X, MI250, RX 7900+) o NVIDIA CUDA (A100, H100, RTX 3090+) con **16GB+ VRAM**
- [ ] **ROCm** (solo AMD): ROCm 6.x instalado — verificar con `rocminfo | grep gfx`
- [ ] **NVIDIA driver** (solo NVIDIA): driver 535+ — verificar con `nvidia-smi`
- [ ] **Docker** con soporte GPU: Docker Engine 24+ instalado
- [ ] **Python 3.12+** (obligatorio para vLLM ROCm; si usas otro Python, pip instala silenciosamente la rueda CUDA incorrecta)
- [ ] **uv** (recomendado) o pip para instalar vLLM
- [ ] **HuggingFace token** (opcional, para modelos con acceso restringido): `huggingface-cli login`
- [ ] **Espacio en disco**: 20GB+ para modelos descargados (~/.cache/huggingface)

## Quickstart

### 1. Detectar GPU

```bash
# NVIDIA
nvidia-smi

# AMD ROCm
rocminfo | grep gfx

# Si no hay GPU, vLLM funciona en CPU (más lento)
```

### 2. Desplegar vLLM con Docker

```bash
# AMD ROCm
docker run -d --name vllm \
  --device=/dev/kfd --device=/dev/dri --group-add=render \
  --cap-add=SYS_PTRACE --security-opt seccomp=unconfined \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai-rocm:latest \
  --model OpenGVLab/InternVL2-8B \
  --dtype float16 \
  --max-model-len 4096

# NVIDIA CUDA
docker run -d --name vllm \
  --runtime nvidia --gpus all \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model OpenGVLab/InternVL2-8B \
  --dtype bfloat16 \
  --max-model-len 4096
```

### 3. Probar Inferencia

```bash
# Verificar que el servidor responde
curl http://localhost:8000/v1/models

# Chat simple
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"InternVL2-8B","messages":[{"role":"user","content":"Hola, ¿qué puedes hacer?"}],"max_tokens":100}'
```

## Step-by-Step

### 1. Detectar Backend de GPU

Ejecuta el script de detección para identificar tu hardware:

```bash
# Detección rápida desde terminal
if command -v nvidia-smi &> /dev/null; then
    echo "✅ Backend: NVIDIA CUDA"
elif command -v rocminfo &> /dev/null; then
    echo "✅ Backend: AMD ROCm ($(rocminfo 2>/dev/null | grep -oP 'gfx\w+' | head -1))"
else
    echo "⚠️  No se detectó GPU — modo CPU"
fi
```

**Arquitecturas AMD ROCm comunes:**

| GPU | GFX | ROCm mínimo | Notas |
|-----|-----|-------------|-------|
| MI300X | gfx942 | 6.1 | Recomendado para vLLM |
| MI250 | gfx90a | 5.3 | Soporte completo |
| MI100 | gfx908 | 5.0 | Soporte completo |
| RX 7900 XTX | gfx1100 | 6.0 | Soporte parcial en vLLM |
| RX 9070 XT | gfx1201 | 6.4 | Experimental |

### 2. Instalar vLLM (si no usas Docker)

**AMD ROCm — Python 3.12 OBLIGATORIO:**
```bash
# Verificar Python
python3 --version  # Debe mostrar 3.12.x

# Instalar con uv (recomendado)
uv pip install vllm --extra-index-url https://wheels.vllm.ai/rocm/

# O con pip
pip install vllm --extra-index-url https://wheels.vllm.ai/rocm/
```

**NVIDIA CUDA:**
```bash
# Instalar con uv (recomendado) o pip
uv pip install vllm

# O con pip
pip install vllm
```

**CPU:**
```bash
pip install vllm
# vLLM detecta automáticamente CPU cuando no hay GPU
```

### 3. Desplegar con Docker — AMD ROCm

```bash
docker run -d --name vllm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=render \
  --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai-rocm:latest \
  --model OpenGVLab/InternVL2-8B \
  --dtype float16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --tensor-parallel-size 1
```

**Variables de entorno ROCm recomendadas:**
```bash
export HSA_OVERRIDE_GFX_VERSION=9.4.2   # Para MI300X (gfx942) si es necesario
export HIP_VISIBLE_DEVICES=0,1           # Seleccionar GPUs específicas
export HIPBLAS_WORKSPACE_CONFIG=:512:8
```

> ⚠️ **HSA_OVERRIDE_GFX_VERSION correcto para MI300X**: El valor correcto es `9.4.2` (gfx942), **no** `11.0.0`. Ver `rocminfo | grep gfx` para determinar tu arquitectura.

### 4. Desplegar con Docker — NVIDIA CUDA

```bash
docker run -d --name vllm \
  --runtime nvidia \
  --gpus all \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model OpenGVLab/InternVL2-8B \
  --dtype bfloat16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --tensor-parallel-size 1 \
  --enable-flash-attention
```

**Variables de entorno NVIDIA recomendadas:**
```bash
export CUDA_VISIBLE_DEVICES=0,1,2,3      # Seleccionar GPUs específicas
export NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

### 5. Desplegar con Docker — CPU Fallback

```bash
docker run -d --name vllm-cpu \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  vllm serve OpenGVLab/InternVL2-8B \
  --device cpu \
  --dtype float32 \
  --max-model-len 2048 \
  --enforce-eager \
  --gpu-memory-utilization 0
```

**Variables de entorno CPU recomendadas:**
```bash
export OMP_NUM_THREADS=$(nproc)          # Número de hilos CPU
export MKL_NUM_THREADS=$(nproc)          # Hilos MKL
```

### 6. Configurar el Modelo

El parámetro más importante es `--dtype`:

| Backend | dtype recomendado | Razón |
|---------|-------------------|-------|
| AMD ROCm | `float16` | ROCm no soporta TF32; float16 ofrece el mejor rendimiento |
| NVIDIA CUDA | `bfloat16` | Mayor rango dinámico que float16; soporte nativo en A100+ |
| CPU | `float32` | Único dtype disponible para CPU |

**Tensor Parallelism** (múltiples GPUs):

```bash
# NVIDIA — usa NCCL
--tensor-parallel-size 4

# AMD ROCm — usa RCCL (compatible con NCCL API)
--tensor-parallel-size 4
```

### 7. Probar Inferencia

**Listar modelos disponibles:**
```bash
curl http://localhost:8000/v1/models
```

**Chat solo texto:**
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "InternVL2-8B",
    "messages": [{"role": "user", "content": "Explain quantum computing in 3 sentences."}],
    "max_tokens": 200,
    "temperature": 0.7
  }'
```

**Chat multimodal (texto + imagen):**
```python
import requests
import base64

# Codificar imagen
with open("imagen.jpg", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

# Enviar petición
resp = requests.post("http://localhost:8000/v1/chat/completions", json={
    "model": "InternVL2-8B",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
            {"type": "text", "text": "Describe esta imagen en detalle."}
        ]
    }],
    "max_tokens": 300,
})
print(resp.json()["choices"][0]["message"]["content"])
```

### 8. Optimizar Rendimiento

Ver [performance-tuning.md](references/performance-tuning.md) para guía completa.

**Ajustes rápidos:**

```bash
# Mayor uso de VRAM (cuidado con OOM)
--gpu-memory-utilization 0.95

# Mayor throughput
--max-num-seqs 512

# Menor latencia (modelos pequeños)
--max-model-len 2048
--gpu-memory-utilization 0.85

# Multi-GPU
--tensor-parallel-size $(nvidia-smi -L | wc -l)  # NVIDIA
--tensor-parallel-size $(rocm-smi --json | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('list',[])))")  # AMD
```

## Reference Documents

| Documento | Descripción |
|-----------|-------------|
| [references/model-configs.md](references/model-configs.md) | Modelos recomendados, VRAM, dtype y configuraciones específicas |
| [references/performance-tuning.md](references/performance-tuning.md) | Optimización de rendimiento por backend, variables de entorno, benchmarking |

## Scripts

| Script | Propósito |
|--------|-----------|
| [scripts/deploy-vllm.sh](scripts/deploy-vllm.sh) | Despliegue automatizado con detección de backend (NVIDIA/AMD/CPU) |
| [scripts/test-vlm.sh](scripts/test-vlm.sh) | Test de inferencia multimodal con métricas de rendimiento |

## Common Issues

### 1. `pip install vllm` instala CUDA en lugar de ROCm
**Causa**: No estás usando Python 3.12. vLLM ROCm wheels solo existen para Python 3.12.
**Solución**: `python3 --version` → debe ser 3.12.x. Si no, crear entorno con Python 3.12:
```bash
uv venv --python 3.12
source .venv/bin/activate
```

### 2. `ModuleNotFoundError: No module named 'vllm'` en contenedor ROCm
**Causa**: El contenedor se construyó correctamente pero el entrypoint no encuentra vLLM.
**Solución**: Usar la imagen oficial `vllm/vllm-openai-rocm:latest` que ya incluye vLLM preinstalado.

### 3. GPU no detectada dentro del contenedor Docker
**Causa**: Faltan flags de dispositivo al ejecutar Docker.
**Solución**:
- AMD: `--device=/dev/kfd --device=/dev/dri --group-add=render`
- NVIDIA: `--runtime nvidia --gpus all`

### 4. `CUDA error: out of memory`
**Causa**: `max_model_len` o `gpu_memory_utilization` demasiado altos para la VRAM disponible.
**Solución**: Reducir `--max-model-len` (ej: 2048) y `--gpu-memory-utilization` (ej: 0.80).

### 5. Inferencia multimodal falla con modelo solo texto
**Causa**: El modelo seleccionado no soporta visión (ej: LLaMA-3.1-8B).
**Solución**: Usar un modelo VLM como InternVL2-8B, Qwen2-VL-7B o LLaVA.

### 6. Rendimiento muy bajo en ROCm comparado con CUDA
**Causa**: dtype incorrecto o falta de optimizaciones ROCm.
**Solución**:
- Usar `--dtype float16` (no bfloat16 ni TF32)
- Verificar `rocminfo | grep gfx` para arquitectura correcta
- No usar `HSA_OVERRIDE_GFX_VERSION` a menos que sea necesario
- Aumentar `--tensor-parallel-size` si hay múltiples GPUs

### 7. `HSA_OVERRIDE_GFX_VERSION=11.0.0` causando errores
**Causa**: Valor incorrecto para MI300X. `11.0.0` es para RDNA3 (RX 7900), no para CDNA3 (MI300X).
**Solución**:
```bash
# Para MI300X (gfx942):
export HSA_OVERRIDE_GFX_VERSION=9.4.2

# Para MI250 (gfx90a):
export HSA_OVERRIDE_GFX_VERSION=9.0.6

# Para RX 7900 XTX (gfx1100):
export HSA_OVERRIDE_GFX_VERSION=11.0.0
```

### 8. El servidor responde pero las peticiones tardan demasiado
**Causa**: Sin GPU o usando CPU fallback involuntariamente.
**Solución**: Verificar que el flag `--device cpu` no esté presente si hay GPU. Verificar logs del contenedor: `docker logs vllm | head -20` debe mostrar el backend detectado.

### 9. Error `ValueError: The model's max model length is too long`
**Causa**: El modelo tiene un `max_position_embeddings` muy grande (ej: 128K) que excede la VRAM.
**Solución**: Forzar `--max-model-len 4096` (o un valor que quepa en tu VRAM).

### 10. Docker: `unknown flag: --device` en Linux
**Causa**: Versión antigua de Docker Engine.
**Solución**: Actualizar Docker Engine a 24+:
```bash
sudo apt-get update && sudo apt-get install docker-ce docker-ce-cli containerd.io
```

## Related Skills

- [`vlm-rocm-inference`](../vlm-rocm-inference/SKILL.md) — Direct PyTorch VLM inference on ROCm/CUDA
- [`rocm-docker`](../rocm-docker/SKILL.md) — Docker with AMD GPU passthrough
- [`rocm-benchmark`](../rocm-benchmark/SKILL.md) — GPU benchmarking and monitoring
