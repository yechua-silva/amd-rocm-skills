#!/usr/bin/env python3
"""
Export YOLOv8x model for AMD ROCm or NVIDIA CUDA inference.

Auto-detects the available GPU backend and selects the best export format:
  - AMD ROCm  → ONNX  (universal, optimizable with MIGraphX)
  - NVIDIA    → TensorRT engine (maximum performance)
  - CPU       → TorchScript (universal, zero dependencies)

Usage:
  python export-yolo.py                                         # auto-detect all
  python export-yolo.py --model yolov8s.pt                      # different model
  python export-yolo.py --format onnx                           # force format
  python export-yolo.py --format engine --validate              # TensorRT + validate
  python export-yolo.py --format torchscript --device cpu       # CPU export

Arguments:
  --model   Path or name of the YOLO model (default: yolov8x.pt)
  --format  Export format: auto, onnx, torchscript, engine, openvino (default: auto)
            auto → onnx (AMD), engine (NVIDIA), torchscript (CPU)
  --device  Override device: cuda:0, cpu, etc. (default: auto-detect)
  --validate  Run inference on the exported model to verify correctness
"""

import argparse
import sys
import os


def detect_backend():
    """Detect the available compute backend (ROCm / CUDA / CPU).

    Returns:
        dict with keys: backend (str), device (str), device_name (str),
                        hip_version (str or None), cuda_version (str or None),
                        vram_gb (float)
    """
    import torch

    info = {
        "backend": "cpu",
        "device": "cpu",
        "device_name": "N/A",
        "hip_version": None,
        "cuda_version": None,
        "vram_gb": 0.0,
    }

    if not torch.cuda.is_available():
        return info

    info["device"] = "cuda:0"
    info["device_name"] = torch.cuda.get_device_name(0)

    try:
        info["vram_gb"] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    except Exception:
        info["vram_gb"] = 0.0

    # ROCm detection: torch.version.hip is set only in ROCm builds
    if torch.version.hip is not None:
        info["backend"] = "rocm"
        info["hip_version"] = torch.version.hip
    elif torch.version.cuda is not None:
        info["backend"] = "cuda"
        info["cuda_version"] = torch.version.cuda
    else:
        # Fallback: CUDA is available but version unknown
        info["backend"] = "cuda"
        info["cuda_version"] = "unknown"

    return info


def get_device(override: str | None = None) -> str:
    """Return the device string to use. Auto-detects if not overridden."""
    if override is not None:
        return override
    import torch
    return "cuda:0" if torch.cuda.is_available() else "cpu"


def select_auto_format(backend: str) -> str:
    """Select the best export format for the detected backend.

    - AMD ROCm  → ONNX (universal, MIGraphX-optimizable)
    - NVIDIA    → TensorRT engine (maximum performance)
    - CPU       → TorchScript (no external runtime needed)
    """
    mapping = {
        "rocm": "onnx",
        "cuda": "engine",
        "cpu": "torchscript",
    }
    return mapping.get(backend, "torchscript")


def validate_export(model_path: str, format: str, device: str) -> bool:
    """Run inference on an exported model to verify it works.

    Creates a dummy image (640×640), runs prediction, and checks for output.
    Returns True if validation passes, False otherwise.
    """
    import numpy as np
    from ultralytics import YOLO

    print(f"\n  Validating exported model: {model_path}")

    # Build a dummy RGB image
    dummy = (np.random.rand(640, 640, 3) * 255).astype(np.uint8)

    try:
        exported_model = YOLO(model_path, task="detect")
        results = exported_model.predict(dummy, device=device, verbose=False)

        if results is None or len(results) == 0:
            print("  ✗ Validation failed: no results returned")
            return False

        boxes = results[0].boxes
        detections = len(boxes) if boxes is not None else 0
        print(f"  ✓ Validation passed: {detections} detections on dummy image")
        return True

    except Exception as e:
        print(f"  ✗ Validation failed: {e}")
        return False


