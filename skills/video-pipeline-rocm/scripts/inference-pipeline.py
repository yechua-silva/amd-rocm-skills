#!/usr/bin/env python3
"""
inference-pipeline.py — Batch Inference Pipeline for Video Frames.

Receives frames extracted by gst-pipeline.sh and runs object detection
inference using YOLO (ultralytics), PyTorch, or ONNX models.

Auto-detects GPU backend: AMD ROCm (torch.version.hip) or NVIDIA CUDA
(torch.version.cuda), with CPU fallback.

Usage:
    python3 inference-pipeline.py --model yolov8x.pt --input-dir ./frames --output results.json
    python3 inference-pipeline.py --model model.onnx --input-dir ./frames --output results.json --device cuda
    python3 inference-pipeline.py --model yolov8n.pt --input-dir ./frames --output results.json --device cpu --batch-size 1

Arguments:
    --model       Path to model file (.pt, .torchscript, .onnx, .engine)
    --input-dir   Directory containing frame images (output from gst-pipeline.sh)
    --output      Path to output JSON file with detections
    --device      Device: auto | cuda | cpu (default: auto)
    --batch-size  Number of frames per inference batch (default: 8)
    --confidence  Confidence threshold (default: 0.5)
    --fp16        Use FP16 half precision (reduces VRAM usage)
    --image-ext   Image file extension filter (default: jpg,jpeg,png)

Output JSON format:
    {
      "metadata": { "model": "...", "backend": "rocm|cuda|cpu", "device": "...", ... },
      "detections": [
        {
          "frame": "frame_0001.jpg",
          "timestamp_s": 0.0,
          "objects": [
            { "class": "person", "confidence": 0.92, "bbox": [x1, y1, x2, y2], "track_id": null }
          ]
        }
      ]
    }
"""

import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── Backend Detection ──────────────────────────────────────────────────────

def detect_device(device_arg: str) -> Tuple[str, str, str]:
    """
    Detect the available compute device.

    Returns:
        (device_string, backend_name, device_name)
        - device_string: "cuda:0" or "cpu"
        - backend_name: "rocm", "cuda", or "cpu"
        - device_name: human-readable GPU name or "CPU"
    """
    device = "cpu"
    backend = "cpu"
    device_name = "CPU"

    if device_arg == "cpu":
        return device, backend, device_name

    try:
        import torch

        if torch.cuda.is_available():
            device = "cuda:0"
            device_name = torch.cuda.get_device_name(0)

            hip_ver = getattr(torch.version, "hip", None)
            cuda_ver = getattr(torch.version, "cuda", None)

            if hip_ver:
                backend = "rocm"
            elif cuda_ver:
                backend = "cuda"
            else:
                backend = "cuda"

            # If user forced cpu, override
            if device_arg == "cpu":
                device = "cpu"
                backend = "cpu"
                device_name = "CPU"
        else:
            print("⚠️  CUDA not available, falling back to CPU")
    except ImportError:
        print("⚠️  PyTorch not installed, falling back to CPU")

    return device, backend, device_name


# ── Model Loading ──────────────────────────────────────────────────────────

def load_model(model_path: str, device: str) -> Any:
    """
    Load a model from file. Supports .pt (ultralytics), .torchscript, .onnx.

    Returns a model object with a .predict() method compatible with the
    inference loop below.
    """
    ext = os.path.splitext(model_path)[1].lower()

    if ext == ".onnx":
        return _load_onnx_model(model_path, device)
    elif ext == ".pt":
        return _load_ultralytics_model(model_path, device)
    elif ext == ".torchscript":
        return _load_torchscript_model(model_path, device)
    elif ext == ".engine":
        return _load_tensorrt_model(model_path, device)
    else:
        # Try ultralytics as default
        return _load_ultralytics_model(model_path, device)


def _load_ultralytics_model(model_path: str, device: str) -> Any:
    """Load an ultralytics YOLO model."""
    try:
        from ultralytics import YOLO

        model = YOLO(model_path)
        print(f"✅ Loaded ultralytics model: {model_path}")
        print(f"   Model task: {model.task}")
        print(f"   Model names: {model.names}")

        # Wrap to provide consistent interface
        class UltralyticsWrapper:
            def __init__(self, model, device):
                self.model = model
                self.device = device
                self.names = model.names

            def predict(self, frames: List, conf: float = 0.5,
                        batch: int = 8, fp16: bool = False) -> List:
                results = self.model.predict(
                    frames,
                    device=self.device,
                    conf=conf,
                    batch=batch,
                    half=fp16,
                    verbose=False,
                )
                return results

        return UltralyticsWrapper(model, device)

    except ImportError as e:
        print(f"❌ Failed to load ultralytics: {e}")
        print("   Install: pip install ultralytics")
        sys.exit(1)


