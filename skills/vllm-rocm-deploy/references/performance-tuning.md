# Performance Tuning for vLLM

Guía completa de optimización de rendimiento para vLLM en AMD ROCm, NVIDIA CUDA y CPU.

## Parámetros Clave de vLLM

| Parámetro | Rango | Default | Efecto |
|-----------|-------|---------|--------|
| `--gpu-memory-utilization` | 0.0 — 1.0 | 0.90 | Fracción de VRAM disponible para el modelo. Mayor = más batch capacity. |
| `--max-num-seqs` | 1 — 1024 | 256 | Máximo de secuencias procesadas simultáneamente. Mayor = más throughput. |
| `--max-model-len` | 128 — 131072 | 4096 | Longitud máxima de contexto (prompt + respuesta). Mayor = más VRAM. |
| `--tensor-parallel-size` | 1 — 8 | 1 | Número de GPUs para tensor parallelism. Escala con GPUs disponibles. |
| `--pipeline-parallel-size` | 1 — 8 | 1 | Número de GPUs para pipeline parallelism. |
| `--enforce-eager` | true/false | false | Desactiva CUDA graphs. Necesario para CPU. |
| `--enable-flash-attention` | true/false | false | Activa Flash Attention (Solo NVIDIA CUDA). |
| `--block-size` | 8, 16, 32 | 16 | Tamaño de bloque para atención PagedAttention. |

### Tabla de Ajustes por Objetivo

| Objetivo | gpu_memory_utilization | max_num_seqs | max_model_len | tensor_parallel_size |
|----------|:----------------------:|:------------:|:-------------:|:--------------------:|
| 🚀 Máximo throughput | 0.95 | 512 | 4096 | máximo disponible |
| ⚡ Mínima latencia | 0.85 | 64 | 2048 | 1 |
| ⚖️ Balanceado | 0.90 | 256 | 4096 | auto |
| 💾 Baja VRAM (16GB) | 0.80 | 128 | 2048 | 1 |
| 🖥️ CPU fallback | 0 | 16 | 2048 | 1 |

## Optimizaciones por Backend

### AMD ROCm

**dtype correcto:**
- Usar SIEMPRE `--dtype float16`
- ROCm **NO** soporta TF32
- bfloat16 funciona en ROCm 6+ pero float16 ofrece mejor rendimiento en GPUs AMD

**Arquitectura GFX correcta:**

Ejecuta `rocminfo | grep gfx` para determinar tu arquitectura:

| GPU | GFX | HSA_OVERRIDE_GFX_VERSION | Notas |
|-----|-----|:------------------------:|-------|
| MI300X | gfx942 | `9.4.2` | ⚠️ NO usar 11.0.0 |
| MI250 | gfx90a | `9.0.6` (solo si necesario) | Generalmente no requiere override |
| MI100 | gfx908 | — | No requiere override |
| RX 7900 XTX | gfx1100 | `11.0.0` (si es necesario) | ROCm 6+ lo soporta nativamente |
| RX 9070 XT | gfx1201 | `11.0.0` | Experimental |

```bash
# Configuración ROCm óptima
export HSA_OVERRIDE_GFX_VERSION=9.4.2   # Solo MI300X si es necesario
export HIP_VISIBLE_DEVICES=0             # Seleccionar GPU
export HIPBLAS_WORKSPACE_CONFIG=:512:8   # Optimización HIPBLAS
export ROCR_VISIBLE_DEVICES=0            # Alternativa a HIP_VISIBLE_DEVICES
```

**Multi-GPU con RCCL:**
```bash
# Tensor parallelism con RCCL (compatible con NCCL API)
--tensor-parallel-size 4

# Variables RCCL
export NCCL_DEBUG=INFO                   # Para debug
export RCCL_MSCCL_ENABLE=1              # Activar MSCpp (si está disponible)
```

**Comando Docker optimizado para ROCm:**
```bash
docker run --device=/dev/kfd --device=/dev/dri --group-add=render \
  --cap-add=SYS_PTRACE --security-opt seccomp=unconfined \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -e HSA_OVERRIDE_GFX_VERSION=9.4.2 \
  -e HIPBLAS_WORKSPACE_CONFIG=:512:8 \
  vllm/vllm-openai-rocm:latest \
  --model OpenGVLab/InternVL2-8B \
  --dtype float16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --max-num-seqs 256
```