def validate_export_path(path: str) -> bool:
    """Check that the exported file exists and has non-zero size."""
    if not os.path.isfile(path):
        return False
    if os.path.getsize(path) == 0:
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Export YOLO model for AMD ROCm / NVIDIA CUDA inference"
    )
    parser.add_argument(
        "--model",
        default="yolov8x.pt",
        help="Model path or name (default: yolov8x.pt)",
    )
    parser.add_argument(
        "--format",
        default="auto",
        choices=["auto", "onnx", "torchscript", "engine", "openvino"],
        help=(
            "Export format. auto → onnx (AMD), engine (NVIDIA), "
            "torchscript (CPU). (default: auto)"
        ),
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Override device (e.g. 'cuda:0', 'cpu'). Auto-detected if omitted.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run post-export validation inference",
    )
    args = parser.parse_args()

    # ── Detect backend ────────────────────────────────────────────────────
    print("=" * 60)
    print("  YOLO Model Export")
    print("=" * 60)

    backend_info = detect_backend()
    device = get_device(args.device)

    print(f"\n  Backend:     {backend_info['backend'].upper()}")
    print(f"  Device:      {device}")
    print(f"  Device name: {backend_info['device_name']}")
    if backend_info["hip_version"]:
        print(f"  HIP version: {backend_info['hip_version']}")
    if backend_info["cuda_version"]:
        print(f"  CUDA version:{backend_info['cuda_version']}")
    if backend_info["vram_gb"] > 0:
        print(f"  VRAM:        {backend_info['vram_gb']:.1f} GB")
    print(f"  Model:       {args.model}")
    print()

    # ── Select format ─────────────────────────────────────────────────────
    export_format = args.format
    if export_format == "auto":
        export_format = select_auto_format(backend_info["backend"])
        print(f"  Auto-selected format: {export_format}")

    # ── Validate format compatibility ─────────────────────────────────────
    if export_format == "engine" and backend_info["backend"] != "cuda":
        print(
            f"  ERROR: TensorRT engine export requires NVIDIA CUDA, "
            f"but {backend_info['backend'].upper()} was detected."
        )
        print(f"  Use --format onnx or --format torchscript instead.")
        sys.exit(1)

    if export_format == "openvino":
        print(
            "  NOTE: OpenVINO export requires Intel hardware and OpenVINO "
            "runtime."
        )
        print("  Falling back to ONNX export.")
        export_format = "onnx"

    # ── Load model ────────────────────────────────────────────────────────
    print("\n  Loading model...")
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
    print()

    # ── Export ────────────────────────────────────────────────────────────
    print(f"  Exporting to {export_format.upper()}...")

    export_kwargs = {
        "format": export_format,
        "device": device,
    }

    # For ONNX exports, enable dynamic batch size
    if export_format == "onnx":
        export_kwargs["dynamic"] = True

    try:
        export_path = model.export(**export_kwargs)
    except Exception as e:
        print(f"  ERROR: Export failed: {e}")
        sys.exit(1)

    print(f"  ✓ Model exported to: {export_path}")

    # ── Verify export file exists ─────────────────────────────────────────
    if not validate_export_path(export_path):
        print(f"  ERROR: Export file '{export_path}' is missing or empty.")
        sys.exit(1)

    print(f"  ✓ Export file verified ({os.path.getsize(export_path) / 1024**2:.1f} MB)")

    # ── Post-export validation ────────────────────────────────────────────
    if args.validate:
        print()
        success = validate_export(export_path, export_format, device)
        if not success:
            print("\n  WARNING: Validation failed. The exported model may be incorrect.")
            sys.exit(1)

    # ── Summary ───────────────────────────────────────────────────────────
    print()
    print("-" * 60)
    print(f"  Export complete")
    print(f"    Model:   {args.model}")
    print(f"    Format:  {export_format}")
    print(f"    Backend: {backend_info['backend'].upper()}")
    print(f"    Output:  {export_path}")
    if args.validate:
        print(f"    Validated: yes")
    print("=" * 60)


if __name__ == "__main__":
    main()
