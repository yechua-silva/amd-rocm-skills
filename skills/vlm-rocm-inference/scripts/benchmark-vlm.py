#!/usr/bin/env python3
"""
benchmark-vlm.py — VLM Inference Benchmark
===========================================
Mide rendimiento de modelos Vision-Language en AMD ROCm / NVIDIA CUDA / CPU.
Prueba múltiples configuraciones de max_new_tokens y reporta métricas.

Uso:
  python3 scripts/benchmark-vlm.py --model InternVL2-8B
  python3 scripts/benchmark-vlm.py --model Qwen2-VL-7B --json resultados.json
  python3 scripts/benchmark-vlm.py --model InternVL2-4B --device cpu
  python3 scripts/benchmark-vlm.py --all-models
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, List, Optional, Tuple

# ─── Detección de backend (replicada de run-vlm.py) ──────────

def detect_backend() -> Tuple[str, str]:
    """Detecta backend GPU disponible."""
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
    return "cuda" if backend != "cpu" else "cpu"


def get_attn_implementation(backend: str) -> str:
    if backend == "rocm":
        return "eager"
    if backend == "cuda":
        try:
            import flash_attn  # noqa: F401
            return "flash_attention_2"
        except ImportError:
            return "eager"
    return "eager"


# ─── Configuración de modelos ────────────────────────────────

MODEL_CONFIGS = {
    "InternVL2-8B": {
        "name": "OpenGVLab/InternVL2-8B",
        "type": "internvl2",
        "prompt_format": "<|user|>\n<image>\n{prompt}\n<|end|>\n<|assistant|>\n",
        "min_vram_gb": 22,
    },
    "InternVL2-4B": {
        "name": "OpenGVLab/InternVL2-4B",
        "type": "internvl2",
        "prompt_format": "<|user|>\n<image>\n{prompt}\n<|end|>\n<|assistant|>\n",
        "min_vram_gb": 12,
    },
    "LLaVA": {
        "name": "llava-hf/llava-v1.6-mistral-7b-hf",
        "type": "llava",
        "prompt_format": "USER: <image>\n{prompt}\nASSISTANT:",
        "min_vram_gb": 20,
    },
    "Qwen2-VL-7B": {
        "name": "Qwen/Qwen2-VL-7B-Instruct",
        "type": "qwen2_vl",
        "prompt_format": None,
        "min_vram_gb": 20,
    },
    "PaliGemma-3B": {
        "name": "google/paligemma-3b-mix-224",
        "type": "paligemma",
        "prompt_format": "caption en\n{prompt}",
        "min_vram_gb": 8,
    },
}


def create_test_image(width: int = 512, height: int = 512) -> "Image.Image":
    """Crea una imagen de test sintética."""
    from PIL import Image, ImageDraw
    
    img = Image.new("RGB", (width, height), color="#1a1a2e")
    draw = ImageDraw.Draw(img)
    
    # Cielo gradiente
    for y in range(height):
        r = int(26 + (y / height) * 20)
        g = int(26 + (y / height) * 15)
        b = int(46 + (y / height) * 30)
        for x in range(0, width, 4):
            img.putpixel((x, y), (r, g, b))
            if x + 1 < width:
                img.putpixel((x + 1, y), (r, g, b))
            if x + 2 < width:
                img.putpixel((x + 2, y), (r, g, b))
            if x + 3 < width:
                img.putpixel((x + 3, y), (r, g, b))
    
    # Sol
    draw.ellipse([width - 130, 60, width - 50, 140], fill="#ffd700", outline="#ffaa00", width=2)
    
    # Montañas
    draw.polygon([
        (0, height * 0.7),
        (width * 0.2, height * 0.35),
        (width * 0.4, height * 0.55),
        (width * 0.6, height * 0.3),
        (width * 0.8, height * 0.5),
        (width, height * 0.4),
        (width, height),
        (0, height)
    ], fill="#2d5016")
    
    draw.polygon([
        (width * 0.4, height * 0.7),
        (width * 0.6, height * 0.45),
        (width * 0.8, height * 0.55),
        (width, height * 0.5),
        (width, height),
        (width * 0.4, height)
    ], fill="#3a6b1e")
    
    # Lago
    draw.rectangle([0, height * 0.75, width, height], fill="#1a5276")
    
    # Casa
    house_x, house_y = width * 0.3, height * 0.6
    draw.rectangle([house_x, house_y, house_x + 80, house_y + 60], fill="#d4a373")
    draw.polygon([
        (house_x - 10, house_y),
        (house_x + 40, house_y - 40),
        (house_x + 90, house_y)
    ], fill="#8b4513")
    draw.rectangle([house_x + 30, house_y + 20, house_x + 50, house_y + 60], fill="#5c3a1e")
    
    # Árbol
    draw.rectangle([width * 0.7, height * 0.55, width * 0.72, height * 0.7], fill="#5c3a1e")
    draw.ellipse([
        width * 0.65, height * 0.45,
        width * 0.77, height * 0.6
    ], fill="#145a32")
    
    return img


# ─── Carga de modelo y processor ─────────────────────────────

def load_model(model_key: str, device: str, dtype, attn_impl: str):
    """Carga modelo VLM para benchmark."""
    from transformers import (
        AutoModel,
        AutoProcessor,
        LlavaForConditionalGeneration,
        LlavaProcessor,
        PaliGemmaForConditionalGeneration,
        PaliGemmaProcessor,
        Qwen2VLForConditionalGeneration,
    )
    import torch
    
    config = MODEL_CONFIGS[model_key]
    model_name = config["name"]
    model_type = config["type"]
    
    print(f"  Cargando {model_key} desde {model_name}...", end=" ", flush=True)
    t0 = time.time()
    
    # Processor
    if model_type == "llava":
        processor = LlavaProcessor.from_pretrained(model_name)
    elif model_type == "paligemma":
        processor = PaliGemmaProcessor.from_pretrained(model_name)
    else:
        processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    
    # Modelo
    load_kwargs = {
        "torch_dtype": dtype,
        "trust_remote_code": True,
        "use_cache": True,
        "attn_implementation": attn_impl,
    }
    if device != "cpu":
        load_kwargs["device_map"] = "auto"
    
    if model_type == "llava":
        model = LlavaForConditionalGeneration.from_pretrained(model_name, **load_kwargs)
    elif model_type == "paligemma":
        model = PaliGemmaForConditionalGeneration.from_pretrained(model_name, **load_kwargs)
    elif model_type == "qwen2_vl":
        model = Qwen2VLForConditionalGeneration.from_pretrained(model_name, **load_kwargs)
    else:
        model = AutoModel.from_pretrained(model_name, **load_kwargs)
    
    if device == "cpu" or not hasattr(model, "hf_device_map"):
        model = model.to(device)
    
    model.eval()
    t1 = time.time()
    print(f"hecho ({t1 - t0:.1f}s)")
    
    # Contar parámetros
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Parámetros: {total_params/1e9:.2f}B total, {trainable_params/1e9:.2f}B entrenables")
    return model, processor, model_type


def build_inputs(model_type, processor, image, prompt, device, dtype):
    """Construye inputs para el modelo."""
    import torch
    
    if model_type == "qwen2_vl":
        messages = [{
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": prompt},
            ],
        }]
        inputs = processor(
            text=messages, images=image, return_tensors="pt", padding=True
        ).to(device, dtype=dtype)
    else:
        fmt = [v["prompt_format"] for k, v in MODEL_CONFIGS.items() if v["type"] == model_type][0]
        text = fmt.format(prompt=prompt)
        inputs = processor(
            text=text, images=image, return_tensors="pt", padding=True, truncation=True
        ).to(device, dtype=dtype)
    
    return inputs


# ─── Benchmark ────────────────────────────────────────────────

def run_single_benchmark(
    model, processor, model_type, image, prompt, device, dtype,
    max_new_tokens: int, temperature: float = 0.0
) -> Dict:
    """Ejecuta una sola medición de benchmark."""
    import torch
    
    # Calentar (primera ejecución siempre es más lenta)
    warmup_inputs = build_inputs(model_type, processor, image, "What do you see?", device, dtype)
    with torch.no_grad():
        _ = model.generate(
            **warmup_inputs,
            max_new_tokens=16,
            temperature=0.0,
            do_sample=False,
            use_cache=True,
        )
    
    # Benchmark real
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    t0 = time.time()
    
    inputs = build_inputs(model_type, processor, image, prompt, device, dtype)
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    prep_time = time.time() - t0
    
    # VRAM antes
    vram_free_before, vram_total = 0, 0
    if torch.cuda.is_available():
        vram_free_before, vram_total = torch.cuda.mem_get_info(0)
    
    # Generación
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    t_gen0 = time.time()
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature if temperature > 0 else None,
            do_sample=temperature > 0,
            use_cache=True,
        )
    
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    gen_time = time.time() - t_gen0
    
    # VRAM después
    vram_free_after = 0
    if torch.cuda.is_available():
        vram_free_after, _ = torch.cuda.mem_get_info(0)
    
    # Métricas
    input_len = inputs["input_ids"].shape[1]
    num_tokens = outputs.shape[1] - input_len
    tokens_per_sec = num_tokens / gen_time if gen_time > 0 else 0
    vram_delta = (vram_free_before - vram_free_after) / 1e9
    vram_peak = (vram_total - vram_free_after) / 1e9
    
    return {
        "max_new_tokens": max_new_tokens,
        "prep_time_s": round(prep_time, 3),
        "gen_time_s": round(gen_time, 3),
        "total_time_s": round(prep_time + gen_time, 3),
        "num_tokens_generated": num_tokens,
        "tokens_per_sec": round(tokens_per_sec, 1),
        "vram_delta_gb": round(vram_delta, 2),
        "vram_peak_gb": round(vram_peak, 2),
        "vram_total_gb": round(vram_total / 1e9, 2),
    }


def run_benchmark(
    model_key: str, device: str, dtype, attn_impl: str,
    token_lengths: List[int], num_runs: int = 2, prompt: str = "Describe esta imagen."
) -> List[Dict]:
    """Ejecuta benchmark completo para múltiples token lengths."""
    import torch
    
    print(f"\n{'='*60}")
    print(f"  Benchmark VLM — {model_key}")
    print(f"  Backend: {device.upper()}")
    print(f"  dtype: {dtype}")
    print(f"{'='*60}")
    print()
    
    # Cargar modelo
    model, processor, model_type = load_model(model_key, device, dtype, attn_impl)
    
    # Crear imagen de test
    image = create_test_image()
    print(f"  Imagen de test: {image.size[0]}x{image.size[1]}")
    print()
    
    results = []
    
    for n_tokens in token_lengths:
        print(f"  ── max_new_tokens = {n_tokens} ──")
        
        run_results = []
        for run in range(num_runs):
            result = run_single_benchmark(
                model, processor, model_type, image, prompt,
                device, dtype, max_new_tokens=n_tokens
            )
            run_results.append(result)
            print(f"    Run {run+1}: {result['gen_time_s']:.2f}s, "
                  f"{result['tokens_per_sec']:.1f} t/s, "
                  f"VRAM: {result['vram_peak_gb']:.1f} GB")
        
        # Promedio
        avg = {
            "max_new_tokens": n_tokens,
            "avg_gen_time_s": round(sum(r["gen_time_s"] for r in run_results) / num_runs, 3),
            "avg_tokens_per_sec": round(sum(r["tokens_per_sec"] for r in run_results) / num_runs, 1),
            "avg_vram_peak_gb": round(sum(r["vram_peak_gb"] for r in run_results) / num_runs, 2),
            "avg_vram_delta_gb": round(sum(r["vram_delta_gb"] for r in run_results) / num_runs, 2),
            "runs": run_results,
        }
        results.append(avg)
        print(f"    → Promedio: {avg['avg_gen_time_s']:.2f}s, "
              f"{avg['avg_tokens_per_sec']:.1f} t/s, "
              f"VRAM: {avg['avg_vram_peak_gb']:.1f} GB")
        print()
    
    # Tabla resumen
    print(f"  {'='*55}")
    print(f"  {'max_tokens':<15} {'Tiempo':<12} {'tokens/s':<12} {'VRAM pico':<12}")
    print(f"  {'─'*51}")
    for r in results:
        print(f"  {r['max_new_tokens']:<15} {r['avg_gen_time_s']:<12.2f} "
              f"{r['avg_tokens_per_sec']:<12.1f} {r['avg_vram_peak_gb']:<12.1f}")
    print(f"  {'='*55}")
    print()
    
    # Limpieza
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    return results


# ─── Comparación GPU vs CPU ───────────────────────────────────

def run_gpu_vs_cpu_comparison(model_key: str, token_lengths: List[int]):
    """Ejecuta benchmark en GPU y CPU para comparar."""
    import torch
    
    print(f"\n{'='*60}")
    print(f"  Comparación GPU vs CPU — {model_key}")
    print(f"{'='*60}")
    
    # GPU
    gpu_backend, _ = detect_backend()
    if gpu_backend != "cpu":
        print(f"\n  ▶ GPU ({gpu_backend.upper()})")
        gpu_results = run_benchmark(
            model_key,
            device=get_device(gpu_backend),
            dtype=get_optimal_dtype(gpu_backend),
            attn_impl=get_attn_implementation(gpu_backend),
            token_lengths=token_lengths,
        )
    else:
        print("\n  ⚠️  No hay GPU disponible para comparación.")
        gpu_results = []
    
    # CPU
    print(f"\n  ▶ CPU")
    cpu_results = run_benchmark(
        model_key,
        device="cpu",
        dtype=torch.float32,
        attn_impl="eager",
        token_lengths=token_lengths,
    )
    
    return {"gpu": gpu_results, "cpu": cpu_results}


# ─── Main ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="VLM Inference Benchmark — AMD ROCm / NVIDIA CUDA / CPU"
    )
    
    parser.add_argument(
        "--model", "-m", type=str, default="InternVL2-8B",
        help="Modelo VLM a benchmarkear (default: InternVL2-8B)"
    )
    parser.add_argument(
        "--device", "-d", type=str, default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Forzar device (auto = detectar backend)"
    )
    parser.add_argument(
        "--token-lengths", type=int, nargs="+", default=[64, 128, 256, 512],
        help="Valores de max_new_tokens a probar (default: 64 128 256 512)"
    )
    parser.add_argument(
        "--runs", type=int, default=2,
        help="Número de ejecuciones por configuración (default: 2)"
    )
    parser.add_argument(
        "--json", type=str, default=None,
        help="Ruta para guardar resultados en JSON"
    )
    parser.add_argument(
        "--compare-cpu", action="store_true",
        help="Comparar GPU vs CPU"
    )
    parser.add_argument(
        "--all-models", action="store_true",
        help="Benchmarkear todos los modelos disponibles"
    )
    
    args = parser.parse_args()
    
    # ── Detectar backend ───────────────────────────────
    backend, device_name = detect_backend()
    
    if args.device != "auto":
        if args.device == "cpu":
            backend = "cpu"
            device_name = "CPU (forzado)"
        elif args.device == "cuda" and backend == "cpu":
            print("ERROR: Se forzó device=cuda pero no hay GPU disponible.")
            sys.exit(1)
    
    import torch
    dtype = get_optimal_dtype(backend)
    device = get_device(backend)
    attn_impl = get_attn_implementation(backend)
    
    # ── Info del sistema ───────────────────────────────
    print()
    print(f"  Sistema: {torch.__config__.show() if hasattr(torch.__config__, 'show') else ''}"[:80])
    print(f"  PyTorch: {torch.__version__}")
    print(f"  Backend: {backend.upper()}")
    print(f"  GPU:     {device_name}")
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        print(f"  VRAM:    {props.total_memory / 1e9:.1f} GB")
        print(f"  Compute: {props.major}.{props.minor}")
    print()
    
    # ── Modelos a benchmarkear ─────────────────────────
    models_to_test = []
    if args.all_models:
        models_to_test = list(MODEL_CONFIGS.keys())
        # Filtrar modelos que no caben en VRAM
        if torch.cuda.is_available():
            vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
            models_to_test = [
                m for m in models_to_test
                if MODEL_CONFIGS[m]["min_vram_gb"] <= vram_gb * 0.9
            ]
            print(f"  Modelos a testear (VRAM disponible: {vram_gb:.0f} GB):")
            for m in models_to_test:
                print(f"    • {m} (mín {MODEL_CONFIGS[m]['min_vram_gb']} GB)")
    else:
        # Validar que el modelo existe
        model_key = args.model
        if model_key not in MODEL_CONFIGS:
            print(f"ERROR: Modelo '{model_key}' no reconocido.")
            print("Disponibles:", ", ".join(MODEL_CONFIGS.keys()))
            sys.exit(1)
        models_to_test = [model_key]
    
    # ── Ejecutar benchmark ─────────────────────────────
    all_results = {}
    
    if args.compare_cpu:
        for model_key in models_to_test:
            result = run_gpu_vs_cpu_comparison(model_key, args.token_lengths)
            all_results[model_key] = result
    else:
        for model_key in models_to_test:
            result = run_benchmark(
                model_key, device, dtype, attn_impl,
                args.token_lengths, num_runs=args.runs
            )
            all_results[model_key] = result
    
    # ── Guardar JSON ──────────────────────────────────
    if args.json:
        output = {
            "metadata": {
                "backend": backend,
                "device": device_name,
                "pytorch_version": torch.__version__,
                "torch_cuda_available": torch.cuda.is_available(),
            },
            "results": all_results,
        }
        
        # Convertir tipos serializables
        class BenchmarkEncoder(json.JSONEncoder):
            def default(self, obj):
                if hasattr(obj, "item"):
                    return obj.item()
                return super().default(obj)
        
        with open(args.json, "w") as f:
            json.dump(output, f, indent=2, cls=BenchmarkEncoder, ensure_ascii=False)
        print(f"Resultados guardados en: {args.json}")
    
    print("Benchmark completado.")


if __name__ == "__main__":
    main()
