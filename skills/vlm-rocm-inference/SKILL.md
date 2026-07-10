---
name: vlm-rocm-inference
description: >
  Inferencia de Vision-Language Models (VLM) en GPU AMD ROCm usando PyTorch
  directo sin vLLM. Cubre carga y ejecución de modelos multimodales (imagen +
  texto) como LLaVA, Qwen2-VL, InternVL2 y PaliGemma con detección automática
  del backend GPU (ROCm, CUDA o CPU). Incluye scripts de inferencia y benchmark
  con métricas de latencia, tokens/s y VRAM. La skill configura el dtype óptimo
  según el backend (float16 para ROCm, bfloat16 para CUDA, float32 para CPU),
  maneja preprocesamiento multimodal, sampling con temperatura/top-p, y
  resolución de issues comunes como OOM, flash-attention no disponible en ROCm,
  y device_map fallback. Ideal para captioning, visual question answering (VQA),
  describe-image, y cualquier tarea de visión-lenguaje en GPUs AMD.
  Keywords: vlm, rocm, amd, multimodal, llava, qwen2-vl, internvl2, paligemma,
  pytorch, inference, vision-language, captioning, vqa, image-description,
  nvidia, cuda, cpu, huggingface, transformers
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: "yechua-silva"
  tags:
    - amd
    - rocm
    - vlm
    - multimodal
    - llava
    - qwen
    - internvl
    - paligemma
    - pytorch
    - inference
    - vision
    - language
    - nvidia
    - cuda
    - cpu
    - huggingface
    - transformers
    - captioning
    - vqa
compatibility: >
  Compatible with Claude Code, OpenCode, Codex, Cursor, Cline, Roo Code,
  Windsurf, Gemini CLI, and Kiro CLI. Requires Linux with AMD ROCm or
  NVIDIA CUDA GPU (CPU fallback supported).
---

# VLM ROCm / CUDA Inference

Inferencia de **Vision-Language Models (VLM)** usando **PyTorch directo** (sin vLLM) con soporte para **AMD ROCm**, **NVIDIA CUDA** y **CPU fallback**. La skill detecta automáticamente el backend disponible, selecciona el dtype óptimo y configura el modelo para máxima compatibilidad con cada plataforma.

## Purpose

- Cargar y ejecutar modelos VLM multimodales (LLaVA, Qwen2-VL, InternVL2, PaliGemma) en GPU AMD ROCm
- Realizar **image captioning**, **visual question answering (VQA)** y **describe image** con PyTorch directo
- Detectar automáticamente el backend GPU y configurar dtype (float16 ROCm, bfloat16 CUDA, float32 CPU)
- Control granular sobre sampling (temperature, top_p, top_k, max_new_tokens)
- Benchmarking de inferencia: latency, time-to-first-token (TTFT), tokens/s, VRAM usage
- Diferenciar cuándo usar PyTorch directo vs vLLM según el caso de uso

## When to Use / Cuándo Usar

- "Run LLaVA on AMD GPU / Ejecutar LLaVA en GPU AMD"
- "Qwen2-VL inference on ROCm / Inferencia Qwen2-VL en ROCm"
- "InternVL2 describe image / Describir imagen con InternVL2"
- "Visual question answering on AMD / Preguntas sobre imágenes en AMD"
- "Image captioning with PaliGemma / Generar descripciones con PaliGemma"
- "Multimodal model PyTorch ROCm / Modelo multimodal PyTorch ROCm"
- "Direct PyTorch VLM inference without vLLM / Inferencia VLM sin vLLM"
- "Alternative to vLLM for unsupported models / Alternativa a vLLM para modelos no soportados"
- Keywords: vlm, llava, qwen2-vl, internvl2, paligemma, multimodal, rocm, cuda, pytorch,
  image-captioning, visual-question-answering, describe-image, inference

## Prerequisites

