# Video Codec Compatibility Reference

Tabla completa de codecs de video y qué backend los soporta para decodificación
y codificación acelerada por hardware (AMD VCN, NVIDIA NVDEC/NVENC) y software (CPU).

---

## 1. Tabla Resumen por Codec

| Codec | Nombre Completo | AMD VCN | NVIDIA NVDEC | NVIDIA NVENC | CPU (Software) |
|-------|-----------------|:-------:|:------------:|:------------:|:--------------:|
| **H.264** | AVC (Advanced Video Coding) | ✅ Dec/Enc | ✅ Dec | ✅ Enc | ✅ Dec/Enc |
| **H.265** | HEVC (High Efficiency Video Coding) | ✅ Dec/Enc | ✅ Dec | ✅ Enc | ✅ Dec/Enc |
| **VP9** | Google VP9 | ✅ Solo Dec | ✅ Dec | ❌ | ✅ Dec |
| **AV1** | Alliance for Open Media AV1 | ✅ Solo Dec | ✅ Dec (Turing+) | ✅ Enc (Ada+) | ✅ Dec/Enc (slow) |
| **MPEG-2** | MPEG-2 Video | ✅ Solo Dec | ✅ Dec | ❌ | ✅ Dec/Enc |
| **MPEG-4** | MPEG-4 Part 2 (ASP/DivX/Xvid) | ✅ Solo Dec | ❌ | ❌ | ✅ Dec/Enc |
| **VC-1** | Windows Media Video | ✅ Solo Dec | ✅ Dec | ❌ | ✅ Dec |
| **VP8** | Google VP8 | ✅ Dec/Enc | ✅ Dec | ❌ | ✅ Dec/Enc |
| **MJPEG** | Motion JPEG | ✅ Dec/Enc | ❌ | ❌ | ✅ Dec/Enc |
| **WMV3** | Windows Media Video 9 | ❌ | ❌ | ❌ | ✅ Dec |

**Leyenda:**
- ✅ Dec = Decodificación acelerada por hardware
- ✅ Enc = Codificación acelerada por hardware
- ✅ Dec/Enc = Ambos soportados
- ❌ = No soportado

---

## 2. AMD VCN — Soporte Detallado

### 2.1 Codecs Soportados por Generación VCN

| Codec | VCN 1.0 (Vega/MI50) | VCN 2.0 (RDNA1) | VCN 3.0 (RDNA2) | VCN 4.0 (RDNA3) | VCN 5.0 (RDNA4) |
|-------|:-------------------:|:----------------:|:----------------:|:----------------:|:----------------:|
| **H.264 Dec** | ✅ 4K | ✅ 4K | ✅ 8K | ✅ 8K | ✅ 8K |
| **H.264 Enc** | ✅ 4K | ✅ 4K | ✅ 8K | ✅ 8K | ✅ 8K |
| **H.265 Dec 8-bit** | ✅ 4K | ✅ 4K | ✅ 8K | ✅ 8K | ✅ 8K |
| **H.265 Dec 10-bit** | ❌ | ✅ 4K | ✅ 8K | ✅ 8K | ✅ 8K |
| **H.265 Enc 8-bit** | ✅ 4K | ✅ 4K | ✅ 8K | ✅ 8K | ✅ 8K |
| **H.265 Enc 10-bit** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **VP9 Dec 8-bit** | ❌ | ✅ 4K | ✅ 8K | ✅ 8K | ✅ 8K |
| **VP9 Dec 10-bit** | ❌ | ❌ | ✅ 8K | ✅ 8K | ✅ 8K |
| **AV1 Dec 8-bit** | ❌ | ❌ | ✅ 8K | ✅ 8K | ✅ 8K |
| **AV1 Dec 10-bit** | ❌ | ❌ | ❌ | ✅ 8K | ✅ 8K |
| **AV1 Enc** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **MPEG-2 Dec** | ✅ 1080p | ✅ 1080p | ✅ 1080p | ✅ 1080p | ✅ 1080p |
| **MPEG-4 Dec** | ✅ 1080p | ✅ 1080p | ✅ 1080p | ✅ 1080p | ✅ 1080p |
| **VC-1 Dec** | ✅ 1080p | ✅ 1080p | ✅ 1080p | ✅ 1080p | ✅ 1080p |
| **VP8 Dec** | ✅ 4K | ✅ 4K | ✅ 4K | ✅ 4K | ✅ 4K |
| **VP8 Enc** | ✅ 1080p | ✅ 1080p | ✅ 1080p | ✅ 1080p | ✅ 1080p |
| **MJPEG Dec** | ✅ 16K | ✅ 16K | ✅ 16K | ✅ 16K | ✅ 16K |
| **MJPEG Enc** | ✅ 16K | ✅ 16K | ✅ 16K | ✅ 16K | ✅ 16K |