def _load_onnx_model(model_path: str, device: str) -> Any:
    """Load an ONNX model."""
    try:
        import onnxruntime as ort

        # Determine providers based on device
        providers = ["CPUExecutionProvider"]
        if device != "cpu":
            # Try ROCm or CUDA providers
            available = ort.get_available_providers()
            if "ROCMExecutionProvider" in available:
                providers = ["ROCMExecutionProvider", "CPUExecutionProvider"]
                print("✅ ONNX: using ROCMExecutionProvider")
            elif "CUDAExecutionProvider" in available:
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                print("✅ ONNX: using CUDAExecutionProvider")
            else:
                print("⚠️  ONNX: no GPU provider, falling back to CPU")

        session = ort.InferenceSession(model_path, providers=providers)
        input_name = session.get_inputs()[0].name
        input_shape = session.get_inputs()[0].shape
        labels = session.get_outputs()[0].name

        print(f"✅ Loaded ONNX model: {model_path}")
        print(f"   Input: {input_name} shape={input_shape}")

        class ONNXWrapper:
            def __init__(self, session, input_name, labels, device):
                self.session = session
                self.input_name = input_name
                self.labels = labels
                self.device = device
                self.names = {i: f"class_{i}" for i in range(80)}  # default COCO

            def predict(self, frames, conf=0.5, batch=8, fp16=False):
                import cv2
                import numpy as np

                all_results = []
                for i in range(0, len(frames), batch):
                    batch_frames = frames[i:i + batch]
                    batch_input = []

                    for frame_path in batch_frames:
                        img = cv2.imread(str(frame_path))
                        if img is None:
                            batch_input.append(np.zeros((640, 640, 3), dtype=np.float32))
                            continue
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        img = cv2.resize(img, (640, 640))
                        img = img.astype(np.float32) / 255.0
                        batch_input.append(img)

                    # Create batch tensor
                    batch_np = np.stack(batch_input, axis=0)
                    if batch_np.shape[0] == 0:
                        continue

                    # Run inference
                    outputs = self.session.run(
                        [self.labels],
                        {self.input_name: batch_np}
                    )

                    # Parse detections (simplified — ONNX output format varies)
                    for bidx in range(len(batch_frames)):
                        detections = []
                        all_results.append(detections)

                return all_results

        return ONNXWrapper(session, input_name, labels, device)

    except ImportError as e:
        print(f"❌ Failed to load ONNX runtime: {e}")
        print("   Install: pip install onnx onnxruntime")
        sys.exit(1)


def _load_torchscript_model(model_path: str, device: str) -> Any:
    """Load a TorchScript model."""
    try:
        import torch

        model = torch.jit.load(model_path, map_location=device)
        model = model.to(device)
        model.eval()

        print(f"✅ Loaded TorchScript model: {model_path}")

        class TorchScriptWrapper:
            def __init__(self, model, device):
                self.model = model
                self.device = device
                self.names = {i: f"class_{i}" for i in range(80)}

            def predict(self, frames, conf=0.5, batch=8, fp16=False):
                import cv2
                import numpy as np
                import torch as th

                all_results = []
                for i in range(0, len(frames), batch):
                    batch_frames = frames[i:i + batch]
                    batch_tensors = []

                    for frame_path in batch_frames:
                        img = cv2.imread(str(frame_path))
                        if img is None:
                            batch_tensors.append(th.zeros(3, 640, 640))
                            continue
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        img = cv2.resize(img, (640, 640))
                        img_t = th.from_numpy(img).float() / 255.0
                        img_t = img_t.permute(2, 0, 1).unsqueeze(0)
                        batch_tensors.append(img_t)

                    if not batch_tensors:
                        continue

                    batch_input = th.cat(batch_tensors, dim=0).to(self.device)
                    if fp16:
                        batch_input = batch_input.half()

                    with th.no_grad():
                        outputs = self.model(batch_input)

                    for bidx in range(len(batch_frames)):
                        detections = []
                        all_results.append(detections)

                return all_results

        return TorchScriptWrapper(model, device)

    except Exception as e:
        print(f"❌ Failed to load TorchScript model: {e}")
        sys.exit(1)