- [ ] **GPU compatible**: AMD ROCm (MI300X, MI250, RX 7900+) o NVIDIA CUDA (A100, H100, RTX 3090+) con **16GB+ VRAM** (recomendado 24GB+ para modelos 7B-8B)
- [ ] **ROCm** (solo AMD): ROCm 7.2+ instalado — verificar con `rocminfo | grep gfx`
- [ ] **NVIDIA driver** (solo NVIDIA): driver 535+ — verificar con `nvidia-smi`
- [ ] **Python 3.10+** con **PyTorch ROCm** (AMD) o **PyTorch CUDA** (NVIDIA)
- [ ] **transformers >= 4.45.0** (necesario para modelos VLM modernos como Qwen2-VL e InternVL2)
- [ ] **accelerate** (para device_map automático)
- [ ] **flash-attn** (opcional, solo NVIDIA CUDA; no disponible en ROCm 7.2)
- [ ] **Pillow** (para procesamiento de imágenes)
- [ ] **HuggingFace token** (opcional, para modelos con acceso restringido): `huggingface-cli login`
- [ ] **Espacio en disco**: 20GB+ para modelos descargados (~/.cache/huggingface)

## Quickstart

### 1. Detectar GPU y Configurar Entorno

```bash
# Verificar GPU
python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Dispositivos: {torch.cuda.device_count()}, Nombre: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

### 2. Ejecutar Inferencia VLM

```bash
# Inferencia con detección automática de backend
python3 scripts/run-vlm.py \
  --model InternVL2-8B \
  --image https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/300px-PNG_transparency_demonstration_1.png \
  --prompt "Describe esta imagen en detalle."
```

### 3. Ejecutar Benchmark

```bash
# Benchmark completo
python3 scripts/benchmark-vlm.py --model InternVL2-8B --json resultados.json
```

## Step-by-Step

### 1. Detectar Backend GPU (ROCm vs CUDA vs CPU)

El primer paso es identificar qué backend GPU está disponible para configurar el dtype y las optimizaciones correctas:

```python
import torch

def detect_backend():
    if torch.cuda.is_available():
        if hasattr(torch.version, 'hip') and torch.version.hip:
            return 'rocm'
        return 'cuda'
    return 'cpu'

backend = detect_backend()
print(f"Backend detectado: {backend}")
```

**Importante**: ROCm usa la API `torch.cuda` al igual que CUDA. La diferencia se detecta mediante `torch.version.hip`.

### 2. Configurar dtype Según Backend

Cada backend tiene un dtype óptimo para rendimiento y precisión:

```python
def get_optimal_dtype(backend):
    if backend == 'rocm':
        return torch.float16      # ROCm: float16 ofrece el mejor rendimiento
    elif backend == 'cuda':
        return torch.bfloat16     # CUDA: bfloat16 mejor rango dinámico (A100+)
    return torch.float32          # CPU: único dtype disponible

dtype = get_optimal_dtype(backend)
print(f"dtype óptimo: {dtype}")
```

| Backend | dtype recomendado | Razón |
|---------|-------------------|-------|
| AMD ROCm | `float16` | ROCm no soporta TF32; float16 ofrece el mejor rendimiento en GPUs AMD |
| NVIDIA CUDA | `bfloat16` | Mayor rango dinámico que float16; soporte nativo en A100+ |
| CPU | `float32` | Único dtype ampliamente soportado en CPU |

### 3. Instalar Dependencias

```bash
# AMD ROCm — instalar PyTorch desde index ROCm
pip install torch torchvision torchaudio \
  --index-url https://download.pytorch.org/whl/rocm6.2

# NVIDIA CUDA — instalar PyTorch estándar
pip install torch torchvision torchaudio

# CPU — PyTorch sin CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Dependencias comunes
pip install transformers>=4.45.0 accelerate pillow sentencepiece
```

**Versiones recomendadas de PyTorch para ROCm:**

| ROCm | PyTorch | Instalación |
|------|---------|-------------|
| 7.2 | 2.4.0+rocm6.2 | `--index-url https://download.pytorch.org/whl/rocm6.2` |
| 6.2 | 2.3.0+rocm6.1 | `--index-url https://download.pytorch.org/whl/rocm6.1` |
| 6.1 | 2.2.0+rocm6.0 | `--index-url https://download.pytorch.org/whl/rocm6.0` |

### 4. Cargar Modelo VLM con device_map y dtype Correcto

Usar `accelerate` para distribuir el modelo automáticamente según la VRAM disponible:

