# VLM Performance — Optimizaciones por Backend

Guía completa de optimización de rendimiento para inferencia de Vision-Language Models con PyTorch directo en AMD ROCm, NVIDIA CUDA y CPU.

## Optimizaciones por Backend

### AMD ROCm

**dtype: float16 (obligatorio)**

ROCm NO soporta TF32. bfloat16 funciona en ROCm 6+ pero float16 ofrece mejor rendimiento en GPUs AMD.

```python
# ROCm: siempre float16
dtype = torch.float16
```

**Attention: eager (obligatorio)**

FlashAttention 2 no tiene soporte oficial para ROCm 7.2. Usar `attn_implementation="eager"`.

```python
model = AutoModel.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    attn_implementation="eager",  # Obligatorio en ROCm
    use_cache=True,
)
```

**torch.compile con inductor (experimental)**

ROCm 7.2+ tiene soporte experimental para `torch.compile` con backend `inductor`:

```python
import torch

# Compilar el modelo (primera ejecución más lenta, luego más rápido)
model = torch.compile(model, backend="inductor", mode="reduce-overhead")

# Verificar que funciona
print(f"torch.compile disponible: {torch.cuda.is_available() and hasattr(torch, 'compile')}")
```

**Variables de entorno ROCm:**

```bash
# Optimizaciones recomendadas para ROCm
export HSA_OVERRIDE_GFX_VERSION=9.4.2   # MI300X (gfx942) — solo si es necesario
export HIP_VISIBLE_DEVICES=0            # Seleccionar GPU específica
export HIPBLAS_WORKSPACE_CONFIG=:512:8  # Workspace HIPBLAS
export ROCR_VISIBLE_DEVICES=0           # Alternativa a HIP_VISIBLE_DEVICES
export OMP_NUM_THREADS=$(nproc)         # Hilos OpenMP para preprocesamiento
export PYTORCH_HIP_ALLOC_CONF=garbage_collection_threshold:0.8  # Gestión de memoria
```

**KV Cache optimizations:**

```python
# Activar KV cache (esencial para generación larga)
model.config.use_cache = True

# ROCm: la KV cache se almacena en float16 por defecto
# No forzar a float32 — duplicaría el uso de VRAM
```

**Resumen ROCm:**

| Parámetro | ROCm |
|-----------|:----:|
| dtype | `float16` |
| attention | `eager` |
| device_map | `auto` (accelerate) |
| torch.compile | `inductor` (experimental) |
| flash-attn | ❌ No soportado |
| TF32 | ❌ No soportado |
| bfloat16 | ⚠️ Funciona pero float16 es mejor |

### NVIDIA CUDA

**dtype: bfloat16 (recomendado)**

GPUs NVIDIA Ampere+ (A100, RTX 3090/4090, H100) soportan bfloat16 nativamente. Ofrece mejor rango dinámico que float16.

```python
# CUDA: bfloat16 para GPUs modernas, float16 para GPUs antiguas
if torch.cuda.get_device_capability(0) >= (8, 0):
    dtype = torch.bfloat16  # A100, H100, RTX 4090
else:
    dtype = torch.float16   # V100, RTX 3090
```

**Attention: flash_attention_2**

```python
try:
    import flash_attn
    attn_impl = "flash_attention_2"
except ImportError:
    attn_impl = "eager"

model = AutoModel.from_pretrained(
    model_name,
    torch_dtype=dtype,
    attn_implementation=attn_impl,
    use_cache=True,
)
```

**TF32 (solo NVIDIA Ampere+):**

```python
# Activar TF32 para matmul (mejora ~50% en operaciones matriciales)
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
```

**torch.compile con cudagraphs (recomendado):**

```python
# CUDA: usar backend cudagraphs para máxima velocidad
model = torch.compile(model, backend="cudagraphs", mode="reduce-overhead")
```

**Variables de entorno CUDA:**

```bash
export CUDA_VISIBLE_DEVICES=0             # Seleccionar GPU
export NVIDIA_DRIVER_CAPABILITIES=compute,utility
export TORCH_CUDNN_V8_API_ENABLED=1       # API cuDNN v8
export CUDA_LAUNCH_BLOCKING=0             # 0 = async (default), 1 = sync (debug)
```

**Resumen CUDA:**

| Parámetro | CUDA (Ampere+) | CUDA (Pre-Ampere) |
|-----------|:--------------:|:------------------:|
| dtype | `bfloat16` | `float16` |
| attention | `flash_attention_2` | `eager` |
| device_map | `auto` | `auto` |
| torch.compile | `cudagraphs` | `inductor` |
| flash-attn | ✅ Sí | ⚠️ Con limitaciones |
| TF32 | ✅ Sí | ❌ No |

### CPU

**dtype: float32 (única opción)**

