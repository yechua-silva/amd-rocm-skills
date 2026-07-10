---
name: ppe-detection-pipeline
description: >
  Pipeline de detección de EPP en video para minería e industria. Usa YOLOv8x
  sobre ROCm/CUDA para detectar casco, chaleco, guantes, lentes y botas en
  tiempo real sobre RTSP, archivos o USB. Tracking de personas con asignación de
  EPP, alertas vía webhook/MQTT/log, video anotado y JSON. Multi-cámara,
  multi-GPU, fine-tuning con data augmentation para minería. AMD ROCm y
  NVIDIA CUDA. Use this skill when building PPE detection systems for mining,
  detecting hardhats/safety vests in video, or setting up industrial safety
  compliance monitoring. / Útil al construir sistemas de detección de EPP para
  minería, detectar cascos/chalecos en video, o configurar monitoreo de
  cumplimiento. Keywords: ppe detection, epp, deteccion elementos proteccion,
  casco seguridad, hardhat detection, chaleco reflectante, safety gear, mining
  safety, industrial surveillance, yolo, rocm, cuda, tracking, video analytics,
  seguridad minera, mineria, industrial safety.
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: "yechua-silva"
  tags:
    - amd
    - rocm
    - ppe
    - epp
    - yolo
    - detection
    - safety
    - mining
    - mining-safety
    - nvidia
    - cuda
    - tracking
    - surveillance
    - industrial
    - hardhat
    - safety-vest
    - ultralytics
    - video-analytics
    - pytorch
compatibility: >
  Compatible with Claude Code, OpenCode, Codex, Cursor, Cline, Roo Code,
  Windsurf, Gemini CLI, and Kiro CLI. Requires Linux with AMD ROCm or
  NVIDIA CUDA GPU (CPU fallback supported).
---

# PPE Detection Pipeline — ROCm / CUDA / CPU

Pipeline completo de detección de **Elementos de Protección Personal (EPP)** en video para minería e industria pesada. Detecta casco, chaleco reflectante, guantes, lentes de seguridad y botas de seguridad en tiempo real usando **YOLOv8x** sobre **AMD ROCm** o **NVIDIA CUDA**, con tracking de personas, alertas configurables y exportación a múltiples formatos.

Esta skill combina y extiende [`yolo-rocm-deploy`](../yolo-rocm-deploy/SKILL.md) y [`video-pipeline-rocm`](../video-pipeline-rocm/SKILL.md) para construir un sistema completo de seguridad industrial.

## Purpose

- **Detectar** 5 clases de EPP + personas en video en tiempo real: hardhat (casco), safety_vest (chaleco reflectante), gloves (guantes), safety_glasses (lentes de seguridad), safety_boots (botas de seguridad), person (persona)
- **Trackear** personas individualmente a través del video, asignando un ID único por persona
- **Verificar** por persona qué elementos de EPP tiene y cuáles le faltan
- **Alertar** cuando una persona ingresa a una zona sin el equipo completo, vía webhook HTTP, MQTT, log local o archivo CSV
- **Procesar** múltiples cámaras simultáneamente con threads independientes
- **Exportar** video anotado con bounding boxes coloreados (verde = EPP completo, rojo = falta equipo, amarillo = parcial) y JSON estructurado por frame
- **Dashboard** de cumplimiento: estadísticas por cámara, por turno, por zona
- **Fine-tune** YOLOv8x con data augmentation específica para minería (polvo, baja luz, lluvia, lentes sucias)
- Funcionar en **cualquier backend GPU**: AMD ROCm (MI300X, MI250, RX 7900), NVIDIA CUDA (A100, H100, RTX 4090), y CPU fallback

## When to Use / Cuándo Usar

La skill se activa con frases como:

- "PPE detection pipeline for mining / pipeline de detección de EPP para minería"
- "Detectar casco y chaleco en video / detect hardhat and safety vest in video"
- "Safety gear detection on RTSP stream / detección de elementos de protección en stream RTSP"
- "Detección de elementos de protección personal en tiempo real"
- "Hardhat detection for industrial safety / detección de cascos de seguridad industrial"
- "Alert when worker is missing PPE / alertar cuando trabajador no tiene EPP"
- "Mining safety video analytics / analítica de video para seguridad minera"
- "Track people and check safety equipment / trackear personas y verificar equipo de seguridad"
- "Fine-tune YOLO for PPE detection / fine-tune YOLO para detección de EPP"
- "Multi-camera PPE monitoring / monitoreo de EPP multi-cámara"
- "Industrial surveillance with PPE compliance / vigilancia industrial con cumplimiento de EPP"
- Keywords: ppe detection, epp, deteccion elementos proteccion, casco seguridad, hardhat, chaleco reflectante, safety vest, safety glasses, gloves, safety boots, mining safety, industrial surveillance, yolo, rocm, cuda, tracking, video analytics, seguridad minera, mineria chilena, ds 132, nch 461