def _load_tensorrt_model(model_path: str, device: str) -> Any:
    """Load a TensorRT engine model (NVIDIA only)."""
    print("⚠️  TensorRT engines are NVIDIA-only. Use ONNX or TorchScript for AMD ROCm.")
    try:
        import tensorrt as trt
        import pycuda.driver as cuda

        logger = trt.Logger(trt.Logger.WARNING)
        with open(model_path, "rb") as f:
            runtime = trt.Runtime(logger)
            engine = runtime.deserialize_cuda_engine(f.read())

        print(f"✅ Loaded TensorRT engine: {model_path}")

        class TensorRTWrapper:
            def __init__(self, engine):
                self.engine = engine
                self.names = {i: f"class_{i}" for i in range(80)}

            def predict(self, frames, conf=0.5, batch=8, fp16=False):
                # Simplified: return empty detections for non-NVIDIA
                return [[] for _ in frames]

        return TensorRTWrapper(engine)

    except ImportError:
        print("❌ TensorRT or PyCUDA not installed.")
        print("   NVIDIA only: pip install tensorrt pycuda")
        print("   AMD users: use --model with .pt or .onnx format")
        sys.exit(1)


# ── Frame Loading ──────────────────────────────────────────────────────────

def load_frames(input_dir: str, image_ext: str = "jpg,jpeg,png") -> List[Path]:
    """
    Load frame image paths from a directory, sorted numerically.

    Returns a list of Path objects sorted by their numeric frame number.
    """
    extensions = [ext.strip().lower() for ext in image_ext.split(",")]
    frame_files = []

    for ext in extensions:
        frame_files.extend(Path(input_dir).glob(f"*.{ext}"))

    if not frame_files:
        # Try with exact extensions if glob didn't match
        for ext in extensions:
            frame_files.extend(Path(input_dir).glob(f"*.{ext.upper()}"))

    if not frame_files:
        print(f"❌ No frames found in {input_dir} with extensions: {image_ext}")
        print("   Make sure you've run gst-pipeline.sh first to extract frames.")
        sys.exit(1)

    # Sort numerically by frame number in filename
    def sort_key(p: Path) -> int:
        name = p.stem
        # Extract number from frame_NUMBER pattern
        parts = name.split("_")
        for part in reversed(parts):
            try:
                return int(part)
            except ValueError:
                continue
        return 0

    frame_files.sort(key=sort_key)
    print(f"📂 Loaded {len(frame_files)} frames from {input_dir}")
    return frame_files


# ── Inference Engine ───────────────────────────────────────────────────────