CPU no soporta float16 ni bfloat16 de forma eficiente en PyTorch. Usar float32 siempre.

```python
dtype = torch.float32
device = "cpu"
```

**Optimizaciones CPU:**

```python
import torch

# torch.compile con backend inductor (mejora ~2x en CPU)
model = torch.compile(model, backend="inductor", mode="reduce-overhead")

# Forzar uso de todos los núcleos
torch.set_num_threads(os.cpu_count())
torch.set_num_interop_threads(os.cpu_count())
```

**Variables de entorno CPU:**

```bash
# Optimizaciones críticas para CPU
export OMP_NUM_THREADS=$(nproc)                      # Todos los núcleos físicos
export MKL_NUM_THREADS=$(nproc)                      # Hilos MKL
export KMP_BLOCKTIME=1                               # Tiempo de bloqueo
export KMP_AFFINITY=granularity=fine,compact,1,0     # Afinidad de hilos
export OMP_SCHEDULE=STATIC                           # Scheduling estático

# Reducir overhead de torch
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:False  # Solo CPU
```

**Modelos ligeros para CPU:**

| Modelo | VRAM RAM | tokens/s (32 hilos) | Recomendado |
|--------|:--------:|:-------------------:|:-----------:|
| PaliGemma-3B | ~18 GB | ~5-15 t/s | ⭐ Mejor opción CPU |
| InternVL2-1B | ~8 GB | ~8-20 t/s | ✅ Muy rápido |
| InternVL2-4B | ~22 GB | ~2-5 t/s | ⚠️ Lento |
| Qwen2-VL-2B | ~14 GB | ~4-10 t/s | ✅ Bueno |
| LLaVA 7B | ~38 GB | ~1-3 t/s | ❌ Muy lento |

**Resumen CPU:**

| Parámetro | CPU |
|-----------|:---:|
| dtype | `float32` |
| attention | `eager` |
| device_map | `None` (model.to("cpu")) |
| torch.compile | `inductor` (experimental) |
| flash-attn | ❌ No |
| TF32 | ❌ No |
| Modelo recomendado | PaliGemma-3B o InternVL2-1B |

## Trade-offs

### dtype vs Accuracy

| dtype | Precisión | VRAM | Velocidad | Backends |
|-------|:---------:|:----:|:---------:|----------|
| float32 | 100% | 4x FP16 | 1x | ROCm, CUDA, CPU |
| float16 | ~99.9% | 2x menos | ~2x | ROCm, CUDA |
| bfloat16 | ~99.95% | 2x menos | ~2x | CUDA (Ampere+), ROCm 6+ |
| int8 | ~98-99% | 4x menos | ~3x | CUDA (con GPTQ/AWQ) |
| int4 | ~95-98% | 8x menos | ~4x | CUDA (con GPTQ/AWQ) |

Para VLM, **float16 y bfloat16 son indistinguibles de float32** en calidad de respuesta. Solo usar float32 si no hay soporte para FP16 (CPU) o para debugging.

### Batch Size vs VRAM

```python
# Batch = 1 (default para inferencia VLM)
# Cada imagen adicional en el batch requiere ~2-4 GB extra

# SIMO procesamiento (Single Image, Multiple Questions)
# Más eficiente que batch: procesar imagen una vez, hacer múltiples preguntas
inputs = processor(text=prompt, images=image, return_tensors="pt")

# Múltiples preguntas sobre la misma imagen
for pregunta in ["Describe", "¿Qué color predomina?", "¿Hay personas?"]:
    # Solo cambiar el texto, misma imagen
    inputs = processor(text=pregunta, images=image, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=128)
```

### max_new_tokens vs Latency

La relación **no es lineal**. Hay overhead fijo de preprocesamiento y forward pass inicial:

```
Latencia total ≈ Latencia prefill + (num_tokens × Latencia por token)
```

Donde:
- **Latencia prefill**: procesamiento de la imagen + prompt (constante, ~0.5-2s)
- **Latencia por token**: ~10-50ms en GPU, ~100-500ms en CPU

| max_new_tokens | Latencia GPU (estimada) | Latencia CPU (estimada) |
|:--------------:|:-----------------------:|:-----------------------:|
| 16 | ~0.8s | ~5s |
| 64 | ~1.2s | ~15s |
| 128 | ~1.8s | ~30s |
| 256 | ~3.0s | ~60s |
| 512 | ~5.5s | ~120s |

### device_map Strategies

| Estrategia | Cuándo usarla | Ventaja | Desventaja |
|------------|---------------|---------|------------|
| `device_map="auto"` | GPU con suficiente VRAM | Distribución automática | Puede fallar con modelos VLM |
| `model.to(device)` | CPU o GPU con VRAM exacta | Simple, predecible | Sin offload a CPU |
| `device_map="auto"` + `max_memory` | VRAM insuficiente | Offload capas a CPU | Más lento si hay offload |
| CPU + GPU híbrido | Modelo grande, VRAM limitada | Ejecuta modelos que no caben | ~10-100x más lento |

