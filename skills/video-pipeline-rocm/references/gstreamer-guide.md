# GStreamer Guide for ROCm / CUDA Video Pipelines

Guía completa de elementos GStreamer para construir pipelines de captura,
decodificación, procesamiento y codificación de video con aceleración hardware
en **AMD ROCm (VAAPI/VCN)**, **NVIDIA CUDA (NVDEC/NVENC)** y **CPU software**.

---

## 1. Elementos GStreamer por Backend

### 1.1 AMD ROCm — VAAPI / VCN

Elementos de decodificación y codificación acelerada por hardware en GPUs AMD
con VCN (Video Core Next) via VAAPI.

| Operación | Codec | Elemento GStreamer | Plugin |
|-----------|-------|-------------------|--------|
| **Decode** | H.264 | `vaapih264dec` | gstreamer1.0-vaapi |
| **Decode** | H.265 / HEVC | `vaapih265dec` | gstreamer1.0-vaapi |
| **Decode** | VP8 | `vaapivp8dec` | gstreamer1.0-vaapi |
| **Decode** | VP9 | `vaapivp9dec` | gstreamer1.0-vaapi |
| **Decode** | MPEG-2 | `vaapimpeg2dec` | gstreamer1.0-vaapi |
| **Decode** | AV1 | `vaapiav1dec` | gstreamer1.0-vaapi (experimental) |
| **Encode** | H.264 | `vaapih264enc` | gstreamer1.0-vaapi |
| **Encode** | H.265 / HEVC | `vaapih265enc` | gstreamer1.0-vaapi |
| **Encode** | VP8 | `vaapivp8enc` | gstreamer1.0-vaapi |
| **Encode** | JPEG | `vaapijpegenc` | gstreamer1.0-vaapi |
| **Postproc** | Deinterlace | `vaapideinterlace` | gstreamer1.0-vaapi |
| **Postproc** | Denoise | `vaapipostproc` | gstreamer1.0-vaapi |

**Elementos adicionales AMD (AMF — Advanced Media Framework):**

| Operación | Codec | Elemento GStreamer | Plugin |
|-----------|-------|-------------------|--------|
| **Decode** | H.264 | `amfh264dec` | gstreamer1.0-amf |
| **Decode** | H.265 / HEVC | `amfh265dec` | gstreamer1.0-amf |
| **Encode** | H.264 | `amfh264enc` | gstreamer1.0-amf |
| **Encode** | H.265 / HEVC | `amfh265enc` | gstreamer1.0-amf |
| **Encode** | AV1 | `amfav1enc` | gstreamer1.0-amf (experimental) |

> **Nota**: AMF es la capa de aceleración multimedia de AMD. VAAPI es más
> comúnmente usado en Linux. En Windows, AMF es el estándar.

### 1.2 NVIDIA CUDA — NVDEC / NVENC

| Operación | Codec | Elemento GStreamer | Plugin |
|-----------|-------|-------------------|--------|
| **Decode** | H.264 | `nvdec` (vía `h264parse ! nvdec`) | gstreamer1.0-plugins-bad |
| **Decode** | H.265 / HEVC | `nvdec` (vía `h265parse ! nvdec`) | gstreamer1.0-plugins-bad |
| **Decode** | VP8 | `nvdec` (vía `vp8parse ! nvdec`) | gstreamer1.0-plugins-bad |
| **Decode** | VP9 | `nvdec` (vía `vp9parse ! nvdec`) | gstreamer1.0-plugins-bad |
| **Decode** | AV1 | `nvdec` (vía `av1parse ! nvdec`) | gstreamer1.0-plugins-bad |
| **Decode** | MPEG-2 | `nvdec` (vía `mpeg2parse ! nvdec`) | gstreamer1.0-plugins-bad |
| **Encode** | H.264 | `nvenc` (vía `h264parse ! nvenc`) | gstreamer1.0-plugins-bad |
| **Encode** | H.265 / HEVC | `nvenc` (vía `h265parse ! nvenc`) | gstreamer1.0-plugins-bad |
| **Encode** | AV1 | `nvenc` (vía `av1parse ! nvenc`) | gstreamer1.0-plugins-bad |

> **Nota**: Los elementos `nvdec` y `nvenc` son wrappers del NVIDIA Video Codec
> SDK. Requieren drivers 535+ y tarjeta con Turing o posterior para AV1.

