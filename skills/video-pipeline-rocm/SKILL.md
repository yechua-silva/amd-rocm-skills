---
name: video-pipeline-rocm
description: >
  Pipeline completo de inferencia sobre video en tiempo real o batch usando
  GStreamer + ROCm. Captura video desde RTSP, archivos locales o cámara (v4l2),
  decodifica con aceleración HW (AMD VCN / NVIDIA NVDEC / CPU fallback),
  extrae frames, ejecuta inferencia con YOLO/VLM en GPU AMD ROCm o NVIDIA CUDA,
  y produce resultados como JSON, video anotado o RTMP push. Multi-backend:
  AMD ROCm (VAAPI/VCN/AMF), NVIDIA CUDA (NVENC/NVDEC), CPU (avdec/soft).
  Incluye detección automática de backend, preprocesamiento de frames,
  inferencia batch optimizada, y post-procesamiento con bounding boxes/tracking.
  Usar al procesar streams RTSP con modelos de IA, transcodificar video con
  aceleración HW, extraer frames por scene change, o construir pipelines
  video-inferencia multi-GPU. Use this skill when building video inference
  pipelines with GStreamer, processing RTSP streams with YOLO, or extracting
  frames with hardware acceleration. / Útil al construir pipelines de inferencia
  de video con GStreamer, procesar streams RTSP con YOLO, o extraer frames con
  aceleración hardware. Keywords: gstreamer, rocm, video, pipeline,
  inference, vcn, amd, nvidia, cuda, rtsp, transcoding, yolo, vlm, frame-extraction,
  video-analytics, vaapi, nvdec, hw-acceleration, video-decode, streaming,
  computer-vision, pytorch, hip, gpu-video, v4l2, appsink
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: "yechua-silva"
  tags:
    - amd
    - rocm
    - gstreamer
    - video
    - pipeline
    - inference
    - vcn
    - nvidia
    - cuda
    - yolo
    - rtsp
    - transcoding
    - hw-acceleration
    - pytorch
    - computer-vision
compatibility: >
  Compatible with Claude Code, OpenCode, Codex, Cursor, Cline, Roo Code,
  Windsurf, Gemini CLI, and Kiro CLI. Requires Linux with AMD ROCm or
  NVIDIA CUDA GPU (CPU fallback supported).
---

# Video Inference Pipeline — ROCm / CUDA / CPU

Pipeline de inferencia sobre video en tiempo real o batch usando **GStreamer** para captura y decodificación, con aceleración hardware en **AMD ROCm (VCN/VAAPI)** o **NVIDIA CUDA (NVDEC/NVENC)**, y fallback a CPU por software.

La skill detecta automáticamente el backend de video disponible, construye el pipeline GStreamer óptimo, extrae frames, ejecuta inferencia con modelos YOLO/VLM, y produce resultados estructurados.

## Purpose

- **Capturar** video desde múltiples fuentes: RTSP, archivos locales, cámaras v4l2
- **Decodificar** con aceleración hardware: AMD VCN (vaapi), NVIDIA NVDEC (nvdec), o CPU (avdec)
- **Extraer frames** por intervalo temporal, por keyframe, o por scene change
- **Preprocesar** frames: redimensionar, normalizar, convertir espacio de color
- **Inferir** con modelos YOLO, ONNX, o PyTorch en GPU AMD ROCm o NVIDIA CUDA
- **Post-procesar** detecciones: bounding boxes, tracking, análisis semántico
- **Output** en JSON, video anotado, o push a RTMP/HLS
- Funcionar en **cualquier backend**: AMD ROCm, NVIDIA CUDA, o CPU

## When to Use / Cuándo Usar

La skill se activa con frases como:

- "Build a video inference pipeline with GStreamer and ROCm"
- "Process an RTSP stream with YOLO on AMD GPU"
- "Extraer frames de video con aceleración hardware"
- "Decode video with VCN on AMD GPU" / "Decodificar video con VCN en GPU AMD"
- "Transcodificar video con VAAPI o NVENC"
- "Run inference on video stream" / "Ejecutar inferencia sobre stream de video"
- "Video analytics pipeline with PyTorch and ROCm"
- "Pipeline de video-inferencia con GStreamer y ROCm"
- "Detección de objetos en video en tiempo real"
- "Process video file with YOLO on NVIDIA GPU"
- Keywords: gstreamer, video pipeline, inference, rocm, vcn, nvdec, vaapi, rtsp,
  video decode, frame extraction, video analytics, amd, nvidia, transcoding,
  yolo, pytorch, streaming, v4l2, appsink, scene change, keyframe

## Prerequisites

- **GStreamer 1.20+** con plugins base, good, bad, ugly, y libav
- **ROCm 7.2+** (AMD) o **CUDA 12+** (NVIDIA) para inferencia GPU
- **GPU con aceleración video**: AMD con VCN (MI300X, RX 7900, RX 9070) o NVIDIA con NVDEC (A100, H100, RTX series)
- **Python 3.10+** con `python3-gi` (GStreamer Python bindings) y PyTorch con soporte ROCm o CUDA
- **ROCm VAAPI driver** (AMD): `rocm-vaapi-driver` o `mesa-va-drivers` para decodificación VCN
- **NVIDIA Video Codec SDK** (NVIDIA): drivers 535+ con soporte NVDEC/NVENC
- **Dependencias opcionales**: `ultralytics` (YOLO), `onnxruntime` (ONNX), `opencv-python` (OpenCV)

## Quickstart

### 1. Detect Video Acceleration Backend

```bash
bash scripts/detect-backend.sh
```

Detecta automáticamente: AMD VCN (vaapi), NVIDIA NVDEC (nvdec), o CPU software decode.

### 2. Run GStreamer Pipeline + Frame Extraction

```bash
# Procesar archivo local con AMD VCN, extraer frame cada 2 segundos
bash scripts/gst-pipeline.sh \
  --source file \
  --input video.mp4 \
  --output ./frames \
  --interval 2 \
  --width 640 \
  --height 480
```

### 3. Run Inference on Extracted Frames

```bash
# Inferir en los frames extraídos
python3 scripts/inference-pipeline.py \
  --model yolov8x.pt \
  --input-dir ./frames \
  --output results.json \
  --batch-size 8 \
  --confidence 0.5
```

## Step-by-Step Instructions

### 1. Detect GPU Video Backend

Ejecuta el script de detección para identificar qué aceleración de video está disponible:

```bash
bash scripts/detect-backend.sh

# Output esperado:
# ============================================================
#   Video Acceleration Backend Detection
# ============================================================
#   Backend:            AMD VCN
#   Decode:             vaapi (vaapih264dec, vaapih265dec, ...)
#   Encode:             vaapi (vaapih264enc, vaapih265enc)
#   Devices:            /dev/dri/renderD128
#   Driver:             Mesa Gallium driver 24.2.0
#   Score:              100 (óptimo)
# ============================================================
```

El script usa cuatro niveles de detección:

| Nivel | Método | AMD | NVIDIA | CPU |
|-------|--------|:---:|:------:|:---:|
| 1 | `vainfo` / `gstvaapiinfo` | ✅ VCN | ❌ | ❌ |
| 2 | `nvidia-smi` + `nv-codec-headers` | ❌ | ✅ NVDEC | ❌ |
| 3 | `gst-inspect-1.0` elementos | ✅ VAAPI | ✅ NVDEC | ✅ avdec |
| 4 | Fallback software | ❌ | ❌ | ✅ avdec |

**Salida JSON** para uso programático:
```bash
bash scripts/detect-backend.sh --json
```

### 2. Install GStreamer with ROCm/VAAPI Support

**AMD ROCm — Ubuntu 22.04/24.04:**
```bash
# Plugins GStreamer base
sudo apt install -y \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-libav \
  gstreamer1.0-vaapi \
  gstreamer1.0-gl \
  python3-gi \
  python3-gst-1.0

# ROCm VAAPI driver (AMD VCN acceleration)
sudo apt install -y rocm-vaapi-driver  # Si está disponible
# O via Mesa:
sudo apt install -y mesa-va-drivers

# Verificar instalación
gst-inspect-1.0 --version
gst-inspect-1.0 vaapih264dec  # Debe mostrar detalles del elemento
```