## Variables de Entorno Recomendadas por Backend

### AMD ROCm

| Variable | Descripción | Valor Recomendado |
|----------|-------------|-------------------|
| `HSA_OVERRIDE_GFX_VERSION` | Override GFX (solo si necesario) | `9.4.2` (MI300X) |
| `HIP_VISIBLE_DEVICES` | GPUs AMD visibles | `0` |
| `ROCR_VISIBLE_DEVICES` | Alternativa a HIP_VISIBLE_DEVICES | `0` |
| `HIPBLAS_WORKSPACE_CONFIG` | Workspace HIPBLAS | `:512:8` |
| `PYTORCH_HIP_ALLOC_CONF` | Gestión de memoria HIP | `garbage_collection_threshold:0.8` |
| `OMP_NUM_THREADS` | Hilos OpenMP | `$(nproc)` |
| `ROCM_PATH` | Ruta ROCm | `/opt/rocm` |

### NVIDIA CUDA

| Variable | Descripción | Valor Recomendado |
|----------|-------------|-------------------|
| `CUDA_VISIBLE_DEVICES` | GPUs NVIDIA visibles | `0` |
| `NVIDIA_DRIVER_CAPABILITIES` | Capacidades driver | `compute,utility` |
| `TORCH_CUDNN_V8_API_ENABLED` | API cuDNN v8 | `1` |
| `CUDA_LAUNCH_BLOCKING` | Debug (0=async) | `0` |
| `OMP_NUM_THREADS` | Hilos OpenMP | `$(nproc)` |

### CPU

| Variable | Descripción | Valor Recomendado |
|----------|-------------|-------------------|
| `OMP_NUM_THREADS` | Hilos OpenMP | `$(nproc)` |
| `MKL_NUM_THREADS` | Hilos MKL | `$(nproc)` |
| `KMP_BLOCKTIME` | Tiempo bloqueo | `1` |
| `KMP_AFFINITY` | Afinidad hilos | `granularity=fine,compact,1,0` |
| `OMP_SCHEDULE` | Scheduling | `STATIC` |

### Comunes

| Variable | Descripción | Valor Recomendado |
|----------|-------------|-------------------|
| `HF_HOME` | Cache HuggingFace | `~/.cache/huggingface` |
| `TRANSFORMERS_CACHE` | Cache transformers | `~/.cache/huggingface/transformers` |
| `TORCH_HOME` | Cache PyTorch | `~/.cache/torch` |
| `XDG_CACHE_HOME` | Cache general | `~/.cache` |
| `HF_HUB_ENABLE_HF_TRANSFER` | Descarga rápida HF | `1` (instalar `hf-transfer`) |

## Checklist de Optimización

### ROCm
- [ ] Usar `dtype=torch.float16` (NUNCA bfloat16 ni float32)
- [ ] Usar `attn_implementation="eager"` (flash-attn no soportado)
- [ ] Verificar ROCm 7.2+ con `rocminfo | grep gfx`
- [ ] Probar `torch.compile(model, backend="inductor")`
- [ ] Configurar `PYTORCH_HIP_ALLOC_CONF`
- [ ] Verificar `use_cache=True`
- [ ] Redimensionar imágenes > 1024px para reducir VRAM
- [ ] Monitorear VRAM con `rocm-smi`

### NVIDIA
- [ ] Usar `dtype=torch.bfloat16` (Ampere+) o `torch.float16`
- [ ] Instalar `flash-attn`: `pip install flash-attn`
- [ ] Activar TF32: `torch.backends.cuda.matmul.allow_tf32 = True`
- [ ] Probar `torch.compile(model, backend="cudagraphs")`
- [ ] Verificar `use_cache=True`
- [ ] Monitorear VRAM con `nvidia-smi`

### CPU
- [ ] Usar `dtype=torch.float32`
- [ ] Configurar `OMP_NUM_THREADS=$(nproc)`
- [ ] Probar `torch.compile(model, backend="inductor")`
- [ ] Usar modelo pequeño (PaliGemma-3B, InternVL2-1B)
- [ ] Reducir `max_new_tokens` a 64-128
- [ ] Redimensionar imágenes a ≤ 448px

## Referencias

- [PyTorch ROCm Documentation](https://rocm.docs.amd.com/en/latest/how-to/pytorch.html)
- [PyTorch torch.compile](https://pytorch.org/docs/stable/generated/torch.compile.html)
- [HuggingFace Optimization Guide](https://huggingface.co/docs/transformers/perf_infer_gpu_one)
- [FlashAttention 2](https://github.com/Dao-AILab/flash-attention)
- [AMD ROCm GitHub](https://github.com/ROCm/ROCm)
