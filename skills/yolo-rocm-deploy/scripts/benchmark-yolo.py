#!/usr/bin/env python3
"""
Benchmark YOLO performance on AMD ROCm / NVIDIA CUDA / CPU.

Auto-detects the available backend, reports latency metrics, FPS, and VRAM
usage. Optionally compares GPU vs CPU performance side by side.

Usage:
  python benchmark-yolo.py                                         # defaults
  python benchmark-yolo.py --model yolov8s.pt --iterations 500     # custom
  python benchmark-yolo.py --compare                               # GPU vs CPU
  python benchmark-yolo.py --json --output results.json            # JSON export
  python benchmark-yolo.py --image test.jpg --device cpu           # CPU only

Arguments:
  --model       YOLO model path or name (default: yolov8x.pt)
  --iterations  Number of inference iterations (default: 100)
  --image       Image path or URL for inference (default: auto-generates)
  --device      Override device: cuda:0, cpu, etc. (default: auto-detect)
  --compare     Also benchmark on CPU and compare results (GPU-only systems)
  --json        Export results as JSON
  --output      Output file path for JSON (default: benchmark-results.json)
"""

import argparse
import sys
import time
import json
import os
import math


def detect_backend():
    """Detect the available compute backend (ROCm / CUDA / CPU).

    Returns:
        dict with keys: backend (str), device (str), device_name (str),
                        hip_version (str or None), cuda_version (str or None),
                        vram_total_gb (float), vram_free_gb (float or None)
    """
    import torch

    info = {
        "backend": "cpu",
        "device": "cpu",
        "device_name": "N/A",
        "hip_version": None,
        "cuda_version": None,
        "vram_total_gb": 0.0,
        "vram_free_gb": None,
    }

    if not torch.cuda.is_available():
        return info

    info["device"] = "cuda:0"
    info["device_name"] = torch.cuda.get_device_name(0)

    try:
        props = torch.cuda.get_device_properties(0)
        info["vram_total_gb"] = props.total_memory / (1024**3)

        # Attempt to measure free VRAM via torch.cuda.memory_stats
        try:
            allocated = torch.cuda.memory_allocated(0) / (1024**3)
            reserved = torch.cuda.memory_reserved(0) / (1024**3)
            # Free = total - reserved (conservative estimate)
            free = info["vram_total_gb"] - reserved
            info["vram_free_gb"] = round(free, 2)
        except Exception:
            info["vram_free_gb"] = None
    except Exception:
        info["vram_total_gb"] = 0.0

    # ROCm detection
    if torch.version.hip is not None:
        info["backend"] = "rocm"
        info["hip_version"] = torch.version.hip
    elif torch.version.cuda is not None:
        info["backend"] = "cuda"
        info["cuda_version"] = torch.version.cuda
    else:
        info["backend"] = "cuda"
        info["cuda_version"] = "unknown"

    return info


def get_device(override: str | None = None) -> str:
    """Return the device string to use. Auto-detects if not overridden."""
    if override is not None:
        return override
    import torch
    return "cuda:0" if torch.cuda.is_available() else "cpu"


def generate_test_image(width: int = 640, height: int = 640) -> str:
    """Generate a synthetic test image and return its file path.

    Creates a simple gradient image with a few shapes so YOLO has
    something to detect (even if it's noise).
    """
    import numpy as np

    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Fill with a gradient
    for y in range(height):
        for x in range(width):
            img[y, x] = [
                int(255 * x / width),
                int(128 * y / height + 64),
                int(255 - 255 * y / height),
            ]

    # Add some white rectangles to simulate objects
    cv_available = False
    try:
        import cv2
        cv_available = True
    except ImportError:
        pass

    if cv_available:
        cv2.rectangle(img, (50, 50), (150, 150), (255, 255, 255), -1)
        cv2.rectangle(img, (400, 300), (550, 500), (255, 255, 255), -1)
        cv2.rectangle(img, (200, 400), (350, 550), (200, 200, 200), -1)
        img_path = "/tmp/yolo-benchmark-test.png"
        cv2.imwrite(img_path, img)
    else:
        # Pure numpy save
        from PIL import Image
        img_path = "/tmp/yolo-benchmark-test.png"
        Image.fromarray(img).save(img_path)

    return img_path