## Prerequisites

- **Python 3.10+** con PyTorch para ROCm o CUDA
- **GPU con 8 GB+ VRAM** para YOLOv8x (16 GB+ recomendado para multi-cámara)
- **ultralytics** instalado (`pip install ultralytics`)
- **OpenCV** con soporte completo (`pip install opencv-python-headless`)
- **Cámara o video**: archivo MP4, stream RTSP, o cámara USB (v4l2)
- **Opcional**: `paho-mqtt` para alertas MQTT, `requests` para webhooks
- **Opcional**: `rocm-smi` (AMD) o `nvidia-smi` (NVIDIA) para monitoreo GPU

### Dependencias

```bash
pip install ultralytics opencv-python-headless numpy pillow requests
pip install paho-mqtt  # Para alertas MQTT
pip install matplotlib # Para dashboard simple
```

## Quickstart

### 1. Detect GPU Backend

```bash
python3 -c "
import torch
backend = 'rocm' if torch.version.hip else ('cuda' if torch.version.cuda else 'cpu')
print(f'Backend: {backend}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')
print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB' if torch.cuda.is_available() else 'N/A')
"
```

### 2. Run PPE Detection Pipeline

```bash
# Detección en archivo de video con output a JSON y video anotado
python3 scripts/ppe-pipeline.py \
  --source video.mp4 \
  --model yolov8x.pt \
  --output ./output \
  --confidence 0.5 \
  --track \
  --alert-log

# Detección en stream RTSP con alertas webhook
python3 scripts/ppe-pipeline.py \
  --source "rtsp://user:pass@192.168.1.100:554/stream1" \
  --model models/ppe-yolov8x.pt \
  --output ./output \
  --confidence 0.6 \
  --track \
  --alert-webhook "https://hooks.example.com/ppe-alerts"
```

### 3. Fine-tune for Mining Environment

```bash
python3 scripts/train-ppe.py \
  --data dataset.yaml \
  --model yolov8x.pt \
  --epochs 100 \
  --imgsz 640 \
  --batch 16 \
  --device cuda:0
```

## Step-by-Step Guide

### 1. Detectar Backend GPU

El pipeline auto-detecta el backend disponible siguiendo este orden: ROCm → CUDA → CPU.

```bash
python3 scripts/ppe-pipeline.py --detect
```

El script reporta:

| Atributo | AMD ROCm | NVIDIA CUDA | CPU |
|----------|----------|-------------|-----|
| `backend` | `rocm` | `cuda` | `cpu` |
| `device` | `cuda:0` | `cuda:0` | `cpu` |
| `torch.version.hip` | `"7.2.0"` | `None` | `None` |
| `torch.version.cuda` | `None` | `"12.4"` | `None` |
| `half precision` | ✅ FP16 | ✅ FP16 | ❌ |

```bash
# Forzar backend específico
python3 scripts/ppe-pipeline.py --device cuda --source video.mp4 ...
python3 scripts/ppe-pipeline.py --device cpu --source video.mp4 ...
```

> **Nota**: `device="cuda:0"` funciona en ambos backends (ROCm y CUDA). Usar `torch.version.hip` para distinguir.

### 2. Cargar Modelo YOLO para PPE

El pipeline soporta tres formas de obtener el modelo:

**A. Modelo pre-entrenado COCO (rápido, clases limitadas):**
```bash
# YOLOv8x entrenado en COCO — detecta "person" pero NO clases PPE específicas
python3 scripts/ppe-pipeline.py --model yolov8x.pt ...
```

**B. Modelo fine-tuned para PPE (recomendado):**
```bash
# Descargar modelo PPE pre-entrenado (si está disponible en el repositorio)
python3 scripts/ppe-pipeline.py --model models/ppe-yolov8x.pt ...
```

**C. Fine-tune propio (ver Paso 11):**
```bash
python3 scripts/train-ppe.py --data dataset.yaml --model yolov8x.pt --epochs 100
# Usar el modelo entrenado:
python3 scripts/ppe-pipeline.py --model runs/detect/ppe-train/weights/best.pt ...
```

**Clases PPE esperadas por el pipeline:**

| ID | Clase | Elemento | Etiqueta |
|----|-------|----------|----------|
| 0 | `hardhat` | Casco de seguridad | Casco |
| 1 | `safety_vest` | Chaleco reflectante | Chaleco |
| 2 | `gloves` | Guantes de seguridad | Guantes |
| 3 | `safety_glasses` | Lentes de seguridad | Lentes |
| 4 | `safety_boots` | Botas de seguridad | Botas |
| 5 | `person` | Persona (tronco/cuerpo completo) | Persona |