**NVIDIA CUDA — NVDEC/NVENC:**
```bash
# GStreamer plugins
sudo apt install -y \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-libav \
  python3-gi

# nv-codec-headers (para soporte NVDEC/NVENC en GStreamer)
git clone https://git.videolan.org/git/ffmpeg/nv-codec-headers.git
cd nv-codec-headers && sudo make install

# gst-plugins-bad con NVDEC (normalmente ya incluido)
gst-inspect-1.0 nvdec  # Debe mostrar detalles del elemento
```

**CPU Fallback:**
```bash
# Los decodificadores software (avdec_*) vienen con gstreamer1.0-libav
sudo apt install -y \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-libav \
  python3-gi \
  python3-gst-1.0
```

### 3. Pipeline de Captura

El script `scripts/gst-pipeline.sh` soporta tres fuentes de video:

**RTSP Source (streaming en red):**
```bash
bash scripts/gst-pipeline.sh \
  --source rtsp \
  --input "rtsp://user:pass@192.168.1.100:554/stream1" \
  --output ./frames \
  --interval 1 \
  --backend auto
```

**File Source (archivo local):**
```bash
bash scripts/gst-pipeline.sh \
  --source file \
  --input video.mp4 \
  --output ./frames \
  --interval 2 \
  --backend amd
```

**Camera Source (v4l2 — cámara USB/CSI):**
```bash
bash scripts/gst-pipeline.sh \
  --source camera \
  --input /dev/video0 \
  --output ./frames \
  --interval 0.5 \
  --width 1280 \
  --height 720 \
  --backend auto
```

### 4. Decodificación Acelerada

El script selecciona automáticamente el decodificador óptimo según el backend:

| Backend | Codec | Elemento Decoder | Elemento Encoder |
|---------|-------|------------------|------------------|
| **AMD VCN** | H.264 | `vaapih264dec` | `vaapih264enc` |
| **AMD VCN** | H.265/HEVC | `vaapih265dec` | `vaapih265enc` |
| **AMD VCN** | VP8 | `vaapivp8dec` | `vaapivp8enc` |
| **AMD VCN** | VP9 | `vaapivp9dec` | — |
| **AMD VCN** | MPEG-2 | `vaapimpeg2dec` | — |
| **NVIDIA NVDEC** | H.264 | `nvdec` (h264parse + nvdec) | `nvenc` (h264parse + nvenc) |
| **NVIDIA NVDEC** | H.265/HEVC | `nvdec` (h265parse + nvdec) | `nvenc` (h265parse + nvenc) |
| **NVIDIA NVDEC** | VP9 | `nvdec` (vp9parse + nvdec) | — |
| **NVIDIA NVDEC** | AV1 | `nvdec` (av1parse + nvdec) | — |
| **CPU** | H.264 | `avdec_h264` | `x264enc` |
| **CPU** | H.265/HEVC | `avdec_h265` | `x265enc` |
| **CPU** | VP9 | `avdec_vp9` | — |
| **CPU** | AV1 | `avdec_av1` (dav1d) | — |
| **CPU** | MPEG-4 | `avdec_mpeg4` | `avenc_mpeg4` |

**Pipeline GStreamer conceptual:**
```
source → demuxer → parser → decoder → videoconvert → videoscale → appsink
```

Ejemplo con AMD VCN para H.264:
```
filesrc location=video.mp4 → qtdemux → h264parse → vaapih264dec → videoconvert → videoscale ! video/x-raw,width=640,height=480 → appsink
```

### 5. Frame Extraction

Dos modos de extracción de frames:

**Por intervalo temporal (default):**
```bash
# Extraer un frame cada N segundos
bash scripts/gst-pipeline.sh \
  --source file \
  --input video.mp4 \
  --output ./frames \
  --interval 2.5  # cada 2.5 segundos
```

**Por keyframe (I-frames solamente):**
```bash
# Extraer solo keyframes (útil para scene detection)
bash scripts/gst-pipeline.sh \
  --source file \
  --input video.mp4 \
  --output ./frames \
  --keyframes-only
```

