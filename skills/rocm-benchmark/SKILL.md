---
name: rocm-benchmark
description: >
  Benchmarking completo de GPU AMD ROCm (MI300X, MI250, RX 7900) y NVIDIA CUDA
  (A100, H100, RTX) para medir rendimiento en memoria, compute, inferencia y
  consumo energético. Incluye detección automática de backend, benchmark de
  bandwidth (H2D/D2H/P2P), throughput de matrix multiply (GEMM) en FP32/FP16,
  benchmark de inferencia PyTorch con dummy CNN y Transformer, monitoreo en
  tiempo real con rocm-smi/nvidia-smi, stress test con detección de thermal
  throttling, y reporte consolidado en JSON. Actívalo al probar rendimiento de
  GPU AMD, comparar ROCm vs CUDA, hacer stress test en MI300X, medir throughput
  de inferencia, o diagnosticar cuello de botella en GPU.
  Keywords: benchmark, rocm, amd, gpu, performance, memory, compute, inference,
  throughput, latency, nvidia, cuda, mi300x, mi250, a100, h100, rocm-smi,
  stress-test, gemm, bandwidth, flops, thermal-throttle, f1
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: "Munin Project"
  tags:
    - amd
    - rocm
    - benchmark
    - gpu
    - performance
    - memory
    - compute
    - inference
    - throughput
    - latency
    - nvidia
    - cuda
    - mi300x
    - rocm-smi
    - stress-test
compatibility:
  - claude-code
  - opencode
  - codex
  - cursor
---

# ROCm Benchmark Skill

Benchmarking completo de GPU **AMD ROCm** con soporte para **NVIDIA CUDA** como comparación. Detecta automáticamente el backend disponible, ejecuta benchmarks de memoria, compute, inferencia, monitorea en tiempo real y genera un reporte consolidado.

## Purpose

Proporciona un conjunto de scripts y referencias para:

- **Benchmark de memoria**: bandwidth host-to-device (H2D), device-to-host (D2H), y peer-to-peer (P2P) entre GPUs
- **Benchmark de compute**: matrix multiply (GEMM) en FP32/FP16, FFT, convoluciones 2D
- **Benchmark de inferencia**: throughput (FPS/tokens/s) y latencia (p50/p95/p99) en modelos dummy CNN y Transformer
- **Monitoreo en tiempo real**: power draw, temperatura, clock speeds, VRAM usage, fan speed
- **Stress test**: carga sostenida con detección de thermal throttling
- **Reporte consolidado**: salida JSON completa para análisis posterior, tabla comparativa con NVIDIA si hay datos

## When to Use / Cuándo Usar

La skill se activa automáticamente al detectar keywords como:

- "benchmark GPU AMD / medir rendimiento ROCm / probar MI300X"
- "GPU benchmark / stress test AMD / probar rendimiento GPU"
- "comparar ROCm vs CUDA / compare AMD vs NVIDIA performance"
- "rocm-smi metrics / monitorear GPU AMD / GPU power draw"
- "throughput test / latency benchmark / medir FPS inferencia"
- "thermal throttling test / GPU stress test sostenido"
- Keywords: benchmark, rocm, cuda, performance, memory bandwidth, gemm, inference throughput, latency, stress test, thermal throttle, rocm-smi, nvidia-smi

## Prerequisites

- **ROCm 7.2+** (para AMD) — verificar con `rocminfo | grep gfx`
- **NVIDIA driver 535+** (para NVIDIA) — verificar con `nvidia-smi`
- **rocm-smi** (para AMD) — herramienta de monitoreo ROCm
- **rocprof** (opcional) — profiling ROCm para métricas avanzadas
- **PyTorch ROCm** — `torch` con soporte ROCm o CUDA (`torch.cuda.is_available()` debe ser `True`)
- **Python 3.10+** con dependencias: `numpy`, `torch`
- **Espacio en disco**: ~1GB para dependencias y modelos dummy
- **Permisos**: usuario en grupos `video` y `render` (AMD) o `video` (NVIDIA)

### Dependencias Adicionales

```bash
pip install numpy torch
# Para benchmark de inferencia con modelos reales (opcional):
pip install ultralytics  # YOLO benchmark
pip install vllm         # LLM benchmark
```

## Quickstart

### 1. Información del Sistema

```bash
# Detectar backend y mostrar información de GPU
python3 scripts/benchmark-gpu.py --info
```

### 2. Benchmark Rápido (todo en uno)