**Flags ROCm que NO debes usar:**
- ❌ `--device hip` — No es un flag válido de vLLM
- ❌ `--dtype auto` en ROCm — Puede seleccionar bfloat16 que es subóptimo
- ❌ `--enable-tf32` — No existe en ROCm
- ❌ `HSA_OVERRIDE_GFX_VERSION=11.0.0` — Incorrecto para MI300X

### NVIDIA CUDA

**dtype correcto:**
- Usar `--dtype bfloat16` (A100, H100, RTX 4090+)
- Usar `--dtype float16` si no soporta bfloat16 (RTX 3090, V100)
- Activar TF32 para matrices (mejora ~50% en Ampere+)

```bash
# Configuración NVIDIA óptima
export CUDA_VISIBLE_DEVICES=0,1,2,3       # Seleccionar GPUs
export NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

**Flash Attention:**
```bash
# Activar Flash Attention (reduce uso de VRAM, mejora throughput)
--enable-flash-attention

# vLLM usa Flash Attention automáticamente en GPUs compatibles
# Forzar desactivación si hay inestabilidad:
--disable-flash-attn
```

**TF32 (solo NVIDIA Ampere+):**
```python
# Activar TF32 en PyTorch
import torch
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
```

**Comando Docker optimizado para NVIDIA:**
```bash
docker run --runtime nvidia --gpus all \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -e CUDA_VISIBLE_DEVICES=0 \
  vllm/vllm-openai:latest \
  --model OpenGVLab/InternVL2-8B \
  --dtype bfloat16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --max-num-seqs 256 \
  --enable-flash-attention
```

### CPU

**dtype correcto:**
- Único dtype disponible: `--dtype float32`
- Mucho más lento que GPU. Usar solo para desarrollo/test.

```bash
# Variables de entorno CPU
export OMP_NUM_THREADS=$(nproc)           # Usar todos los núcleos
export MKL_NUM_THREADS=$(nproc)           # Hilos MKL
export KMP_BLOCKTIME=1                    # Tiempo de bloqueo de hilos
export KMP_AFFINITY=granularity=fine,compact,1,0  # Afinidad de hilos
```

**Comando Docker optimizado para CPU:**
```bash
docker run -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -e OMP_NUM_THREADS=$(nproc) \
  -e MKL_NUM_THREADS=$(nproc) \
  vllm/vllm-openai:latest \
  vllm serve OpenGVLab/InternVL2-8B \
  --device cpu \
  --dtype float32 \
  --max-model-len 2048 \
  --max-num-seqs 16 \
  --enforce-eager \
  --gpu-memory-utilization 0
```

## Variables de Entorno por Backend

### AMD ROCm

| Variable | Descripción | Valor Recomendado |
|----------|-------------|-------------------|
| `HSA_OVERRIDE_GFX_VERSION` | Override de arquitectura GFX | `9.4.2` (MI300X), `11.0.0` (RX 7900) |
| `HIP_VISIBLE_DEVICES` | GPUs AMD visibles | `0,1` (según GPUs disponibles) |
| `ROCR_VISIBLE_DEVICES` | Alternativa a HIP_VISIBLE_DEVICES | `0,1` |
| `HIPBLAS_WORKSPACE_CONFIG` | Configuración workspace HIPBLAS | `:512:8` |
| `ROCM_PATH` | Ruta de instalación ROCm | `/opt/rocm` |
| `ROCM_HOME` | Ruta home de ROCm | `/opt/rocm` |
| `NCCL_DEBUG` | Debug de comunicaciones RCCL/NCCL | `INFO` (solo debug) |
| `RCCL_MSCCL_ENABLE` | Activar MSCCL para RCCL | `1` |

### NVIDIA CUDA

| Variable | Descripción | Valor Recomendado |
|----------|-------------|-------------------|
| `CUDA_VISIBLE_DEVICES` | GPUs NVIDIA visibles | `0,1,2,3` |
| `NVIDIA_VISIBLE_DEVICES` | GPUs visibles en Docker | `all` |
| `NVIDIA_DRIVER_CAPABILITIES` | Capacidades del driver | `compute,utility` |
| `CUDA_LAUNCH_BLOCKING` | Debug de lanzamiento CUDA | `1` (solo debug) |
| `TORCH_CUDNN_V8_API_ENABLED` | API cuDNN v8 | `1` |

### CPU

| Variable | Descripción | Valor Recomendado |
|----------|-------------|-------------------|
| `OMP_NUM_THREADS` | Número de hilos OpenMP | `$(nproc)` |
| `MKL_NUM_THREADS` | Número de hilos MKL | `$(nproc)` |
| `KMP_BLOCKTIME` | Tiempo de bloqueo de hilos | `1` |
| `KMP_AFFINITY` | Afinidad de hilos | `granularity=fine,compact,1,0` |
| `OMP_SCHEDULE` | Política de scheduling | `STATIC` |

### Comunes a todos los backends

| Variable | Descripción | Valor Recomendado |
|----------|-------------|-------------------|
| `HF_HOME` | Cache de HuggingFace | `~/.cache/huggingface` |
| `TRANSFORMERS_CACHE` | Cache de transformers | `~/.cache/huggingface/transformers` |
| `TORCH_HOME` | Cache de PyTorch | `~/.cache/torch` |
| `XDG_CACHE_HOME` | Cache general | `~/.cache` |
| `VLLM_USE_V1` | Usar motor vLLM v1 | `1` (experimental, mejora rendimiento) |
| `VLLM_LOGGING_LEVEL` | Nivel de log vLLM | `INFO` (default) |

## Benchmarking Guide

### Medición Rápida con curl

```bash
# Medir tiempo de respuesta
time curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "InternVL2-8B",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100,
    "temperature": 0
  }' | python3 -c "