**Por scene change (detección de cambios de escena):**
```bash
# Extraer frame cuando cambia la escena (usando GStreamer scenechange)
bash scripts/gst-pipeline.sh \
  --source file \
  --input video.mp4 \
  --output ./frames \
  --scene-change
```

### 6. Preprocesamiento de Frames

Antes de la inferencia, los frames se preprocesan:

```python
# El script inference-pipeline.py hace esto automáticamente:
from PIL import Image
from torchvision import transforms

preprocess = transforms.Compose([
    transforms.Resize((640, 640)),           # Redimensionar
    transforms.ToTensor(),                    # Convertir a tensor
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],          # Normalizar ImageNet
        std=[0.229, 0.224, 0.225]
    ),
])
```

**Pipeline completo de preprocesamiento:**
1. **Decodificar** frame desde JPEG/PNG → RGB
2. **Redimensionar** manteniendo aspect ratio (letterbox)
3. **Normalizar** a [0,1] y restar media/desviación
4. **Mover a GPU** (`.to('cuda')`) para ROCm o CUDA
5. **Formato batch** para inferencia eficiente

### 7. Inferencia Batch con PyTorch/YOLO

```bash
# Inferencia batch con auto-backend detection
python3 scripts/inference-pipeline.py \
  --model yolov8x.pt \
  --input-dir ./frames \
  --output results.json \
  --batch-size 16 \
  --confidence 0.5 \
  --device auto
```

El script maneja tres modos de dispositivo:

```bash
# Forzar GPU AMD ROCm
python3 scripts/inference-pipeline.py --device cuda --model yolov8x.pt ...

# Forzar NVIDIA CUDA
python3 scripts/inference-pipeline.py --device cuda --model yolov8x.pt ...

# Forzar CPU
python3 scripts/inference-pipeline.py --device cpu --model yolov8n.pt ...

# Auto-detección (default)
python3 scripts/inference-pipeline.py --device auto --model yolov8x.pt ...
```

**Optimización de throughput — batch inference:**
```python
import torch
from ultralytics import YOLO

model = YOLO("yolov8x.pt")
device = "cuda:0" if torch.cuda.is_available() else "cpu"

# Batch inference — mayor throughput
results = model.predict(
    frame_batch,           # Lista de imágenes
    device=device,
    batch=16,              # Tamaño del batch
    verbose=False,
)
```

**Formatos de modelo soportados:**

| Formato | Descripción | AMD ROCm | NVIDIA CUDA | CPU |
|---------|-------------|:---------:|:-----------:|:---:|
| `.pt` (PyTorch) | Original ultralytics | ✅ | ✅ | ✅ |
| `.torchscript` | TorchScript export | ✅ | ✅ | ✅ |
| `.onnx` | ONNX universal | ✅ (MIGraphX) | ✅ (TensorRT) | ✅ |
| `.engine` | TensorRT (NVIDIA) | ❌ | ✅ | ❌ |

### 8. Post-procesamiento: Bounding Boxes y Tracking

```python
# El script inference-pipeline.py produce JSON con detecciones por frame
{
  "metadata": {
    "model": "yolov8x.pt",
    "backend": "rocm",
    "device": "AMD Instinct MI300X",
    "total_frames": 150,
    "fps": 45.2
  },
  "detections": [
    {
      "frame": "frame_0001.jpg",
      "timestamp_s": 0.0,
      "objects": [
        {
          "class": "person",
          "confidence": 0.92,
          "bbox": [120, 45, 320, 580],
          "track_id": 1
        },
        {
          "class": "car",
          "confidence": 0.87,
          "bbox": [400, 200, 600, 350],
          "track_id": null
        }
      ]
    }
  ]
}
```

**Post-processing pipeline (dentro de scripts/inference-pipeline.py):**
1. Filtrar detecciones por `confidence`
2. Non-Maximum Suppression (NMS) para eliminar duplicados
3. Asignar track IDs (seguimiento simple entre frames)
4. Escalar bounding boxes a coordenadas originales
5. Serializar a JSON