### 3. Configurar Pipeline de Video

Tres fuentes de video soportadas:

**Archivo local:**
```bash
python3 scripts/ppe-pipeline.py \
  --source video.mp4 \
  --fps 30 \
  --resolution 1920x1080
```

**Stream RTSP (cámara IP):**
```bash
python3 scripts/ppe-pipeline.py \
  --source "rtsp://user:password@192.168.1.100:554/stream1" \
  --rtsp-transport tcp \
  --fps 15  # Limitar FPS para no saturar GPU
```

**Cámara USB (v4l2):**
```bash
python3 scripts/ppe-pipeline.py \
  --source /dev/video0 \
  --resolution 1280x720 \
  --fps 10
```

**Múltiples fuentes simultáneas:**
```bash
python3 scripts/ppe-pipeline.py \
  --source "rtsp://cam1/stream" "rtsp://cam2/stream" "rtsp://cam3/stream" \
  --multi-camera \
  --device "cuda:0,cuda:1"  # Balancear entre GPUs
```

### 4. Frame Extraction y Preprocesamiento

El pipeline extrae frames de la fuente de video y aplica preprocesamiento:

```python
# Internamente en ppe-pipeline.py:
import cv2
from PIL import Image

def extract_frame(cap):
    ret, frame = cap.read()
    if not ret:
        return None
    # Redimensionar manteniendo aspect ratio (letterbox)
    frame_resized = letterbox(frame, (640, 640))
    # Convertir BGR → RGB (YOLO espera RGB)
    frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
    # Normalizar a [0, 1]
    frame_norm = frame_rgb.astype(np.float32) / 255.0
    return frame_norm
```

Parámetros de preprocesamiento configurables:
- `--resolution`: resolución de captura (no afecta resolución de inferencia que es 640×640)
- `--fps`: límite de FPS de procesamiento (el video fuente puede correr más rápido)
- `--frame-skip`: saltar N frames entre inferencias para aumentar throughput

### 5. Inferencia Batch con YOLO

El pipeline ejecuta inferencia en batches para maximizar throughput GPU:

```python
from ultralytics import YOLO

model = YOLO("ppe-yolov8x.pt")
device = "cuda:0" if torch.cuda.is_available() else "cpu"

# Inferencia batch
results = model.predict(
    frame_batch,        # Lista de frames preprocesados
    device=device,
    batch=8,            # Batch size configurable
    imgsz=640,
    conf=0.5,           # Umbral de confianza
    iou=0.45,           # Umbral NMS IoU
    verbose=False,
)
```

Benchmark integrado reporta:
- **FPS**: frames por segundo procesados (incluyendo todo el pipeline)
- **Latency media**: tiempo por frame en ms
- **Detecciones por frame**: promedio de detecciones
- **VRAM usage**: memoria GPU utilizada

### 6. Post-procesamiento: NMS, Filtrado y Mapeo de Clases

```python
def postprocess(results, confidence_threshold=0.5):
    detections = []
    for r in results:
        boxes = r.boxes
        for box in boxes:
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            if conf < confidence_threshold:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            detections.append({
                "class_id": cls_id,
                "class_name": PPE_CLASSES[cls_id],
                "confidence": conf,
                "bbox": [x1, y1, x2, y2],
            })
    # Non-Maximum Suppression (ya aplicado por ultralytics)
    return detections
```

**Mapeo de clases PPE:**
```python
PPE_CLASSES = {
    0: "hardhat",
    1: "safety_vest",
    2: "gloves",
    3: "safety_glasses",
    4: "safety_boots",
    5: "person",
}
```

Filtrado por clases específicas:
```bash
# Detectar solo casco y chaleco
python3 scripts/ppe-pipeline.py --classes hardhat safety_vest ...

# Detectar todas las clases PPE
python3 scripts/ppe-pipeline.py --classes hardhat safety_vest gloves safety_glasses safety_boots person ...
```

### 7. Tracking de Personas con Asignación de EPP

El tracking asigna un ID único a cada persona y le asocia los elementos de EPP detectados:

```python
class PersonTracker:
    def __init__(self, iou_threshold=0.3, max_lost_frames=30):
        self.next_id = 0
        self.tracks = {}      # track_id -> {bbox, ppe_status, lost_frames}
        self.iou_threshold = iou_threshold
        self.max_lost_frames = max_lost_frames

    def update(self, detections):
        # Separar personas del resto de detecciones
        persons = [d for d in detections if d["class_name"] == "person"]
        ppe_items = [d for d in detections if d["class_name"] != "person"]

        # Matching IoU entre tracks existentes y nuevas personas
        for person in persons:
            best_match = None
            best_iou = self.iou_threshold
            for track_id, track in self.tracks.items():
                iou = self.compute_iou(track["bbox"], person["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_match = track_id

            if best_match is not None:
                # Actualizar track existente
                track_id = best_match
                self.tracks[track_id]["bbox"] = person["bbox"]
                self.tracks[track_id]["lost_frames"] = 0
                self.tracks[track_id]["person_bbox"] = person["bbox"]
            else:
                # Nuevo track
                track_id = self.next_id
                self.next_id += 1
                self.tracks[track_id] = {
                    "bbox": person["bbox"],
                    "person_bbox": person["bbox"],
                    "ppe_status": {},
                    "lost_frames": 0,
                    "alert_sent": False,
                }

            # Asignar EPP a la persona (IoU entre bounding box de persona y EPP)
            person_bbox = person["bbox"]
            self.tracks[track_id]["ppe_status"] = self.assign_ppe(
                person_bbox, ppe_items
            )

        # Marcar personas perdidas
        for track_id in self.tracks:
            self.tracks[track_id]["lost_frames"] += 1

        # Limpiar tracks perdidos hace mucho
        self.tracks = {
            tid: t for tid, t in self.tracks.items()
            if t["lost_frames"] <= self.max_lost_frames
        }

        return self.tracks
```

**Verificación de EPP por persona:**

```python
PPE_REQUIRED = ["hardhat", "safety_vest", "gloves", "safety_glasses", "safety_boots"]

def check_ppe_compliance(track):
    """Retorna (completo, faltantes, presentes) para una persona."""
    ppe_status = track["ppe_status"]
    presentes = [item for item, detected in ppe_status.items() if detected]
    faltantes = [item for item in PPE_REQUIRED if item not in presentes]

    if len(faltantes) == 0:
        return "complete", faltantes, presentes
    elif len(presentes) >= 3:
        return "partial", faltantes, presentes
    else:
        return "missing", faltantes, presentes
```

### 8. Alertas: Log, Webhook, MQTT

El sistema de alertas se activa cuando una persona no tiene el EPP completo:

**Log local:**
```bash
python3 scripts/ppe-pipeline.py --alert-log ...
# Output: [ALERT] 14:23:05 | Camera cam1 | Person ID 3 | Missing: hardhat, safety_glasses
```

**Webhook HTTP POST:**
```bash
python3 scripts/ppe-pipeline.py \
  --alert-webhook "https://hooks.example.com/ppe-alerts" \
  --alert-webhook-header "Authorization: Bearer token123"
```

Payload enviado:
```json
{
  "timestamp": "2026-06-27T14:23:05.123Z",
  "camera_id": "cam1",
  "person_id": 3,
  "ppe_missing": ["hardhat", "safety_glasses"],
  "ppe_present": ["safety_vest", "gloves", "safety_boots"],
  "status": "missing",
  "location": {"bbox": [120, 45, 320, 580]},
  "frame": "frame_0042.jpg"
}
```

**MQTT:**
```bash
python3 scripts/ppe-pipeline.py \
  --alert-mqtt "mqtt://broker.example.com:1883" \
  --alert-mqtt-topic "mining/ppe/alerts" \
  --alert-mqtt-username "user" \
  --alert-mqtt-password "pass"
```

**Rate limiting** (configurado en `alert-manager.py`):
- No repetir la misma alerta para la misma persona en menos de 30 segundos
- Mínimo 1 alerta por persona cada 5 minutos (evita spam)
- Agrupar alertas por turno/zona si hay muchas

### 9. Output: Video Anotado

El pipeline genera video anotado con bounding boxes coloreados por estado de EPP:

```bash
python3 scripts/ppe-pipeline.py \
  --source video.mp4 \
  --output ./output \
  --output-video \
  --show-fps
```

**Código de colores:**
| Estado | Color | Significado |
|--------|-------|-------------|
| `complete` | Verde `#00FF00` | Todos los elementos EPP presentes |
| `partial` | Amarillo `#FFFF00` | Algunos elementos faltan |
| `missing` | Rojo `#FF0000` | Mayoría de elementos faltan |
| `unknown` | Gris `#888888` | No se pudo verificar (track nuevo) |

El video anotado incluye:
- Bounding box de la persona con color según estado
- ID de la persona en la esquina superior del bounding box
- Lista de EPP detectado (iconos o texto) al lado del bounding box
- Contador de personas totales en esquina superior izquierda
- FPS y timestamp en esquina superior derecha
- Estado general de la escena (OK/ALERTA) en la parte superior

### 10. Output: JSON por Frame

```bash
python3 scripts/ppe-pipeline.py \
  --source video.mp4 \
  --output ./output \
  --output-json
```