### 1.3 CPU Software Decode

| Operación | Codec | Elemento GStreamer | Plugin |
|-----------|-------|-------------------|--------|
| **Decode** | H.264 | `avdec_h264` | gstreamer1.0-libav |
| **Decode** | H.265 / HEVC | `avdec_h265` | gstreamer1.0-libav |
| **Decode** | VP9 | `avdec_vp9` | gstreamer1.0-libav |
| **Decode** | AV1 | `avdec_av1` | gstreamer1.0-libav (dav1d) |
| **Decode** | MPEG-4 | `avdec_mpeg4` | gstreamer1.0-libav |
| **Decode** | MPEG-2 | `avdec_mpeg2` | gstreamer1.0-libav |
| **Encode** | H.264 | `x264enc` | gstreamer1.0-plugins-ugly |
| **Encode** | H.265 / HEVC | `x265enc` | gstreamer1.0-plugins-bad |
| **Encode** | VP8 | `vp8enc` | gstreamer1.0-plugins-good |
| **Encode** | VP9 | `vp9enc` | gstreamer1.0-plugins-bad |
| **Encode** | AV1 | `av1enc` | gstreamer1.0-plugins-bad (experimental) |
| **Encode** | MPEG-4 | `avenc_mpeg4` | gstreamer1.0-libav |

### 1.4 Elementos Universales

| Elemento | Propósito | Plugin |
|----------|-----------|--------|
| `videoconvert` | Conversión entre formatos de color (RGB ↔ YUV) | gstreamer1.0-plugins-base |
| `videoscale` | Redimensionamiento de video | gstreamer1.0-plugins-base |
| `videorate` | Cambio de framerate / intervalado | gstreamer1.0-plugins-base |
| `capsfilter` | Filtro de capacidades (negociación de formato) | gstreamer1.0-plugins-base |
| `appsink` | Consumer de frames en aplicaciones Python/C | gstreamer1.0-plugins-base |
| `appsrc` | Producer de frames desde aplicaciones Python/C | gstreamer1.0-plugins-base |
| `fakesink` | Sink dummy para debugging | gstreamer1.0-plugins-base |
| `identity` | Debug/control de flujo de datos | gstreamer1.0-plugins-base |
| `tee` | Split de flujo en múltiples destinos | gstreamer1.0-plugins-base |
| `queue` | Buffer / cola entre elementos | gstreamer1.0-plugins-base |
| `multifilesink` | Guardar cada frame a un archivo separado | gstreamer1.0-plugins-good |
| `jpegenc` | Codificador JPEG | gstreamer1.0-plugins-good |
| `pngenc` | Codificador PNG | gstreamer1.0-plugins-good |
| `compositor` | Composición de múltiples flujos de video | gstreamer1.0-plugins-good |
| `textoverlay` | Superposición de texto en video | gstreamer1.0-plugins-base |
| `scenechange` | Detección de cambio de escena | gstreamer1.0-plugins-bad |

---

## 2. Pipeline Patterns

### 2.1 Captura + Decode + Appsink (para Python)

**Archivo local con AMD VCN:**
```
gst-launch-1.0 \
  filesrc location=video.mp4 ! \
  qtdemux ! \
  h264parse ! \
  vaapih264dec ! \
  videoconvert ! \
  videoscale ! \
  video/x-raw,width=640,height=480,format=RGB ! \
  appsink name=sink
```

**Archivo local con NVIDIA NVDEC:**
```
gst-launch-1.0 \
  filesrc location=video.mp4 ! \
  qtdemux ! \
  h264parse ! \
  nvdec ! \
  videoconvert ! \
  videoscale ! \
  video/x-raw,width=640,height=480,format=RGB ! \
  appsink name=sink
```

**CPU fallback:**
```
gst-launch-1.0 \
  filesrc location=video.mp4 ! \
  qtdemux ! \
  h264parse ! \
  avdec_h264 ! \
  videoconvert ! \
  videoscale ! \
  video/x-raw,width=640,height=480,format=RGB ! \
  appsink name=sink
```

### 2.2 RTSP Source