### 9. Output: Video Anotado y RTMP Push

**Video anotado con detecciones overlay:**
```bash
# Usar GStreamer para overlays en tiempo real
# (Requiere compositor + cairo o OpenCV)
python3 -c "
import cv2
import json

with open('results.json') as f:
    data = json.load(f)

cap = cv2.VideoCapture('video.mp4')
out = cv2.VideoWriter('annotated.mp4',
    cv2.VideoWriter_fourcc(*'mp4v'), 30, (1280, 720))

for det in data['detections']:
    ret, frame = cap.read()
    if not ret: break
    for obj in det['objects']:
        x1, y1, x2, y2 = obj['bbox']
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f\"{obj['class']} {obj['confidence']:.2f}\"
        cv2.putText(frame, label, (x1, y1-10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    out.write(frame)

cap.release(); out.release()
"
```

**Push a RTMP streaming:**
```bash
# Pipeline GStreamer con overlays + RTMP push
gst-launch-1.0 \
  filesrc location=video.mp4 ! qtdemux ! h264parse ! vaapih264dec ! \
  videoconvert ! \
  compositor name=comp \
    sink_0::xpos=0 sink_0::ypos=0 ! \
    videoconvert ! x264enc ! flvmux ! rtmpsink location='rtmp://live.example.com/stream' \
  filesrc location=overlay.png ! pngdec ! comp.
```

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/gstreamer-guide.md](references/gstreamer-guide.md) | Guía completa de GStreamer con ROCm: elementos, pipelines, RTSP, integración Python |
| [references/video-codecs.md](references/video-codecs.md) | Tabla de codecs y compatibilidad por backend (AMD VCN, NVIDIA NVDEC, CPU) |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/gst-pipeline.sh` | Pipeline GStreamer: captura + decode + frame extraction multi-backend. Soporta RTSP, file, camera. Extracción por intervalo, keyframe o scene change. |
| `scripts/inference-pipeline.py` | Inferencia batch sobre frames extraídos con detección automática de backend. YOLO/ONNX/PyTorch, output JSON, tracking simple. |
| `scripts/detect-backend.sh` | Detección de backend de video acceleration: AMD VCN (vaapi), NVIDIA NVDEC (nvdec), CPU (avdec). Reporta decodificadores, codificadores, codecs soportados. |

## Common Issues

### 1. "VCN no disponible" / "VAAPI element not found"

**Síntoma:** `gst-inspect-1.0 vaapih264dec` no encuentra el elemento. O `vainfo` reporta "libva error: /usr/lib/x86_64-linux-gnu/dri/*.so initialisation failed".

**Causa:** El driver VAAPI para AMD no está instalado o no es compatible con la GPU.

**Solución:**
```bash
# Verificar GPU soportada
lspci | grep -E "VGA|Display" | grep -i amd

# Instalar driver VAAPI (Mesa)
sudo apt install -y mesa-va-drivers

# O driver ROCm VAAPI
sudo apt install -y rocm-vaapi-driver

# Verificar
vainfo
gst-inspect-1.0 vaapih264dec
```

Si vainfo falla con "initialisation failed", probar:
```bash
# Forzar driver Intel (a veces funciona en APUs AMD)
export LIBVA_DRIVER_NAME=iHD
vainfo

# O forzar driver AMD
export LIBVA_DRIVER_NAME=radeonsi
vainfo
```

### 2. Decodificación falla con "No such element" en RTSP

**Síntoma:** `gst-launch-1.0 rtspsrc ...` falla con "WARNING: erroneous pipeline: no element 'rtspsrc'" o similar.

**Causa:** Faltan plugins GStreamer (gst-plugins-good o gst-plugins-bad).

**Solución:**
```bash
# Instalar todos los plugins
sudo apt install -y \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly \
  gstreamer1.0-libav

