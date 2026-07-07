#!/usr/bin/env python3
"""
run-vlm.py — VLM Inference on AMD ROCm / NVIDIA CUDA / CPU
===========================================================
Carga y ejecuta modelos Vision-Language (LLaVA, Qwen2-VL, InternVL2, PaliGemma)
con detección automática de backend GPU.

Uso:
  python3 scripts/run-vlm.py --model InternVL2-8B --image foto.jpg --prompt "Describe"
  python3 scripts/run-vlm.py --model Qwen2-VL-7B --image https://ejemplo.com/img.jpg
  python3 scripts/run-vlm.py --model LLaVA --image foto.jpg --stream
  python3 scripts/run-vlm.py --model PaliGemma-3B --device cpu --max-tokens 64
  python3 scripts/run-vlm.py --benchmark --image test.jpg
"""

import argparse
import importlib
import json
import os
import sys
import time
from typing import Optional, Tuple

# ─── Detección de backend ─────────────────────────────────────

def detect_backend() -> Tuple[str, str]:
    """Detecta backend GPU disponible.
    
    Returns:
        Tuple de (backend: str, device_name: str)
        backend: "rocm", "cuda", o "cpu"
    """
    try:
        import torch
    except ImportError:
        return "cpu", "No PyTorch"
    
    if not torch.cuda.is_available():
        return "cpu", "No GPU detected"
    
    device_name = torch.cuda.get_device_name(0)
    if hasattr(torch.version, 'hip') and torch.version.hip:
        return "rocm", device_name
    
    return "cuda", device_name


def get_optimal_dtype(backend: str):
    """Retorna el dtype óptimo según el backend."""
    import torch
    if backend == "rocm":
        return torch.float16
    elif backend == "cuda":
        return torch.bfloat16
    return torch.float32


def get_device(backend: str) -> str:
    """Retorna el device string según el backend."""
    return "cuda" if backend != "cpu" else "cpu"


def get_attn_implementation(backend: str) -> str:
    """Retorna la implementación de atención según backend.
    
    ROCm: flash-attn no soportado oficialmente → eager
    CUDA: flash-attn si está instalado
    """
    if backend == "rocm":
        return "eager"
    # Intentar flash-attn para CUDA
    if backend == "cuda":
        try:
            importlib.import_module("flash_attn")
            return "flash_attention_2"
        except ImportError:
            return "eager"
    return "eager"


# ─── Configuración de modelos ──────────────────────────────────

MODEL_CONFIGS = {
    "LLaVA": {
        "name": "llava-hf/llava-v1.6-mistral-7b-hf",
        "type": "llava",
        "model_class": "LlavaForConditionalGeneration",
        "processor_class": "LlavaProcessor",
        "prompt_format": "USER: <image>\n{prompt}\nASSISTANT:",
        "min_vram_gb": 20,
        "description": "LLaVA 1.6 Mistral 7B — buen balance accuracy/velocidad",
    },
    "Qwen2-VL-7B": {
        "name": "Qwen/Qwen2-VL-7B-Instruct",
        "type": "qwen2_vl",
        "model_class": "Qwen2VLForConditionalGeneration",
        "processor_class": "AutoProcessor",
        "prompt_format": None,  # Qwen usa formato conversacional
        "min_vram_gb": 20,
        "description": "Qwen2-VL 7B — excelente soporte multilingüe, alta resolución",
    },
    "InternVL2-8B": {
        "name": "OpenGVLab/InternVL2-8B",
        "type": "internvl2",
        "model_class": "AutoModel",
        "processor_class": "AutoProcessor",
        "prompt_format": "<|user|>\n<image>\n{prompt}\n<|end|>\n<|assistant|>\n",
        "min_vram_gb": 22,
        "description": "InternVL2-8B — recomendado Munin, mejor balance accuracy/VRAM",
    },
    "InternVL2-4B": {
        "name": "OpenGVLab/InternVL2-4B",
        "type": "internvl2",
        "model_class": "AutoModel",
        "processor_class": "AutoProcessor",
        "prompt_format": "<|user|>\n<image>\n{prompt}\n<|end|>\n<|assistant|>\n",
        "min_vram_gb": 12,
        "description": "InternVL2-4B — modelo ligero para GPUs de 16GB",
    },
    "PaliGemma-3B": {
        "name": "google/paligemma-3b-mix-224",
        "type": "paligemma",
        "model_class": "PaliGemmaForConditionalGeneration",
        "processor_class": "PaliGemmaProcessor",
        "prompt_format": "caption en\n{prompt}",
        "min_vram_gb": 8,
        "description": "PaliGemma 3B — muy ligero, ideal para CPU y GPUs pequeñas",
    },
}

