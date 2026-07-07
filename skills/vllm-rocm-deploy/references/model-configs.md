# Model Configurations for vLLM

Configuraciones recomendadas para modelos LLM y VLM en vLLM según el backend disponible (AMD ROCm, NVIDIA CUDA, CPU).

## Recommended Models / Modelos Recomendados

| Modelo | Tipo | VRAM Mínima | ROCm dtype | CUDA dtype | CPU dtype | Performance |
|--------|------|-------------|------------|------------|-----------|-------------|
| [InternVL2-8B](https://huggingface.co/OpenGVLab/InternVL2-8B) | VLM (Lenguaje + Visión) | 24 GB | float16 | bfloat16 | float32 | ⭐ Excelente |
| [InternVL2-26B](https://huggingface.co/OpenGVLab/InternVL2-26B) | VLM (Lenguaje + Visión) | 52 GB | float16 | bfloat16 | — | 🟡 Moderado (requiere MI300X o multi-GPU) |
| [Qwen2-VL-7B](https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct) | VLM (Lenguaje + Visión) | 20 GB | float16 | bfloat16 | float32 | ⭐ Excelente |
| [LLaMA-3.1-8B](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | LLM (Solo texto) | 16 GB | float16 | bfloat16 | float32 | ⭐ Excelente |
| [Mistral-7B](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3) | LLM (Solo texto) | 16 GB | float16 | bfloat16 | float32 | ⭐ Excelente |

### Notas de VRAM

- **VRAM mínima**: asume `max_model_len=4096` y `gpu_memory_utilization=0.90`
- **VRAM adicional** necesaria por cada aumento de contexto:
  - `max_model_len=8192`: +4-8 GB
  - `max_model_len=16384`: +8-16 GB
  - `max_model_len=32768`: +16-32 GB
- **Modelos VLM** (InternVL2, Qwen2-VL) requieren VRAM extra para procesamiento de imágenes (~2-4 GB adicionales)
- Si tu GPU tiene menos VRAM, reducir `max_model_len` o usar `gpu_memory_utilization=0.80`

### Selección Rápida por GPU

| GPU | VRAM | Modelos recomendados |
|-----|------|---------------------|
| NVIDIA RTX 3090 / 4090 | 24 GB | InternVL2-8B, Qwen2-VL-7B, LLaMA-3.1-8B, Mistral-7B |
| NVIDIA A100 40GB | 40 GB | InternVL2-8B, Qwen2-VL-7B, InternVL2-26B (con TP=2) |
| NVIDIA A100 80GB | 80 GB | Cualquier modelo, InternVL2-26B con contexto largo |
| NVIDIA H100 | 80 GB | Cualquier modelo con bfloat16 |
| AMD MI250 | 64 GB | Cualquier modelo con float16 |
| AMD MI300X | 192 GB | Cualquier modelo, contexto muy largo |
| AMD RX 7900 XTX | 24 GB | InternVL2-8B, Qwen2-VL-7B, LLaMA-3.1-8B |
| CPU only | — | Mistral-7B, LLaMA-3.1-8B (más lentos) |

## vLLM Configuration per Model

### InternVL2-8B

Modelo por defecto de Munin. Balance óptimo entre capacidad y VRAM.

**ROCm:**
```bash
docker run --device=/dev/kfd --device=/dev/dri --group-add=render \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai-rocm:latest \
  --model OpenGVLab/InternVL2-8B \
  --dtype float16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --max-num-seqs 256
```

**CUDA:**
```bash
docker run --runtime nvidia --gpus all \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model OpenGVLab/InternVL2-8B \
  --dtype bfloat16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --max-num-seqs 256 \
  --enable-flash-attention
```

**CPU fallback:**
```bash
docker run -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  vllm serve OpenGVLab/InternVL2-8B \
  --device cpu \
  --dtype float32 \
  --max-model-len 2048 \
  --enforce-eager \
  --gpu-memory-utilization 0
```

### InternVL2-26B

Requiere GPU con 52GB+ o multi-GPU con tensor parallelism.

**ROCm (2 GPUs):**
```bash
docker run --device=/dev/kfd --device=/dev/dri --group-add=render \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai-rocm:latest \
  --model OpenGVLab/InternVL2-26B \
  --dtype float16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --tensor-parallel-size 2
```

**CUDA (2 GPUs):**
```bash
docker run --runtime nvidia --gpus all \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model OpenGVLab/InternVL2-26B \
  --dtype bfloat16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --tensor-parallel-size 2
```

### Qwen2-VL-7B

Buen rendimiento en GPUs de 20GB+. Soporta imágenes de alta resolución.

**ROCm:**
```bash
docker run --device=/dev/kfd --device=/dev/dri --group-add=render \
  -p 8000:8000 \
  vllm/vllm-openai-rocm:latest \
  --model Qwen/Qwen2-VL-7B-Instruct \
  --dtype float16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90
```

**CUDA:**
```bash
docker run --runtime nvidia --gpus all \
  -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2-VL-7B-Instruct \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --enable-flash-attention
```

### LLaMA-3.1-8B

Modelo solo texto, rápido, bajo consumo de VRAM. No soporta imágenes.

**ROCm:**
```bash
docker run --device=/dev/kfd --device=/dev/dri --group-add=render \
  -p 8000:8000 \
  vllm/vllm-openai-rocm:latest \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --dtype float16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90
```

**CUDA:**
```bash
docker run --runtime nvidia --gpus all \
  -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --enable-flash-attention
```

### Mistral-7B

Modelo solo texto, muy eficiente. Ideal para CPU y GPUs de baja VRAM.

**ROCm:**
```bash
docker run --device=/dev/kfd --device=/dev/dri --group-add=render \
  -p 8000:8000 \
  vllm/vllm-openai-rocm:latest \
  --model mistralai/Mistral-7B-Instruct-v0.3 \
  --dtype float16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90
```

**CUDA:**
```bash
docker run --runtime nvidia --gpus all \
  -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model mistralai/Mistral-7B-Instruct-v0.3 \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --enable-flash-attention
```

**CPU:**
```bash
docker run -p 8000:8000 \
  vllm/vllm-openai:latest \
  vllm serve mistralai/Mistral-7B-Instruct-v0.3 \
  --device cpu \
  --dtype float32 \
  --max-model-len 4096 \
  --enforce-eager \
  --gpu-memory-utilization 0
```

## Parámetros Clave por Modelo

| Parámetro | InternVL2-8B | InternVL2-26B | Qwen2-VL-7B | LLaMA-3.1-8B | Mistral-7B |
|-----------|:---:|:---:|:---:|:---:|:---:|
| max_model_len (default) | 4096 | 4096 | 8192 | 8192 | 8192 |
| gpu_memory_utilization | 0.90 | 0.90 | 0.90 | 0.90 | 0.90 |
| max_num_seqs | 256 | 128 | 256 | 256 | 256 |
| tensor_parallel_size (recomendado) | 1 | 2+ | 1 | 1 | 1 |
| Multimodal | ✅ Sí | ✅ Sí | ✅ Sí | ❌ No | ❌ No |
| Contexto máximo real | 4096 | 4096 | 32768 | 131072 | 32768 |

## Ajuste de max_model_len por VRAM

Usa esta tabla para determinar el `max_model_len` adecuado según tu VRAM disponible:

| VRAM | InternVL2-8B | InternVL2-26B | Qwen2-VL-7B | LLaMA-3.1-8B | Mistral-7B |
|------|:---:|:---:|:---:|:---:|:---:|
| 16 GB | 2048 | — | 2048 | 4096 | 4096 |
| 24 GB | 4096 | — | 4096 | 8192 | 8192 |
| 32 GB | 8192 | 2048 | 8192 | 16384 | 16384 |
| 48 GB | 16384 | 4096 | 16384 | 32768 | 32768 |
| 80 GB | 32768 | 8192 | 32768 | 65536 | 65536 |
| 192 GB (MI300X) | 65536 | 16384 | 65536 | 131072 | 131072 |

> Los valores son aproximados y dependen del dtype y gpu_memory_utilization. Si encuentras OOM, reduce `max_model_len` o `gpu_memory_utilization`.

## Referencias

- [vLLM Supported Models](https://docs.vllm.ai/en/latest/models/supported_models/)
- [HuggingFace — InternVL2](https://huggingface.co/OpenGVLab/InternVL2-8B)
- [HuggingFace — Qwen2-VL](https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct)
- [HuggingFace — LLaMA 3.1](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct)
- [vLLM AMD Installation](https://docs.vllm.ai/en/latest/getting_started/amd-installation.html)