### 2.2 GPUs AMD y su VCN Generation

| GPU | Arquitectura | VCN Generation | Notas |
|-----|-------------|:--------------:|-------|
| **Instinct MI50** | Vega 20 (gfx906) | VCN 1.0 | Decodificación limitada a 4K |
| **Instinct MI100** | CDNA 1 (gfx908) | VCN 1.0 | Sin soporte VP9/AV1 |
| **Instinct MI250** | CDNA 2 (gfx90a) | VCN 2.0 | Soporte VP9, H.265 10-bit |
| **Instinct MI300X** | CDNA 3 (gfx942) | VCN 3.0 | Soporte AV1 decode, 8K |
| **Radeon RX 5000** | RDNA 1 (gfx1010) | VCN 2.0 | Buena cobertura codecs |
| **Radeon RX 6000** | RDNA 2 (gfx1030) | VCN 3.0 | AV1 decode, 8K |
| **Radeon RX 7000** | RDNA 3 (gfx1100) | VCN 4.0 | AV1 10-bit decode |
| **Radeon RX 9070** | RDNA 4 (gfx1201) | VCN 5.0 | AV1 encode, mejoras calidad |

### 2.3 Resoluciones Máximas AMD VCN

| Codec | VCN 1.0 | VCN 2.0 | VCN 3.0+ |
|-------|:-------:|:-------:|:---------:|
| H.264 Decode | 4096×2304 @ 60fps | 4096×2304 @ 60fps | 8192×8192 @ 60fps |
| H.264 Encode | 4096×2304 @ 60fps | 4096×2304 @ 60fps | 8192×8192 @ 60fps |
| H.265 Decode | 4096×2304 @ 60fps | 4096×2304 @ 60fps | 8192×8192 @ 60fps |
| H.265 Encode | 4096×2304 @ 60fps | 4096×2304 @ 60fps | 8192×8192 @ 60fps |
| VP9 Decode | ❌ | 4096×2304 @ 60fps | 8192×8192 @ 60fps |
| AV1 Decode | ❌ | ❌ | 8192×8192 @ 60fps |

### 2.4 Sesiones Simultáneas AMD VCN

| GPU | Sesiones Decode | Sesiones Encode |
|-----|:---------------:|:---------------:|
| Instinct MI300X | 8+ | 4+ |
| Instinct MI250 | 6+ | 4+ |
| Radeon RX 7000 | 4+ | 3+ |
| Radeon RX 6000 | 3+ | 2+ |
| Radeon RX 5000 | 2+ | 2+ |

> **Nota**: Las GPUs Instinct y Radeon Pro tienen soporte para más sesiones
> concurrentes que las GPUs de consumo Radeon RX.

---

## 3. NVIDIA NVDEC/NVENC — Soporte Detallado

### 3.1 Codecs Soportados por Generación NVIDIA

| Codec | Maxwell (GTX 900) | Pascal (GTX 1000) | Turing (RTX 2000) | Ampere (RTX 3000) | Ada (RTX 4000) | Blackwell (RTX 5000) |
|-------|:-----------------:|:------------------:|:-----------------:|:-----------------:|:--------------:|:--------------------:|
| **H.264 Dec** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **H.264 Enc** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **H.265 Dec 8-bit** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **H.265 Dec 10-bit** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **H.265 Enc 8-bit** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **H.265 Enc 10-bit** | ❌ | ❌ | ❌ | ✅ (NVENC gen 6) | ✅ | ✅ |
| **VP9 Dec** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **VP9 Enc** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **AV1 Dec** | ❌ | ❌ | ✅ (GPU) | ✅ (GPU) | ✅ (GPU) | ✅ (GPU) |
| **AV1 Enc** | ❌ | ❌ | ❌ | ❌ | ✅ (NVENC gen 9) | ✅ |
| **MPEG-2 Dec** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **VC-1 Dec** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **VP8 Dec** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### 3.2 GPUs NVIDIA y su NVENC/NVDEC Generation