```bash
# Ejecutar todos los benchmarks con configuración por defecto
python3 scripts/benchmark-gpu.py --all --iterations 100
```

### 3. Generar Reporte JSON

```bash
# Benchmark completo con salida JSON
python3 scripts/benchmark-gpu.py --all --iterations 200 --json --output results.json
```

## Step-by-Step

### 1. Detectar Backend y Recopilar Información GPU

Ejecuta el script de benchmark con `--info` para identificar tu hardware:

```bash
python3 scripts/benchmark-gpu.py --info
```

El script detecta:

| Atributo | Descripción | Ejemplo AMD | Ejemplo NVIDIA |
|----------|-------------|-------------|----------------|
| `backend` | Backend detectado | `rocm` | `cuda` |
| `device_name` | Nombre de GPU | `AMD Instinct MI300X` | `NVIDIA A100-SXM-80GB` |
| `device_count` | Número de GPUs | `8` | `8` |
| `driver_version` | Versión driver | `7.2.0` | `535.154.05` |
| `torch_version` | Versión PyTorch | `2.4.0+rocm6.2` | `2.4.0+cu124` |
| `gfx_arch` | Arquitectura GFX | `gfx942` | `N/A` |
| `vram_total_gb` | VRAM total | `192.0` GB | `80.0` GB |
| `compute_capability` | Capacidad compute | `N/A` | `8.0` |

```bash
# Salida típica:
# ╔══════════════════════════════════════════╗
# ║       MUNIN — GPU Benchmark Suite       ║
# ╚══════════════════════════════════════════╝
#   Backend:    ROCM
#   Device:     AMD Instinct MI300X
#   GPU Count:  8
#   Driver:     7.2.0
#   GFX Arch:   gfx942
#   Torch:      2.4.0+rocm6.2
#   VRAM Total: 192.0 GB
```

### 2. Benchmark de Memoria

Mide el ancho de banda de memoria en varias configuraciones:

```bash
# Benchmark de memoria con sizes por defecto
python3 scripts/benchmark-gpu.py --memory

# Configuración personalizada
python3 scripts/benchmark-gpu.py --memory --memory-sizes 1024,4096,16384 --iterations 50
```

El benchmark mide tres tipos de transferencia:

- **H2D (Host-to-Device)**: transferencia de CPU a GPU. Crítico para alimentar datos al modelo.
- **D2H (Device-to-Host)**: transferencia de GPU a CPU. Importante para recuperar resultados.
- **P2P (Peer-to-Peer)**: transferencia directa entre GPUs. Relevante en configuración multi-GPU.

**Interpretación de resultados (MI300X):**

| Métrica | MI300X (HBM3) | A100 (HBM2e) | H100 (HBM3) |
|---------|:-------------:|:------------:|:-----------:|
| H2D Bandwidth | ~27 GB/s (PCIe 4.0) | ~25 GB/s (PCIe 4.0) | ~32 GB/s (PCIe 5.0) |
| D2H Bandwidth | ~27 GB/s (PCIe 4.0) | ~25 GB/s (PCIe 4.0) | ~32 GB/s (PCIe 5.0) |
| P2P Bandwidth | ~160 GB/s (Infinity Fabric) | ~200 GB/s (NVLink) | ~450 GB/s (NVLink) |
| HBM Bandwidth | ~3.3 TB/s | ~2.0 TB/s | ~3.35 TB/s |

> **Nota**: H2D/D2H miden bandwidth PCIe, no HBM. Para medir bandwidth HBM, usa el benchmark de compute (GEMM) que ejerce la memoria interna de la GPU.

### 3. Benchmark de Compute

Mide el throughput de cómputo con operaciones fundamentales:

```bash
# Benchmark de compute con sizes por defecto
python3 scripts/benchmark-gpu.py --compute

# Especificar tamaños de matriz
python3 scripts/benchmark-gpu.py --compute --matrix-sizes 512,1024,2048,4096 --iterations 100

# Solo FP16 (más rápido en MI300X con Matrix Cores)
python3 scripts/benchmark-gpu.py --compute --dtype fp16
```

Operaciones medidas:
- **GEMM** (General Matrix Multiply): `C = A @ B` en FP32 y FP16 para matrices de 512, 1024, 2048, 4096
- **FFT**: Fast Fourier Transform 2D en sizes de potencia de 2
- **Convolución 2D**: convolución con kernel 3x3, canales variables

**Interpretación de resultados:**