# Verificar elementos específicos
gst-inspect-1.0 rtspsrc   # Debe existir
gst-inspect-1.0 rtph264depay
gst-inspect-1.0 rtspclientsink
```

### 3. GPU Out of Memory (OOM) durante inferencia

**Síntoma:** `torch.cuda.OutOfMemoryError: CUDA out of memory` o error similar en ROCm.

**Causa:** El batch size es demasiado grande para la VRAM disponible, o el modelo es muy grande (YOLOv8x necesita ~7.2 GB).

**Solución:**
```bash
# Reducir batch size
python3 scripts/inference-pipeline.py \
  --batch-size 4 \
  --model yolov8x.pt \
  --input-dir ./frames \
  --output results.json

# Usar modelo más pequeño
python3 scripts/inference-pipeline.py \
  --model yolov8n.pt \
  --input-dir ./frames \
  --output results.json

# Forzar FP16 (reduce VRAM ~50%)
python3 scripts/inference-pipeline.py \
  --model yolov8x.pt \
  --fp16 \
  --input-dir ./frames \
  --output results.json

# Liberar caché entre batches
python3 -c "
import torch
torch.cuda.empty_cache()
"
```

### 4. RTSP timeout / conexión fallida

**Síntoma:** GStreamer se queda colgado en "Trying to connect to RTSP server..." y nunca se conecta, o la conexión se cae después de un tiempo.

**Causa:** Timeout por defecto de GStreamer es muy largo, RTSP server no responde, o problemas de red.

**Solución:**
```bash
# Pipeline con timeout explícito y reconexión
gst-launch-1.0 \
  rtspsrc location="rtsp://user:pass@192.168.1.100:554/stream1" \
    timeout=0 \
    buffer-mode=0 \
    latency=2000 \
    drop-on-latency=true \
    retransmission-retry-timeout=50 \
  ! rtph264depay \
  ! h264parse \
  ! vaapih264dec \
  ! videoconvert \
  ! appsink name=sink

# Probar conexión básica primero
ffprobe -rtsp_transport tcp "rtsp://user:pass@192.168.1.100:554/stream1"

# Forzar transporte TCP (más estable que UDP)
gst-launch-1.0 rtspsrc location="rtsp://..." protocols=tcp ! ...
```

En `scripts/gst-pipeline.sh`, usar `--rtsp-transport tcp`:
```bash
bash scripts/gst-pipeline.sh \
  --source rtsp \
  --input "rtsp://..." \
  --rtsp-transport tcp \
  --output ./frames
```

### 5. Frame drop excesivo / baja tasa de inferencia

**Síntoma:** La inferencia no alcanza el framerate del video de entrada, se acumulan frames, o muchos frames saltados.

**Causa:** La GPU de inferencia no da abasto para el framerate / resolución / batch size actual.

**Solución:**
```bash
# Reducir resolución de frames extraídos
bash scripts/gst-pipeline.sh \
  --source file \
  --input video.mp4 \
  --width 320 \
  --height 240 \
  --output ./frames

# Aumentar intervalo entre frames
bash scripts/gst-pipeline.sh \
  --source file \
  --input video.mp4 \
  --interval 5  # Frame cada 5 segundos

# Batch inference + FP16
python3 scripts/inference-pipeline.py \
  --batch-size 16 \
  --fp16 \
  --input-dir ./frames

# Skipping adaptativo: si la cola de frames crece, saltar frames
export GST_DEBUG=*appsink*:5
```

### 6. VAAPI vs VCN — confusión de backends

**Síntoma:** `gst-inspect-1.0 vaapih264dec` existe pero la decodificación falla, o `vainfo` reporta "Driver not found" a pesar de tener GPU AMD.

**Causa:** VAAPI es la interfaz, VCN es el hardware. No todos los drivers VAAPI usan VCN. Hay dos drivers principales: `radeonsi` (Mesa, para GPUs gráficas) y `amdgpu` (ROCm VAAPI, para GPUs compute). Además, `rocm-vaapi-driver` es un driver experimental.

**Solución:**

| Driver | GPU compatible | Instalación | Notas |
|--------|---------------|-------------|-------|
| `radeonsi` (Mesa) | RX 7900, RX 9070, APUs | `apt install mesa-va-drivers` | Recomendado para GPUs gráficas AMD |
| `amdgpu` (ROCm VAAPI) | MI300X, MI250 | `apt install rocm-vaapi-driver` | Recomendado para GPUs compute AMD |
| `iHD` (Intel) | No AMD | `apt install intel-media-va-driver` | Solo Intel, no usar en AMD |

**Diagnóstico:**
```bash
# Ver qué driver VAAPI está usando
vainfo 2>&1 | head -5

