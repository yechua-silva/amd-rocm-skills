---
name: yolo-rocm-deploy
description: |
  Despliegue de YOLOv8x con PyTorch para detección de objetos en GPUs AMD ROCm
  o NVIDIA CUDA, con fallback automático a CPU. Exportación a ONNX (universal),
  TorchScript, TensorRT (NVIDIA) y OpenVINO (Intel). Benchmark completo de
  rendimiento: FPS, latencia p50/p95/p99, VRAM, throughput. Validación de
  precisión mAP@50 y mAP@50:95. Usar cuando necesites ejecutar YOLO en GPU
  AMD o NVIDIA, exportar modelos para diferentes backends, o benchmarkear
  detección de objetos. Keywords: yolo, rocm, cuda, pytorch, ultralytics,
  detection, onnx, benchmark, mi300x
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: "Munin Project"
  tags:
    - amd
    - rocm
    - yolo
    - pytorch
    - detection
    - benchmark
    - nvidia
    - cuda
    - ultralytics
compatibility:
  - claude-code
  - opencode
  - codex
  - cursor
---

# YOLO ROCm / CUDA Deploy Skill

## Purpose

Deploy YOLOv8x with PyTorch for object detection on **both AMD ROCm and NVIDIA CUDA** GPUs. The skill auto-detects the available backend, sets the correct device, and provides unified scripts for inference, model export, and benchmarking.

This skill is backend-agnostic: the same scripts work on AMD MI300X, NVIDIA A100/H100, and CPU fallback. All PyTorch APIs (`torch.cuda`, `torch.version.hip`) are handled transparently.

## When to Use

- "Run YOLO on AMD GPU / ejecutar YOLO en GPU AMD"
- "Run YOLO on NVIDIA GPU / ejecutar YOLO en GPU NVIDIA"
- "Export YOLO model for inference / exportar modelo YOLO para inferencia"
- "Benchmark YOLO performance / benchmark de rendimiento YOLO"
- "Compare GPU vs CPU performance for YOLO / comparar GPU vs CPU para YOLO"
- Keywords: yolo, rocm, pytorch, cuda, object detection, ultralytics, amd, nvidia, benchmark, export, onnx, torchscript

## Prerequisites

- **Python 3.10+**
- **PyTorch** with ROCm or CUDA support (`torch.cuda.is_available()` must return `True`)
- **ultralytics** package installed
- **GPU with 8GB+ VRAM** for YOLOv8x (use smaller models like YOLOv8n for ≤4GB)
- **Optional**: `onnxruntime` or `onnxruntime-rocm` if exporting to ONNX
- **Optional**: `nvidia-tensorrt` if exporting to TensorRT engine (NVIDIA only)

## Quickstart

### 1. Detect GPU Backend

```bash
python3 -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'Device count: {torch.cuda.device_count()}')
print(f'Device name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')
print(f'HIP version: {torch.version.hip or \"N/A\"}')
print(f'CUDA version: {torch.version.cuda or \"N/A\"}')
"
```

### 2. Run YOLO Inference

```bash
# Auto-detects backend (ROCm, CUDA, or CPU)
python3 scripts/export-yolo.py --model yolov8x.pt
python3 scripts/benchmark-yolo.py --model yolov8x.pt --iterations 100
```

### 3. Benchmark with JSON Output

```bash
python3 scripts/benchmark-yolo.py --model yolov8x.pt --iterations 200 --json --output benchmark-results.json
```

## Step-by-Step Guide

### 1. Detect Backend

The scripts auto-detect which backend is available:

| Check | AMD ROCm | NVIDIA CUDA | CPU Fallback |
|-------|----------|-------------|--------------|
| `torch.cuda.is_available()` | `True` | `True` | `False` |
| `torch.version.hip` | `"7.2.0"` (or similar) | `None` | `None` |
| `torch.version.cuda` | `None` | `"12.4"` (or similar) | `None` |
| `torch.cuda.get_device_name(0)` | `"AMD Instinct MI300X"` | `"NVIDIA A100-SXM-80GB"` | N/A |