Estructura JSON:
```json
{
  "metadata": {
    "source": "video.mp4",
    "model": "ppe-yolov8x.pt",
    "backend": "rocm",
    "device": "AMD Instinct MI300X",
    "total_frames": 4500,
    "fps_pipeline": 28.3,
    "classes": ["hardhat", "safety_vest", "gloves", "safety_glasses", "safety_boots", "person"]
  },
  "frames": [
    {
      "frame_id": 42,
      "timestamp_s": 1.4,
      "camera_id": "cam1",
      "people_count": 5,
      "people": [
        {
          "person_id": 3,
          "bbox": [120, 45, 320, 580],
          "confidence": 0.92,
          "ppe_status": "missing",
          "ppe_present": ["safety_vest", "gloves"],
          "ppe_missing": ["hardhat", "safety_glasses", "safety_boots"],
          "ppe_items": [
            {"class": "safety_vest", "confidence": 0.88, "bbox": [115, 180, 325, 350]},
            {"class": "gloves", "confidence": 0.76, "bbox": [100, 400, 160, 480]}
          ]
        }
      ],
      "alerts": [
        {
          "person_id": 3,
          "type": "ppe_missing",
          "missing_items": ["hardhat", "safety_glasses", "safety_boots"]
        }
      ]
    }
  ]
}
```

### 11. Fine-tuning para Minería

El script `train-ppe.py` fine-tunea YOLOv8x para detección de EPP con aumentación específica para minería:

```bash
python3 scripts/train-ppe.py \
  --data dataset.yaml \
  --model yolov8x.pt \
  --epochs 100 \
  --imgsz 640 \
  --batch 16 \
  --device cuda:0 \
  --project runs/ppe \
  --name mining-ppe-v1
```

**Estructura esperada del dataset (formato YOLO):**
```
dataset/
├── dataset.yaml
├── images/
│   ├── train/
│   │   ├── img_0001.jpg
│   │   └── ...
│   └── val/
│       ├── img_1001.jpg
│       └── ...
└── labels/
    ├── train/
    │   ├── img_0001.txt
    │   └── ...
    └── val/
        ├── img_1001.txt
        └── ...
```

**dataset.yaml:**
```yaml
path: ./dataset
train: images/train
val: images/val

nc: 6
names: ["hardhat", "safety_vest", "gloves", "safety_glasses", "safety_boots", "person"]
```

**Data augmentation específica para minería (incluida en train-ppe.py):**

| Augmentación | Parámetro | Simula |
|-------------|-----------|--------|
| `hsv_h` | 0.015 | Variación de luz natural |
| `hsv_s` | 0.7 | Polvo, suciedad en lentes |
| `hsv_v` | 0.4 | Baja luz, sombras profundas |
| `degrees` | 10.0 | Cabezas inclinadas, movimiento |
| `translate` | 0.1 | Movimiento de cámara |
| `scale` | 0.5 | Distancias variables |
| `mosaic` | 1.0 | Escenas mineras complejas |
| `mixup` | 0.1 | Datos sintéticos |
| `flipud` | 0.5 | Visión desde arriba (drones) |

**Evaluación post-entrenamiento:**
```
Class            Images  Instances   mAP@50   mAP@50:95
hardhat           1200       3200    0.952      0.712
safety_vest       1200       2800    0.938      0.689
gloves            1200       1500    0.871      0.623
safety_glasses    1200       1100    0.845      0.598
safety_boots      1200       2100    0.912      0.671
person            1200       3500    0.967      0.734
all               1200      14200    0.914      0.671
```

### 12. Exportar Modelo Post-Entrenamiento

```bash
# Exportar a ONNX
python3 scripts/train-ppe.py \
  --data dataset.yaml \
  --model runs/ppe/mining-ppe-v1/weights/best.pt \
  --export onnx

# Exportar a TorchScript
python3 scripts/train-ppe.py \
  --model runs/ppe/mining-ppe-v1/weights/best.pt \
  --export torchscript

# Exportar a TensorRT (NVIDIA solamente)
python3 scripts/train-ppe.py \
  --model runs/ppe/mining-ppe-v1/weights/best.pt \
  --export engine
```

### 13. Multi-Cámara y Multi-GPU

**Multi-cámara (threading):**
```bash
python3 scripts/ppe-pipeline.py \
  --source "rtsp://cam1/stream" "rtsp://cam2/stream" \
  --multi-camera \
  --max-threads 4
```

El pipeline spawns un thread por cámara, cada uno con su propio tracker y buffer de frames. Los resultados se consolidan en un único output JSON.

**Multi-GPU (balanceo de carga):**
```bash
# Asignar GPUs específicas a cada cámara
python3 scripts/ppe-pipeline.py \
  --source "rtsp://cam1" "rtsp://cam2" "rtsp://cam3" "rtsp://cam4" \
  --multi-camera \
  --device "cuda:0,cuda:1,cuda:0,cuda:1"
```