import json, sys
data = json.load(sys.stdin)
usage = data.get('usage', {})
print(f'Prompt tokens: {usage.get(\"prompt_tokens\", \"?\")}')
print(f'Completion tokens: {usage.get(\"completion_tokens\", \"?\")}')
print(f'Total tokens: {usage.get(\"total_tokens\", \"?\")}')
"
```

### Script de Benchmark

```bash
#!/bin/bash
# benchmark.sh — Mide throughput y latencia de vLLM
# Dependencias: pip install aiohttp tqdm

cat << 'PYEOF' | python3
import asyncio
import aiohttp
import time
import json

SERVER = "http://localhost:8000"
MODEL = "InternVL2-8B"
PROMPT = "What is the meaning of life in 3 sentences?"
REQUESTS = 10
CONCURRENT = 4
MAX_TOKENS = 200

async def single_request(session, sem, idx):
    async with sem:
        start = time.time()
        try:
            async with session.post(
                f"{SERVER}/v1/chat/completions",
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": PROMPT}],
                    "max_tokens": MAX_TOKENS,
                    "temperature": 0,
                },
                timeout=aiohttp.ClientTimeout(total=300)
            ) as resp:
                data = await resp.json()
                elapsed = time.time() - start
                usage = data.get("usage", {})
                completion_tokens = usage.get("completion_tokens", 0)
                prompt_tokens = usage.get("prompt_tokens", 0)
                return {
                    "ok": resp.status == 200,
                    "elapsed": elapsed,
                    "completion_tokens": completion_tokens,
                    "prompt_tokens": prompt_tokens,
                    "total_tokens": completion_tokens + prompt_tokens,
                    "code": resp.status,
                }
        except Exception as e:
            return {"ok": False, "elapsed": time.time() - start, "error": str(e)}

async def run_benchmark():
    sem = asyncio.Semaphore(CONCURRENT)
    async with aiohttp.ClientSession() as session:
        tasks = [single_request(session, sem, i) for i in range(REQUESTS)]
        results = await asyncio.gather(*tasks)
    
    ok_results = [r for r in results if r.get("ok")]
    
    print(f"\n{'='*50}")
    print(f"  Benchmark vLLM — {MODEL}")
    print(f"  Requests: {REQUESTS} | Concurrent: {CONCURRENT} | Max tokens: {MAX_TOKENS}")
    print(f"{'='*50}")
    
    if not ok_results:
        print(f"\n  ❌ Todos los requests fallaron")
        for r in results[:3]:
            print(f"  Error: {r.get('error', 'unknown')}")
        return
    
    elapsed_list = [r["elapsed"] for r in ok_results]
    total_completion = sum(r["completion_tokens"] for r in ok_results)
    total_prompt = sum(r["prompt_tokens"] for r in ok_results)
    total_time = sum(elapsed_list)
    
    print(f"\n  ✅ Requests exitosos: {len(ok_results)}/{len(results)}")
    print(f"")
    print(f"  ⏱  Latencia:")
    print(f"     Promedio: {sum(elapsed_list)/len(elapsed_list)*1000:.0f}ms")
    print(f"     P50:      {sorted(elapsed_list)[len(elapsed_list)//2]*1000:.0f}ms")
    print(f"     P95:      {sorted(elapsed_list)[int(len(elapsed_list)*0.95)]*1000:.0f}ms")
    print(f"     P99:      {sorted(elapsed_list)[int(len(elapsed_list)*0.99)]*1000:.0f}ms")
    print(f"")
    print(f"  📊 Throughput:")
    print(f"     Total tokens completados: {total_completion}")
    print(f"     Tiempo total de generación: {total_time:.1f}s")
    print(f"     Throughput: {total_completion/total_time:.1f} tokens/s")
    print(f"     Requests/s: {len(ok_results)/total_time:.1f} req/s")
    print(f"")