**Important**: There is no `torch.rocm` API. Both backends use `torch.cuda` transparently. Use `torch.version.hip` to distinguish AMD from NVIDIA.

### 2. Install Ultralytics

```bash
pip install ultralytics onnx onnxruntime
```

For NVIDIA TensorRT export:
```bash
pip install tensorrt
```

For ROCm ONNX optimization:
```bash
pip install onnxruntime-rocm
```

### 3. Load a YOLO Model

```python
from ultralytics import YOLO

# Auto-downloads yolov8x.pt if not present
model = YOLO("yolov8x.pt")
```

Ultralytics supports these model families:
- **YOLOv8**: n/s/m/l/x (3.2M to 68.2M parameters)
- **YOLO11**: n/s/m/l/x (latest generation)
- Custom trained models (.pt files)

### 4. Run Inference on GPU

```python
import torch

device = "cuda:0" if torch.cuda.is_available() else "cpu"
model = YOLO("yolov8x.pt")

# Single image inference
results = model.predict("image.jpg", device=device, verbose=False)

# Batch inference (improves throughput)
results = model.predict(["img1.jpg", "img2.jpg", "img3.jpg"], device=device, batch=8, verbose=False)
```

The `device="cuda:0"` parameter works identically on AMD ROCm and NVIDIA CUDA. Ultralytics internally maps it to the correct backend.

### 5. CPU Fallback (No GPU Available)

```python
# Falls back automatically if no GPU detected
device = "cuda:0" if torch.cuda.is_available() else "cpu"
model = YOLO("yolov8x.pt")
results = model.predict("image.jpg", device=device, verbose=False)
```

On CPU, expect 5–15× slower inference. YOLOv8n is recommended for CPU-only deployments. The `--device` argument explicitly overrides auto-detection:

```bash
python3 scripts/benchmark-yolo.py --device cpu
```

### 6. Export Model

```python
from ultralytics import YOLO

model = YOLO("yolov8x.pt")

# TorchScript — universal, works on all backends
model.export(format="torchscript", device="cuda:0")

# ONNX — universal, best interoperability
model.export(format="onnx", device="cuda:0")

# TensorRT engine — NVIDIA only (will fail on AMD)
# model.export(format="engine", device="cuda:0")

# OpenVINO — Intel only
# model.export(format="openvino", device="cpu")
```

The `export-yolo.py` script auto-selects the best format:
- **AMD ROCm** → ONNX (universal, MIGraphX optimizable)
- **NVIDIA CUDA** → TensorRT engine (max performance)
- **CPU** → TorchScript (universal, no dependencies)

### 7. Benchmarking

```bash
# Basic benchmark
python3 scripts/benchmark-yolo.py --model yolov8x.pt --iterations 200

# Compare GPU vs CPU
python3 scripts/benchmark-yolo.py --model yolov8x.pt --iterations 100 --compare

# JSON output for further analysis
python3 scripts/benchmark-yolo.py --model yolov8s.pt --iterations 500 --json --output results.json

# Custom image
python3 scripts/benchmark-yolo.py --model yolov8n.pt --image test.jpg --iterations 1000
```

### 8. Metrics Reported

