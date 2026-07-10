#!/usr/bin/env python3
"""
Fine-tuning de YOLOv8x para detección de Elementos de Protección Personal (EPP).

Entrena un modelo YOLOv8x para detectar casco, chaleco reflectante, guantes,
lentes de seguridad y botas de seguridad en entornos mineros e industriales.

Incluye:
  - Data augmentation específica para minería: polvo, baja luz, lluvia
  - Detección automática de backend GPU (ROCm / CUDA / CPU)
  - Evaluación: mAP@50, mAP@50:95, confusion matrix
  - Export a ONNX, TorchScript y TensorRT post-entrenamiento
  - ROCm acceleration (device="cuda:0" funciona en ambos backends)

Uso:
  # Entrenamiento completo
  python3 train-ppe.py --data dataset.yaml --model yolov8x.pt --epochs 100

  # Reanudar entrenamiento
  python3 train-ppe.py --data dataset.yaml --model runs/ppe/exp/weights/last.pt

  # Evaluar modelo entrenado
  python3 train-ppe.py --data dataset.yaml --model runs/ppe/exp/weights/best.pt --evaluate-only

  # Exportar modelo entrenado
  python3 train-ppe.py --model runs/ppe/exp/weights/best.pt --export onnx

Requisitos del dataset (formato YOLO):
  dataset/
  ├── dataset.yaml
  ├── images/
  │   ├── train/
  │   └── val/
  └── labels/
      ├── train/
      └── val/
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("train-ppe")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PPE_CLASSES: List[str] = [
    "hardhat",          # 0: Casco de seguridad
    "safety_vest",      # 1: Chaleco reflectante
    "gloves",           # 2: Guantes de seguridad
    "safety_glasses",   # 3: Lentes de seguridad
    "safety_boots",     # 4: Botas de seguridad
    "person",           # 5: Persona
]

# Data augmentation específica para minería
# Estos parámetros simulan condiciones reales de faena
MINING_AUGMENTATION: Dict[str, float] = {
    "hsv_h": 0.015,   # Variación de tono (luz natural cambiante)
    "hsv_s": 0.7,     # Variación de saturación (polvo, suciedad)
    "hsv_v": 0.4,     # Variación de brillo (baja luz, sombras)
    "degrees": 10.0,  # Rotación (cabezas inclinadas, movimiento)
    "translate": 0.1, # Traslación (movimiento de cámara)
    "scale": 0.5,     # Escala (distancias variables)
    "shear": 2.0,     # Shear (perspectiva)
    "perspective": 0.0,
    "flipud": 0.5,    # Flip vertical (visión desde altura/drones)
    "fliplr": 0.5,    # Flip horizontal
    "mosaic": 1.0,    # Mosaic (escenas complejas mineras)
    "mixup": 0.1,     # Mixup (datos sintéticos)
    "copy_paste": 0.1, # Copy-paste (objetos EPP en contextos variados)
    "auto_augment": "randaugment",
    "erasing": 0.4,   # Random erasing (oclusión parcial)
    "crop_fraction": 1.0,
}

# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

def detect_backend() -> Tuple[str, str]:
    """
    Detecta el backend GPU disponible para entrenamiento.

    Returns:
        (backend, device)
        backend: "rocm", "cuda", or "cpu"
        device: "cuda:0" or "cpu"
    """
    if not torch.cuda.is_available():
        log.warning("CUDA not available. Training will be on CPU (very slow!).")
        return "cpu", "cpu"

    device = "cuda:0"
    if torch.version.hip is not None:
        backend = "rocm"
        log.info("AMD ROCm backend detected: %s (HIP %s)",
                 torch.cuda.get_device_name(0), torch.version.hip)
    elif torch.version.cuda is not None:
        backend = "cuda"
        log.info("NVIDIA CUDA backend detected: %s (CUDA %s)",
                 torch.cuda.get_device_name(0), torch.version.cuda)
    else:
        backend = "cuda"
        log.info("CUDA backend detected: %s", torch.cuda.get_device_name(0))

    # Mostrar GPUs disponibles
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        log.info("  GPU %d: %s (%d cores, %.1f GB VRAM)",
                 i, props.name, props.multi_processor_count,
                 props.total_memory / 1e9)

    return backend, device


# ---------------------------------------------------------------------------
# Dataset validation
# ---------------------------------------------------------------------------

def validate_dataset(data_path: str) -> bool:
    """
    Valida la estructura del dataset YOLO.

    Args:
        data_path: Ruta al archivo dataset.yaml

    Returns:
        True si el dataset es válido, False en caso contrario.
    """
    try:
        with open(data_path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        log.error("Cannot read dataset.yaml: %s", e)
        return False

    required_fields = ["path", "train", "val", "nc", "names"]
    for field in required_fields:
        if field not in data:
            log.error("Missing required field '%s' in dataset.yaml", field)
            return False

    # Verificar número de clases
    if data["nc"] != 6:
        log.warning("Expected 6 classes (PPE + person), got %d. Verify dataset.yaml.", data["nc"])

    # Verificar nombres de clases
    if "names" in data and len(data["names"]) != data["nc"]:
        log.warning("Mismatch between nc=%d and len(names)=%d", data["nc"], len(data["names"]))

    # Verificar que existan directorios de imágenes
    base = Path(data["path"])
    for split in ["train", "val"]:
        img_dir = base / data[split]
        if not img_dir.exists():
            log.warning("Image directory not found: %s", img_dir)
            # Intentar ruta relativa
            img_dir = Path(data[split])
            if not img_dir.exists():
                log.error("Image directory not found: %s", img_dir)
                return False

        # Contar imágenes
        img_count = len(list(img_dir.glob("*.jpg")) +
                        list(img_dir.glob("*.jpeg")) +
                        list(img_dir.glob("*.png")))
        if img_count == 0:
            log.error("No images found in %s", img_dir)
            return False
        log.info("  %s: %d images", split, img_count)

        # Verificar labels correspondientes
        label_dir = base / "labels" / split
        if not label_dir.exists():
            label_dir = Path("labels") / split
        label_count = len(list(label_dir.glob("*.txt")))
        if label_count == 0:
            log.error("No labels found in %s", label_dir)
            return False
        log.info("  %s labels: %d", split, label_count)

    log.info("Dataset validation passed: %s", data_path)
    return True


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(args: argparse.Namespace):
    """
    Ejecuta fine-tuning de YOLOv8x para PPE detection.

    Configura:
      - Backend GPU automático
      - Data augmentation para minería
      - ROCm/CUDA optimizations
      - Evaluación periódica
    """
    from ultralytics import YOLO

    # Detectar backend
    backend, device = detect_backend()
    if args.device != "auto":
        device = args.device

    log.info("Starting PPE training...")
    log.info("  Model:      %s", args.model)
    log.info("  Data:       %s", args.data)
    log.info("  Epochs:     %d", args.epochs)
    log.info("  Img Size:   %d", args.imgsz)
    log.info("  Batch:      %d", args.batch)
    log.info("  Device:     %s", device)
    log.info("  Workers:    %d", args.workers)
    log.info("  Patience:   %d", args.patience)

    # Cargar modelo
    model = YOLO(args.model)

    # Preparar augmentation mining
    augmentation = MINING_AUGMENTATION.copy()
    if args.augment_light:
        augmentation["hsv_v"] = 0.6  # Más variación de luz
    if args.augment_dust:
        augmentation["hsv_s"] = 0.8  # Más variación de saturación (polvo)
    if args.augment_occlusion:
        augmentation["erasing"] = 0.5  # Más oclusión

    # Iniciar entrenamiento
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        workers=args.workers,
        patience=args.patience,
        project=args.project,
        name=args.name,
        exist_ok=True,
        pretrained=True,
        optimizer=args.optimizer,
        lr0=args.lr0,
        lrf=args.lrf,
        momentum=args.momentum,
        weight_decay=args.weight_decay,
        warmup_epochs=args.warmup_epochs,
        warmup_momentum=args.warmup_momentum,
        warmup_bias_lr=args.warmup_bias_lr,
        box=args.loss_box,
        cls=args.loss_cls,
        dfl=args.loss_dfl,
        # Data augmentation para minería
        hsv_h=augmentation["hsv_h"],
        hsv_s=augmentation["hsv_s"],
        hsv_v=augmentation["hsv_v"],
        degrees=augmentation["degrees"],
        translate=augmentation["translate"],
        scale=augmentation["scale"],
        shear=augmentation["shear"],
        perspective=augmentation["perspective"],
        flipud=augmentation["flipud"],
        fliplr=augmentation["fliplr"],
        mosaic=augmentation["mosaic"],
        mixup=augmentation["mixup"],
        copy_paste=augmentation["copy_paste"],
        auto_augment=augmentation["auto_augment"],
        erasing=augmentation["erasing"],
        crop_fraction=augmentation["crop_fraction"],
        # Validación
        val=True,
        plots=True,
        save=True,
        save_period=args.save_period,
        verbose=args.verbose,
    )

    log.info("Training complete!")
    log.info("Best model saved to: %s", str(Path(args.project) / args.name / "weights" / "best.pt"))

    # Mostrar resultados
    if hasattr(results, "results_dict"):
        metrics = results.results_dict
        log.info("Results:")
        for k, v in metrics.items():
            log.info("  %s: %s", k, v)

    return results


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(args: argparse.Namespace):
    """
    Evalúa un modelo entrenado en el dataset de validación.

    Reporta:
      - mAP@50 por clase
      - mAP@50:95 por clase
      - Matriz de confusión
      - F1-score por clase
    """
    from ultralytics import YOLO

    backend, device = detect_backend()
    if args.device != "auto":
        device = args.device

    log.info("Evaluating model: %s", args.model)
    log.info("  Data:   %s", args.data)
    log.info("  Device: %s", device)

    model = YOLO(args.model)

    results = model.val(
        data=args.data,
        device=device,
        imgsz=args.imgsz,
        batch=args.batch,
        conf=args.confidence,
        iou=args.iou,
        plots=True,
        save_json=True,
        save_hybrid=True,
        verbose=True,
    )

    # Mostrar resultados por clase
    if hasattr(results, "class_result") and results.class_result is not None:
        print("\n" + "=" * 70)
        print("  PPE Evaluation Results")
        print("=" * 70)
        print(f"  {'Class':<20} {'Images':>8} {'Instances':>10} {'mAP@50':>10} {'mAP@50:95':>10}")
        print("  " + "-" * 58)

        for i, cls_name in enumerate(PPE_CLASSES):
            if i < len(results.class_result):
                cr = results.class_result[i]
                print(f"  {cls_name:<20} {int(cr[0]):>8} {int(cr[1]):>10} {cr[2]:>10.3f} {cr[3]:>10.3f}")

        print("  " + "-" * 58)
        if hasattr(results, "box"):
            print(f"  {'all':<20} {'':>8} {'':>10} {results.box.map50:>10.3f} {results.box.map:>10.3f}")
        print("=" * 70)

    # Guardar métricas
    metrics_path = Path(args.project or "runs") / args.name / "metrics.json"
    if hasattr(results, "box"):
        metrics = {
            "mAP50": results.box.map50,
            "mAP50-95": results.box.map,
            "fitness": results.fitness if hasattr(results, "fitness") else 0,
            "precision": results.box.p if hasattr(results.box, "p") else 0,
            "recall": results.box.r if hasattr(results.box, "r") else 0,
        }
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
        log.info("Metrics saved to: %s", metrics_path)

    return results


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_model(args: argparse.Namespace):
    """
    Exporta modelo entrenado a diferentes formatos.

    Formatos soportados:
      - ONNX: universal, funciona en ROCm y CUDA
      - TorchScript: universal, óptimo para CPU
      - TensorRT Engine: NVIDIA solamente (falla en ROCm)
    """
    from ultralytics import YOLO

    backend, device = detect_backend()
    if args.device != "auto":
        device = args.device

    format_map = {
        "onnx": "onnx",
        "torchscript": "torchscript",
        "engine": "engine",  # TensorRT — NVIDIA only
        "openvino": "openvino",  # Intel only
        "coreml": "coreml",  # Apple only
    }

    export_format = format_map.get(args.export)
    if export_format is None:
        log.error("Unsupported export format: %s. Supported: %s",
                   args.export, ", ".join(format_map.keys()))
        sys.exit(1)

    # Verificar compatibilidad
    if export_format == "engine" and backend != "cuda":
        log.error("TensorRT engine export is NVIDIA-only. Use 'onnx' for AMD ROCm.")
        sys.exit(1)

    if export_format == "openvino" and backend == "rocm":
        log.warning("OpenVINO export on AMD may have limited GPU support. Use 'onnx' instead.")

    log.info("Exporting model %s to %s format...", args.model, export_format)

    model = YOLO(args.model)

    # Exportar
    export_path = model.export(
        format=export_format,
        device=device,
        imgsz=args.imgsz,
        half=args.half,
        simplify=args.simplify,
        opset=args.opset,
        dynamic=args.dynamic,
    )

    log.info("Model exported to: %s", export_path)

    # Validar exportación
    if args.validate and export_format in ("onnx", "torchscript"):
        log.info("Validating exported model...")
        try:
            if export_format == "onnx":
                import onnx
                onnx_model = onnx.load(export_path)
                onnx.checker.check_model(onnx_model)
                log.info("ONNX validation passed!")
            elif export_format == "torchscript":
                exported = torch.jit.load(export_path)
                dummy = torch.randn(1, 3, args.imgsz, args.imgsz)
                if device != "cpu":
                    dummy = dummy.to(device)
                    exported = exported.to(device)
                output = exported(dummy)
                log.info("TorchScript validation passed! Output shape: %s", output.shape)
        except Exception as e:
            log.error("Export validation failed: %s", e)
            sys.exit(1)

    return export_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tuning de YOLOv8x para detección de EPP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Modo
    parser.add_argument("--evaluate-only", action="store_true",
                        help="Evaluate model only (no training)")
    parser.add_argument("--export", choices=["onnx", "torchscript", "engine", "openvino", "coreml"],
                        help="Export trained model to format")

    # Dataset
    parser.add_argument("--data", "-d",
                        help="Path to dataset.yaml")
    parser.add_argument("--model", "-m", default="yolov8x.pt",
                        help="Model path (default: yolov8x.pt)")

    # Training
    parser.add_argument("--epochs", type=int, default=100,
                        help="Number of epochs (default: 100)")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Image size (default: 640)")
    parser.add_argument("--batch", "-b", type=int, default=16,
                        help="Batch size (default: 16)")
    parser.add_argument("--device", default="auto",
                        help="Device: auto, cuda:0, cpu (default: auto)")
    parser.add_argument("--workers", type=int, default=8,
                        help="Data loading workers (default: 8)")
    parser.add_argument("--patience", type=int, default=50,
                        help="Early stopping patience (default: 50)")

    # Optimizer
    parser.add_argument("--optimizer", default="AdamW",
                        choices=["SGD", "Adam", "AdamW"],
                        help="Optimizer (default: AdamW)")
    parser.add_argument("--lr0", type=float, default=0.001,
                        help="Initial learning rate (default: 0.001)")
    parser.add_argument("--lrf", type=float, default=0.01,
                        help="Final learning rate fraction (default: 0.01)")
    parser.add_argument("--momentum", type=float, default=0.937,
                        help="SGD momentum (default: 0.937)")
    parser.add_argument("--weight-decay", type=float, default=0.0005,
                        help="Weight decay (default: 0.0005)")

    # Warmup
    parser.add_argument("--warmup-epochs", type=float, default=3.0,
                        help="Warmup epochs (default: 3.0)")
    parser.add_argument("--warmup-momentum", type=float, default=0.8,
                        help="Warmup momentum (default: 0.8)")
    parser.add_argument("--warmup-bias-lr", type=float, default=0.1,
                        help="Warmup bias LR (default: 0.1)")

    # Loss weights
    parser.add_argument("--loss-box", type=float, default=7.5,
                        help="Box loss weight (default: 7.5)")
    parser.add_argument("--loss-cls", type=float, default=0.5,
                        help="Class loss weight (default: 0.5)")
    parser.add_argument("--loss-dfl", type=float, default=1.5,
                        help="DFL loss weight (default: 1.5)")

    # Augmentation
    parser.add_argument("--augment-light", action="store_true",
                        help="Extra light variation augmentation (mining)")
    parser.add_argument("--augment-dust", action="store_true",
                        help="Extra dust/saturation augmentation (mining)")
    parser.add_argument("--augment-occlusion", action="store_true",
                        help="Extra occlusion augmentation (mining)")

    # Project
    parser.add_argument("--project", default="runs/ppe",
                        help="Project directory (default: runs/ppe)")
    parser.add_argument("--name", default=None,
                        help="Experiment name (default: auto)")
    parser.add_argument("--save-period", type=int, default=-1,
                        help="Save checkpoint every N epochs (-1 = only best/last)")

    # Evaluation
    parser.add_argument("--confidence", "-c", type=float, default=0.001,
                        help="Confidence threshold for evaluation (default: 0.001)")
    parser.add_argument("--iou", type=float, default=0.6,
                        help="IoU threshold for evaluation (default: 0.6)")

    # Export
    parser.add_argument("--half", action="store_true",
                        help="Export with FP16 quantization")
    parser.add_argument("--simplify", action="store_true", default=True,
                        help="Simplify ONNX model (default: True)")
    parser.add_argument("--opset", type=int, default=17,
                        help="ONNX opset version (default: 17)")
    parser.add_argument("--dynamic", action="store_true",
                        help="Dynamic batch size for ONNX export")
    parser.add_argument("--validate", action="store_true",
                        help="Validate exported model")

    # General
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")

    return parser.parse_args()


def main():
    args = parse_args()

    # Mostrar configuración del dataset
    if args.data:
        log.info("Dataset: %s", args.data)
        if not validate_dataset(args.data):
            log.error("Dataset validation failed. Aborting.")
            sys.exit(1)

    # Modo export
    if args.export:
        export_model(args)
        return

    # Modo evaluación
    if args.evaluate_only:
        if not args.data:
            log.error("--data required for evaluation")
            sys.exit(1)
        evaluate(args)
        return

    # Modo entrenamiento
    if not args.data:
        log.error("--data required for training")
        sys.exit(1)

    train(args)


if __name__ == "__main__":
    main()