```python
from transformers import AutoModel, AutoProcessor
import torch

backend = detect_backend()
dtype = get_optimal_dtype(backend)
device = "cuda" if backend != "cpu" else "cpu"

# Cargar processor y modelo
model_name = "OpenGVLab/InternVL2-8B"

processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
model = AutoModel.from_pretrained(
    model_name,
    torch_dtype=dtype,
    device_map="auto" if backend != "cpu" else None,
    trust_remote_code=True,
    use_cache=True,
    attn_implementation="eager"  # ROCm: flash-attn no disponible, usar eager
)

if backend == "cpu":
    model = model.to(device)
```

**Notas importantes:**
- `device_map="auto"` (de accelerate) funciona en ROCm y CUDA, pero puede fallar en modelos VLM con `trust_remote_code`. Si falla, usar `model.to(device)` manual.
- `attn_implementation="eager"` es necesario en ROCm 7.2 porque flash-attention no tiene soporte ROCm. En CUDA se puede usar `"flash_attention_2"` si flash-attn está instalado.
- `use_cache=True` activa el KV-cache, esencial para generación eficiente.

### 5. Preprocesar Imagen

El processor VLM maneja la transformación de la imagen automáticamente:

```python
from PIL import Image
import requests

def load_image(image_source):
    """Carga imagen desde ruta local o URL."""
    if image_source.startswith(("http://", "https://")):
        return Image.open(requests.get(image_source, stream=True).raw)
    return Image.open(image_source)

# Cargar y preprocesar
image = load_image("imagen.jpg")

# El processor VLM redimensiona, normaliza y convierte a tensor automáticamente
# InternVL2 y Qwen2-VL usan procesamiento de imagen propio
```

El processor de cada modelo maneja internamente:
- Redimensionamiento manteniendo aspect ratio
- Normalización (mean/std del modelo)
- Padding a tamaño cuadrado si es necesario
- Conversión a tensor en el dtype/device correcto

**Tamaños de imagen soportados:**

| Modelo | Tamaño máximo | Resolución dinámica |
|--------|---------------|---------------------|
| LLaVA 1.6 | 336x336 | No |
| Qwen2-VL | 1280x1280 | Sí (any resolution) |
| InternVL2 | 448x448 | Sí (dynamic tiling) |
| PaliGemma | 224x224 | No |

### 6. Preprocesar Texto y Generar Input Multimodal

Cada modelo VLM tiene un formato de prompt específico. El processor unifica la creación del input multimodal:

```python
from transformers import AutoProcessor

processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)

# Formato del prompt según el modelo
if "internvl" in model_name.lower():
    prompt = f"<|user|>\n<image>\n{user_prompt}\n<|end|>\n<|assistant|>\n"
elif "qwen" in model_name.lower():
    prompt = [{"role": "user", "content": [{"type": "image", "image": image},
                                           {"type": "text", "text": user_prompt}]}]
elif "llava" in model_name.lower():
    prompt = f"USER: <image>\n{user_prompt}\nASSISTANT:"
elif "paligemma" in model_name.lower():
    prompt = f"caption en\n{user_prompt}"  # PaliGemma usa prefix específico

# Tokenizar (el processor intercala image tokens en el texto)
inputs = processor(
    text=prompt,
    images=image,
    return_tensors="pt",
    padding=True,
    truncation=True
).to(device, dtype=dtype)
```

**Formatos de prompt por modelo:**

| Modelo | Formato |
|--------|---------|
| LLaVA 1.6 | `USER: <image>\n{prompt}\nASSISTANT:` |
| Qwen2-VL | `[{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]` |
| InternVL2 | `<|user|>\n<image>\n{prompt}\n<|end|>\n<|assistant|>\n` |
| PaliGemma | `{prefix}\n{prompt}` (prefix: "caption", "vqa", etc.) |

### 7. Generar Respuesta con Sampling Controlado

```python
outputs = model.generate(
    **inputs,
    max_new_tokens=256,
    temperature=0.7,
    top_p=0.9,
    top_k=50,
    do_sample=True,
    use_cache=True,
    num_beams=1,
    repetition_penalty=1.05,
    pad_token_id=processor.tokenizer.eos_token_id
)

# Decodificar
response = processor.decode(outputs[0], skip_special_tokens=True)
print(f"Respuesta: {response}")
```

**Parámetros de sampling:**