MODEL_ALIASES = {
    "llava": "LLaVA",
    "llava-7b": "LLaVA",
    "qwen2-vl": "Qwen2-VL-7B",
    "qwen2-vl-7b": "Qwen2-VL-7B",
    "qwen2": "Qwen2-VL-7B",
    "qwen": "Qwen2-VL-7B",
    "internvl2": "InternVL2-8B",
    "internvl2-8b": "InternVL2-8B",
    "internvl2-4b": "InternVL2-4B",
    "internvl": "InternVL2-8B",
    "paligemma": "PaliGemma-3B",
    "paligemma-3b": "PaliGemma-3B",
    "gemma": "PaliGemma-3B",
}

# ─── Prompt templates por modelo ──────────────────────────────

def build_prompt(model_type: str, user_prompt: str, model_config: dict) -> str:
    """Construye el prompt según el formato del modelo."""
    fmt = model_config["prompt_format"]
    if fmt:
        return fmt.format(prompt=user_prompt)
    # Qwen2-VL usa formato conversacional
    return None  # Se maneja por separado


def build_qwen2_vl_messages(user_prompt: str):
    """Construye mensajes para Qwen2-VL en formato conversacional."""
    return [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": user_prompt},
            ],
        }
    ]


# ─── Carga de modelo ──────────────────────────────────────────

def load_model_and_processor(
    model_key: str, device: str, dtype, attn_impl: str
):
    """Carga modelo VLM y processor."""
    import torch
    from transformers import (
        AutoModel,
        AutoProcessor,
        LlavaForConditionalGeneration,
        LlavaProcessor,
        PaliGemmaForConditionalGeneration,
        PaliGemmaProcessor,
        Qwen2VLForConditionalGeneration,
    )
    
    config = MODEL_CONFIGS[model_key]
    model_name = config["name"]
    model_type = config["type"]
    
    print(f"  Cargando modelo: {model_name}")
    print(f"  dtype: {dtype}, attention: {attn_impl}")
    print(f"  device_map: {'auto' if device != 'cpu' else 'manual'}")
    print()
    
    # Cargar processor
    if model_type == "llava":
        processor = LlavaProcessor.from_pretrained(model_name)
    elif model_type == "paligemma":
        processor = PaliGemmaProcessor.from_pretrained(model_name)
    else:
        processor = AutoProcessor.from_pretrained(
            model_name, trust_remote_code=True
        )
    
    # Cargar modelo
    load_kwargs = {
        "torch_dtype": dtype,
        "trust_remote_code": True,
        "use_cache": True,
        "attn_implementation": attn_impl,
    }
    
    if device != "cpu":
        load_kwargs["device_map"] = "auto"
    
    if model_type == "llava":
        model = LlavaForConditionalGeneration.from_pretrained(
            model_name, **load_kwargs
        )
    elif model_type == "paligemma":
        model = PaliGemmaForConditionalGeneration.from_pretrained(
            model_name, **load_kwargs
        )
    elif model_type == "qwen2_vl":
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_name, **load_kwargs
        )
    else:
        model = AutoModel.from_pretrained(model_name, **load_kwargs)
    
    # Si device_map falló o es CPU, mover manualmente
    if device == "cpu" or not hasattr(model, "hf_device_map"):
        model = model.to(device)
    
    model.eval()
    return model, processor, model_type, model_name