```bash
# Distribución automática
python3 scripts/ppe-pipeline.py \
  --source "rtsp://cam1" "rtsp://cam2" "rtsp://cam3" "rtsp://cam4" \
  --multi-camera \
  --device auto  # Distribuye uniformemente entre GPUs disponibles
```

### 14. Benchmark Integrado

```bash
# Benchmark completo
python3 scripts/ppe-pipeline.py \
  --source video.mp4 \
  --model ppe-yolov8x.pt \
  --benchmark-only \
  --frames 500

# Output:
# ════════════════════════════════════════
#   PPE Pipeline Benchmark
# ════════════════════════════════════════
#   Backend:            ROCM
#   Device:             AMD Instinct MI300X
#   Model:              ppe-yolov8x.pt
#   Resolution:         640×640
#   Batch Size:         8
#
#   FPS:                42.3
#   Latency avg:        23.6 ms
#   Latency p50:        22.1 ms
#   Latency p95:        28.4 ms
#   Latency p99:        35.2 ms
#   VRAM usage:         6.8 GB
#   Detections/frame:   6.2
#   People tracked:     5
#   PPE violations:     2
# ════════════════════════════════════════
```

### 15. Dashboard de Cumplimiento

El pipeline puede generar un dashboard HTML simple con estadísticas:

```bash
python3 scripts/ppe-pipeline.py \
  --source video.mp4 \
  --output ./output \
  --dashboard
```

Esto genera `output/dashboard.html` con:
- Gráfico de cumplimiento por hora
- Tabla de infracciones por persona
- Mapa de calor de zonas con más infracciones
- Estadísticas por turno
- Exportación CSV de datos históricos

## Classes PPE

| Clase | Elemento | Descripción | Colores típicos | Norma chilena |
|-------|----------|-------------|-----------------|---------------|
| `hardhat` | Casco de seguridad | Protección craneana, con barbiquejo. Sin casco = falta grave. | Blanco, amarillo, azul, rojo, naranja | NCh 461 |
| `safety_vest` | Chaleco reflectante | Chaleco con bandas reflectantes de alta visibilidad. | Naranja/amarillo con bandas plateadas | DS 132 |
| `gloves` | Guantes de seguridad | Guantes anti-corte, anti-vibración, dieléctricos según tarea. | Cuero, kevlar, nitrilo (variable) | NCh 2193 |
| `safety_glasses` | Lentes de seguridad | Anti-impacto, anti-empañamiento, con protección UV. | Transparentes, oscuros o espejados | NCh 328 |
| `safety_boots` | Botas de seguridad | Botas con puntera de acero/composite, suela anti-resbalo. | Café o negro con puntera metálica | NCh 2111 |
| `person` | Persona | Cuerpo completo o torso de trabajador. | — | — |

**Combinaciones válidas por zona:**
- **Mina subterránea**: casco + chaleco + botas + lentes + guantes (equipo completo)
- **Planta de proceso**: casco + chaleco + botas + lentes (guantes en áreas específicas)
- **Taller de mantención**: casco + botas + lentes + guantes (chaleco en áreas de tránsito)
- **Oficina administrativa**: sin EPP obligatorio (excepto en zonas de visita)

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/ppe-dataset.md](references/ppe-dataset.md) | Guía de datasets de EPP públicos, formato COCO/YOLO, clases recomendadas, data augmentation para minería |
| [references/ppe-classes.md](references/ppe-classes.md) | Definición detallada de cada clase PPE, combinaciones por zona, normativa chilena (NCh 461, DS 132) |
| [references/deployment-industrial.md](references/deployment-industrial.md) | Despliegue en entorno industrial: cámaras, servidores, integración SCADA, latencia, alta disponibilidad |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/ppe-pipeline.py` | Pipeline principal de detección PPE: captura, inferencia, tracking, alertas, output JSON/video, benchmark, multi-cámara |
| `scripts/train-ppe.py` | Fine-tuning de YOLOv8x para EPP con data augmentation para minería, evaluación y exportación |
| `scripts/alert-manager.py` | Gestión de alertas multi-canal: log, webhook HTTP, MQTT, CSV. Rate limiting, umbrales por tiempo y zona |

## Common Issues

### 1. Falsos Positivos en Chalecos y Cascos

**Síntoma**: El modelo detecta chalecos donde no hay (ej. conos de tránsito naranjas) o cascos en objetos circulares (ej. tambores, tuberías).

**Causa**: El modelo pre-entrenado no fue fine-tuneado con datos de la mina específica. Los objetos industriales comparten colores y formas con EPP.

**Solución**:
```bash
# 1. Aumentar umbral de confianza
python3 scripts/ppe-pipeline.py --confidence 0.65 ...