| Parámetro | Default | Rango | Efecto |
|-----------|---------|-------|--------|
| `temperature` | 0.7 | 0.0 - 2.0 | Controla creatividad. 0 = determinista, >1 = más aleatorio |
| `top_p` | 0.9 | 0.0 - 1.0 | Nucleus sampling: selecciona tokens con probabilidad acumulada p |
| `top_k` | 50 | 1 - 1000 | Selecciona solo los k tokens más probables |
| `do_sample` | True | True/False | Activa sampling probabilístico. False = greedy decoding |
| `num_beams` | 1 | 1 - 10 | Beam search. >1 mejora calidad pero es más lento |
| `repetition_penalty` | 1.0 | 1.0 - 2.0 | Penaliza tokens repetidos. >1 reduce repetición |
| `max_new_tokens` | 256 | 1 - 2048 | Número máximo de tokens a generar |

### 8. Post-procesar Output

Limpiar la respuesta eliminando tokens especiales y formato del modelo:

```python
def clean_response(response, model_type="internvl2"):
    """Limpia la respuesta del modelo eliminando tokens de sistema."""
    # Remover tokens especiales según el modelo
    if model_type == "internvl2":
        response = response.replace("<|user|>", "").replace("<|end|>", "")
        response = response.replace("<|assistant|>", "").replace("<image>", "")
    elif model_type == "llava":
        response = response.replace("USER:", "").replace("ASSISTANT:", "")
        response = response.replace("<image>", "")
    elif model_type == "qwen":
        import re
        response = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', response, flags=re.DOTALL)
    
    response = response.strip()
    # Si el modelo repite el prompt, extraer solo la respuesta
    if response.startswith(("Yes", "No", "The image", "En la imagen", "This")):
        return response
    return response
```

### 9. Benchmark de Inferencia

Medir latencia, tokens/s y VRAM:

```python
import time

def benchmark_inference(model, processor, image, prompt, device, dtype,
                        max_new_tokens=256):
    """Mide time-to-first-token, latencia total y tokens/s."""
    
    # Preparar inputs (medir tiempo de preprocesamiento)
    t0 = time.time()
    inputs = processor(text=prompt, images=image, return_tensors="pt").to(device, dtype=dtype)
    prep_time = time.time() - t0
    
    # VRAM antes
    vram_before = torch.cuda.mem_get_info(0) if torch.cuda.is_available() else (0, 0)
    
    # Generar midiendo TTFT y latencia total
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    t1 = time.time()
    
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        temperature=0.7,
        do_sample=True,
        use_cache=True,
        output_attentions=False
    )
    
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    t2 = time.time()
    
    # VRAM después
    vram_after = torch.cuda.mem_get_info(0) if torch.cuda.is_available() else (0, 0)
    
    # Métricas
    total_latency = t2 - t1
    num_tokens = outputs.shape[1] - inputs["input_ids"].shape[1]
    tokens_per_sec = num_tokens / total_latency if total_latency > 0 else 0
    
    vram_free_before, vram_total = vram_before
    vram_free_after, _ = vram_after
    vram_used = (vram_free_before - vram_free_after) / 1e9  # GB
    
    return {
        "total_latency_s": round(total_latency, 2),
        "num_tokens": num_tokens,
        "tokens_per_sec": round(tokens_per_sec, 1),
        "vram_used_gb": round(vram_used, 2),
        "prep_time_s": round(prep_time, 3)
    }
```

## Diferencias con vLLM: Cuándo usar PyTorch directo vs vLLM

### Usar PyTorch Directo (esta skill) CUANDO:

| Escenario | Razón |
|-----------|-------|
| **Modelos no soportados por vLLM** | vLLM soporta ~50 modelos; PyTorch directo corre cualquier modelo de 🤗 Transformers |
| **Fine-tuning o LoRA** | PyTorch directo permite entrenamiento; vLLM es solo inferencia |
| **Control granular** | Acceso completo a hidden states, logits, attentions |
| **Debugging** | Fácil inspeccionar capas, activaciones, gradients |
| **Batch pequeño (< 4)** | Overhead de vLLM no se justifica |
| **ROCm con modelos nuevos** | vLLM ROCm puede tener delays en soporte de modelos nuevos |
| **Prototipado rápido** | Menos configuración, código directo |

### Usar vLLM (vllm-rocm-deploy skill) CUANDO:

| Escenario | Razón |
|-----------|-------|
| **Alto throughput** | vLLM usa PagedAttention y batching continuo |
| **Serving con OpenAI API** | API compatible con `/v1/chat/completions` |
| **Múltiples requests concurrentes** | vLLM maneja cola y batching automático |
| **Latencia consistente** | Mejor que PyTorch para serving en producción |
| **Modelos soportados** | Si vLLM ya soporta el modelo, es más eficiente |
| **Multi-GPU tensor parallelism** | vLLM maneja TP automáticamente |

## Reference Documents

| Documento | Descripción |
|-----------|-------------|
| [references/vlm-models.md](references/vlm-models.md) | Tabla comparativa de modelos VLM: parámetros, VRAM, tamaños de imagen, notas ROCm |
| [references/performance-vlm.md](references/performance-vlm.md) | Optimizaciones específicas por backend, variables de entorno, trade-offs dtype vs accuracy |

## Scripts

| Script | Propósito |
|--------|-----------|
| [scripts/run-vlm.py](scripts/run-vlm.py) | Script principal de inferencia VLM con detección automática de backend, soporte para 4 modelos, sampling y benchmark |
| [scripts/benchmark-vlm.py](scripts/benchmark-vlm.py) | Benchmark de inferencia VLM: TTFT, tokens/s, VRAM peak, múltiples max_new_tokens, output JSON |

## Common Issues

### 1. `torch.cuda.OutOfMemoryError` — OOM durante la carga del modelo

**Causa**: El modelo completo no cabe en VRAM. LLaVA-13B requiere ~26GB FP16, InternVL2-8B requiere ~22GB FP16.

**Solución**:
- Usar `device_map="auto"` para distribuir capas entre CPU y GPU
- Reducir `max_new_tokens` (ej: 128 en lugar de 512)
- Usar un modelo más pequeño: InternVL2-4B en lugar de 8B, o PaliGemma-3B
- Cerrar otros procesos que usen GPU: `fuser -v /dev/nvidia*` / `rocm-smi`
- Forzar `attn_implementation="eager"` (reduce uso de VRAM comparado con flash-attn)
- En CPU: el modelo carga completo en RAM. Asegurar 32GB+ RAM para modelos 7B.

### 2. `flash-attn` no disponible en ROCm 7.2

**Causa**: FlashAttention 2 no tiene soporte oficial para ROCm. Al usar `attn_implementation="flash_attention_2"` en ROCm, falla.

**Solución**:
```python
# Detectar ROCm y forzar eager
if backend == 'rocm':
    attn_impl = "eager"
else:
    try:
        import flash_attn
        attn_impl = "flash_attention_2"
    except ImportError:
        attn_impl = "eager"

model = AutoModel.from_pretrained(
    model_name,
    torch_dtype=dtype,
    attn_implementation=attn_impl,
    ...
)
```

El rendimiento con `eager` es ~20-30% menor que con flash-attention, pero es completamente funcional.

### 3. `device_map="auto"` falla con modelos VLM

**Causa**: `device_map="auto"` de accelerate puede fallar con modelos que usan `trust_remote_code=True` porque el cálculo de memoria no reconoce arquitecturas personalizadas.

**Solución**:
```python
# Opción 1: Cargar sin device_map y asignar manualmente
model = AutoModel.from_pretrained(model_name, torch_dtype=dtype, ...)
model = model.to(device)

# Opción 2: Usar device_map con max_memory
from accelerate import infer_auto_device_map
max_memory = {0: "16GiB", "cpu": "32GiB"}  # Ajustar según VRAM
model = AutoModel.from_pretrained(
    model_name,
    torch_dtype=dtype,
    device_map="auto",
    max_memory=max_memory,
    ...
)
```

### 4. Tokenizer mismatch — `tokenizer()` no acepta `images`

**Causa**: El processor no es el correcto para el modelo VLM. Usar `AutoTokenizer` en lugar de `AutoProcessor` no maneja image tokens.

**Solución**: Usar SIEMPRE `AutoProcessor` para modelos VLM:
```python
# ✅ Correcto
from transformers import AutoProcessor
processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)

# ❌ Incorrecto (no maneja imágenes)
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained(model_name)  # No sirve para VLMs
```