| GPU | NVENC Gen | NVDEC Gen | Notas |
|-----|:---------:|:---------:|-------|
| **A100** | N/A (sin encode HW) | NVDEC 5 | Compute-only, sin NVENC |
| **H100** | N/A (sin encode HW) | NVDEC 6 | Compute-only, sin NVENC |
| **H200** | N/A (sin encode HW) | NVDEC 6 | Compute-only, sin NVENC |
| **RTX 4090** | NVENC 8 (Ada) | NVDEC 6 | AV1 encode |
| **RTX 4080** | NVENC 8 (Ada) | NVDEC 6 | AV1 encode |
| **RTX 4070** | NVENC 8 (Ada) | NVDEC 6 | AV1 encode |
| **RTX 3090** | NVENC 7 (Ampere) | NVDEC 5 | Sin AV1 encode |
| **RTX 3080** | NVENC 7 (Ampere) | NVDEC 5 | Sin AV1 encode |
| **RTX 2080** | NVENC 6 (Turing) | NVDEC 4 | Sin AV1 encode |
| **RTX 2070** | NVENC 6 (Turing) | NVDEC 4 | Sin AV1 encode |
| **RTX 3060** | NVENC 7 (Ampere) | NVDEC 5 | Sin AV1 encode |
| **GTX 1660** | NVENC 6 (Turing) | NVDEC 4 | Sin AV1 |
| **GTX 1080** | NVENC 5 (Pascal) | NVDEC 3 | Sin VP9 |
| **T4** | NVENC 6 (Turing) | NVDEC 4 | GPU servidor media |
| **L4** | NVENC 8 (Ada) | NVDEC 6 | GPU servidor media, AV1 |

### 3.3 Sesiones Simultáneas NVIDIA

| GPU Class | Sesiones NVDEC | Sesiones NVENC |
|-----------|:--------------:|:--------------:|
| Tesla/Enterprise (A100, H100) | Ilimitado (licencia) | Ilimitado (licencia) |
| Tesla/Enterprise (T4, L4) | Ilimitado (licencia) | Ilimitado (licencia) |
| RTX 4090, RTX 4080 | 3 | 3 (límite artificial) |
| RTX 3090, RTX 3080 | 3 | 3 (límite artificial) |
| RTX 2080, RTX 2070 | 3 | 3 (límite artificial) |
| GTX 1660, GTX 1080 | 3 | 3 (límite artificial) |

> **Importante**: NVIDIA impone un límite artificial de 3 sesiones NVENC
> simultáneas en GPUs de consumo (GeForce RTX). Las GPUs Tesla, Quadro y
> Enterprise no tienen este límite. En Linux, se puede parchear el driver
> para eliminar el límite (no recomendado en producción).

---

## 4. CPU Software Decode — Soporte Detallado

### 4.1 Codecs Soportados por Software (FFmpeg/libav)

Todos los codecs son soportados por software. Los más importantes:

| Codec | Elemento GStreamer | Rendimiento Relativo | Notas |
|-------|-------------------|:--------------------:|-------|
| **H.264** | `avdec_h264` | 1× (línea base) | Optimizado en CPU modernas |
| **H.265/HEVC** | `avdec_h265` | 1.5-2× más lento que H.264 | Más complejo |
| **VP9** | `avdec_vp9` | 2-3× más lento que H.264 | Consume más CPU |
| **AV1** | `avdec_av1` (dav1d) | 4-6× más lento que H.264 | Muy intensivo |
| **MPEG-2** | `avdec_mpeg2` | 0.3× más rápido que H.264 | Muy simple, bajo consumo |
| **MPEG-4** | `avdec_mpeg4` | 0.5× de H.264 | Simple pero obsoleto |
| **VC-1** | `avdec_vc1` | 0.8× de H.264 | WMV, relativamente eficiente |

### 4.2 Resolución Máxima por Hardware (CPU Software)

No hay límite de resolución en software más allá de la capacidad de la CPU:

| CPU | H.264 1080p | H.264 4K | H.265 4K | AV1 4K | AV1 8K |
|-----|:-----------:|:--------:|:--------:|:------:|:------:|
| Intel Core i5-13600K | ✅ | ✅ 60fps | ✅ 30fps | ✅ 30fps | ❌ |
| Intel Core i9-13900K | ✅ | ✅ 120fps | ✅ 60fps | ✅ 60fps | ✅ 24fps |
| AMD Ryzen 5 7600 | ✅ | ✅ 60fps | ✅ 30fps | ✅ 24fps | ❌ |
| AMD Ryzen 9 7950X | ✅ | ✅ 120fps | ✅ 60fps | ✅ 60fps | ✅ 24fps |
| AMD EPYC 9654 | ✅ | ✅ 30fps | ✅ 15fps | ✅ 15fps | ❌ |
| ARM Graviton 3 | ✅ | ✅ 30fps | ✅ 15fps | ❌ | ❌ |

### 4.3 Recomendaciones de Perfil para CPU