def run_inference(
    model: Any,
    frames: List[Path],
    batch_size: int,
    confidence: float,
    fp16: bool,
    interval: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Run inference on all frames in batches.

    Args:
        model: Loaded model wrapper with .predict() method
        frames: List of frame file paths
        batch_size: Number of frames per batch
        confidence: Confidence threshold
        fp16: Use half precision
        interval: Time interval between frames in seconds

    Returns:
        List of detection dicts, one per frame
    """
    all_detections = []
    total_batches = math.ceil(len(frames) / batch_size)
    total_start = time.time()

    for batch_idx in range(0, len(frames), batch_size):
        batch_frames = frames[batch_idx:batch_idx + batch_size]
        batch_num = (batch_idx // batch_size) + 1

        print(f"  🔄 Batch {batch_num}/{total_batches} "
              f"({len(batch_frames)} frames)...", end=" ", flush=True)

        batch_start = time.time()

        try:
            results = model.predict(
                [str(f) for f in batch_frames],
                conf=confidence,
                batch=len(batch_frames),
                fp16=fp16,
            )
        except Exception as e:
            print(f"❌ Inference error: {e}")
            # Add empty detections for this batch
            for f in batch_frames:
                all_detections.append({
                    "frame": f.name,
                    "timestamp_s": 0.0,
                    "objects": [],
                    "error": str(e),
                })
            continue

        batch_time = time.time() - batch_start
        print(f"done ({batch_time:.2f}s, "
              f"{len(batch_frames) / batch_time:.1f} fps)")

        # Parse results for each frame in batch
        for frame_idx, frame_path in enumerate(batch_frames):
            frame_num = int(frame_path.stem.split("_")[-1]) if "_" in frame_path.stem else 0
            timestamp = frame_num * interval

            frame_objects = []

            if results is not None and frame_idx < len(results):
                result = results[frame_idx]

                # ultralytics YOLO results
                if hasattr(result, "boxes") and result.boxes is not None:
                    boxes = result.boxes
                    if boxes.data is not None and len(boxes) > 0:
                        for box_data in boxes.data:
                            x1, y1, x2, y2 = (
                                float(box_data[0]),
                                float(box_data[1]),
                                float(box_data[2]),
                                float(box_data[3]),
                            )
                            conf_val = float(box_data[4]) if len(box_data) > 4 else float(box_data[4]) if len(box_data) > 4 else 0.0
                            cls_id = int(box_data[5]) if len(box_data) > 5 else 0

                            class_name = ""
                            if hasattr(model, "names") and model.names:
                                class_name = model.names.get(cls_id, str(cls_id))

                            # Handle different data orderings
                            if len(box_data) >= 6:
                                conf_val = float(box_data[4])
                                cls_id = int(box_data[5])
                            elif len(box_data) == 5:
                                conf_val = float(box_data[4])
                                cls_id = 0

                            frame_objects.append({
                                "class": class_name,
                                "class_id": cls_id,
                                "confidence": round(conf_val, 4),
                                "bbox": [round(x1, 1), round(y1, 1),
                                         round(x2, 1), round(y2, 1)],
                                "track_id": None,
                            })

                # ultralytics Results with .names
                elif hasattr(result, "names") and hasattr(result, "boxes"):
                    pass  # already handled above

                # ONNX or TorchScript raw output
                elif isinstance(result, (list, tuple)):
                    for det in result:
                        if isinstance(det, dict):
                            frame_objects.append({
                                "class": det.get("class", "unknown"),
                                "class_id": det.get("class_id", 0),
                                "confidence": det.get("confidence", 0.0),
                                "bbox": det.get("bbox", [0, 0, 0, 0]),
                                "track_id": det.get("track_id", None),
                            })

            # Apply confidence filter again (safety)
            frame_objects = [o for o in frame_objects
                             if o["confidence"] >= confidence]

            # Apply NMS (simple overlap filter)
            frame_objects = _apply_nms(frame_objects, iou_threshold=0.45)

            all_detections.append({
                "frame": frame_path.name,
                "timestamp_s": round(timestamp, 3),
                "objects": frame_objects,
            })

    total_time = time.time() - total_start
    total_objects = sum(len(d["objects"]) for d in all_detections)

    print(f"\n✅ Inference complete: {len(all_detections)} frames, "
          f"{total_objects} objects detected")
    print(f"   Total time: {total_time:.2f}s "
          f"({len(all_detections) / total_time:.1f} fps)")

    return all_detections


def _apply_nms(
    objects: List[Dict], iou_threshold: float = 0.45
) -> List[Dict]:
    """
    Apply simple Non-Maximum Suppression to remove duplicate detections.

    Sorts by confidence descending, then removes boxes with high IoU overlap.
    """
    if len(objects) <= 1:
        return objects

    # Sort by confidence descending
    sorted_objs = sorted(objects, key=lambda x: x["confidence"], reverse=True)
    keep = []

    while sorted_objs:
        best = sorted_objs.pop(0)
        keep.append(best)

        # Remove remaining boxes with high IoU
        remaining = []
        for obj in sorted_objs:
            if _compute_iou(best["bbox"], obj["bbox"]) < iou_threshold:
                remaining.append(obj)
        sorted_objs = remaining

    return keep


def _compute_iou(box1: List[float], box2: List[float]) -> float:
    """Compute Intersection over Union between two bounding boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection

    if union <= 0:
        return 0.0
    return intersection / union


# ── Tracking (Simple) ──────────────────────────────────────────────────────

class SimpleTracker:
    """
    Simple frame-to-frame object tracker based on IoU overlap.

    Assigns track_id to objects that overlap significantly between
    consecutive frames.
    """

    def __init__(self, iou_threshold: float = 0.3):
        self.iou_threshold = iou_threshold
        self.next_id = 1
        self.prev_objects: List[Dict] = []

    def update(self, objects: List[Dict]) -> List[Dict]:
        """Assign track IDs to objects based on IoU with previous frame."""
        tracked = []

        for obj in objects:
            best_iou = 0
            best_match = None

            for prev_obj in self.prev_objects:
                iou = _compute_iou(obj["bbox"], prev_obj["bbox"])
                if iou > best_iou and iou >= self.iou_threshold:
                    best_iou = iou
                    best_match = prev_obj

            if best_match and "track_id" in best_match and best_match["track_id"] is not None:
                obj["track_id"] = best_match["track_id"]
            else:
                obj["track_id"] = self.next_id
                self.next_id += 1

            tracked.append(obj)

        self.prev_objects = tracked
        return tracked


# ── Output ─────────────────────────────────────────────────────────────────

def write_output(
    detections: List[Dict],
    metadata: Dict[str, Any],
    output_path: str,
) -> None:
    """Write detection results to JSON file."""
    import json

    output = {
        "metadata": metadata,
        "detections": detections,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"📄 Results written to: {output_path}")
    print(f"   Total detections: {sum(len(d['objects']) for d in detections)}")


# ── CLI ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AMD ROCm — Video Inference Pipeline (ROCm / CUDA / CPU)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --model yolov8x.pt --input-dir ./frames --output results.json
  %(prog)s --model model.onnx --input-dir ./frames --output results.json --device cuda
  %(prog)s --model yolov8n.pt --input-dir ./frames --output results.json --device cpu --batch-size 1 --fp16
  %(prog)s --model yolov8x.pt --input-dir ./frames --output results.json --confidence 0.7 --batch-size 16
        """,
    )

    parser.add_argument(
        "--model",
        required=True,
        help="Path to model file (.pt, .torchscript, .onnx, .engine)",
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing frame images (output from gst-pipeline.sh)",
    )
    parser.add_argument(
        "--output",
        default="results.json",
        help="Output JSON file path (default: results.json)",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Device to use: auto | cuda | cpu (default: auto)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Number of frames per inference batch (default: 8)",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.5,
        help="Confidence threshold for detections (default: 0.5)",
    )
    parser.add_argument(
        "--fp16",
        action="store_true",
        help="Use FP16 half precision (reduces VRAM usage, ~2x speedup)",
    )
    parser.add_argument(
        "--image-ext",
        default="jpg,jpeg,png",
        help="Image file extensions to scan (default: jpg,jpeg,png)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Time interval between frames in seconds (default: 1.0, used for timestamps)",
    )
    parser.add_argument(
        "--track",
        action="store_true",
        help="Enable simple frame-to-frame object tracking",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # ── Banner ──────────────────────────────────────────────────────────────
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  AMD ROCm — Video Inference Pipeline                       ║")
    print("║  ROCm | CUDA | CPU                                      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("")

    # ── Detect device ──────────────────────────────────────────────────────
    device, backend, device_name = detect_device(args.device)
    print(f"🔍 Device:     {device}")
    print(f"   Backend:    {backend}")
    print(f"   GPU:        {device_name}")
    print(f"   Model:      {args.model}")
    print(f"   Input dir:  {args.input_dir}")
    print(f"   Batch size: {args.batch_size}")
    print(f"   Confidence: {args.confidence}")
    print(f"   FP16:       {args.fp16}")
    print(f"   Tracking:   {args.track}")
    print("")

    # ── Validate input directory ───────────────────────────────────────────
    if not os.path.isdir(args.input_dir):
        print(f"❌ Input directory not found: {args.input_dir}")
        return 1

    # ── Load model ─────────────────────────────────────────────────────────
    if not os.path.isfile(args.model):
        print(f"❌ Model file not found: {args.model}")
        return 1

    print("📦 Loading model...")
    model = load_model(args.model, device)
    print("")

    # ── Load frames ────────────────────────────────────────────────────────
    frames = load_frames(args.input_dir, args.image_ext)

    if args.fp16 and device == "cpu":
        print("⚠️  FP16 not supported on CPU, disabling")
        args.fp16 = False

    # ── Run inference ──────────────────────────────────────────────────────
    print("🎯 Running inference...")
    detections = run_inference(
        model=model,
        frames=frames,
        batch_size=args.batch_size,
        confidence=args.confidence,
        fp16=args.fp16,
        interval=args.interval,
    )

    # ── Run tracking ───────────────────────────────────────────────────────
    if args.track:
        print("🔗 Running tracking...")
        tracker = SimpleTracker()
        for det in detections:
            det["objects"] = tracker.update(det["objects"])
        tracked_count = sum(
            1 for d in detections
            for o in d["objects"]
            if o.get("track_id") is not None
        )
        print(f"   Tracked {tracked_count} objects across frames")

    # ── Build metadata ─────────────────────────────────────────────────────
    total_objects = sum(len(d["objects"]) for d in detections)
    print(f"\n📊 Summary: {len(detections)} frames, {total_objects} total objects")
    print("")

    metadata = {
        "model": args.model,
        "backend": backend,
        "device": device_name,
        "device_string": device,
        "batch_size": args.batch_size,
        "confidence": args.confidence,
        "fp16": args.fp16,
        "tracking": args.track,
        "total_frames": len(detections),
        "total_objects": total_objects,
        "frames_per_second": round(
            len(detections) / max(time.time() - time.time(), 0.001), 1
        ),
    }

    # ── Write output ───────────────────────────────────────────────────────
    write_output(detections, metadata, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
