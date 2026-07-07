#!/usr/bin/env python3
"""
benchmark-gpu.py — GPU Benchmark Suite for AMD ROCm and NVIDIA CUDA.

Benchmark completo de GPU: memoria (H2D/D2H/P2P), compute (GEMM, FFT, Conv2D),
inferencia (CNN, Transformer, YOLO, LLM), monitoreo en tiempo real, stress test
con detección de thermal throttling, y reporte consolidado.

Backends: AMD ROCm (MI300X, MI250, RX 7900) y NVIDIA CUDA (A100, H100, RTX).
Fallback a CPU cuando no hay GPU.

Usage:
    python3 benchmark-gpu.py --info                    # Información del sistema
    python3 benchmark-gpu.py --memory                  # Benchmark de memoria
    python3 benchmark-gpu.py --compute                 # Benchmark de compute
    python3 benchmark-gpu.py --inference               # Benchmark de inferencia
    python3 benchmark-gpu.py --stress                  # Stress test
    python3 benchmark-gpu.py --all                     # Todo
    python3 benchmark-gpu.py --all --json --output results.json

Arguments:
    --memory          Run memory benchmarks (H2D, D2H, P2P)
    --compute         Run compute benchmarks (GEMM, FFT, Conv2D)
    --inference       Run inference benchmarks (CNN, Transformer)
    --stress          Run stress test (sustained load + throttle detection)
    --all             Run all benchmarks
    --info            Show system information and exit
    --device          Override device (auto/cuda:0/cpu)
    --iterations      Iterations per benchmark (default: 100)
    --warmup          Warmup iterations (default: 10)
    --duration        Stress test duration in seconds (default: 60)
    --batch-size      Batch size for inference (default: 32)
    --memory-sizes    Memory transfer sizes in MB (default: 1024,4096,16384)
    --matrix-sizes    GEMM matrix sizes (default: 512,1024,2048,4096)
    --dtype           Precision for compute (fp32/fp16, default: fp32)
    --model           Inference model type (cnn/transformer/yolo/llm)
    --monitor         Enable real-time GPU monitoring during benchmark
    --monitor-interval Monitor polling interval in seconds (default: 1)
    --json            Export results as JSON
    --output          Output file path for JSON (default: benchmark-results.json)
    --runs            Number of benchmark runs (default: 1)
    --cooldown        Cooldown between runs in seconds (default: 5)
    --threshold       Clock drop % for throttling detection (default: 5)
    --yolo-model      YOLO model name/path for real inference (default: yolov8n.pt)
    --llm-model       LLM model name for real inference (default: none)
"""

import argparse
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════
#  BACKEND DETECTION
# ═══════════════════════════════════════════════════════════