| Codec | Perfil Recomendado | Bitrate para 1080p | Bitrate para 4K |
|-------|-------------------|:------------------:|:----------------:|
| H.264 | High | 2-5 Mbps | 10-20 Mbps |
| H.265/HEVC | Main | 1-3 Mbps | 5-12 Mbps |
| VP9 | 0 (mejor calidad) | 1-3 Mbps | 5-10 Mbps |
| AV1 | Main | 0.5-2 Mbps | 3-8 Mbps |

---

## 5. Recomendaciones

### 5.1 Mejor Calidad/Bitrate — H.265 (HEVC)

**Recomendado** para la mayoría de casos de uso:

```bash
# AMD VCN — decode H.264, encode H.265
gst-launch-1.0 \
  filesrc location=input.mp4 ! qtdemux ! h264parse ! \
  vaapih264dec ! videoconvert ! \
  vaapih265enc ! mp4mux ! filesink location=output_hevc.mp4

# NVIDIA NVENC — decode H.264, encode H.265
gst-launch-1.0 \
  filesrc location=input.mp4 ! qtdemux ! h264parse ! \
  nvdec ! videoconvert ! \
  nvenc ! h265parse ! mp4mux ! filesink location=output_hevc.mp4
```

**Ventajas de H.265 sobre H.264:**
- 30-50% menor bitrate para la misma calidad visual
- Mejor calidad en condiciones de baja luminosidad
- Soporte para HDR10/HLG
- Resolución 8K nativa

**Desventajas:**
- Mayor complejidad computacional
- Patentes (royalties)
- Compatibilidad: dispositivos modernos, pero no todos los legacy

### 5.2 Máxima Compatibilidad — H.264

Usar H.264 cuando la compatibilidad con dispositivos legacy es crítica:

```bash
# AMD VCN
gst-launch-1.0 \
  filesrc location=input.mp4 ! qtdemux ! h264parse ! \
  vaapih264dec ! videoconvert ! \
  vaapih264enc ! mp4mux ! filesink location=output_avc.mp4
```

**Ventajas de H.264:**
- Compatibilidad universal
- Madurez y estabilidad
- Bajo costo computacional
- Ideal para streaming en tiempo real

### 5.3 Máxima Eficiencia — AV1

Para almacenamiento y transmisión donde la eficiencia de compresión es crítica:

```bash
# Decode AV1 con AMD VCN 3.0+ o NVIDIA NVDEC (Turing+)
gst-launch-1.0 \
  filesrc location=input_av1.mp4 ! qtdemux ! av1parse ! \
  vaapiav1dec ! videoconvert ! fakesink
```

**Ventajas de AV1:**
- 30% mejor compresión que H.265
- Libre de royalties
- Ideal para archivo y streaming adaptativo

**Desventajas:**
- Hardware decode solo en GPUs recientes (VCN 3.0+, Turing+)
- Hardware encode solo en VCN 5.0+ o Ada Lovelace+
- Software decode muy intensivo

### 5.4 Guía Rápida de Selección de Codec

| Caso de Uso | Codec Recomendado | Backend Recomendado | Razón |
|-------------|:-----------------:|:-------------------:|-------|
| **Streaming RTSP en tiempo real** | H.264 | AMD VCN / NVIDIA NVDEC | Baja latencia, compatible |
| **Análisis de video (frames)** | H.264 | AMD VCN / NVIDIA NVDEC | Fácil extracción de frames |
| **Archivo de alta calidad** | H.265 / HEVC | AMD VCN 3.0+ / NVIDIA Ada | Mejor calidad/bitrate |
| **Streaming adaptativo** | H.265 / HEVC | AMD VCN / NVIDIA NVENC | Bueno para ABR |
| **Archivo de largo plazo** | AV1 | CPU (lento) / VCN 5.0+ | Mejor compresión |
| **Dispositivos legacy** | H.264 | Cualquiera | Compatibilidad máxima |
| **Video 8K** | H.265 / HEVC | AMD VCN 3.0+ / NVIDIA Ada | Único codec práctico |
| **Transcodificación batch** | H.265 / HEVC | AMD VCN | Buena relación calidad/velocidad |

---

## 6. Bitrate Recomendado por Resolución y Codec