**RTSP + AMD VCN + Frame Extraction:**
```
gst-launch-1.0 \
  rtspsrc location="rtsp://user:pass@192.168.1.100:554/stream1" \
    protocols=tcp latency=2000 drop-on-latency=true timeout=0 ! \
  rtph264depay ! \
  h264parse ! \
  vaapih264dec ! \
  videoconvert ! \
  videorate ! \
  video/x-raw,framerate=1/1 ! \
  jpegenc ! \
  multifilesink location="frames/frame_%05d.jpg" index=1
```

**RTSP con autenticación:**
```
gst-launch-1.0 \
  rtspsrc location="rtsp://admin:password@192.168.1.100:554/stream1" \
    protocols=tcp latency=1000 ! \
  rtph264depay ! \
  h264parse ! \
  avdec_h264 ! \
  videoconvert ! \
  fakesink
```

**RTSP con transporte UDP (menor latencia, menos fiable):**
```
gst-launch-1.0 \
  rtspsrc location="rtsp://192.168.1.100:554/stream1" \
    protocols=udp latency=500 ! \
  rtph264depay ! \
  h264parse ! \
  vaapih264dec ! \
  videoconvert ! \
  fakesink
```

### 2.3 Camera Source (v4l2)

**Cámara USB/CSI + AMD VCN encode:**
```
gst-launch-1.0 \
  v4l2src device=/dev/video0 ! \
  video/x-raw,width=1280,height=720,framerate=30/1 ! \
  videoconvert ! \
  vaapih264enc ! \
  mp4mux ! \
  filesink location=output.mp4
```

**Cámara + frame extraction:**
```
gst-launch-1.0 \
  v4l2src device=/dev/video0 ! \
  video/x-raw,width=640,height=480 ! \
  videoconvert ! \
  videorate ! \
  video/x-raw,framerate=1/2 ! \
  jpegenc ! \
  multifilesink location="frames/frame_%05d.jpg" index=1
```

### 2.4 Transcodificación

**H.264 → H.265 con AMD VCN:**
```
gst-launch-1.0 \
  filesrc location=input.mp4 ! \
  qtdemux ! \
  h264parse ! \
  vaapih264dec ! \
  videoconvert ! \
  vaapih265enc ! \
  mp4mux ! \
  filesink location=output.mp4
```

**H.264 → H.265 con NVIDIA NVENC:**
```
gst-launch-1.0 \
  filesrc location=input.mp4 ! \
  qtdemux ! \
  h264parse ! \
  nvdec ! \
  videoconvert ! \
  nvenc ! \
  h265parse ! \
  mp4mux ! \
  filesink location=output.mp4
```

**Transcodificación por software:**
```
gst-launch-1.0 \
  filesrc location=input.mp4 ! \
  qtdemux ! \
  h264parse ! \
  avdec_h264 ! \
  videoconvert ! \
  x265enc ! \
  mp4mux ! \
  filesink location=output.mp4
```

### 2.5 Frame Extraction Estratégica

**Por keyframe (I-frames):**
Extrae solo los frames completos (I-frames), útil para scene detection sin
elementos adicionales:
```
gst-launch-1.0 \
  filesrc location=video.mp4 ! \
  qtdemux ! \
  h264parse ! \
  vaapih264dec ! \
  videoconvert ! \
  videorate ! \
  capsfilter caps=video/x-raw,framerate=0/1 ! \
  jpegenc ! \
  multifilesink location="frame_%05d.jpg"
```

**Por scene change (usando elemento scenechange):**
```
gst-launch-1.0 \
  filesrc location=video.mp4 ! \
  qtdemux ! \
  h264parse ! \
  avdec_h264 ! \
  videoconvert ! \
  scenechange threshold=3000000 ! \
  jpegenc ! \
  multifilesink location="scene_%05d.jpg"
```

---

## 3. RTSP Examples con Autenticación

### 3.1 RTSP Simple
```bash
gst-launch-1.0 rtspsrc location="rtsp://192.168.1.100:554/stream1" \
  protocols=tcp ! rtph264depay ! h264parse ! vaapih264dec ! \
  videoconvert ! fakesink
```

### 3.2 RTSP con Usuario y Contraseña
```bash
gst-launch-1.0 rtspsrc location="rtsp://admin:pass123@192.168.1.100:554/stream1" \
  protocols=tcp latency=2000 ! rtph264depay ! h264parse ! avdec_h264 ! \
  videoconvert ! fakesink
```

