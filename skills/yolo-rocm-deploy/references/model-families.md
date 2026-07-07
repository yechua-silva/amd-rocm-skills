# YOLO Model Families

## Overview

This reference compares YOLOv8 and YOLO11 model families for object detection.
All models are supported by the Ultralytics library and run on AMD ROCm,
NVIDIA CUDA, and CPU (with varying performance).

## YOLOv8 vs YOLO11 Comparison

| Model | Params (M) | mAP@50 | Speed CPU (ms) | Speed GPU (ms) | VRAM (GB) | Use Case |
|-------|-----------|--------|----------------|----------------|-----------|----------|
| **YOLOv8n** | 3.2 | 37.3 | 12 | 1.8 | 1.2 | Edge devices, CPU-only, real-time on low-power |
| **YOLOv8s** | 11.2 | 44.9 | 22 | 3.2 | 2.0 | Lightweight deployment, mobile, embedded |
| **YOLOv8m** | 25.9 | 50.2 | 40 | 5.8 | 3.5 | Balanced accuracy/speed, general purpose |
| **YOLOv8l** | 43.7 | 52.9 | 65 | 9.1 | 5.0 | High accuracy, server-side batch inference |
| **YOLOv8x** | 68.2 | 53.9 | 95 | 14.0 | 7.2 | Maximum accuracy, Munin PPE detection |
| **YOLO11n** | 2.6 | 39.5 | 10 | 1.5 | 1.0 | Edge, lighter than v8n with better mAP |
| **YOLO11s** | 9.4 | 47.0 | 18 | 2.8 | 1.8 | Lightweight, improved over v8s |
| **YOLO11m** | 20.1 | 52.3 | 34 | 5.0 | 3.2 | Strong balance, 23% fewer params than v8m |
| **YOLO11l** | 38.2 | 54.6 | 55 | 8.0 | 4.8 | High accuracy, efficient over v8l |
| **YOLO11x** | 56.9 | 55.6 | 80 | 12.0 | 6.8 | Best accuracy, 17% fewer params than v8x |

### Notes on the table

- **Params**: Millions of parameters — smaller is faster but less accurate.
- **mAP@50**: Mean Average Precision at IoU=0.5 — higher is better.
- **Speed CPU**: Approximate inference time on an AMD Ryzen 9 / Intel i9 (ms per 640×640 image). Varies significantly by hardware.
- **Speed GPU**: Approximate inference time on AMD MI300X or NVIDIA A100 (ms per 640×640 image). Real-world values depend on batch size, precision, and driver.
- **VRAM**: Approximate GPU memory usage at FP32 precision. Use FP16 (`model.half()`) to halve VRAM requirements.
- All models default to 640×640 input resolution. Larger resolutions (e.g., 1280×1280) improve accuracy but increase latency and VRAM proportionally.

## Recommended Model for Munin PPE Detection

### YOLOv8x (primary)

| Property | Value |
|----------|-------|
| Parameters | 68.2M |
| mAP@50 | 53.9 |
| VRAM (FP32) | ~7.2 GB |
| VRAM (FP16) | ~3.8 GB |
| Resolution | 640×640 |
| Speed (MI300X) | ~14 ms/image → ~70 FPS |
| Speed (A100 80GB) | ~8 ms/image → ~120 FPS |

YOLOv8x offers the maximum accuracy in the YOLOv8 family, critical for PPE
detection where false negatives (missed hard hat, vest, etc.) have safety
implications. At FP16 precision, it fits comfortably within an 8 GB GPU.

### YOLO11x (alternative)

YOLO11x achieves 55.6 mAP@50 (vs 53.9 for v8x) with 17% fewer parameters
(56.9M vs 68.2M), making it both more accurate and slightly faster. If your
pipeline supports YOLO11, it is the recommended upgrade path.

## Trade-offs

### Accuracy vs Speed

```
Accuracy (mAP@50)
    56 ┤                                    ● YOLO11x
    54 ┤                          ● YOLOv8x ● YOLO11l
    52 ┤                    ● YOLOv8l
    50 ┤              ● YOLO11m
    48 ┤        ● YOLOv8m
    46 ┤
    44 ┤  ● YOLO11s
    42 ┤
    40 ┤  ● YOLO11n
    38 ┤  ● YOLOv8n
    36 └───┬───┬───┬───┬───┬───┬───┬───┬───
          0   10  20  30  40  50  60  70
                  Parameters (M)
```

**Key insight**: The v8x → v8l drop loses only ~1 mAP point but saves 36%
parameters and 30% VRAM. If your PPE classes are well-separated, YOLOv8l may
be sufficient.

### VRAM Constraints

| VRAM Available | Max Model (FP32) | Max Model (FP16) | Recommended Batch |
|---------------|------------------|-------------------|-------------------|
| 4 GB | YOLOv8s | YOLOv8x | 1 |
| 8 GB | YOLOv8x | YOLO11x | 4 |
| 16 GB | YOLO11x + batch | Ensemble | 8 |
| 32 GB+ | Any | Any + large batch | 32+ |

### Precision Trade-offs

| Precision | VRAM Savings | Speed Impact | Accuracy Impact |
|-----------|-------------|--------------|-----------------|
| FP32 | Baseline | Baseline | Baseline |
| FP16 | ~50% | ~1.5× faster | Negligible (<0.1 mAP) |
| INT8 (via ONNX) | ~75% | ~2× faster | Small (0.2–0.5 mAP) |

**Recommendation**: Always use FP16 for production GPU inference. The accuracy
loss is negligible and the speed/memory benefits are substantial.

## Model Selection Flowchart

```
Need object detection on AMD/NVIDIA GPU?
│
├─ VRAM ≥ 8 GB ──► YOLOv8x (max accuracy)
│                   YOLO11x (if available, even better)
│
├─ VRAM ≤ 4 GB ──► YOLOv8s or YOLO11s (FP16)
│
├─ CPU only ─────► YOLOv8n or YOLO11n
│
└─ Batch inference? ──► YOLOv8l with batch=8 (FP16)
                        YOLOv8x with batch=4 (FP16)
```

## References

- [Ultralytics Documentation](https://docs.ultralytics.com)
- [YOLOv8 GitHub](https://github.com/ultralytics/ultralytics)
- [YOLO11 Release Notes](https://github.com/ultralytics/ultralytics/releases)