def detect_backend() -> Dict[str, Any]:
    """Detect the available GPU backend (ROCm, CUDA, or CPU).

    Returns:
        dict with backend info: available, backend, device_name, device_count,
        driver_version, torch_version, hip_version, cuda_version, gfx_arch,
        vram_total_gb, vram_free_gb
    """
    info: Dict[str, Any] = {
        "available": False,
        "backend": "cpu",
        "device_name": "",
        "device_count": 0,
        "driver_version": "",
        "torch_version": "",
        "hip_version": None,
        "cuda_version": None,
        "gfx_arch": "",
        "vram_total_gb": 0.0,
        "vram_free_gb": None,
        "compute_capability": "",
    }

    try:
        import torch

        info["torch_version"] = torch.__version__

        if not torch.cuda.is_available():
            return info

        info["available"] = True
        info["device_count"] = torch.cuda.device_count()
        info["device_name"] = torch.cuda.get_device_name(0)

        # VRAM total
        try:
            props = torch.cuda.get_device_properties(0)
            info["vram_total_gb"] = round(props.total_memory / (1024**3), 2)
        except Exception:
            pass

        # VRAM free
        try:
            total = torch.cuda.mem_get_info(0)
            info["vram_free_gb"] = round(total[0] / (1024**3), 2)
        except Exception:
            try:
                allocated = torch.cuda.memory_allocated(0) / (1024**3)
                info["vram_free_gb"] = round(info["vram_total_gb"] - allocated, 2)
            except Exception:
                pass

        # Backend discrimination
        hip_ver = getattr(torch.version, "hip", None)
        cuda_ver = getattr(torch.version, "cuda", None)

        if hip_ver:
            info["backend"] = "rocm"
            info["hip_version"] = hip_ver

            # Get GFX arch from rocminfo
            try:
                ri = subprocess.run(
                    ["rocminfo"], capture_output=True, text=True, timeout=10
                )
                for line in ri.stdout.split("\n"):
                    m = re.search(r"(gfx\d+)", line)
                    if m:
                        info["gfx_arch"] = m.group(1)
                        break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

            # Driver version from rocm-smi
            try:
                rs = subprocess.run(
                    ["rocm-smi", "--showproductname", "--json"],
                    capture_output=True, text=True, timeout=10
                )
                if rs.returncode == 0:
                    data = json.loads(rs.stdout)
                    info["driver_version"] = data.get("version", "")
            except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
                pass

        elif cuda_ver:
            info["backend"] = "cuda"
            info["cuda_version"] = cuda_ver

            # NVIDIA driver version
            try:
                nv = subprocess.run(
                    ["nvidia-smi", "--query-gpu=driver_version",
                     "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=10
                )
                if nv.returncode == 0:
                    info["driver_version"] = nv.stdout.strip()
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

            # Compute capability
            try:
                cap = torch.cuda.get_device_capability(0)
                info["compute_capability"] = f"{cap[0]}.{cap[1]}"
            except Exception:
                pass
        else:
            info["backend"] = "cuda"
            info["cuda_version"] = "unknown"

    except ImportError:
        info["torch_version"] = "no instalado"

    return info


def get_device(override: Optional[str] = None) -> str:
    """Return the device string to use. Auto-detects if not overridden."""
    if override is not None and override != "auto":
        return override
    try:
        import torch
        return "cuda:0" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


# ═══════════════════════════════════════════════════════════
#  MEMORY BENCHMARK
# ═══════════════════════════════════════════════════════════

def memory_benchmark(
    device: str,
    sizes_mb: List[int],
    iterations: int = 50,
    warmup: int = 5,
) -> Dict[str, Any]:
    """Benchmark memory bandwidth: H2D, D2H, P2P.

    Args:
        device: Device string (e.g., "cuda:0")
        sizes_mb: List of sizes in MB to benchmark
        iterations: Number of iterations per size
        warmup: Number of warmup iterations

    Returns:
        dict with bandwidth results in GB/s
    """
    import torch

    results: Dict[str, Any] = {
        "h2d": {},
        "d2h": {},
        "p2p": {},
        "device": device,
    }

    is_cuda = device.startswith("cuda")
    if not is_cuda:
        results["error"] = "Memory benchmark requires a CUDA/ROCm device"
        return results

    dev_idx = int(device.split(":")[1]) if ":" in device else 0

    for size_mb in sizes_mb:
        size_bytes = size_mb * 1024 * 1024
        numel = size_bytes // 4  # float32
        h2d_gbps = 0.0
        d2h_gbps = 0.0

        # Host tensor
        host_tensor = torch.randn(numel, device="cpu")

        # Warmup
        for _ in range(warmup):
            _ = host_tensor.to(device, non_blocking=False)
            torch.cuda.synchronize(device=dev_idx)

        # H2D bandwidth
        latencies_h2d = []
        for _ in range(iterations):
            torch.cuda.synchronize(device=dev_idx)
            start = time.perf_counter()
            d = host_tensor.to(device, non_blocking=False)
            torch.cuda.synchronize(device=dev_idx)
            elapsed = time.perf_counter() - start
            latencies_h2d.append(elapsed)

        avg_h2d_s = statistics.mean(latencies_h2d)
        h2d_gbps = (size_bytes / avg_h2d_s) / 1e9 if avg_h2d_s > 0 else 0.0

        # D2H bandwidth
        device_tensor = torch.randn(numel, device=device)
        torch.cuda.synchronize(device=dev_idx)

        latencies_d2h = []
        for _ in range(iterations):
            torch.cuda.synchronize(device=dev_idx)
            start = time.perf_counter()
            h = device_tensor.to("cpu", non_blocking=False)
            torch.cuda.synchronize(device=dev_idx)
            elapsed = time.perf_counter() - start
            latencies_d2h.append(elapsed)

        avg_d2h_s = statistics.mean(latencies_d2h)
        d2h_gbps = (size_bytes / avg_d2h_s) / 1e9 if avg_d2h_s > 0 else 0.0

        results["h2d"][str(size_mb)] = round(h2d_gbps, 2)
        results["d2h"][str(size_mb)] = round(d2h_gbps, 2)

    # P2P: requires at least 2 GPUs
    if torch.cuda.device_count() >= 2:
        try:
            p2p_sizes = [s for s in sizes_mb if s <= 1024]  # P2P con sizes moderados
            if not p2p_sizes:
                p2p_sizes = [1024]

            for size_mb in p2p_sizes:
                size_bytes = size_mb * 1024 * 1024
                numel = size_bytes // 4

                src_tensor = torch.randn(numel, device="cuda:0")
                torch.cuda.synchronize(device=0)

                latencies_p2p = []
                for _ in range(min(iterations, 20)):
                    torch.cuda.synchronize(device=0)
                    torch.cuda.synchronize(device=1)
                    start = time.perf_counter()
                    dst_tensor = src_tensor.to("cuda:1", non_blocking=False)
                    torch.cuda.synchronize(device=0)
                    torch.cuda.synchronize(device=1)
                    elapsed = time.perf_counter() - start
                    latencies_p2p.append(elapsed)

                avg_p2p_s = statistics.mean(latencies_p2p)
                p2p_gbps = (size_bytes / avg_p2p_s) / 1e9 if avg_p2p_s > 0 else 0.0
                results["p2p"][str(size_mb)] = round(p2p_gbps, 2)
        except Exception as e:
            results["p2p"]["error"] = str(e)
    else:
        results["p2p"]["note"] = "Requires 2+ GPUs"

    return results


# ═══════════════════════════════════════════════════════════
#  COMPUTE BENCHMARK
# ═══════════════════════════════════════════════════════════

def compute_benchmark(
    device: str,
    matrix_sizes: List[int],
    iterations: int = 100,
    warmup: int = 10,
    dtype_str: str = "fp32",
) -> Dict[str, Any]:
    """Benchmark compute throughput: GEMM, FFT, Conv2D.

    Args:
        device: Device string
        matrix_sizes: List of matrix sizes (N x N)
        iterations: Number of iterations per size
        warmup: Number of warmup iterations
        dtype_str: Precision ("fp32" or "fp16")

    Returns:
        dict with TFLOPS results
    """
    import torch

    results: Dict[str, Any] = {
        "gemm_fp32": {},
        "gemm_fp16": {},
        "fft": {},
        "conv2d": {},
        "device": device,
        "dtype": dtype_str,
    }

    is_cuda = device.startswith("cuda")
    if not is_cuda:
        results["error"] = "Compute benchmark requires a CUDA/ROCm device"
        return results

    dev_idx = int(device.split(":")[1]) if ":" in device else 0

    # ── GEMM FP32 ────────────────────────────────────────────────

    for n in matrix_sizes:
        a = torch.randn(n, n, device=device)
        b = torch.randn(n, n, device=device)

        # Warmup
        for _ in range(warmup):
            c = torch.mm(a, b)
            torch.cuda.synchronize(device=dev_idx)

        latencies = []
        for _ in range(iterations):
            torch.cuda.synchronize(device=dev_idx)
            start = time.perf_counter()
            c = torch.mm(a, b)
            torch.cuda.synchronize(device=dev_idx)
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)

        avg_s = statistics.mean(latencies)
        # FLOP count for matmul: 2*N^3 - N^2 ≈ 2*N^3 for large N
        flops = 2 * n**3
        tflops = (flops / avg_s) / 1e12 if avg_s > 0 else 0.0
        results["gemm_fp32"][str(n)] = round(tflops, 2)

    # ── GEMM FP16 ────────────────────────────────────────────────

    for n in matrix_sizes:
        try:
            a_fp16 = torch.randn(n, n, device=device, dtype=torch.float16)
            b_fp16 = torch.randn(n, n, device=device, dtype=torch.float16)

            for _ in range(warmup):
                c_fp16 = torch.mm(a_fp16, b_fp16)
                torch.cuda.synchronize(device=dev_idx)

            latencies = []
            for _ in range(iterations):
                torch.cuda.synchronize(device=dev_idx)
                start = time.perf_counter()
                c_fp16 = torch.mm(a_fp16, b_fp16)
                torch.cuda.synchronize(device=dev_idx)
                elapsed = time.perf_counter() - start
                latencies.append(elapsed)

            avg_s = statistics.mean(latencies)
            flops = 2 * n**3
            tflops = (flops / avg_s) / 1e12 if avg_s > 0 else 0.0
            results["gemm_fp16"][str(n)] = round(tflops, 2)
        except Exception as e:
            results["gemm_fp16"][str(n)] = f"error: {e}"

    # ── FFT 2D ────────────────────────────────────────────────────

    fft_sizes = [s for s in matrix_sizes if s & (s - 1) == 0]  # powers of 2
    if not fft_sizes:
        fft_sizes = [1024, 2048]

    for n in fft_sizes:
        try:
            x = torch.randn(n, n, device=device, dtype=torch.complex64)

            for _ in range(warmup):
                y = torch.fft.fft2(x)
                torch.cuda.synchronize(device=dev_idx)

            latencies = []
            for _ in range(iterations):
                torch.cuda.synchronize(device=dev_idx)
                start = time.perf_counter()
                y = torch.fft.fft2(x)
                torch.cuda.synchronize(device=dev_idx)
                elapsed = time.perf_counter() - start
                latencies.append(elapsed)

            avg_s = statistics.mean(latencies)
            # Throughput in GB/s (data processed per second)
            bytes_processed = n * n * 8  # complex64 = 8 bytes per element
            throughput_gbs = (bytes_processed / avg_s) / 1e9 if avg_s > 0 else 0.0
            results["fft"][str(n)] = round(throughput_gbs, 2)
        except Exception as e:
            results["fft"][str(n)] = f"error: {e}"

    # ── Conv2D ────────────────────────────────────────────────────

    for n in [s for s in matrix_sizes if s >= 128]:
        try:
            batch = 8
            in_channels = 64
            out_channels = 128
            kernel_size = 3
            input_size = min(n, 1024)

            x = torch.randn(batch, in_channels, input_size, input_size, device=device)
            conv = torch.nn.Conv2d(
                in_channels, out_channels, kernel_size, padding=1, bias=False
            ).to(device)

            for _ in range(warmup):
                y = conv(x)
                torch.cuda.synchronize(device=dev_idx)

            latencies = []
            for _ in range(iterations):
                torch.cuda.synchronize(device=dev_idx)
                start = time.perf_counter()
                y = conv(x)
                torch.cuda.synchronize(device=dev_idx)
                elapsed = time.perf_counter() - start
                latencies.append(elapsed)

            avg_s = statistics.mean(latencies)
            # Rough FLOP estimate for Conv2D
            output_size = input_size  # with padding=1
            flops_per_conv = (
                2 * kernel_size * kernel_size * in_channels * out_channels *
                output_size * output_size * batch
            )
            tflops = (flops_per_conv / avg_s) / 1e12 if avg_s > 0 else 0.0
            results["conv2d"][f"{input_size}"] = round(tflops, 2)
        except Exception as e:
            results["conv2d"][f"{n}"] = f"error: {e}"

    return results