# ─── Carga de imagen ──────────────────────────────────────────

def load_image(image_source: str):
    """Carga imagen desde ruta local o URL."""
    from PIL import Image
    import requests
    
    if image_source.startswith(("http://", "https://")):
        response = requests.get(image_source, stream=True, timeout=30)
        response.raise_for_status()
        return Image.open(response.raw)
    return Image.open(image_source)


def resize_for_vram(image, max_size: int = 768):
    """Redimensiona imagen para reducir VRAM."""
    from PIL import Image
    w, h = image.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        image = image.resize(new_size, Image.LANCZOS)
    return image


# ─── Inferencia ────────────────────────────────────────────────

def run_inference(
    model,
    processor,
    model_type: str,
    model_name: str,
    image,
    user_prompt: str,
    device: str,
    dtype,
    max_new_tokens: int = 256,
    temperature: float = 0.7,
    top_p: float = 0.9,
    do_sample: bool = True,
    stream: bool = False,
    benchmark: bool = False,
):
    """Ejecuta inferencia VLM y retorna respuesta + métricas."""
    import torch
    
    # ── Preparar inputs ──────────────────────────────────────
    t_start = time.time()
    
    if model_type == "qwen2_vl":
        messages = build_qwen2_vl_messages(user_prompt)
        inputs = processor(
            text=messages,
            images=image,
            return_tensors="pt",
            padding=True,
        ).to(device, dtype=dtype)
    else:
        # Encontrar config para este model_type
        model_cfg = None
        for cfg in MODEL_CONFIGS.values():
            if cfg["type"] == model_type:
                model_cfg = cfg
                break
        prompt = build_prompt(model_type, user_prompt, model_cfg)
        inputs = processor(
            text=prompt,
            images=image,
            return_tensors="pt",
            padding=True,
            truncation=True,
        ).to(device, dtype=dtype)
    
    prep_time = time.time() - t_start
    
    # ── Medir VRAM antes ─────────────────────────────────────
    vram_free_before, vram_total = 0, 0
    if torch.cuda.is_available():
        vram_free_before, vram_total = torch.cuda.mem_get_info(0)
    
    # ── Generar ──────────────────────────────────────────────
    if stream:
        return _stream_inference(
            model, inputs, processor, max_new_tokens, temperature,
            top_p, do_sample, device, prep_time, vram_free_before, vram_total
        )
    
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    t_gen_start = time.time()
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,
            use_cache=True,
            pad_token_id=processor.tokenizer.eos_token_id
            if hasattr(processor, "tokenizer")
            else None,
        )
    
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    gen_time = time.time() - t_gen_start
    
    # ── Medir VRAM después ───────────────────────────────────
    vram_free_after = 0
    if torch.cuda.is_available():
        vram_free_after, _ = torch.cuda.mem_get_info(0)
    
    # ── Decodificar ──────────────────────────────────────────
    input_len = inputs["input_ids"].shape[1]
    new_tokens = outputs[0][input_len:]
    response = processor.decode(new_tokens, skip_special_tokens=True)
    response = _clean_response(response, model_type)
    
    num_tokens = outputs.shape[1] - input_len
    tokens_per_sec = num_tokens / gen_time if gen_time > 0 else 0
    vram_delta = (vram_free_before - vram_free_after) / 1e9  # GB
    
    metrics = {
        "prep_time_s": round(prep_time, 2),
        "gen_time_s": round(gen_time, 2),
        "total_latency_s": round(prep_time + gen_time, 2),
        "num_tokens": num_tokens,
        "tokens_per_sec": round(tokens_per_sec, 1),
        "vram_before_gb": round(vram_free_before / 1e9, 2) if vram_free_before else 0,
        "vram_after_gb": round(vram_free_after / 1e9, 2) if vram_free_after else 0,
        "vram_delta_gb": round(vram_delta, 2),
    }
    
    if benchmark:
        _print_metrics(metrics)
    
    return response, metrics