# Ver elementos VAAPI disponibles
gst-inspect-1.0 vaapi 2>/dev/null | head -20

# Probar decodificación directa
gst-launch-1.0 filesrc location=video.h264 ! h264parse ! vaapih264dec ! videoconvert ! fakesink
```

**Soluciones rápidas:**
```bash
# Probar driver radeonsi
export LIBVA_DRIVER_NAME=radeonsi
vainfo
gst-launch-1.0 filesrc location=video.h264 ! h264parse ! vaapih264dec ! fakesink

# Probar driver amdgpu (ROCm)
export LIBVA_DRIVER_NAME=amdgpu
vainfo

# Si nada funciona, fallback a CPU
bash scripts/gst-pipeline.sh --backend cpu ...
```

### 7. Error "caps not negotiated" en pipeline GStreamer

**Síntoma:** GStreamer lanza "WARNING: erroneous pipeline: could not link elements" o "Internal data stream error: caps not negotiated".

**Causa:** Los formatos de salida de un elemento no son compatibles con la entrada del siguiente elemento en el pipeline.

**Solución:** Insertar `videoconvert` y `capsfilter` entre elementos:
```bash
# ❌ Pipeline sin conversión (puede fallar)
gst-launch-1.0 filesrc ! qtdemux ! h264parse ! vaapih264dec ! appsink

# ✅ Pipeline con videoconvert + capsfilter
gst-launch-1.0 filesrc location=video.mp4 ! \
  qtdemux ! h264parse ! vaapih264dec ! \
  videoconvert ! videoscale ! \
  video/x-raw,width=640,height=480,format=RGB ! \
  appsink name=sink
```

### 8. Decodificación HEVC/H.265 falla en AMD VCN

**Síntoma:** `vaapih265dec` no existe o falla al decodificar video H.265.

**Causa:** No todas las GPUs AMD soportan decodificación H.265 por hardware. Las GPUs GCN (antiguas) no tienen VCN.

**Solución:**
```bash
# Verificar soporte VCN para HEVC
gst-inspect-1.0 vaapih265dec  # Si no existe, no hay soporte HW

# Ver dispositivos VCN
ls /dev/dri/
cat /sys/class/drm/card0/device/vendor  # 0x1002 = AMD

# Usar CPU fallback para HEVC si no hay soporte HW
bash scripts/gst-pipeline.sh --backend cpu ...
```

## Technical Notes

- **`torch.cuda` API funciona en ROCm y CUDA**: No hay `torch.rocm`. Usar `torch.version.hip` para detectar AMD ROCm, `torch.version.cuda` para NVIDIA CUDA.
- **Ultralytics + GStreamer**: Ultralytics YOLO puede recibir frames directamente como numpy arrays (vía `appsink`), sin necesidad de archivos intermedios.
- **Buffer management**: En pipelines en tiempo real, usar `drop-on-latency=true` para evitar acumulación de frames si la inferencia va más lenta que el video.
- **Multi-GPU**: Los scripts soportan múltiples GPUs. Usar `HIP_VISIBLE_DEVICES=0,1` (AMD) o `CUDA_VISIBLE_DEVICES=0,1` (NVIDIA) para seleccionar GPUs específicas.
- **VCN decodifica en GPU, inferencia en GPU**: Ambos ocurren en la misma GPU, compitiendo por VRAM. Monitorear con `rocm-smi` (AMD) o `nvidia-smi` (NVIDIA).

## Related Skills

- [`yolo-rocm-deploy`](../yolo-rocm-deploy/SKILL.md) — YOLO object detection on ROCm/CUDA
- [`vlm-rocm-inference`](../vlm-rocm-inference/SKILL.md) — Direct PyTorch VLM inference on ROCm/CUDA
- [`ppe-detection-pipeline`](../ppe-detection-pipeline/SKILL.md) — PPE detection for mining safety