### 3.3 RTSP con Transporte TCP (recomendado)
```bash
gst-launch-1.0 rtspsrc location="rtsp://admin:pass@192.168.1.100:554/h264/ch1/main/av_stream" \
  protocols=tcp latency=1000 drop-on-latency=true ! \
  rtph264depay ! h264parse ! vaapih264dec ! videoconvert ! \
  videoscale ! video/x-raw,width=640,height=480 ! \
  jpegenc ! multifilesink location="frame_%05d.jpg"
```

### 3.4 RTSP con Reconexión Automática
```bash
# Usando un script wrapper para reconexión:
gst-launch-1.0 \
  rtspsrc location="rtsp://admin:pass@192.168.1.100:554/stream1" \
    protocols=tcp latency=2000 drop-on-latency=true timeout=0 \
    retransmission-retry-timeout=50 ! \
  rtph264depay ! h264parse ! vaapih264dec ! \
  videoconvert ! fakesink
```

### 3.5 RTSP Push (enviar streaming a servidor RTMP)
```bash
gst-launch-1.0 \
  rtspsrc location="rtsp://admin:pass@camera:554/stream1" protocols=tcp ! \
  rtph264depay ! h264parse ! vaapih264dec ! videoconvert ! \
  videoscale ! video/x-raw,width=1280,height=720 ! \
  vaapih264enc ! \
  flvmux ! \
  rtmpsink location="rtmp://live.example.com/stream/mykey"
```

---

## 4. Integración con Python via Gst Python Bindings (gi)

### 4.1 Básico: appsink para recibir frames

```python
#!/usr/bin/env python3
"""
Ejemplo: Recibir frames de GStreamer en Python via appsink.
Compatible con AMD VCN, NVIDIA NVDEC y CPU.
"""
import sys

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib

Gst.init(None)

# Pipeline: file source → decode → videoconvert → appsink
pipeline_str = (
    "filesrc location=video.mp4 ! "
    "qtdemux ! "
    "h264parse ! "
    "vaapih264dec ! "     # Cambiar a nvdec o avdec_h264 según backend
    "videoconvert ! "
    "videoscale ! "
    "video/x-raw,width=640,height=480,format=RGB ! "
    "appsink name=sink emit-signals=true max-buffers=1 drop=true"
)

pipeline = Gst.parse_launch(pipeline_str)
appsink = pipeline.get_by_name("sink")

# Callback cuando hay un frame nuevo
def on_new_sample(sink):
    sample = sink.emit("pull-sample")
    if sample:
        buffer = sample.get_buffer()
        # Procesar buffer (numpy array)
        # caps = sample.get_caps()
        # print(f"Frame recibido: {buffer.get_size()} bytes")
        return Gst.FlowReturn.OK
    return Gst.FlowReturn.ERROR

appsink.connect("new-sample", on_new_sample)

# Iniciar pipeline
pipeline.set_state(Gst.State.PLAYING)

# Loop principal
loop = GLib.MainLoop()
try:
    loop.run()
except KeyboardInterrupt:
    pass
finally:
    pipeline.set_state(Gst.State.NULL)
```

### 4.2 Frame extraction con numpy

```python
#!/usr/bin/env python3
"""
Extraer frames como arrays numpy para usar con OpenCV / PyTorch.
"""
import numpy as np

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")
from gi.repository import Gst, GstApp

Gst.init(None)

def create_pipeline(backend="amd", width=640, height=480):
    """Crea pipeline según backend."""
    decoders = {
        "amd": "vaapih264dec",
        "nvidia": "nvdec",
        "cpu": "avdec_h264",
    }
    decoder = decoders.get(backend, "avdec_h264")

    pipeline_str = (
        f"filesrc location=video.mp4 ! "
        f"qtdemux ! h264parse ! {decoder} ! "
        f"videoconvert ! videoscale ! "
        f"video/x-raw,width={width},height={height},format=RGB ! "
        f"appsink name=sink"
    )
    return Gst.parse_launch(pipeline_str)

def get_frame(appsink, timeout=1_000_000_000):
    """Obtiene un frame como numpy array."""
    sample = appsink.try_pull_sample(timeout)
    if not sample:
        return None

    buffer = sample.get_buffer()
    caps = sample.get_caps()
    structure = caps.get_structure(0)

    width = structure.get_value("width")
    height = structure.get_value("height")

    # Mapear buffer a numpy array
    success, map_info = buffer.map(Gst.MapFlags.READ)
    if not success:
        return None

    frame = np.ndarray(
        shape=(height, width, 3),
        dtype=np.uint8,
        buffer=map_info.data,
    ).copy()

    buffer.unmap(map_info)
    return frame

# Uso
pipeline = create_pipeline("amd")
pipeline.set_state(Gst.State.PLAYING)

appsink = pipeline.get_by_name("sink")

# Extraer frames e inferir
frame = get_frame(appsink)
while frame is not None:
    # frame es un numpy array (H, W, 3) — listo para PyTorch/OpenCV
    # results = model.predict(frame)
    print(f"Frame shape: {frame.shape}")

    frame = get_frame(appsink, timeout=500_000_000)  # 500ms timeout

pipeline.set_state(Gst.State.NULL)
```