def _stream_inference(
    model, inputs, processor, max_new_tokens, temperature, top_p,
    do_sample, device, prep_time, vram_free_before, vram_total
):
    """Inferencia con streaming token a token."""
    import torch
    
    input_len = inputs["input_ids"].shape[1]
    generated_tokens = []
    t_start = time.time()
    
    for _ in range(max_new_tokens):
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=len(generated_tokens) + 1,
                temperature=temperature,
                top_p=top_p,
                do_sample=do_sample,
                use_cache=True,
            )
        
        new_token = outputs[0][-1]
        generated_tokens.append(new_token.item())
        
        # Mostrar token en tiempo real
        token_text = processor.decode([new_token.item()], skip_special_tokens=True)
        print(token_text, end="", flush=True)
        
        # Verificar EOS
        if new_token.item() == processor.tokenizer.eos_token_id:
            break
    
    print()
    gen_time = time.time() - t_start
    
    # Decodificar completa
    full_output = outputs[0]
    new_tokens = full_output[input_len:]
    response = processor.decode(new_tokens, skip_special_tokens=True)
    response = _clean_response(response, "generic")
    
    num_tokens = len(generated_tokens)
    tokens_per_sec = num_tokens / gen_time if gen_time > 0 else 0
    
    vram_free_after = 0
    if torch.cuda.is_available():
        vram_free_after, _ = torch.cuda.mem_get_info(0)
    vram_delta = (vram_free_before - vram_free_after) / 1e9
    
    metrics = {
        "prep_time_s": round(prep_time, 2),
        "gen_time_s": round(gen_time, 2),
        "total_latency_s": round(prep_time + gen_time, 2),
        "num_tokens": num_tokens,
        "tokens_per_sec": round(tokens_per_sec, 1),
        "vram_delta_gb": round(vram_delta, 2),
    }
    
    return response, metrics


def _clean_response(response: str, model_type: str) -> str:
    """Limpia la respuesta de tokens especiales."""
    import re
    response = response.strip()
    
    # Remover tokens de sistema por modelo
    if model_type == "internvl2":
        response = response.replace("<|user|>", "").replace("<|end|>", "")
        response = response.replace("<|assistant|>", "").replace("<image>", "")
    elif model_type == "llava":
        response = response.replace("USER:", "").replace("ASSISTANT:", "")
        response = response.replace("<image>", "")
    elif model_type == "qwen2_vl":
        response = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', response, flags=re.DOTALL)
    elif model_type == "paligemma":
        # PaliGemma puede repetir el prefix
        response = re.sub(r'^caption en\n', '', response)
    
    return response.strip()


def _print_metrics(metrics: dict):
    """Imprime métricas de rendimiento."""
    print()
    print("  ── Métricas ──────────────────────────")
    print(f"  Tiempo preparación:    {metrics['prep_time_s']}s")
    print(f"  Tiempo generación:     {metrics['gen_time_s']}s")
    print(f"  Latencia total:        {metrics['total_latency_s']}s")
    print(f"  Tokens generados:      {metrics['num_tokens']}")
    print(f"  Throughput:            {metrics['tokens_per_sec']} tokens/s")
    if 'vram_delta_gb' in metrics and metrics['vram_delta_gb']:
        print(f"  VRAM delta:            {metrics['vram_delta_gb']:.2f} GB")
    print("  ─────────────────────────────────────")
    print()


# ─── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="VLM Inference — AMD ROCm / NVIDIA CUDA / CPU",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s --model InternVL2-8B --image foto.jpg --prompt "Describe"
  %(prog)s --model Qwen2-VL-7B --image https://ejemplo.com/img.jpg
  %(prog)s --model LLaVA --image foto.jpg --stream --temperature 0.9
  %(prog)s --model PaliGemma-3B --device cpu --max-tokens 64
  %(prog)s --benchmark --image test.jpg

