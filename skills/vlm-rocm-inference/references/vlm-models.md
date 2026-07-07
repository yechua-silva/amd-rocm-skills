# VLM Models for PyTorch ROCm / CUDA Inference

Tabla comparativa de modelos Vision-Language compatibles con inferencia PyTorch directa en AMD ROCm, NVIDIA CUDA y CPU.

## Modelos Soportados

| Modelo | Parámetros | VRAM FP16 | VRAM FP32 | Input Image Size | Lenguaje | Proveedor HF | Notas ROCm |
|--------|:----------:|:---------:|:---------:|:----------------:|:--------:|:------------:|------------|
| **PaliGemma-3B** | 2.9B | 8 GB | 18 GB | 224x224 | EN | [`google/paligemma-3b-mix-224`](https://huggingface.co/google/paligemma-3b-mix-224) | ✅ Excelente en ROCm, carga rápida, bajo VRAM |
| **InternVL2-1B** | 1.0B | 4 GB | 8 GB | 448x448 | EN/ZH | [`OpenGVLab/InternVL2-1B`](https://huggingface.co/OpenGVLab/InternVL2-1B) | ✅ Ideal para CPU y GPUs pequeñas |
| **InternVL2-4B** | 3.8B | 12 GB | 22 GB | 448x448 | EN/ZH | [`OpenGVLab/InternVL2-4B`](https://huggingface.co/OpenGVLab/InternVL2-4B) | ✅ Bueno para GPUs de 16GB |
| **InternVL2-8B** | 8.1B | 22 GB | 40 GB | 448x448 | EN/ZH | [`OpenGVLab/InternVL2-8B`](https://huggingface.co/OpenGVLab/InternVL2-8B) | ⭐ **Recomendado Munin**, balance accuracy/VRAM |
| **InternVL2-26B** | 25.6B | 52 GB | 96 GB | 448x448 | EN/ZH | [`OpenGVLab/InternVL2-26B`](https://huggingface.co/OpenGVLab/InternVL2-26B) | ⚠️ Requiere MI300X o multi-GPU |
| **LLaVA 1.6 Mistral 7B** | 7.0B | 20 GB | 38 GB | 336x336 | EN | [`llava-hf/llava-v1.6-mistral-7b-hf`](https://huggingface.co/llava-hf/llava-v1.6-mistral-7b-hf) | ✅ Bueno en ROCm, comunidad grande |
| **LLaVA 1.6 13B** | 13B | 28 GB | 52 GB | 336x336 | EN | [`llava-hf/llava-v1.6-vicuna-13b-hf`](https://huggingface.co/llava-hf/llava-v1.6-vicuna-13b-hf) | ⚠️ Requiere 32GB+ VRAM |
| **Qwen2-VL-2B** | 2.0B | 6 GB | 14 GB | variable* | EN/ZH/ES | [`Qwen/Qwen2-VL-2B-Instruct`](https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct) | ✅ Ligero, soporta resolución dinámica |
| **Qwen2-VL-7B** | 7.6B | 20 GB | 38 GB | variable* | EN/ZH/ES | [`Qwen/Qwen2-VL-7B-Instruct`](https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct) | ✅ Excelente multilingüe, alta resolución |
| **Qwen2-VL-72B** | 72.7B | 140 GB | 260 GB | variable* | EN/ZH/ES | [`Qwen/Qwen2-VL-72B-Instruct`](https://huggingface.co/Qwen/Qwen2-VL-72B-Instruct) | ⚠️ Solo multi-GPU (4+ MI300X o A100 80GB) |

\* Qwen2-VL soporta **resolución dinámica** — las imágenes se procesan a su resolución nativa hasta 1280x1280. El número de image tokens varía según la resolución.

## VRAM: Cuánto necesitas realmente

La VRAM indicada arriba es para **inferencia básica** (max_new_tokens=256, batch=1). Los valores reales varían según:

| Factor | Impacto en VRAM |
|--------|----------------|
| **max_new_tokens** | +~2 MB por token adicional (KV cache) |
| **Resolución de imagen** | +~1-4 GB para imágenes grandes (4K+) |
| **Batch size** | ~lineal con batch (batch=2 → 2x VRAM) |
| **device_map="auto"** | Distribuye capas entre GPU y CPU (reduce VRAM GPU) |
| **attn_implementation="eager"** | +~5-10% VRAM vs flash-attention |

## Selección Rápida por VRAM

### 16 GB VRAM (RTX 4060 Ti, RTX 3060, RX 7600)

| Modelo | Recomendación | max_new_tokens | Imagen |
|--------|:------------:|:--------------:|:------:|
| InternVL2-4B | ⭐ **Primera opción** | ≤ 256 | ≤ 768px |
| PaliGemma-3B | ✅ Alternativa ligera | ≤ 512 | ≤ 448px |
| Qwen2-VL-2B | ✅ Bueno si necesitas multi-idioma | ≤ 256 | ≤ 768px |
| InternVL2-8B | ❌ No cabe (22GB necesarios) | — | — |
| LLaVA 7B | ❌ No cabe (20GB necesarios) | — | — |

### 24 GB VRAM (RTX 3090, RTX 4090, RX 7900 XTX)

| Modelo | Recomendación | max_new_tokens | Imagen |
|--------|:------------:|:--------------:|:------:|
| InternVL2-8B | ⭐ **Recomendado Munin** | ≤ 512 | ≤ 1024px |
| LLaVA 1.6 7B | ✅ Bueno si prefieres LLaVA | ≤ 512 | ≤ 768px |
| Qwen2-VL-7B | ✅ Excelente multilingüe | ≤ 256 | ≤ 768px |
| InternVL2-4B | ✅ Alternativa más ligera | ≤ 1024 | ≤ 2048px |
| InternVL2-26B | ❌ No cabe (52GB necesarios) | — | — |
| Qwen2-VL-72B | ❌ No cabe | — | — |

### 48 GB VRAM (A100 40GB, MI250 × 1 GCD, 2× RTX 3090)

| Modelo | Recomendación | max_new_tokens | Imagen |
|--------|:------------:|:--------------:|:------:|
| InternVL2-8B | ⭐ Ideal | ≤ 2048 | ≤ 2048px |
| Qwen2-VL-7B | ✅ Ideal para multi-idioma | ≤ 1024 | ≤ 2048px |
| LLaVA 13B | ✅ Bueno si necesitas mayor capacidad | ≤ 512 | ≤ 1024px |
| InternVL2-26B | ❌ Límite (52GB, no cabe) | — | — |

### 192 GB VRAM (MI300X)

| Modelo | Recomendación | max_new_tokens | Imagen |
|--------|:------------:|:--------------:|:------:|
| InternVL2-8B | ⭐ Ideal | ≤ 8192 | ≤ 4096px |
| Qwen2-VL-7B | ✅ Ideal para multi-idioma | ≤ 4096 | ≤ 4096px |
| InternVL2-26B | ⭐ Mejor accuracy | ≤ 2048 | ≤ 2048px |
| Qwen2-VL-72B | ✅ El más capaz | ≤ 1024 | ≤ 2048px |
| LLaVA 13B | ✅ Bueno | ≤ 4096 | ≤ 2048px |

## Recomendación Munin

**InternVL2-8B** es el modelo recomendado por defecto por:

| Ventaja | Detalle |
|---------|---------|
| **Balance accuracy/VRAM** | 8B params caben en 22GB FP16 → funcional en RTX 3090/4090 y RX 7900 |
| **Dynamic tiling** | Procesa imágenes de alta resolución sin OOM |
| **Bilingüe EN/ZH** | Buen rendimiento en ambos idiomas |
| **Transformers nativo** | No requiere `trust_remote_code` complejo |
| **Comunidad activa** | Actualizaciones frecuentes en HuggingFace |

**Segunda opción**: Qwen2-VL-7B si necesitas:
- Soporte multilingüe (español, árabe, etc.)
- Resolución de imagen dinámica nativa
- Mayor contexto (hasta 32K tokens)

**Tercera opción**: PaliGemma-3B si necesitas:
- Inferencia en CPU o GPU con < 12GB VRAM
- Máxima velocidad de inferencia
- Prototipado rápido

## Proveedores HuggingFace — Nombres Exactos

| Modelo | Repo HF |
|--------|---------|
| LLaVA 1.6 Mistral 7B | `llava-hf/llava-v1.6-mistral-7b-hf` |
| LLaVA 1.6 Vicuna 13B | `llava-hf/llava-v1.6-vicuna-13b-hf` |
| Qwen2-VL-2B Instruct | `Qwen/Qwen2-VL-2B-Instruct` |
| Qwen2-VL-7B Instruct | `Qwen/Qwen2-VL-7B-Instruct` |
| Qwen2-VL-72B Instruct | `Qwen/Qwen2-VL-72B-Instruct` |
| InternVL2-1B | `OpenGVLab/InternVL2-1B` |
| InternVL2-4B | `OpenGVLab/InternVL2-4B` |
| InternVL2-8B | `OpenGVLab/InternVL2-8B` |
| InternVL2-26B | `OpenGVLab/InternVL2-26B` |
| PaliGemma 3B Mix 224 | `google/paligemma-3b-mix-224` |

## Referencias

- [HuggingFace — Transformers VLM](https://huggingface.co/docs/transformers/model_doc/auto)
- [InternVL2 GitHub](https://github.com/OpenGVLab/InternVL)
- [Qwen2-VL Blog](https://qwenlm.github.io/blog/qwen2-vl/)
- [LLaVA Project](https://llava-vl.github.io/)
- [PaliGemma Announcement](https://ai.google.dev/gemma/docs/paligemma)