Para LLaVA, usar `LlavaProcessor` específico:
```python
from transformers import LlavaProcessor
processor = LlavaProcessor.from_pretrained(model_name)
```

### 5. Imagen demasiado grande causa OOM en VRAM

**Causa**: Imágenes de alta resolución (> 4K) generan secuencias de image tokens muy largas (ej: Qwen2-VL con imagen 4K → ~4096 image tokens).

**Solución**:
```python
from PIL import Image

def resize_image_for_vlm(image, max_size=768):
    """Redimensiona imagen manteniendo aspect ratio para reducir VRAM."""
    w, h = image.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        image = image.resize(new_size, Image.LANCZOS)
    return image

# Redimensionar antes de pasar al processor
image = resize_image_for_vlm(image, max_size=768)
```

Para Qwen2-VL, además se puede limitar la resolución dinámica:
```python
from transformers import Qwen2VLProcessor
processor = Qwen2VLProcessor.from_pretrained(model_name)
processor.image_processor.do_resize = True
processor.image_processor.size = {"shortest_edge": 448, "longest_edge": 768}
```

### 6. dtype conflict — modelo cargado en float32 cuando debería ser float16

**Causa**: `torch_dtype` no se aplica correctamente porque el modelo tiene capas que fuerzan float32 (ej: layer norms, embeddings).

**Solución**:
```python
# Forzar dtype en todas las capas después de cargar
model = model.to(dtype)

# Verificar dtype real
for name, param in model.named_parameters():
    if param.dtype == torch.float32 and "norm" not in name:
        print(f"  {name}: {param.dtype}")  # Solo algunas norms deben ser float32
        break

# Contar parámetros por dtype
fp16 = sum(p.numel() for p in model.parameters() if p.dtype == torch.float16)
fp32 = sum(p.numel() for p in model.parameters() if p.dtype == torch.float32)
print(f"Parámetros: {fp16/1e6:.0f}M en float16, {fp32/1e6:.0f}M en float32")
```

### 7. `KeyError: 'image_seq_length'` o error similar al cargar InternVL2

**Causa**: Versión de transformers demasiado antigua. InternVL2 requiere transformers >= 4.45.0.

**Solución**:
```bash
pip install --upgrade transformers>=4.45.0
# Verificar versión
python3 -c "import transformers; print(transformers.__version__)"
```

### 8. La generación es muy lenta en CPU

**Causa**: CPU no tiene aceleración para transformers grandes. Modelos 7B+ pueden tomar minutos por respuesta.

**Solución**:
```bash
# Optimizaciones para CPU
export OMP_NUM_THREADS=$(nproc)
export MKL_NUM_THREADS=$(nproc)

# Usar modelo pequeño
python3 scripts/run-vlm.py --model PaliGemma-3B --prompt "Describe" --image foto.jpg

# Reducir max_new_tokens
python3 scripts/run-vlm.py --model PaliGemma-3B --max-tokens 64 --image foto.jpg

# Forzar CPU optimizado con torch.compile (experimental)
model = torch.compile(model, backend="inductor", mode="reduce-overhead")
```

### 9. El output del modelo contiene el prompt repetido

**Causa**: El modelo VLM no separa correctamente el prompt de la respuesta porque el formato de chat es incorrecto o `skip_special_tokens=True` no elimina todos los tokens.

**Solución**:
```python
# Decodificar solo los nuevos tokens
input_len = inputs["input_ids"].shape[1]
new_tokens = outputs[0][input_len:]
response = processor.decode(new_tokens, skip_special_tokens=True)

# O buscar el último token de asistente
response = processor.decode(outputs[0], skip_special_tokens=True)
if "<|assistant|>" in response:
    response = response.split("<|assistant|>")[-1].strip()
if "ASSISTANT:" in response:
    response = response.split("ASSISTANT:")[-1].strip()

## Related Skills

- [`vllm-rocm-deploy`](../vllm-rocm-deploy/SKILL.md) — vLLM deployment for high-throughput LLM serving
- [`video-pipeline-rocm`](../video-pipeline-rocm/SKILL.md) — Video inference pipelines with GStreamer
- [`rocm-benchmark`](../rocm-benchmark/SKILL.md) — GPU benchmarking and monitoring
```