### 4.3 Pipeline completo appsink → PyTorch inference

```python
#!/usr/bin/env python3
"""
Pipeline GStreamer + PyTorch: decode → appsink → inferencia → resultados
"""
import numpy as np
import torch
from ultralytics import YOLO

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")
from gi.repository import Gst, GstApp

Gst.init(None)

# Configuración
BACKEND = "auto"  # auto, amd, nvidia, cpu
MODEL_PATH = "yolov8x.pt"
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

# Detectar backend GStreamer
if BACKEND == "auto":
    if Gst.ElementFactory.find("vaapih264dec"):
        BACKEND = "amd"
    elif Gst.ElementFactory.find("nvdec"):
        BACKEND = "nvidia"
    else:
        BACKEND = "cpu"

print(f"Backend GStreamer: {BACKEND}")
print(f"Device PyTorch:    {DEVICE}")

# Pipeline builder
decoder_map = {
    "amd": "vaapih264dec",
    "nvidia": "nvdec",
    "cpu": "avdec_h264",
}
decoder = decoder_map.get(BACKEND, "avdec_h264")

pipeline_str = (
    "filesrc location=video.mp4 ! "
    "qtdemux ! h264parse ! "
    f"{decoder} ! "
    "videoconvert ! videoscale ! "
    "video/x-raw,width=640,height=480,format=RGB ! "
    "appsink name=sink max-buffers=1 drop=true"
)

# Crear pipeline
pipeline = Gst.parse_launch(pipeline_str)
appsink = pipeline.get_by_name("sink")

# Cargar modelo
model = YOLO(MODEL_PATH)

# Procesar frames
pipeline.set_state(Gst.State.PLAYING)

frame_count = 0
while True:
    sample = appsink.try_pull_sample(1_000_000_000)
    if not sample:
        break

    buffer = sample.get_buffer()
    caps = sample.get_caps()
    structure = caps.get_structure(0)
    width = structure.get_value("width")
    height = structure.get_value("height")

    success, map_info = buffer.map(Gst.MapFlags.READ)
    if not success:
        continue

    frame = np.ndarray(
        shape=(height, width, 3),
        dtype=np.uint8,
        buffer=map_info.data,
    ).copy()
    buffer.unmap(map_info)

    # Inferencia
    results = model.predict(frame, device=DEVICE, verbose=False)
    detections = results[0].boxes.data.cpu().numpy() if len(results) > 0 else []

    frame_count += 1
    if frame_count % 30 == 0:
        print(f"Frame {frame_count}: {len(detections)} detecciones")

pipeline.set_state(Gst.State.NULL)
print(f"Procesados {frame_count} frames")
```

---

## 5. Codecs Soportados por VCN

AMD Video Core Next (VCN) — presente en GPUs AMD desde la serie RX 5000 (Navi)
y todas las GPUs Instinct MI series.

| Codec | Decode | Encode | VCN Generation | Resolución Máxima |
|-------|:------:|:------:|----------------|:-----------------:|
| H.264 (AVC) | ✅ | ✅ | VCN 1.0+ | 4K @ 60fps (VCN 1.0) / 8K (VCN 3.0+) |
| H.265 (HEVC) 8-bit | ✅ | ✅ | VCN 1.0+ | 4K (VCN 1.0) / 8K (VCN 3.0+) |
| H.265 (HEVC) 10-bit | ✅ | ✅ | VCN 2.0+ | 4K / 8K |
| VP9 8-bit | ✅ | ❌ | VCN 2.0+ | 4K (VCN 2.0) / 8K (VCN 3.0+) |
| VP9 10-bit | ✅ | ❌ | VCN 3.0+ | 8K |
| AV1 8-bit | ✅ | ❌ | VCN 3.0+ (RX 6000+) | 8K |
| AV1 10-bit | ✅ | ❌ | VCN 4.0+ (RX 7000+) | 8K |
| MPEG-2 | ✅ | ❌ | VCN 1.0+ | 1080p |
| MPEG-4 (ASP) | ✅ | ❌ | VCN 1.0+ | 1080p |
| VC-1 | ✅ | ❌ | VCN 1.0+ | 1080p |
| JPEG/MJPEG | ✅ | ✅ | VCN 1.0+ | 16K |