# 2. Fine-tune con datos del sitio específico (ver Paso 11)
# 3. Agregar clases negativas (hardhat_negative, vest_negative) al dataset
# 4. Post-procesar con heurísticas: tamaño mínimo de casco en píxeles, relación de aspecto
```

### 2. Oclusión Parcial de Personas

**Síntoma**: Personas parcialmente ocultas por maquinaria, pilares, o polvo. El tracking pierde IDs o no detecta EPP faltante.

**Causa**: Entornos mineros tienen mucha oclusión. Una persona puede estar parcialmente visible (solo torso, solo cabeza).

**Solución**:
```bash
# 1. Activar tracking con IoU matching (incluido)
# 2. Mantener track por hasta 30 frames perdidos (configurable)
# 3. Verificar EPP parcial: si se ve casco pero no chaleco, no alertar inmediatamente
python3 scripts/ppe-pipeline.py --max-lost-frames 60 ...

# 4. Múltiples ángulos de cámara para cubrir zonas ciegas
# 5. Si una persona reaparece cerca de donde desapareció, reasignar mismo ID
```

### 3. Tracking Loss en Multitudes

**Síntoma**: En zonas de paso (entrada a túnel, casino), muchas personas se cruzan y el tracking intercambia IDs.

**Causa**: IoU matching falla cuando múltiples personas se superponen o están muy cerca.

**Solución**:
```bash
# 1. Reducir umbral IoU para matching más estricto
python3 scripts/ppe-pipeline.py --iou-threshold 0.5 ...

# 2. Usar tracking basado en embeddings (ReID) — requiere modelo adicional
# 3. Cámaras con vista superior (cenital) para minimizar oclusión
# 4. Segmentar zona de interés: no trackear en áreas de alta congestión
# 5. Implementar buffer de reappearance: si un ID desaparece y otro aparece cerca en <1s, es el mismo
```

### 4. Baja Luz / Condiciones de Oscuridad

**Síntoma**: En minas subterráneas o noche, el modelo no detecta personas ni EPP.

**Causa**: YOLOv8x fue entrenado con imágenes diurnas. En oscuridad, el contraste es insuficiente.

**Solución**:
```bash
# 1. Usar cámara con IR (infrarrojo) y filtro cut
# 2. Preprocesamiento: ecualización de histograma, CLAHE
python3 scripts/ppe-pipeline.py --preprocess clahe ...

# 3. Fine-tune con imágenes nocturnas/subterráneas
# 4. Aumentar brillo sintético en data augmentation
# 5. Usar modelo con mayor resolución (1280×1280) para mejor detección en baja luz
# 6. Chalecos reflectantes: asegurar que las bandas reflectantes sean visibles (iluminación IR)
```

### 5. Modelo No Entrenado para Minería Chilena

**Síntoma**: El modelo pre-entrenado no reconoce EPP de proveedores locales (ej. cascos 3M con diseño chileno, botas de seguridad nacionales).

**Causa**: Los datasets públicos (COCO, PPE Kaggle) usan EPP norteamericano/europeo. La minería chilena usa colores y diseños específicos.

**Solución**:
```bash
# 1. Fine-tune obligatorio con datos de faena chilena
# 2. Recopilar mínimo 500 imágenes por clase de EPP chileno
# 3. Data augmentation con: polvo rojo (simular óxido/mineral), alta exposición solar
# 4. Clases específicas: hardhat_white, hardhat_yellow (cascos por rol en minería chilena)
# 5. Validar con data de faena local antes de poner en producción
```

### 6. Performance con N Cámaras Simultáneas

**Síntoma**: Al agregar más cámaras, el FPS general cae linealmente. Con 8 cámaras, el sistema no da abasto.

**Causa**: Cada cámara ejecuta inferencia completa. Sin balanceo de carga, la GPU se satura.

**Solución**:
```bash
# 1. Distribuir cámaras entre GPUs disponibles
python3 scripts/ppe-pipeline.py \
  --source "rtsp://cam1" "rtsp://cam2" "rtsp://cam3" "rtsp://cam4" \
  --device "cuda:0,cuda:0,cuda:1,cuda:1"

# 2. Reducir FPS por cámara
python3 scripts/ppe-pipeline.py --fps 5 --source ...

# 3. Frame skipping adaptativo: si la cola de frames crece, saltar frames
python3 scripts/ppe-pipeline.py --adaptive-skip ...