# ═══════════════════════════════════════════════════════════
#  INFERENCE BENCHMARK
# ═══════════════════════════════════════════════════════════

class DummyCNN(torch.nn.Module):
    """Dummy CNN model for inference benchmarking."""

    def __init__(self):
        super().__init__()
        self.conv1 = torch.nn.Conv2d(3, 64, kernel_size=3, padding=1)
        self.bn1 = torch.nn.BatchNorm2d(64)
        self.conv2 = torch.nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.bn2 = torch.nn.BatchNorm2d(128)
        self.pool = torch.nn.MaxPool2d(2)
        self.conv3 = torch.nn.Conv2d(128, 256, kernel_size=3, padding=1)
        self.bn3 = torch.nn.BatchNorm2d(256)
        self.conv4 = torch.nn.Conv2d(256, 512, kernel_size=3, padding=1)
        self.bn4 = torch.nn.BatchNorm2d(512)
        self.gap = torch.nn.AdaptiveAvgPool2d(1)
        self.fc = torch.nn.Linear(512, 1000)

    def forward(self, x):
        x = torch.relu(self.bn1(self.conv1(x)))
        x = self.pool(torch.relu(self.bn2(self.conv2(x))))
        x = torch.relu(self.bn3(self.conv3(x)))
        x = self.pool(torch.relu(self.bn4(self.conv4(x))))
        x = self.gap(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x


class DummyTransformer(torch.nn.Module):
    """Dummy Transformer model for inference benchmarking."""

    def __init__(self, vocab_size=30522, d_model=768, nhead=12,
                 num_layers=4, max_len=512):
        super().__init__()
        self.embedding = torch.nn.Embedding(vocab_size, d_model)
        self.pos_encoder = torch.nn.Embedding(max_len, d_model)
        encoder_layer = torch.nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, batch_first=True,
            dim_feedforward=3072, dropout=0.1, activation='gelu'
        )
        self.transformer = torch.nn.TransformerEncoder(
            encoder_layer, num_layers=num_layers
        )
        self.fc = torch.nn.Linear(d_model, vocab_size)

    def forward(self, x):
        positions = torch.arange(x.size(1), device=x.device).unsqueeze(0)
        x = self.embedding(x) + self.pos_encoder(positions)
        x = self.transformer(x)
        x = self.fc(x[:, 0, :])  # CLS token
        return x