def measure_vram(device_idx: int = 0) -> float | None:
    """Measure current VRAM usage in GB. Returns None if unavailable."""
    import torch
    try:
        allocated = torch.cuda.memory_allocated(device_idx) / (1024**3)
        return round(allocated, 2)
    except Exception:
        return None


def measure_vram_peak(device_idx: int = 0) -> float | None:
    """Measure peak VRAM usage in GB. Returns None if unavailable."""
    import torch
    try:
        peak = torch.cuda.max_memory_allocated(device_idx) / (1024**3)
        return round(peak, 2)
    except Exception:
        return None


def reset_vram_stats(device_idx: int = 0):
    """Reset peak memory tracking."""
    import torch
    try:
        torch.cuda.reset_peak_memory_stats(device_idx)
    except Exception:
        pass


def benchmark_on_device(
    model,
    image_path: str,
    device: str,
    iterations: int,
    label: str = "GPU",
) -> dict:
    """Run benchmark on a specific device.

    Returns a dict with latency stats, FPS, and VRAM usage.
    """
    import torch

    print(f"\n  --- Benchmarking on {label}: {device} ---")
    print(f"  Iterations: {iterations}")

    # Ensure model is on the correct device
    model.predict(image_path, device=device, verbose=False)

    # Warmup: 10 iterations to stabilize GPU/CPU caches
    print(f"  Warming up...")
    for _ in range(10):
        _ = model.predict(image_path, device=device, verbose=False)

    # Reset VRAM stats before benchmark
    if device.startswith("cuda"):
        reset_vram_stats()
        vram_before = measure_vram()
    else:
        vram_before = None

    # Benchmark loop
    latencies = []
    print(f"  Running {iterations} iterations...")

    for i in range(iterations):
        start = time.perf_counter()
        _ = model.predict(image_path, device=device, verbose=False)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

        if (i + 1) % max(1, iterations // 5) == 0:
            print(f"    {i + 1}/{iterations} - {elapsed * 1000:.1f} ms")

    # Post-benchmark VRAM
    if device.startswith("cuda"):
        vram_after = measure_vram()
        vram_peak = measure_vram_peak()
    else:
        vram_after = None
        vram_peak = None

    # Compute statistics
    import statistics

    avg_ms = statistics.mean(latencies) * 1000
    min_ms = min(latencies) * 1000
    max_ms = max(latencies) * 1000
    stdev_ms = statistics.stdev(latencies) * 1000 if len(latencies) > 1 else 0.0
    fps = 1000.0 / avg_ms if avg_ms > 0 else 0.0
    p50_ms = statistics.median(latencies) * 1000
    p95_ms = sorted(latencies)[int(len(latencies) * 0.95)] * 1000
    p99_ms = sorted(latencies)[int(len(latencies) * 0.99)] * 1000

    # VRAM delta (how much extra VRAM the model uses)
    vram_delta = None
    if vram_before is not None and vram_after is not None:
        vram_delta = round(vram_after - vram_before, 2)

    return {
        "device": device,
        "label": label,
        "iterations": iterations,
        "latency_avg_ms": round(avg_ms, 2),
        "latency_min_ms": round(min_ms, 2),
        "latency_max_ms": round(max_ms, 2),
        "latency_stdev_ms": round(stdev_ms, 2),
        "latency_p50_ms": round(p50_ms, 2),
        "latency_p95_ms": round(p95_ms, 2),
        "latency_p99_ms": round(p99_ms, 2),
        "fps": round(fps, 1),
        "vram_before_gb": vram_before,
        "vram_after_gb": vram_after,
        "vram_peak_gb": vram_peak,
        "vram_delta_gb": vram_delta,
    }


def print_report(results: dict, compare_results: dict | None):
    """Print a nicely formatted benchmark report."""
    r = results

    print()
    print("=" * 64)
    print("                    BENCHMARK REPORT")
    print("=" * 64)

    # Backend info
    bi = r.get("backend_info", {})
    print(f"  Backend:          {bi.get('backend', 'N/A').upper()}")
    print(f"  Device:           {bi.get('device_name', 'N/A')}")
    if bi.get("hip_version"):
        print(f"  HIP version:      {bi['hip_version']}")
    if bi.get("cuda_version"):
        print(f"  CUDA version:     {bi['cuda_version']}")
    print(f"  VRAM total:       {bi.get('vram_total_gb', 0):.1f} GB")
    print(f"  Model:            {r.get('model', 'N/A')}")
    print(f"  Image size:       {r.get('image_size', 'N/A')}")
    print(f"  Iterations:       {r['iterations']}")
    print()

    # Primary device results
    print("-" * 64)
    print(f"  Primary: {r['label']} ({r['device']})")
    print("-" * 64)
    print(f"    Latency avg:     {r['latency_avg_ms']:>8.2f} ms")
    print(f"    Latency min:     {r['latency_min_ms']:>8.2f} ms")
    print(f"    Latency max:     {r['latency_max_ms']:>8.2f} ms")
    print(f"    Latency stdev:   {r['latency_stdev_ms']:>8.2f} ms")
    print(f"    Latency P50:     {r['latency_p50_ms']:>8.2f} ms")
    print(f"    Latency P95:     {r['latency_p95_ms']:>8.2f} ms")
    print(f"    Latency P99:     {r['latency_p99_ms']:>8.2f} ms")
    print(f"    Throughput:      {r['fps']:>8.1f} FPS")

    if r.get("vram_delta_gb") is not None:
        print(f"    VRAM delta:      {r['vram_delta_gb']:>8.2f} GB")
    if r.get("vram_peak_gb") is not None:
        print(f"    VRAM peak:       {r['vram_peak_gb']:>8.2f} GB")
    print()

    # Comparison (GPU vs CPU)
    if compare_results:
        cr = compare_results
        print("-" * 64)
        print(f"  Comparison: {cr['label']} ({cr['device']})")
        print("-" * 64)
        print(f"    Latency avg:     {cr['latency_avg_ms']:>8.2f} ms")
        print(f"    Latency min:     {cr['latency_min_ms']:>8.2f} ms")
        print(f"    Latency max:     {cr['latency_max_ms']:>8.2f} ms")
        print(f"    Latency stdev:   {cr['latency_stdev_ms']:>8.2f} ms")
        print(f"    Throughput:      {cr['fps']:>8.1f} FPS")

        if cr.get("vram_delta_gb") is not None:
            print(f"    VRAM delta:      {cr['vram_delta_gb']:>8.2f} GB")
        print()

        # Speedup
        if cr["latency_avg_ms"] > 0 and r["latency_avg_ms"] > 0:
            ratio = cr["latency_avg_ms"] / r["latency_avg_ms"]
            print(f"  GPU vs CPU speedup: {ratio:.1f}x")
            print()

    # ── Single-line summary ──────────────────────────────────────────────
    print("-" * 64)
    summary = (
        f"  {r['label']:5s}: {r['fps']:>6.1f} FPS  |  "
        f"avg {r['latency_avg_ms']:>6.1f} ms  |  "
        f"min {r['latency_min_ms']:>5.1f}  max {r['latency_max_ms']:>5.1f}  "
    )
    if r.get("vram_peak_gb") is not None:
        summary += f"|  VRAM {r['vram_peak_gb']:.1f} GB"
    print(summary)

    if compare_results and compare_results.get("latency_avg_ms"):
        cs = compare_results
        summary2 = (
            f"  {cs['label']:5s}: {cs['fps']:>6.1f} FPS  |  "
            f"avg {cs['latency_avg_ms']:>6.1f} ms  |  "
            f"min {cs['latency_min_ms']:>5.1f}  max {cs['latency_max_ms']:>5.1f}  "
        )
        print(summary2)

    print("=" * 64)


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark YOLO performance on AMD ROCm / NVIDIA CUDA / CPU"
    )
    parser.add_argument(
        "--model",
        default="yolov8x.pt",
        help="Model path or name (default: yolov8x.pt)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of inference iterations (default: 100)",
    )
    parser.add_argument(
        "--image",
        default=None,
        help="Image path or URL for inference (default: auto-generates)",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Override device (default: auto-detect)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Also benchmark on CPU and compare results",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Export results as JSON",
    )
    parser.add_argument(
        "--output",
        default="benchmark-results.json",
        help="JSON output file path (default: benchmark-results.json)",
    )
    args = parser.parse_args()

    # ── Detect backend ────────────────────────────────────────────────────
    print("=" * 64)
    print("                YOLO BENCHMARK")
    print("=" * 64)

    backend_info = detect_backend()
    device = get_device(args.device)

    print(f"\n  Backend:     {backend_info['backend'].upper()}")
    print(f"  Device:      {backend_info['device_name']}")
    print(f"  Compute:     {device}")
    if backend_info["hip_version"]:
        print(f"  HIP version: {backend_info['hip_version']}")
    if backend_info["cuda_version"]:
        print(f"  CUDA version:{backend_info['cuda_version']}")
    if backend_info["vram_total_gb"] > 0:
        print(f"  VRAM total:  {backend_info['vram_total_gb']:.1f} GB")
    print(f"  Model:       {args.model}")
    print(f"  Iterations:  {args.iterations}")

    # ── Load model ────────────────────────────────────────────────────────
    print(f"\n  Loading model...")
    try:
        from ultralytics import YOLO
    except ImportError:
        print("  ERROR: ultralytics not installed.")
        print("  Run: pip install ultralytics")
        sys.exit(1)

    try:
        model = YOLO(args.model)
    except Exception as e:
        print(f"  ERROR: Failed to load model '{args.model}': {e}")
        sys.exit(1)

    print(f"  ✓ Model loaded: {args.model}")
    print(f"  Model task: {model.task}")
    print(f"  Model names: {model.names}")

    # ── Prepare image ─────────────────────────────────────────────────────
    if args.image:
        image_path = args.image
        print(f"\n  Using provided image: {image_path}")
    else:
        print(f"\n  Generating synthetic test image...")
        image_path = generate_test_image()
        print(f"  ✓ Test image: {image_path}")

    # Get image dimensions
    try:
        from PIL import Image
        img = Image.open(image_path)
        image_size = f"{img.width}x{img.height}"
    except Exception:
        image_size = "unknown"

    print(f"  Image size:  {image_size}")

    # ── Primary benchmark ─────────────────────────────────────────────────
    label = backend_info["backend"].upper()
    if device == "cpu":
        label = "CPU"

    results = benchmark_on_device(
        model=model,
        image_path=image_path,
        device=device,
        iterations=args.iterations,
        label=label,
    )
    results["backend_info"] = backend_info
    results["model"] = args.model
    results["image_size"] = image_size

    # ── Comparison benchmark (GPU vs CPU) ─────────────────────────────────
    compare_results = None
    if args.compare and device.startswith("cuda"):
        print(f"\n  {'=' * 60}")
        print(f"  Now benchmarking CPU for comparison...")
        print(f"  {'=' * 60}")
        compare_results = benchmark_on_device(
            model=model,
            image_path=image_path,
            device="cpu",
            iterations=min(args.iterations, 50),  # fewer iterations for CPU
            label="CPU",
        )
        compare_results["backend_info"] = detect_backend()
        compare_results["model"] = args.model
        compare_results["image_size"] = image_size
    elif args.compare and device == "cpu":
        print(f"\n  NOTE: --compare requires a GPU device. Skipping comparison.")

    # ── Print report ──────────────────────────────────────────────────────
    print_report(results, compare_results)

    # ── JSON export ───────────────────────────────────────────────────────
    if args.json:
        export = {
            "benchmark": results,
        }
        if compare_results:
            export["comparison"] = compare_results

        output_path = args.output
        try:
            with open(output_path, "w") as f:
                json.dump(export, f, indent=2)
            print(f"\n  ✓ JSON results exported to: {output_path}")
        except Exception as e:
            print(f"\n  ERROR: Failed to write JSON: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