| Operación | MI300X FP16 | MI300X FP32 | A100 FP16 | A100 FP32 |
|-----------|:----------:|:----------:|:---------:|:---------:|
| GEMM 4096 | ~261 TFLOPS | ~81 TFLOPS | ~312 TFLOPS | ~78 TFLOPS |
| GEMM 2048 | ~245 TFLOPS | ~76 TFLOPS | ~290 TFLOPS | ~72 TFLOPS |
| GEMM 1024 | ~180 TFLOPS | ~55 TFLOPS | ~200 TFLOPS | ~50 TFLOPS |
| FFT 2048 | ~1.2 TB/s | ~0.8 TB/s | ~1.0 TB/s | ~0.6 TB/s |

> Los valores reales dependen de la frecuencia sostenida, temperatura y configuración del sistema.

### 4. Benchmark de Inferencia PyTorch (Modelo Dummy)

Mide throughput y latencia de inferencia con arquitecturas dummy que ejercitan operaciones reales:

```bash
# Benchmark de inferencia con modelo CNN
python3 scripts/benchmark-gpu.py --inference --model cnn

# Benchmark con modelo Transformer
python3 scripts/benchmark-gpu.py --inference --model transformer --batch-size 32

# Batch sizes múltiples para encontrar el óptimo
python3 scripts/benchmark-gpu.py --inference --model transformer --batch-sizes 1,8,16,32,64
```

Modelos dummy:
- **CNN**: 4 capas convolucionales + pooling + fully connected. Similar a ResNet simplificado.
- **Transformer**: 4 capas TransformerEncoder con self-attention multi-head. Similar a BERT simplificado.

**Métricas reportadas:**

| Métrica | Descripción |
|---------|-------------|
| Throughput | FPS (Frames/capturas por segundo) o tokens/s |
| Latency p50 | Mediana de latencia por batch |
| Latency p95 | Percentil 95 — impacto de outliers |
| Latency p99 | Percentil 99 — peor caso |
| VRAM peak | Pico de VRAM usado durante inferencia |
| VRAM delta | VRAM adicional usada por el modelo |

### 5. Benchmark de Inferencia Real (YOLO / vLLM)

Si los paquetes están instalados, el script detecta automáticamente modelos reales:

```bash
# YOLO (si ultralytics está instalado)
python3 scripts/benchmark-gpu.py --inference --model yolo --yolo-model yolov8n.pt

# vLLM (si vllm está instalado)
python3 scripts/benchmark-gpu.py --inference --model llm --llm-model mistralai/Mistral-7B-v0.1
```

La detección es automática:
- Si `ultralytics` está instalado, YOLO se ofrece como opción
- Si `vllm` está instalado, modelos LLM están disponibles
- Si no hay ninguno, se usan modelos dummy PyTorch

### 6. Monitoreo en Tiempo Real

Durante cualquier benchmark, el script puede monitorear la GPU en paralelo:

```bash
# Monitor independiente con rocm-smi
bash scripts/rocm-monitor.sh --interval 1

# Monitor integrado con benchmark
python3 scripts/benchmark-gpu.py --all --monitor

# Log a archivo con timestamp
bash scripts/rocm-monitor.sh --interval 2 --log monitor.log
```

El monitor muestra en tiempo real:
```
[12:34:56] GPU 0 | 245W | 65°C | 1650 MHz | 1200 MHz | 45.2 GB VRAM | 45% fan
[12:34:57] GPU 0 | 252W | 66°C | 1650 MHz | 1200 MHz | 45.8 GB VRAM | 46% fan
```

Al salir (Ctrl+C), muestra un resumen:
```
═══ Monitor Summary ═══
  Power:     min 45W | avg 210W | max 275W
  Temp:      min 32°C | avg 58°C | max 72°C
  VRAM:      min 0.5 GB | avg 32.1 GB | max 48.0 GB
  Clock:     min 300 MHz | avg 1620 MHz | max 1750 MHz
```

### 7. Stress Test

Carga sostenida para verificar estabilidad térmica y eléctrica:

```bash
# Stress test de 60 segundos
python3 scripts/benchmark-gpu.py --stress --duration 60

# Stress test con monitoreo integrado
python3 scripts/benchmark-gpu.py --stress --duration 120 --monitor

# Script dedicado con más control
bash scripts/stress-test.sh --duration 120 --load 4096
```