def inference_benchmark(
    device: str,
    batch_size: int = 32,
    iterations: int = 100,
    warmup: int = 10,
    model_type: str = "cnn",
    extra_args: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Benchmark inference throughput and latency.

    Args:
        device: Device string
        batch_size: Batch size for inference
        iterations: Number of iterations
        warmup: Number of warmup iterations
        model_type: "cnn", "transformer", "yolo", or "llm"
        extra_args: Extra arguments (yolo_model, llm_model, etc.)

    Returns:
        dict with throughput (FPS) and latency (p50/p95/p99) metrics
    """
    import torch

    results: Dict[str, Any] = {
        "model_type": model_type,
        "device": device,
        "batch_size": batch_size,
        "iterations": iterations,
        "throughput_fps": 0.0,
        "latency_avg_ms": 0.0,
        "latency_p50_ms": 0.0,
        "latency_p95_ms": 0.0,
        "latency_p99_ms": 0.0,
        "vram_peak_gb": None,
        "vram_delta_gb": None,
    }

    if extra_args is None:
        extra_args = {}

    is_cuda = device.startswith("cuda")
    dev_idx = int(device.split(":")[1]) if ":" in device else 0

    try:
        # ── Load model ────────────────────────────────────────────
        model = None
        input_data = None

        if model_type == "yolo":
            try:
                from ultralytics import YOLO
                yolo_model = extra_args.get("yolo_model", "yolov8n.pt")
                model = YOLO(yolo_model)
                # YOLO needs image input, use random tensor
                input_data = torch.randn(batch_size, 3, 640, 640, device=device)
            except ImportError:
                results["error"] = "ultralytics not installed"
                return results

        elif model_type == "llm":
            try:
                from vllm import LLM, SamplingParams
                llm_model_name = extra_args.get("llm_model", "")
                if not llm_model_name:
                    results["error"] = "No llm_model specified"
                    return results
                # vLLM benchmark is special: run multiple requests
                prompts = ["Hello, how are you?"] * batch_size
                llm = LLM(model=llm_model_name, dtype="float16", device=device)

                latencies = []
                for i in range(min(iterations, 20)):
                    start = time.perf_counter()
                    outputs = llm.generate(prompts)
                    elapsed = time.perf_counter() - start
                    latencies.append(elapsed)

                avg_s = statistics.mean(latencies)
                results["throughput_fps"] = round(batch_size / avg_s, 2) if avg_s > 0 else 0.0
                results["latency_avg_ms"] = round(avg_s * 1000, 2)
                results["note"] = "LLM benchmark uses vLLM (fewer iterations)"
                return results
            except ImportError:
                results["error"] = "vllm not installed"
                return results

        elif model_type == "cnn":
            model = DummyCNN().to(device)
            model.eval()
            input_data = torch.randn(batch_size, 3, 224, 224, device=device)

        elif model_type == "transformer":
            model = DummyTransformer().to(device)
            model.eval()
            input_data = torch.randint(0, 1000, (batch_size, 128), device=device)

        else:
            results["error"] = f"Unknown model_type: {model_type}"
            return results

        # ── Benchmark ─────────────────────────────────────────────
        if model is not None and input_data is not None:
            # Warmup
            with torch.no_grad():
                for _ in range(warmup):
                    _ = model(input_data)
                    if is_cuda:
                        torch.cuda.synchronize(device=dev_idx)

            # Reset peak memory tracking
            if is_cuda:
                try:
                    torch.cuda.reset_peak_memory_stats(dev_idx)
                    vram_before = torch.cuda.memory_allocated(dev_idx) / (1024**3)
                except Exception:
                    vram_before = None
            else:
                vram_before = None

            # Benchmark loop
            latencies = []
            with torch.no_grad():
                for i in range(iterations):
                    if is_cuda:
                        torch.cuda.synchronize(device=dev_idx)
                    start = time.perf_counter()
                    _ = model(input_data)
                    if is_cuda:
                        torch.cuda.synchronize(device=dev_idx)
                    elapsed = time.perf_counter() - start
                    latencies.append(elapsed)

            # VRAM stats
            vram_peak = None
            if is_cuda:
                try:
                    vram_peak = torch.cuda.max_memory_allocated(dev_idx) / (1024**3)
                    vram_after = torch.cuda.memory_allocated(dev_idx) / (1024**3)
                    results["vram_peak_gb"] = round(vram_peak, 2)
                    if vram_before is not None:
                        results["vram_delta_gb"] = round(vram_after - vram_before, 2)
                except Exception:
                    pass

            # Compute stats
            avg_s = statistics.mean(latencies)
            sorted_lat = sorted(latencies)
            results["throughput_fps"] = round(1.0 / avg_s, 2) if avg_s > 0 else 0.0
            results["latency_avg_ms"] = round(avg_s * 1000, 2)
            results["latency_p50_ms"] = round(statistics.median(latencies) * 1000, 2)
            results["latency_p95_ms"] = round(sorted_lat[int(len(sorted_lat) * 0.95)] * 1000, 2)
            results["latency_p99_ms"] = round(sorted_lat[int(len(sorted_lat) * 0.99)] * 1000, 2)

    except Exception as e:
        results["error"] = str(e)

    return results


# ═══════════════════════════════════════════════════════════
#  STRESS TEST
# ═══════════════════════════════════════════════════════════

def stress_test(
    device: str,
    duration: int = 60,
    matrix_size: int = 4096,
    threshold_pct: float = 5.0,
    monitor: bool = False,
    monitor_interval: float = 1.0,
) -> Dict[str, Any]:
    """Run sustained GPU load and detect thermal throttling.

    Args:
        device: Device string
        duration: Test duration in seconds
        matrix_size: GEMM matrix size (N x N)
        threshold_pct: Clock drop percentage to flag throttling
        monitor: Whether to run rocm-smi/nvidia-smi monitoring
        monitor_interval: Monitoring polling interval in seconds

    Returns:
        dict with stability results and thermal metrics
    """
    import torch

    results: Dict[str, Any] = {
        "device": device,
        "duration_s": duration,
        "matrix_size": matrix_size,
        "stable": False,
        "throttling_detected": False,
        "clock_drop_pct": 0.0,
        "max_temp_c": 0.0,
        "max_power_w": 0.0,
        "iterations_completed": 0,
    }

    is_cuda = device.startswith("cuda")
    if not is_cuda:
        results["error"] = "Stress test requires a CUDA/ROCm device"
        return results

    dev_idx = int(device.split(":")[1]) if ":" in device else 0

    # Create matrices for GEMM
    a = torch.randn(matrix_size, matrix_size, device=device)
    b = torch.randn(matrix_size, matrix_size, device=device)

    start_time = time.time()
    iter_count = 0
    temps = []
    clocks = []
    powers = []

    print(f"  Stress test: {duration}s with GEMM {matrix_size}")
    print(f"  Monitoring: {'ON' if monitor else 'OFF'}")

    while time.time() - start_time < duration:
        # GEMM loop
        loop_start = time.time()
        while time.time() - loop_start < 1.0:  # 1-second chunks
            c = torch.mm(a, b)
            torch.cuda.synchronize(device=dev_idx)
            iter_count += 1

        # Sample monitoring data each second
        if monitor:
            temp, clock, power = _sample_gpu_metrics(is_cuda, dev_idx)
            if temp is not None:
                temps.append(temp)
            if clock is not None:
                clocks.append(clock)
            if power is not None:
                powers.append(power)

        elapsed = time.time() - start_time
        pct = min(elapsed / duration * 100, 100)
        print(f"\r  Stress: {pct:.0f}% | iterations: {iter_count} | "
              f"temp: {temps[-1] if temps else '?'}°C | "
              f"clock: {clocks[-1] if clocks else '?'} MHz", end="")

    print()

    # Analyze results
    results["iterations_completed"] = iter_count

    if temps:
        results["max_temp_c"] = round(max(temps), 1)
        results["avg_temp_c"] = round(statistics.mean(temps), 1)

    if clocks:
        initial_clock = clocks[0]
        final_clock = clocks[-1] if len(clocks) > 3 else initial_clock
        clock_drop = 0.0
        if initial_clock > 0:
            clock_drop = (initial_clock - final_clock) / initial_clock * 100
            results["clock_drop_pct"] = round(clock_drop, 2)
        results["initial_clock_mhz"] = initial_clock
        results["final_clock_mhz"] = final_clock
        results["min_clock_mhz"] = min(clocks)
        results["max_clock_mhz"] = max(clocks)

        if clock_drop >= threshold_pct:
            results["throttling_detected"] = True
            results["stable"] = False
        else:
            results["stable"] = True

    if powers:
        results["max_power_w"] = round(max(powers), 1)
        results["avg_power_w"] = round(statistics.mean(powers), 1)
        results["min_power_w"] = round(min(powers), 1)

    # If no monitoring data, just check that it ran without error
    if not temps and not clocks:
        results["stable"] = True
        results["note"] = "Monitoring data unavailable (install rocm-smi/nvidia-smi)"

    return results


def _sample_gpu_metrics(
    is_cuda: bool, device_idx: int = 0
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Sample GPU temperature, clock speed, and power draw.

    Returns:
        Tuple of (temperature_c, clock_mhz, power_w) or (None, None, None)
    """
    temp = None
    clock = None
    power = None

    if is_cuda:
        # NVIDIA: use nvidia-smi
        try:
            nv = subprocess.run(
                [
                    "nvidia-smi",
                    f"--id={device_idx}",
                    "--query-gpu=temperature.gpu,clocks.gr,power.draw",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True, text=True, timeout=5
            )
            if nv.returncode == 0:
                parts = [p.strip() for p in nv.stdout.strip().split(",")]
                if len(parts) >= 3:
                    temp = float(parts[0]) if parts[0] else None
                    clock_str = parts[1].split()[0] if parts[1] else "0"
                    clock = float(clock_str) if clock_str else None
                    power = float(parts[2]) if parts[2] else None
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass
    else:
        # AMD: use rocm-smi
        try:
            rs = subprocess.run(
                ["rocm-smi", "--showtemp", "--showclk", "--showpower", "--json"],
                capture_output=True, text=True, timeout=5
            )
            if rs.returncode == 0:
                data = json.loads(rs.stdout)
                card_key = f"card{device_idx}"
                if card_key in data:
                    card = data[card_key]
                    try:
                        temp_str = card.get("Temperature (Sensor edge) (C)", "")
                        temp = float(temp_str) if temp_str else None
                    except (ValueError, TypeError):
                        pass
                    try:
                        clock_str = card.get("sclk", "")
                        clock = float(clock_str) if clock_str else None
                    except (ValueError, TypeError):
                        pass
                    try:
                        power_str = card.get("Power Draw (W)", "")
                        power = float(power_str) if power_str else None
                    except (ValueError, TypeError):
                        pass
        except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
            pass

        # Fallback: try /sys/class/drm/ interface
        if temp is None:
            try:
                drm_dir = f"/sys/class/drm/card{device_idx}/device/hwmon"
                if os.path.isdir(drm_dir):
                    hwmon_dirs = os.listdir(drm_dir)
                    for hd in hwmon_dirs:
                        temp_path = os.path.join(drm_dir, hd, "temp1_input")
                        if os.path.isfile(temp_path):
                            with open(temp_path) as f:
                                temp = float(f.read().strip()) / 1000.0
                            break
            except (FileNotFoundError, ValueError, OSError):
                pass

    return temp, clock, power


# ═══════════════════════════════════════════════════════════
#  GPU MONITOR (inline)
# ═══════════════════════════════════════════════════════════

class GPUMonitor:
    """Real-time GPU monitor that samples metrics during benchmark."""

    def __init__(self, interval: float = 1.0, is_cuda: bool = True):
        self.interval = interval
        self.is_cuda = is_cuda
        self.samples: List[Dict[str, Any]] = []
        self.running = False

    def start(self):
        """Start monitoring in background."""
        import threading
        self.running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> List[Dict[str, Any]]:
        """Stop monitoring and return collected samples."""
        self.running = False
        if hasattr(self, '_thread'):
            self._thread.join(timeout=5)
        return self.samples

    def _poll_loop(self):
        """Poll GPU metrics at regular intervals."""
        while self.running:
            temp, clock, power = _sample_gpu_metrics(self.is_cuda)
            if temp is not None or clock is not None:
                self.samples.append({
                    "timestamp": time.time(),
                    "temp_c": temp,
                    "clock_mhz": clock,
                    "power_w": power,
                })
            time.sleep(self.interval)

    def summary(self) -> Dict[str, Any]:
        """Compute summary statistics from collected samples."""
        if not self.samples:
            return {"note": "No samples collected"}

        temps = [s["temp_c"] for s in self.samples if s["temp_c"] is not None]
        clocks = [s["clock_mhz"] for s in self.samples if s["clock_mhz"] is not None]
        powers = [s["power_w"] for s in self.samples if s["power_w"] is not None]

        summary: Dict[str, Any] = {}
        if temps:
            summary["temp"] = {
                "min_c": round(min(temps), 1),
                "avg_c": round(statistics.mean(temps), 1),
                "max_c": round(max(temps), 1),
            }
        if clocks:
            summary["clock"] = {
                "min_mhz": round(min(clocks), 1),
                "avg_mhz": round(statistics.mean(clocks), 1),
                "max_mhz": round(max(clocks), 1),
            }
        if powers:
            summary["power"] = {
                "min_w": round(min(powers), 1),
                "avg_w": round(statistics.mean(powers), 1),
                "max_w": round(max(powers), 1),
            }
        return summary


# ═══════════════════════════════════════════════════════════
#  REPORTING
# ═══════════════════════════════════════════════════════════

def print_info(backend_info: Dict[str, Any]):
    """Print system information."""
    print("╔══════════════════════════════════════════╗")
    print("║       MUNIN — GPU Benchmark Suite       ║")
    print("╚══════════════════════════════════════════╝")
    bi = backend_info
    print(f"  Backend:          {bi['backend'].upper()}")
    print(f"  Device:           {bi['device_name'] or 'N/A'}")
    print(f"  GPU Count:        {bi['device_count']}")
    print(f"  Driver:           {bi['driver_version'] or 'N/A'}")
    print(f"  Torch:            {bi['torch_version'] or 'N/A'}")
    print(f"  Torch CUDA:       {bi.get('torch_cuda', False)}")

    if bi.get("hip_version"):
        print(f"  HIP version:      {bi['hip_version']}")
    if bi.get("cuda_version"):
        print(f"  CUDA version:     {bi['cuda_version']}")
    if bi.get("gfx_arch"):
        print(f"  GFX Arch:         {bi['gfx_arch']}")
    if bi.get("compute_capability"):
        print(f"  Compute Cap:      {bi['compute_capability']}")
    if bi.get("vram_total_gb", 0) > 0:
        print(f"  VRAM Total:       {bi['vram_total_gb']} GB")
    if bi.get("vram_free_gb") is not None:
        print(f"  VRAM Free:        {bi['vram_free_gb']} GB")


def print_report(all_results: Dict[str, Any], backend_info: Dict[str, Any]):
    """Print consolidated benchmark report."""
    print()
    print("═" * 64)
    print("         MUNIN — GPU Benchmark Report")
    print("═" * 64)

    bi = backend_info
    print(f"  System:       {bi.get('device_name', 'N/A')} ({bi['backend'].upper()})")
    print(f"  Driver:       {bi.get('driver_version', 'N/A')}")
    print(f"  Torch:        {bi.get('torch_version', 'N/A')}")

    # Memory
    if "memory" in all_results:
        mem = all_results["memory"]
        print()
        print("── Memory (GB/s) ─────────────────────────────────────")
        h2d = mem.get("h2d", {})
        d2h = mem.get("d2h", {})
        p2p = mem.get("p2p", {})
        if h2d:
            best_size = max(h2d.keys(), key=lambda k: float(h2d[k]) if isinstance(h2d[k], (int, float)) else 0)
            print(f"  H2D:          {h2d[best_size]:>8.1f} GB/s  (size: {best_size} MB)")
        if d2h:
            best_size = max(d2h.keys(), key=lambda k: float(d2h[k]) if isinstance(d2h[k], (int, float)) else 0)
            print(f"  D2H:          {d2h[best_size]:>8.1f} GB/s  (size: {best_size} MB)")
        if p2p:
            valid = {k: v for k, v in p2p.items() if isinstance(v, (int, float))}
            if valid:
                best_size = max(valid.keys(), key=lambda k: float(valid[k]))
                print(f"  P2P:          {p2p[best_size]:>8.1f} GB/s  (size: {best_size} MB)")
            if "note" in p2p:
                print(f"  P2P:          {p2p['note']}")

    # Compute
    if "compute" in all_results:
        comp = all_results["compute"]
        print()
        print("── Compute (TFLOPS) ──────────────────────────────────")
        for dtype_key, label in [("gemm_fp32", "GEMM FP32"), ("gemm_fp16", "GEMM FP16")]:
            gemm = comp.get(dtype_key, {})
            valid = {k: v for k, v in gemm.items() if isinstance(v, (int, float))}
            if valid:
                for size in sorted(valid.keys(), key=int):
                    print(f"  {label} {size:>5s}:  {valid[size]:>8.2f} TFLOPS")

        fft = comp.get("fft", {})
        valid_fft = {k: v for k, v in fft.items() if isinstance(v, (int, float))}
        if valid_fft:
            for size in sorted(valid_fft.keys(), key=int):
                print(f"  FFT {size:>5s}:      {valid_fft[size]:>8.2f} GB/s")

        conv = comp.get("conv2d", {})
        valid_conv = {k: v for k, v in conv.items() if isinstance(v, (int, float))}
        if valid_conv:
            for size in sorted(valid_conv.keys(), key=int):
                print(f"  Conv2D {size:>5s}:   {valid_conv[size]:>8.2f} TFLOPS")

    # Inference
    if "inference" in all_results:
        inf = all_results["inference"]
        print()
        print("── Inference ────────────────────────────────────────")
        for model_type in ["cnn", "transformer", "yolo", "llm"]:
            if model_type in inf:
                m = inf[model_type]
                if "error" in m:
                    print(f"  {model_type.capitalize()}: {m['error']}")
                else:
                    fps = m.get("throughput_fps", 0)
                    p50 = m.get("latency_p50_ms", 0)
                    p95 = m.get("latency_p95_ms", 0)
                    p99 = m.get("latency_p99_ms", 0)
                    print(f"  {model_type.capitalize()}: {fps:>8.1f} FPS  |  "
                          f"p50 {p50:>6.2f} ms  |  p95 {p95:>6.2f} ms  |  "
                          f"p99 {p99:>6.2f} ms")
                    if m.get("vram_peak_gb"):
                        print(f"            VRAM peak: {m['vram_peak_gb']:.1f} GB")
                    if m.get("vram_delta_gb"):
                        print(f"            VRAM delta: {m['vram_delta_gb']:.1f} GB")

    # Stress
    if "stress_test" in all_results:
        st = all_results["stress_test"]
        print()
        print("── Stress Test ──────────────────────────────────────")
        if "error" in st:
            print(f"  {st['error']}")
        else:
            stable = st.get("stable", False)
            status = "✅ YES" if stable else "❌ NO (throttling)"
            print(f"  Duration:     {st.get('duration_s', 0):.0f} s")
            print(f"  Iterations:   {st.get('iterations_completed', 0)}")
            print(f"  Stable:       {status}")
            if st.get("clock_drop_pct") is not None:
                print(f"  Clock Drop:   {st['clock_drop_pct']:.1f}%")
            if st.get("max_temp_c", 0) > 0:
                print(f"  Max Temp:     {st['max_temp_c']:.0f}°C")
            if st.get("max_power_w", 0) > 0:
                print(f"  Max Power:    {st['max_power_w']:.0f} W")

    # Monitor summary
    if "monitor_summary" in all_results:
        ms = all_results["monitor_summary"]
        print()
        print("── GPU Monitor ──────────────────────────────────────")
        if "temp" in ms:
            t = ms["temp"]
            print(f"  Temperature:  min {t['min_c']}°C  |  avg {t['avg_c']}°C  |  max {t['max_c']}°C")
        if "power" in ms:
            p = ms["power"]
            print(f"  Power:        min {p['min_w']}W  |  avg {p['avg_w']}W  |  max {p['max_w']}W")
        if "clock" in ms:
            c = ms["clock"]
            print(f"  Clock:        min {c['min_mhz']} MHz  |  avg {c['avg_mhz']} MHz  |  max {c['max_mhz']} MHz")

    # Overall
    has_errors = False
    for section in ["memory", "compute", "inference", "stress_test"]:
        if section in all_results and "error" in all_results[section]:
            has_errors = True

    print()
    print("══ Summary ════════════════════════════════════════════")
    if has_errors:
        print("  Overall:    ⚠️  PARTIAL (some benchmarks had errors)")
    else:
        print("  Overall:    ✅ PASS (all benchmarks completed)")
    print("═" * 64)


# ═══════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="GPU Benchmark Suite for AMD ROCm and NVIDIA CUDA",
    )
    parser.add_argument("--memory", action="store_true", help="Run memory benchmarks")
    parser.add_argument("--compute", action="store_true", help="Run compute benchmarks")
    parser.add_argument("--inference", action="store_true", help="Run inference benchmarks")
    parser.add_argument("--stress", action="store_true", help="Run stress test")
    parser.add_argument("--all", action="store_true", help="Run all benchmarks")
    parser.add_argument("--info", action="store_true", help="Show system information")
    parser.add_argument("--device", default="auto", help="Device (auto/cuda:0/cpu)")
    parser.add_argument("--iterations", type=int, default=100, help="Iterations per benchmark")
    parser.add_argument("--warmup", type=int, default=10, help="Warmup iterations")
    parser.add_argument("--duration", type=int, default=60, help="Stress test duration (s)")
    parser.add_argument("--batch-size", type=int, default=32, help="Inference batch size")
    parser.add_argument("--batch-sizes", type=str, default="", help="Comma-separated batch sizes")
    parser.add_argument("--memory-sizes", type=str, default="1024,4096,16384",
                        help="Memory sizes in MB")
    parser.add_argument("--matrix-sizes", type=str, default="512,1024,2048,4096",
                        help="GEMM matrix sizes")
    parser.add_argument("--dtype", default="fp32", help="Compute dtype (fp32/fp16)")
    parser.add_argument("--model", default="cnn",
                        help="Inference model (cnn/transformer/yolo/llm)")
    parser.add_argument("--monitor", action="store_true",
                        help="Enable real-time GPU monitoring")
    parser.add_argument("--monitor-interval", type=float, default=1.0,
                        help="Monitor polling interval")
    parser.add_argument("--json", action="store_true", help="Export results as JSON")
    parser.add_argument("--output", default="benchmark-results.json",
                        help="JSON output file path")
    parser.add_argument("--runs", type=int, default=1, help="Number of benchmark runs")
    parser.add_argument("--cooldown", type=int, default=5, help="Cooldown between runs (s)")
    parser.add_argument("--threshold", type=float, default=5.0,
                        help="Clock drop % for throttling detection")
    parser.add_argument("--yolo-model", default="yolov8n.pt",
                        help="YOLO model name for real inference")
    parser.add_argument("--llm-model", default="",
                        help="LLM model name for real inference (vLLM)")
    return parser.parse_args()


def main():
    args = parse_args()

    # Detect backend
    backend_info = detect_backend()
    device = get_device(args.device)

    # If device is cpu but we have a GPU, warn
    if device == "cpu" and backend_info["available"]:
        print("  ⚠️  GPU detected but using CPU (use --device auto for GPU)")

    # Show info only
    if args.info or not (args.memory or args.compute or args.inference or args.stress or args.all):
        print_info(backend_info)
        if not (args.memory or args.compute or args.inference or args.stress or args.all):
            print()
            print("  Run with --memory, --compute, --inference, --stress, or --all")
            return

    # Determine what to run
    run_memory = args.memory or args.all
    run_compute = args.compute or args.all
    run_inference = args.inference or args.all
    run_stress = args.stress or args.all

    # Parse size lists
    memory_sizes = [int(s.strip()) for s in args.memory_sizes.split(",") if s.strip()]
    matrix_sizes = [int(s.strip()) for s in args.matrix_sizes.split(",") if s.strip()]
    batch_sizes = [int(s.strip()) for s in args.batch_sizes.split(",") if s.strip()]
    if not batch_sizes:
        batch_sizes = [args.batch_size]

    all_results: Dict[str, Any] = {}

    # Start monitor if requested
    monitor = None
    if args.monitor and device.startswith("cuda"):
        is_cuda = backend_info["backend"] == "cuda"
        monitor = GPUMonitor(interval=args.monitor_interval, is_cuda=is_cuda)
        monitor.start()
        print("  ✅ GPU monitoring active")

    # ── Memory Benchmark ───────────────────────────────────────────
    if run_memory and device.startswith("cuda"):
        print()
        print("─" * 64)
        print("  MEMORY BENCHMARK")
        print("─" * 64)
        mem_results = memory_benchmark(
            device=device,
            sizes_mb=memory_sizes,
            iterations=args.iterations,
            warmup=args.warmup,
        )
        all_results["memory"] = mem_results
        if "error" not in mem_results:
            best_h2d = max((v for v in mem_results["h2d"].values() if isinstance(v, (int, float))), default=0)
            best_d2h = max((v for v in mem_results["d2h"].values() if isinstance(v, (int, float))), default=0)
            print(f"  H2D: {best_h2d:.1f} GB/s  |  D2H: {best_d2h:.1f} GB/s")
            for k, v in mem_results.get("p2p", {}).items():
                if isinstance(v, (int, float)):
                    print(f"  P2P: {v:.1f} GB/s")
                elif k != "error":
                    print(f"  P2P: {v}")
        else:
            print(f"  ⚠️  {mem_results['error']}")

    # ── Compute Benchmark ──────────────────────────────────────────
    if run_compute and device.startswith("cuda"):
        print()
        print("─" * 64)
        print("  COMPUTE BENCHMARK")
        print("─" * 64)
        comp_results = compute_benchmark(
            device=device,
            matrix_sizes=matrix_sizes,
            iterations=args.iterations,
            warmup=args.warmup,
            dtype_str=args.dtype,
        )
        all_results["compute"] = comp_results
        if "error" not in comp_results:
            for dtype_key in ["gemm_fp32", "gemm_fp16"]:
                gemm = comp_results.get(dtype_key, {})
                valid = {k: v for k, v in gemm.items() if isinstance(v, (int, float))}
                if valid:
                    best = max(valid.values())
                    print(f"  {dtype_key.upper()}: {best:.1f} TFLOPS peak")
        else:
            print(f"  ⚠️  {comp_results['error']}")

    # ── Inference Benchmark ────────────────────────────────────────
    if run_inference:
        print()
        print("─" * 64)
        print("  INFERENCE BENCHMARK")
        print("─" * 64)

        inf_results = {}
        models_to_run = [args.model] if args.model else ["cnn", "transformer"]

        # Also try YOLO if ultralytics available
        if "yolo" not in models_to_run:
            try:
                import ultralytics  # noqa: F401
                models_to_run.append("yolo")
            except ImportError:
                pass

        for model_type in models_to_run:
            for bs in batch_sizes:
                print(f"  Model: {model_type} | batch: {bs}")
                extra = {}
                if model_type == "yolo":
                    extra["yolo_model"] = args.yolo_model
                elif model_type == "llm":
                    extra["llm_model"] = args.llm_model

                m_results = inference_benchmark(
                    device=device,
                    batch_size=bs,
                    iterations=args.iterations,
                    warmup=args.warmup,
                    model_type=model_type,
                    extra_args=extra,
                )
                inf_results[f"{model_type}_b{bs}"] = m_results

                if "error" not in m_results:
                    print(f"    Throughput: {m_results.get('throughput_fps', 0):.1f} FPS  |  "
                          f"p50 {m_results.get('latency_p50_ms', 0):.2f} ms  |  "
                          f"p95 {m_results.get('latency_p95_ms', 0):.2f} ms")
                else:
                    print(f"    ⚠️  {m_results['error']}")

        all_results["inference"] = inf_results

    # ── Stress Test ────────────────────────────────────────────────
    if run_stress and device.startswith("cuda"):
        print()
        print("─" * 64)
        print("  STRESS TEST")
        print("─" * 64)
        st_results = stress_test(
            device=device,
            duration=args.duration,
            matrix_size=matrix_sizes[-1] if matrix_sizes else 4096,
            threshold_pct=args.threshold,
            monitor=True,
            monitor_interval=args.monitor_interval,
        )
        all_results["stress_test"] = st_results
        if "error" not in st_results:
            if st_results.get("stable"):
                print(f"  ✅ Stable (clock drop: {st_results.get('clock_drop_pct', 0):.1f}%)")
            else:
                print(f"  ❌ Throttling detected (clock drop: {st_results.get('clock_drop_pct', 0):.1f}%)")

    # ── Stop Monitor ───────────────────────────────────────────────
    if monitor:
        samples = monitor.stop()
        monitor_summary = monitor.summary()
        all_results["monitor_summary"] = monitor_summary
        print()
        print("─" * 64)
        print("  MONITOR SUMMARY")
        print("─" * 64)
        if "temp" in monitor_summary:
            t = monitor_summary["temp"]
            print(f"  Temperature:  min {t['min_c']}°C  avg {t['avg_c']}°C  max {t['max_c']}°C")
        if "power" in monitor_summary:
            p = monitor_summary["power"]
            print(f"  Power:        min {p['min_w']}W  avg {p['avg_w']}W  max {p['max_w']}W")
        if "clock" in monitor_summary:
            c = monitor_summary["clock"]
            print(f"  Clock:        min {c['min_mhz']} MHz  avg {c['avg_mhz']} MHz  max {c['max_mhz']} MHz")
        print(f"  Samples:      {len(samples)}")

    # ── Final Report ───────────────────────────────────────────────
    all_results["system"] = backend_info
    print_report(all_results, backend_info)

    # ── JSON Export ────────────────────────────────────────────────
    if args.json:
        output_path = args.output
        try:
            with open(output_path, "w") as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            print(f"\n  ✅ JSON results exported to: {output_path}")
        except Exception as e:
            print(f"\n  ❌ ERROR: Failed to write JSON: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