# 4. Usar batch inference entre cámaras (frames de múltiples cámaras en un batch)
# 5. Modelo más pequeño para zonas de baja seguridad, YOLOv8x para zonas críticas
```

**Referencia de capacidad:**

| Cámaras | GPU | FPS por cámara | Total FPS | Batch | VRAM |
|---------|-----|----------------|-----------|-------|------|
| 1 | MI300X | 42 | 42 | 8 | 6.8 GB |
| 4 | MI300X | 10 | 40 | 8 | 7.2 GB |
| 8 | 2× MI300X | 10 | 80 | 8 | 7.2 GB c/u |
| 16 | 4× MI300X | 8 | 128 | 16 | 8.0 GB c/u |

### 7. Alertas por Worker Sin Casco en Zona No Crítica

**Síntoma**: El sistema alerta constantemente por personas sin EPP en zonas donde no es obligatorio (ej. oficinas dentro de la faena).

**Causa**: No hay configuración de zonas con distintos niveles de exigencia de EPP.

**Solución**:
```bash
# 1. Definir zonas en el pipeline (usando coordenadas en frame o líneas virtuales)
# 2. Configurar EPP requerido por zona
python3 scripts/ppe-pipeline.py \
  --zone-rules "zone1:hardhat,safety_vest,safety_boots" \
  --zone-rules "zone2:hardhat,safety_boots" \
  --zone-rules "zone3:none"

# 3. Usar máscara de zona (draw polygons en la imagen)
python3 scripts/ppe-pipeline.py --zone-mask zone_mask.png ...

# 4. Ignorar personas fuera de zona de interés
python3 scripts/ppe-pipeline.py --roi 100,100,1800,900 ...
```

### 8. GPU Out of Memory con YOLOv8x

**Síntoma**: `torch.cuda.OutOfMemoryError` al cargar el modelo o durante inferencia.

**Causa**: YOLOv8x requiere ~7.2 GB en FP32. En GPUs con 8 GB, no queda espacio para buffers de video y tracking.

**Solución**:
```bash
# 1. Forzar FP16 (reduce VRAM ~50%)
python3 scripts/ppe-pipeline.py --fp16 ...

# 2. Reducir batch size
python3 scripts/ppe-pipeline.py --batch 2 ...

# 3. Usar YOLOv8l en lugar de v8x
python3 scripts/ppe-pipeline.py --model yolov8l.pt ...

# 4. Liberar VRAM entre batches
# (ya incluido en el pipeline: torch.cuda.empty_cache() periódico)

# 5. Monitorear VRAM en tiempo real
watch -n 1 rocm-smi  # AMD
watch -n 1 nvidia-smi  # NVIDIA
```

### 9. Latencia Alta en Pipeline End-to-End

**Síntoma**: Desde que ocurre una infracción hasta que llega la alerta pasan más de 5 segundos.

**Causa**: El pipeline completo incluye: captura → decode → preprocess → inferencia → postprocess → tracking → alerta. Cada etapa agrega latencia.

**Solución**:
```bash
# 1. Medir latencia por etapa
python3 scripts/ppe-pipeline.py --benchmark-detailed

# 2. Optimizar decode: usar hardware decode
# 3. Reducir resolución de decode (no de inferencia)
# 4. Pipeline asíncrono: captura en thread separado de inferencia
# 5. Alertas inmediatas sin esperar a escribir JSON
# 6. Usar UDP en lugar de TCP para RTSP (menor latencia, posible packet loss)

# Benchmark típico end-to-end (MI300X):
#   Captura+decode:   8 ms
#   Preprocess:       2 ms
#   Inferencia:      14 ms
#   Postprocess:      1 ms
#   Tracking:         3 ms
#   Alerta+log:       1 ms
#   ─────────────────────
#   Total:           29 ms → ~34 FPS
```

## Technical Notes

- **`torch.cuda` API funciona en ROCm y CUDA**: No hay `torch.rocm`. Usar `torch.version.hip` para detectar AMD ROCm.
- **Ultralytics auto-detecta backend**: El parámetro `device="cuda:0"` funciona en ambos backends.
- **FP16 recomendado siempre**: La pérdida de precisión es insignificante (<0.1 mAP) y la reducción de VRAM es ~50%.
- **Multi-GPU**: Distribuir cámaras entre GPUs manualmente con `--device "cuda:0,cuda:1"`. No hay balanceo automático.
- **Tracking**: El IoU matching simple funciona bien para ≤10 personas por frame. Para más, considerar ByteTrack o BoT-SORT.
- **Persistencia de alertas**: Usar `alert-manager.py` como servicio independiente para no perder alertas si el pipeline se cae.

## Related Skills

- [`ds132-compliance`](../ds132-compliance/SKILL.md) — DS 132 compliance for Chilean mining regulations
- [`yolo-rocm-deploy`](../yolo-rocm-deploy/SKILL.md) — YOLO object detection on ROCm/CUDA
- [`video-pipeline-rocm`](../video-pipeline-rocm/SKILL.md) — Video inference pipelines with GStreamer