El stress test:
1. Ejecuta GEMM 4096 repetidamente
2. Monitorea temperatura, power, clock en cada iteración
3. Detecta thermal throttling: si la frecuencia del clock baja más de 5% mientras la temperatura sube
4. Reporta estabilidad: OK o THROTTLING DETECTED

**Parámetros del stress test:**

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `--duration` | 60 | Duración en segundos |
| `--load` | 4096 | Tamaño de matriz GEMM |
| `--monitor` | false | Monitorear con rocm-smi o nvidia-smi |
| `--threshold` | 5 | % de caída de clock para detectar throttling |

### 8. Reporte Consolidado

Al finalizar todos los benchmarks, se genera un reporte completo:

```bash
# Reporte completo con comparativa
python3 scripts/benchmark-gpu.py --all --iterations 200 --json --output full-report.json

# Ver reporte
cat full-report.json | python3 -m json.tool
```

El reporte JSON incluye:
```json
{
  "system": {
    "backend": "rocm",
    "device_name": "AMD Instinct MI300X",
    "device_count": 8,
    "driver_version": "7.2.0",
    "torch_version": "2.4.0+rocm6.2",
    "gfx_arch": "gfx942",
    "vram_total_gb": 192.0
  },
  "memory": { "h2d_gbps": ..., "d2h_gbps": ..., "p2p_gbps": ... },
  "compute": {
    "gemm_fp32": { "512": ..., "1024": ..., "2048": ..., "4096": ... },
    "gemm_fp16": { "512": ..., "1024": ..., "2048": ..., "4096": ... },
    "fft": ...,
    "conv2d": ...
  },
  "inference": {
    "cnn": { "throughput_fps": ..., "latency_p50_ms": ..., "latency_p95_ms": ..., "latency_p99_ms": ... },
    "transformer": { "throughput_fps": ..., "latency_p50_ms": ..., "latency_p95_ms": ..., "latency_p99_ms": ... }
  },
  "stress_test": {
    "duration_s": 60,
    "stable": true,
    "max_temp_c": 72,
    "max_power_w": 275,
    "clock_drop_pct": 1.2,
    "throttling_detected": false
  },
  "monitor_summary": {
    "power": { "min_w": 45, "avg_w": 210, "max_w": 275 },
    "temp": { "min_c": 32, "avg_c": 58, "max_c": 72 },
    "vram": { "min_gb": 0.5, "avg_gb": 32.1, "max_gb": 48.0 },
    "clock": { "min_mhz": 300, "avg_mhz": 1620, "max_mhz": 1750 }
  }
}
```

En modo texto, el reporte incluye una tabla comparativa:
```
═══════════════════════════════════════════════════════════════
              MUNIN — GPU Benchmark Report
═══════════════════════════════════════════════════════════════
 System:        AMD Instinct MI300X (ROCM)
 Driver:        7.2.0
 Torch:         2.4.0+rocm6.2

── Memory ──────────────────────────────────────────────────
  H2D:           26.8 GB/s
  D2H:           27.1 GB/s
  P2P:          158.2 GB/s

── Compute ──────────────────────────────────────────────────
  GEMM FP32 4096:   78.5 TFLOPS
  GEMM FP16 4096:  253.2 TFLOPS
  FFT 2048:          1.1 TB/s
  Conv2D:           12.4 TFLOPS

── Inference ────────────────────────────────────────────────
  CNN:        452.3 FPS  |  p50 2.21 ms  |  p95 2.45 ms  |  p99 2.89 ms
  Transformer: 189.7 FPS |  p50 5.27 ms  |  p95 5.81 ms  |  p99 6.42 ms

── Stress Test ─────────────────────────────────────────────
  Duration:    60.0 s
  Stable:      ✅ YES (clock drop: 1.2%)
  Max Temp:    72°C
  Max Power:   275 W

══ Summary ═════════════════════════════════════════════════
  Overall:    ✅ PASS (all benchmarks completed)
═══════════════════════════════════════════════════════════════
```

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/benchmark-metrics.md](references/benchmark-metrics.md) | Explicación detallada de cada métrica: bandwidth, TFLOPS, FPS, latencia, VRAM, power, temperatura, clock. Valores de referencia para MI300X, A100, H100. |
| [references/rocm-smi-guide.md](references/rocm-smi-guide.md) | Guía completa de rocm-smi: comandos, monitoreo continuo, parseo para scripts, equivalentes NVIDIA nvidia-smi, variables de entorno. |

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/benchmark-gpu.py` | Benchmark principal multi-backend: memoria, compute, inferencia, stress test. Salida JSON + reporte formateado. | `python3 scripts/benchmark-gpu.py --all` |
| `scripts/rocm-monitor.sh` | Monitoreo en tiempo real con rocm-smi/nvidia-smi. Log a archivo con timestamp, resumen de máximos/promedios. | `bash scripts/rocm-monitor.sh --interval 1` |
| `scripts/stress-test.sh` | Stress test dedicado con detección de thermal throttling. Carga sostenida con PyTorch GEMM loop. | `bash scripts/stress-test.sh --duration 120` |

## Common Issues

### 1. Thermal Throttling Durante Stress Test

**Síntoma**: El clock de GPU baja progresivamente mientras la temperatura sube. El benchmark reporta "THROTTLING DETECTED".

**Causa**: El sistema de refrigeración no puede disipar el calor generado por carga sostenida. MI300X tiene un TDP de ~350W.

**Solución**:
```bash
# 1. Verificar temperatura actual
rocm-smi --showtemp