| Resolución | H.264 | H.265/HEVC | AV1 | VP9 |
|------------|:-----:|:----------:|:---:|:---:|
| **426×240 (240p)** | 0.3-0.8 Mbps | 0.2-0.5 Mbps | 0.1-0.3 Mbps | 0.2-0.4 Mbps |
| **640×360 (360p)** | 0.5-1.5 Mbps | 0.3-0.8 Mbps | 0.2-0.5 Mbps | 0.3-0.6 Mbps |
| **854×480 (480p)** | 1-3 Mbps | 0.5-1.5 Mbps | 0.3-1 Mbps | 0.5-1.2 Mbps |
| **1280×720 (720p)** | 2-5 Mbps | 1-3 Mbps | 0.5-2 Mbps | 1-2.5 Mbps |
| **1920×1080 (1080p)** | 4-10 Mbps | 2-6 Mbps | 1-4 Mbps | 2-5 Mbps |
| **2560×1440 (1440p)** | 8-20 Mbps | 4-12 Mbps | 2-8 Mbps | 4-10 Mbps |
| **3840×2160 (4K)** | 15-40 Mbps | 8-25 Mbps | 5-15 Mbps | 10-20 Mbps |
| **7680×4320 (8K)** | ❌ | 40-100 Mbps | 20-60 Mbps | ❌ |

> **Nota**: Los rangos de bitrate son orientativos. El bitrate óptimo depende
> del contenido (acción, talking heads, animación), framerate y calidad deseada
> (CRF/QP).

---

## 7. Formatos de Contenedor (Muxer)

| Contenedor | Codecs Soportados | Uso Recomendado | Elemento GStreamer |
|------------|:-----------------:|-----------------|-------------------|
| **MP4** | H.264, H.265, AV1, MPEG-4 | Universal, streaming | `mp4mux` |
| **MKV** | Todos | Archivo, preservación | `matroskamux` |
| **WebM** | VP8, VP9, AV1 | Web, HTML5 | `webmmux` |
| **TS (MPEG-TS)** | H.264, H.265 | Broadcast, RTSP | `mpegtsmux` |
| **FLV** | H.264, VP6 | RTMP, Flash legacy | `flvmux` |
| **AVI** | MPEG-4, MJPEG | Legacy | `avimux` |
| **MOV** | H.264, H.265, ProRes | Apple, producción | `qtmux` |

---

## 8. Formatos de Pixel y Espacios de Color

### 8.1 Formatos Soportados por Backend

| Formato | Descripción | AMD VCN | NVIDIA NVDEC | CPU | Uso |
|---------|-------------|:-------:|:------------:|:---:|-----|
| **NV12** | YUV 4:2:0 planar | ✅ | ✅ | ✅ | Nativo decodificación |
| **I420** | YUV 4:2:0 planar | ✅ | ✅ | ✅ | Estándar |
| **YV12** | YUV 4:2:0 swapped | ✅ | ✅ | ✅ | Legacy |
| **RGB** | RGB 8-bit | ✅ (vía convert) | ✅ (vía convert) | ✅ | Visión por computadora |
| **BGR** | BGR 8-bit | ✅ (vía convert) | ✅ (vía convert) | ✅ | OpenCV |
| **RGBA** | RGB + Alpha | ✅ | ✅ | ✅ | Overlays |
| **P010** | YUV 4:2:0 10-bit | ✅ | ✅ | ✅ | HDR |
| **I422** | YUV 4:2:2 | ❌ | ✅ | ✅ | Producción |

### 8.2 Conversión Recomendada para Inferencia

```bash
# Pipeline de inferencia: video → RGB 8-bit → appsink
gst-launch-1.0 \
  filesrc location=video.mp4 ! qtdemux ! h264parse ! \
  vaapih264dec ! \
  videoconvert ! \
  videoscale ! \
  video/x-raw,width=640,height=480,format=RGB,pixel-aspect-ratio=1/1 ! \
  appsink name=sink
```

- **Formato de salida**: RGB (para visión por computadora)
- **Profundidad**: 8-bit (suficiente para la mayoría de modelos)
- **Resolución**: 640×480 (buen balance calidad/rendimiento)
- **Eliminar aspect ratio**: `pixel-aspect-ratio=1/1`

---

## 9. Referencias

- [AMD VCN Decode/Encode Support Matrix](https://github.com/HandBrake/HandBrake/wiki/AMD-VCN-Guide)
- [NVIDIA Video Codec SDK Support Matrix](https://developer.nvidia.com/video-codec-sdk)
- [FFmpeg Hardware Acceleration](https://trac.ffmpeg.org/wiki/HWAccelIntro)
- [GStreamer VAAPI](https://gstreamer.freedesktop.org/documentation/vaapi/)
- [NVIDIA NVDEC Documentation](https://developer.nvidia.com/nvenc)
- [Microsoft Media Foundation H.264](https://learn.microsoft.com/en-us/windows/win32/medfound/h-264-video-encoder)