### GPUs y su generación VCN:

| Serie AMD | Arquitectura | VCN Generation |
|-----------|--------------|:--------------:|
| RX 5000 (Navi 10/14) | RDNA 1 | VCN 2.0 |
| RX 6000 (Navi 21/22/23) | RDNA 2 | VCN 3.0 |
| RX 7000 (Navi 31/32/33) | RDNA 3 | VCN 4.0 |
| RX 9070 (Navi 48) | RDNA 4 | VCN 5.0 |
| MI100 | CDNA 1 | VCN 1.0 |
| MI250 | CDNA 2 | VCN 2.0 |
| MI300X | CDNA 3 | VCN 3.0 |

---

## 6. Integración con NVIDIA NVDEC

### 6.1 Verificar soporte NVDEC
```bash
# Verificar GPU y driver
nvidia-smi

# Verificar elementos GStreamer NVDEC
gst-inspect-1.0 nvdec

# Verificar codecs soportados (NVIDIA)
nvidia-smi -q | grep -i "Encoder\|Decoder"

# Ver decodificadores disponibles
gst-inspect-1.0 nvdec | grep "application/x-h264\|application/x-h265\|application/x-vp9"
```

### 6.2 Limitaciones de NVDEC
- Una sesión NVDEC por GPU para la mayoría de GPUs consumer (RTX series)
- GPUs Tesla/Quadro/Enterprise soportan múltiples sesiones simultáneas
- NVIDIA limita NVENC a 3 sesiones concurrentes en GPUs consumer (2025+)
- AV1 decode solo en GPUs Turing (RTX 2000) y posteriores
- AV1 encode solo en GPUs Ada Lovelace (RTX 4000) y posteriores

---

## 7. Debugging y Logging

### 7.1 Variables de entorno GST_DEBUG
```bash
# Niveles de debug: 0 (none) a 9 (full)
export GST_DEBUG=3  # Nivel INFO general

# Debug específico para un elemento
export GST_DEBUG=*vaapi*:5,*appsink*:5

# Debug para RTSP
export GST_DEBUG=*rtspsrc*:5,*rtp*:5

# Debug para negociación de capacidades
export GST_DEBUG=*caps*:5,*negotiation*:5

# Mostrar leaks y memory
export GST_DEBUG=*memory*:5,*buffer*:5

# Log a archivo
export GST_DEBUG_FILE=/tmp/gst-debug.log
```

### 7.2 Comandos de diagnóstico
```bash
# Listar todos los elementos GStreamer
gst-inspect-1.0 | grep -i "dec\|enc" | sort

# Ver capacidades de un elemento
gst-inspect-1.0 vaapih264dec

# Probar pipeline simple
gst-launch-1.0 videotestsrc ! videoconvert ! fakesink

# Ver versión GStreamer
gst-launch-1.0 --version

# Verificar plugins VAAPI
gst-inspect-1.0 vaapi

# Probar decode de archivo
gst-launch-1.0 filesrc location=test.h264 ! h264parse ! avdec_h264 ! fakesink -v
```

---

## 8. Referencias

- [GStreamer Documentation](https://gstreamer.freedesktop.org/documentation/)
- [GStreamer VAAPI](https://github.com/intel/gstreamer-vaapi)
- [ROCm VAAPI Driver](https://github.com/ROCm/ROCm-VAAPI-Driver)
- [NVIDIA Video Codec SDK](https://developer.nvidia.com/video-codec-sdk)
- [GStreamer Python Bindings](https://gstreamer.freedesktop.org/documentation/gstreamer-1.0/gi-reference.html)
- [AMD VCN Documentation](https://github.com/HandBrake/HandBrake/wiki/AMD-VCN-Guide)