# 2. Verificar velocidad de ventiladores
rocm-smi --showfan

# 3. Aumentar velocidad de ventiladores (si el hardware lo permite)
rocm-smi --setfan 80

# 4. Reducir la carga (matrices más pequeñas)
python3 scripts/benchmark-gpu.py --stress --duration 60 --load 2048

# 5. Para servidores: verificar airflow, seating de GPUs, temperatura ambiente
```

Si el throttling ocurre inmediatamente, puede ser un problema de hardware (thermal paste, contactos, o ventiladores defectuosos).

### 2. Out of Memory (OOM) en Benchmark

**Síntoma**: Error `torch.cuda.OutOfMemoryError` o muerte del proceso.

**Causa**: Tamaños de matriz muy grandes para la VRAM disponible, o múltiples benchmarks ejecutándose sin liberar memoria.

**Solución**:
```bash
# 1. Verificar VRAM libre antes de empezar
rocm-smi --showmeminfo vram

# 2. Reducir tamaños de matriz
python3 scripts/benchmark-gpu.py --compute --matrix-sizes 512,1024 --iterations 50

# 3. Liberar memoria entre benchmarks
python3 -c "import torch; torch.cuda.empty_cache()"

# 4. Monitorear VRAM durante benchmark
bash scripts/rocm-monitor.sh --interval 1

# 5. Verificar que otros procesos no estén usando VRAM
rocm-smi --showpid
```

Para MI300X (192 GB), los tamaños máximos recomendados son:
- GEMM 16384: requiere ~2 GB VRAM (seguro)
- GEMM 32768: requiere ~8 GB VRAM (seguro)
- Inference batch 256: ~8-16 GB VRAM (seguro)

### 3. Driver Timeout en Benchmark Largo

**Síntoma**: El benchmark se detiene con error "driver timeout", "killed", o la pantalla se congela.

**Causa**: Los drivers GPU tienen un watchdog que mata procesos que toman más de N segundos en el kernel. Común en GPUs de consumo (RDNA) más que en Instinct (CDNA).

**Solución**:
```bash
# 1. Aumentar timeout del driver AMD (Linux)
sudo bash -c 'echo "export GPU_TIMEOUT=60" >> /etc/profile.d/rocm-timeout.sh'

# 2. Para AMD RDNA (RX 7900), deshabilitar watchdog
sudo bash -c 'echo "options amdgpu gpu_timeout=60000" > /etc/modprobe.d/amdgpu-timeout.conf'
# Reiniciar o recargar: sudo modprobe -r amdgpu && sudo modprobe amdgpu

# 3. Reducir duración del benchmark
python3 scripts/benchmark-gpu.py --stress --duration 30

# 4. Usar tamaños de matriz más pequeños
python3 scripts/benchmark-gpu.py --compute --matrix-sizes 1024,2048 --iterations 30

# 5. Para NVIDIA:
# El timeout es controlado por nvidia-smi -pm (persistence mode)
sudo nvidia-smi -pm 1
```

### 4. `rocm-smi` No Disponible

**Síntoma**: El monitor muestra "rocm-smi: command not found". No se puede monitorear GPU AMD.

**Causa**: ROCm no está instalado, o solo está instalada la parte runtime sin las tools de administración.

**Solución**:
```bash
# 1. Instalar rocm-smi desde el paquete rocm-libs
sudo apt install rocm-libs