asyncio.run(run_benchmark())
PYEOF
```

### Interpretación de Resultados

| Métrica | Qué mide | Bueno | Excelente | Cómo mejorar |
|---------|----------|:-----:|:---------:|--------------|
| **Latencia P50** | Tiempo de respuesta típico | < 2000ms | < 500ms | Reducir max_num_seqs, reducir max_model_len, dtype más rápido |
| **Throughput** | Tokens generados por segundo | > 50 t/s | > 200 t/s | Aumentar max_num_seqs, tensor_parallel_size, gpu_memory_utilization |
| **Requests/s** | Peticiones por segundo | > 5 req/s | > 20 req/s | Aumentar concurrencia, batch size |
| **VRAM usada** | Memoria GPU consumida | < 90% | < 80% | Reducir gpu_memory_utilization, max_model_len, max_num_seqs |

### Valores de Referencia (Aproximados)

| Configuración | Latencia P50 | Throughput | VRAM |
|---------------|:-----------:|:----------:|:----:|
| InternVL2-8B en MI300X (float16) | ~800ms | ~120 t/s | ~22 GB |
| InternVL2-8B en A100 80GB (bfloat16) | ~500ms | ~180 t/s | ~20 GB |
| InternVL2-8B en RTX 4090 (bfloat16) | ~600ms | ~150 t/s | ~20 GB |
| LLaMA-3.1-8B en A100 (bfloat16) | ~300ms | ~250 t/s | ~16 GB |
| Mistral-7B en CPU (32 hilos) | ~5000ms | ~15 t/s | ~16 GB RAM |

> Los valores son orientativos y varían según carga, modelo exacto, parámetros y versión de vLLM.

## Checklist de Optimización

### ROCm
- [ ] Usar `--dtype float16` (no bfloat16, no TF32)
- [ ] Verificar `rocminfo | grep gfx` para arquitectura correcta
- [ ] NO usar `HSA_OVERRIDE_GFX_VERSION=11.0.0` en MI300X (usar `9.4.2`)
- [ ] Usar `--gpu-memory-utilization 0.90` (0.95 si sobra VRAM)
- [ ] Ajustar `--max-num-seqs` según throughput deseado
- [ ] Activar `--tensor-parallel-size` si hay múltiples GPUs
- [ ] Monitorear con `rocm-smi` temperatura y consumo

### NVIDIA
- [ ] Usar `--dtype bfloat16` (si GPU lo soporta)
- [ ] Activar `--enable-flash-attention`
- [ ] Activar TF32 en PyTorch (Ampere+)
- [ ] Usar `--gpu-memory-utilization 0.90`
- [ ] Monitorear con `nvidia-smi` temperatura y consumo

### CPU
- [ ] Usar `--device cpu` y `--enforce-eager`
- [ ] Configurar `OMP_NUM_THREADS` = número de núcleos
- [ ] Reducir `--max-model-len` a 2048 o menos
- [ ] Reducir `--max-num-seqs` a 16 o menos
- [ ] Usar modelos pequeños (Mistral-7B, LLaMA-3.1-8B)

## Referencias

- [vLLM Performance Tuning Guide](https://docs.vllm.ai/en/latest/performance/performance_tuning.html)
- [vLLM ROCm Installation](https://docs.vllm.ai/en/latest/getting_started/amd-installation.html)
- [AMD ROCm Documentation](https://rocm.docs.amd.com/)
- [ROCm vLLM Wheels](https://wheels.vllm.ai/rocm/)
- [vLLM GitHub — ROCm Issues](https://github.com/vllm-project/vllm/issues?q=is%3Aissue+is%3Aopen+rocm)