Modelos:
  InternVL2-8B   (OpenGVLab/InternVL2-8B)          — Recomendado
  InternVL2-4B   (OpenGVLab/InternVL2-4B)          — Ligero 16GB
  LLaVA          (llava-hf/llava-v1.6-mistral-7b-hf)
  Qwen2-VL-7B    (Qwen/Qwen2-VL-7B-Instruct)
  PaliGemma-3B   (google/paligemma-3b-mix-224)     — Muy ligero
        """
    )
    
    parser.add_argument(
        "--model", "-m", type=str, default="auto",
        help="Modelo VLM (auto-detecta según VRAM disponible)"
    )
    parser.add_argument(
        "--image", "-i", type=str, required=True,
        help="Ruta o URL de la imagen"
    )
    parser.add_argument(
        "--prompt", "-p", type=str, default="Describe esta imagen en detalle.",
        help="Prompt de texto para la inferencia"
    )
    parser.add_argument(
        "--device", "-d", type=str, default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Forzar device (auto = detectar backend)"
    )
    parser.add_argument(
        "--max-tokens", type=int, default=256,
        help="Máximo de tokens a generar (default: 256)"
    )
    parser.add_argument(
        "--temperature", "-t", type=float, default=0.7,
        help="Temperatura de sampling (default: 0.7)"
    )
    parser.add_argument(
        "--top-p", type=float, default=0.9,
        help="Top-p nucleus sampling (default: 0.9)"
    )
    parser.add_argument(
        "--stream", action="store_true",
        help="Activar streaming de tokens"
    )
    parser.add_argument(
        "--benchmark", action="store_true",
        help="Mostrar métricas de rendimiento detalladas"
    )
    parser.add_argument(
        "--no-sample", action="store_true",
        help="Desactivar sampling (greedy decoding)"
    )
    parser.add_argument(
        "--resize", type=int, default=0,
        help="Redimensionar imagen al tamaño máximo especificado (píxeles)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output en JSON"
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="Listar modelos disponibles y salir"
    )
    
    args = parser.parse_args()
    
    # ── Listar modelos ─────────────────────────────────
    if args.list_models:
        print("Modelos VLM disponibles:\n")
        for key, config in MODEL_CONFIGS.items():
            print(f"  {key:20s} — {config['description']}")
            print(f"                    Repo: {config['name']}")
            print(f"                    VRAM mín: {config['min_vram_gb']}GB (FP16)")
            print()
        return
    
    # ── Detectar backend ───────────────────────────────
    backend, device_name = detect_backend()
    
    if args.device != "auto":
        if args.device == "cpu":
            backend = "cpu"
            device_name = "CPU (forzado)"
        elif args.device == "cuda":
            if backend == "cpu":
                print("ERROR: Se forzó device=cuda pero no hay GPU disponible.")
                sys.exit(1)
            # Mantener backend detectado (rocm o cuda)
    
    import torch
    dtype = get_optimal_dtype(backend)
    device = get_device(backend)
    attn_impl = get_attn_implementation(backend)
    
    # ── Seleccionar modelo ─────────────────────────────
    model_key = args.model
    if model_key == "auto":
        # Auto-detectar según VRAM
        vram_gb = 0
        if torch.cuda.is_available():
            vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        
        if vram_gb >= 22:
            model_key = "InternVL2-8B"
        elif vram_gb >= 12:
            model_key = "InternVL2-4B"
        elif vram_gb >= 8:
            model_key = "LLaVA"
        else:
            model_key = "PaliGemma-3B"
    else:
        # Resolver alias
        model_key_lower = model_key.lower()
        if model_key_lower in MODEL_ALIASES:
            model_key = MODEL_ALIASES[model_key_lower]
        
        if model_key not in MODEL_CONFIGS:
            print(f"ERROR: Modelo '{model_key}' no reconocido.")
            print("Modelos disponibles:", ", ".join(MODEL_CONFIGS.keys()))
            print("Alias:", ", ".join(MODEL_ALIASES.keys()))
            sys.exit(1)
    
    config = MODEL_CONFIGS[model_key]
    
    # ── Banner ─────────────────────────────────────────
    print()
    print("=" * 55)
    print("  VLM Inference — Munin")
    print("=" * 55)
    print(f"  Modelo:       {model_key}")
    print(f"  Repo:         {config['name']}")
    print(f"  Backend:      {backend.upper()}")
    print(f"  Dispositivo:  {device_name}")
    print(f"  dtype:        {dtype}")
    print(f"  Attention:    {attn_impl}")
    print(f"  Prompt:       \"{args.prompt[:60]}{'...' if len(args.prompt) > 60 else ''}\"")
    print(f"  Imagen:       {args.image}")
    print(f"  Parámetros:   max_tokens={args.max_tokens}, "
          f"temperature={args.temperature}, top_p={args.top_p}")
    print()
    
    # ── Cargar modelo ─────────────────────────────────
    try:
        model, processor, model_type, model_name = load_model_and_processor(
            model_key, device, dtype, attn_impl
        )
    except Exception as e:
        print(f"ERROR al cargar el modelo: {e}")
        print()
        print("Posibles soluciones:")
        print("  1. Verificar que transformers >= 4.45.0: pip install --upgrade transformers")
        print("  2. Verificar que el modelo existe en HuggingFace")
        print("  3. Si es CPU, usar --device cpu explícitamente")
        sys.exit(1)
    
    # ── Cargar imagen ─────────────────────────────────
    try:
        image = load_image(args.image)
        if args.resize > 0:
            image = resize_for_vram(image, max_size=args.resize)
        print(f"  Imagen cargada: {image.size[0]}x{image.size[1]} ({image.mode})")
    except Exception as e:
        print(f"ERROR al cargar imagen: {e}")
        sys.exit(1)
    
    # ── Ejecutar inferencia ───────────────────────────
    print()
    print("  ── Generando respuesta ──")
    print()
    
    try:
        response, metrics = run_inference(
            model=model,
            processor=processor,
            model_type=model_type,
            model_name=model_name,
            image=image,
            user_prompt=args.prompt,
            device=device,
            dtype=dtype,
            max_new_tokens=args.max_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            do_sample=not args.no_sample,
            stream=args.stream,
            benchmark=args.benchmark,
        )
    except torch.cuda.OutOfMemoryError as e:
        print()
        print(f"ERROR: Out of Memory en GPU.")
        print(f"  VRAM disponible: ~{torch.cuda.get_device_properties(0).total_memory / 1e9:.0f} GB")
        print(f"  Soluciones:")
        print(f"  1. Usar modelo más pequeño: --model PaliGemma-3B")
        print(f"  2. Reducir --max-tokens (ej: 64)")
        print(f"  3. Redimensionar imagen: --resize 448")
        print(f"  4. Forzar CPU: --device cpu")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR durante inferencia: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # ── Output ─────────────────────────────────────────
    if args.json:
        output = {
            "model": model_key,
            "model_name": config["name"],
            "backend": backend,
            "device": device_name,
            "dtype": str(dtype),
            "attention": attn_impl,
            "prompt": args.prompt,
            "response": response,
            "metrics": metrics,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print()
        print("  ── Respuesta ─────────────────────────────")
        print(f"  {response}")
        print("  ─────────────────────────────────────────")
        print()
        
        if args.benchmark or args.stream:
            print("  ── Métricas ─────────────────────────────")
            print(f"  Tiempo generación:     {metrics['gen_time_s']}s")
            print(f"  Tokens:                {metrics['num_tokens']}")
            print(f"  Throughput:            {metrics['tokens_per_sec']} t/s")
            if 'vram_delta_gb' in metrics and metrics['vram_delta_gb']:
                print(f"  VRAM usada:            {metrics['vram_delta_gb']:.2f} GB")
            print("  ─────────────────────────────────────────")
    
    # ── Cleanup ────────────────────────────────────────
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