# 2. O instalar el paquete específico
sudo amdgpu-install --usecase=rocm,hip,rocmdevtools

# 3. Verificar instalación
which rocm-smi
rocm-smi --version

# 4. Si no se puede instalar, usar alternativas:
# - /sys/class/drm/card*/device/ (lectura directa de HW)
cat /sys/class/drm/card0/device/gpu_busy_percent
cat /sys/class/drm/card1/device/hwmon/hwmon*/temp1_input

# 5. O usar el script con --device cpu para benchmark sin monitoreo
python3 scripts/benchmark-gpu.py --compute --device cpu
```

### 5. Resultados de Benchmark Demasiado Variables

**Síntoma**: Las métricas fluctúan más de 20% entre ejecuciones consecutivas en el mismo hardware.

**Causa**: 
- Variación de temperatura entre runs (el primer run está frío, el caliente es más lento)
- Procesos en background usando GPU (monitoreo, otros benchmarks)
- Power capping activo (límites de consumo)
- Modo de ahorro de energía

**Solución**:
```bash
# 1. Hacer warmup antes de medir (ya incluido en el script: 5 iteraciones iniciales)
python3 scripts/benchmark-gpu.py --compute --iterations 200 --warmup 20

# 2. Fijar frecuencia de GPU para mediciones consistentes
# AMD (como root):
# rocm-smi --setsclk 7  # Fijar clock más alto (de 0-7)

# NVIDIA:
sudo nvidia-smi -lgc 1500,1500  # Fijar clock a 1500 MHz

# 3. Asegurar que no hay otros procesos en GPU
rocm-smi --showpid
# Matar procesos no esenciales: sudo kill -9 <PID>

# 4. Hacer pausa entre benchmarks para que se enfríe
# El script incluye --cooldown <seconds>

# 5. Ejecutar múltiples runs y reportar promedio
python3 scripts/benchmark-gpu.py --compute --iterations 500 --runs 3
```

### 6. Benchmark Multi-GPU No Detecta Todas las GPUs

**Síntoma**: `device_count` reporta menos GPUs de las físicamente instaladas.

**Causa**: Variables de entorno (`HIP_VISIBLE_DEVICES`, `CUDA_VISIBLE_DEVICES`) limitan las GPUs visibles.

**Solución**:
```bash
# 1. Verificar variables de entorno
echo $HIP_VISIBLE_DEVICES
echo $CUDA_VISIBLE_DEVICES

# 2. Desactivar filtros para ver todas las GPUs
unset HIP_VISIBLE_DEVICES
unset ROCR_VISIBLE_DEVICES
unset CUDA_VISIBLE_DEVICES

# 3. Verificar GPUs físicas
rocm-smi --showproductname

# 4. Verificar desde PyTorch
python3 -c "import torch; print(f'GPUs visibles: {torch.cuda.device_count()}')"

# 5. Para benchmark multi-GPU específico
HIP_VISIBLE_DEVICES=0,1,2,3 python3 scripts/benchmark-gpu.py --all

# 6. Forzar device específico
python3 scripts/benchmark-gpu.py --all --device cuda:0
```

### 7. Benchmark de Memoria Reporta 0 GB/s

**Síntoma**: El bandwidth H2D/D2H reporta 0 GB/s o valores absurdamente altos/bajos.

**Causa**: El benchmark mide solo operaciones sincrónicas, pero PyTorch por defecto usa streams asíncronos. Sin `torch.cuda.synchronize()`, las mediciones de tiempo son incorrectas.

**Solución**: El script `benchmark-gpu.py` ya incluye sincronización. Si haces benchmarks manuales:
```python
import torch
import time

# CORRECTO: sincronizar antes de medir
start = time.perf_counter()
x = torch.randn(10000, 10000, device='cuda')
torch.cuda.synchronize()  # ← Crucial
end = time.perf_counter()
```

### 8. Benchmark de Inferencia con YOLO Falla

**Síntoma**: Error al ejecutar `--inference --model yolo`.

**Causa**: Ultralytics no está instalado, o el modelo YOLO no se encuentra.

**Solución**:
```bash
# Instalar ultralytics
pip install ultralytics

# Verificar que el modelo existe
python3 -c "from ultralytics import YOLO; model = YOLO('yolov8n.pt'); print('✅ YOLO ready')"

# Usar modelo pequeño para benchmark rápido
python3 scripts/benchmark-gpu.py --inference --model yolo --yolo-model yolov8n.pt --iterations 50
```