| Metric | Description |
|--------|-------------|
| **Latency Avg** | Mean inference time per image (ms) |
| **Latency Min** | Fastest single inference (ms) |
| **Latency Max** | Slowest single inference (ms) |
| **Latency Stdev** | Latency variability (ms) |
| **FPS** | Frames per second (1000 / avg latency ms) |
| **VRAM Usage** | GPU memory used during inference (GB) |
| **Backend** | Detected backend (ROCm / CUDA / CPU) |

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/model-families.md](references/model-families.md) | YOLO model comparison: params, speed, VRAM, use cases |
| [references/rocm-vs-cuda.md](references/rocm-vs-cuda.md) | ROCm vs CUDA performance comparison with optimization tips |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/export-yolo.py` | Export YOLO model to ONNX/TorchScript/TensorRT with auto-backend detection |
| `scripts/benchmark-yolo.py` | Full benchmark: latency, FPS, VRAM, GPU vs CPU comparison, JSON export |

## Common Issues

### 1. "CUDA error: no kernel image is available for execution on the device"

**Problem**: PyTorch was compiled for a different GPU architecture than the one installed.
**Solution**: Reinstall PyTorch for the correct ROCm version:
```bash
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm7.2
```

### 2. "hipErrorNoBinaryForGPU" when loading model

**Problem**: The installed ROCm runtime does not support the GPU (e.g., a consumer AMD card without ROCm support).
**Solution**: Check GPU compatibility at [rocm.docs.amd.com](https://rocm.docs.amd.com). For unsupported GPUs, use CPU fallback or ONNX with MIGraphX.

### 3. "OutOfMemoryError" with YOLOv8x

**Problem**: GPU does not have enough VRAM (YOLOv8x needs ~7.2 GB at FP32).
**Solution**: Use a smaller model (`yolov8n`, `yolov8s`), enable FP16 with `model.half()`, or use CPU fallback with `--device cpu`.

### 4. TensorRT export fails on AMD GPU

**Problem**: TensorRT (`engine` format) is NVIDIA-only and will fail on AMD ROCm with "libnvinfer.so not found" or a cryptic CUDA error.
**Solution**: Use ONNX export (`--format onnx`) instead. AMD GPUs can optimize ONNX models via MIGraphX.

### 5. OpenVINO export fails on AMD/NVIDIA GPU

**Problem**: OpenVINO is Intel hardware-specific. Export requires `--device cpu` and OpenVINO may not be installed.
**Solution**: Use `--format onnx` or `--format torchscript` which are universal formats.

### 6. "torch.cuda.is_available()" returns False despite having an AMD GPU

**Problem**: PyTorch was installed from the standard index (pytorch.org) which ships CUDA-only binaries.
**Solution**: Install PyTorch from the ROCm index:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm7.2
```

### 7. Slow inference on ROCm compared to CUDA

**Problem**: ROCm inference can be 1.3–1.8× slower than equivalent CUDA on comparable hardware, especially without optimizations.
**Solution**: Export to TorchScript for ~15% speedup, use FP16 precision (`model.half()`), enable batch inference, and consider MIGraphX optimization for ONNX exports.

### 8. Model export succeeds but inference gives wrong results

**Problem**: Post-export validation was not performed. Some export formats have precision loss, especially with FP16 or INT8 quantization.
**Solution**: Always validate exported models by running inference and comparing results with the original. The `export-yolo.py` script includes auto-validation:
```bash
python3 scripts/export-yolo.py --model yolov8x.pt --format onnx --validate
```

## Technical Notes

- **`torch.cuda` API works on both ROCm and CUDA**: All standard PyTorch CUDA operations (`torch.cuda.is_available()`, `torch.cuda.device_count()`, `torch.cuda.get_device_name()`, `torch.cuda.memory_allocated()`) function identically on AMD GPUs.
- **`torch.version.hip` is the ROCm detector**: This attribute is `None` on CUDA builds and contains the HIP version string on ROCm builds (e.g., `"7.2.0"`).
- **`torch.version.cuda` is the CUDA detector**: This attribute is `None` on ROCm builds and contains the CUDA version string on CUDA builds.
- **Ultralytics auto-detects backend**: The `device` parameter in Ultralytics accepts `"cuda:0"` regardless of whether the backend is NVIDIA or AMD.
- **Multi-GPU**: Use `device="0,1"` for multi-GPU inference. Works on both ROCm (multiple MI300X) and CUDA (multiple A100/H100).
