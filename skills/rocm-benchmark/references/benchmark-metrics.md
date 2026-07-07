# Benchmark Metrics Reference

Guía completa de métricas de benchmark para GPU AMD ROCm y NVIDIA CUDA.
Explica qué mide cada métrica, cómo interpretarla, y valores de referencia
para GPUs comunes (MI300X, A100, H100).

---

## 1. Memory Bandwidth (GB/s)

### Qué mide

La velocidad de transferencia de datos entre la CPU y la GPU (o entre GPUs).

| Métrica | Descripción | Unidad |
|---------|-------------|--------|
| **H2D** (Host-to-Device) | CPU → GPU (subir datos, parámetros, inputs) | GB/s |
| **D2H** (Device-to-Host) | GPU → CPU (bajar resultados, gradientes) | GB/s |
| **P2P** (Peer-to-Peer) | GPU → GPU (transferencia directa entre GPUs) | GB/s |
| **HBM Bandwidth** | Ancho de banda interno de la VRAM (GPU → GPU local) | GB/s |

### Cómo se mide

```python
# H2D: transferir tensor de CPU a GPU
tensor_cpu = torch.randn(N, device="cpu")
start = time.perf_counter()
tensor_gpu = tensor_cpu.to("cuda:0", non_blocking=False)
torch.cuda.synchronize()
elapsed = time.perf_counter() - start
bandwidth = (N * 4) / elapsed / 1e9  # GB/s (float32 = 4 bytes)
```

> **Importante**: H2D/D2H miden bandwidth PCIe, no HBM. Para medir bandwidth
> HBM se usan benchmarks de compute (GEMM) que ejercitan la memoria interna.

### Factores que afectan

- **PCIe gen**: PCIe 4.0 x16 ≈ 32 GB/s teóricos, ~27 GB/s reales
- **PCIe 5.0 x16**: ≈ 64 GB/s teóricos, ~55 GB/s reales
- **Tamaño de transferencia**: transfers más grandes alcanzan mejor bandwidth
- **P2P depende de interconexión**: Infinity Fabric (AMD), NVLink (NVIDIA)

### Valores de Referencia

| GPU | H2D (PCIe) | D2H (PCIe) | P2P | HBM |
|-----|:----------:|:----------:|:---:|:---:|
| **MI300X** (PCIe 4.0) | ~27 GB/s | ~27 GB/s | ~160 GB/s (IF) | **~3.3 TB/s** |
| **MI250** (PCIe 4.0) | ~25 GB/s | ~25 GB/s | ~100 GB/s (IF) | ~1.6 TB/s |
| **A100** (PCIe 4.0) | ~25 GB/s | ~25 GB/s | ~200 GB/s (NVLink3) | ~2.0 TB/s |
| **H100** (PCIe 5.0) | ~55 GB/s | ~55 GB/s | ~450 GB/s (NVLink4) | **~3.35 TB/s** |
| **A100 SXM** (NVLink) | ~25 GB/s | ~25 GB/s | ~600 GB/s (NVLink3) | ~2.0 TB/s |
| **RX 7900 XTX** (PCIe 4.0) | ~27 GB/s | ~27 GB/s | N/A | ~960 GB/s |

> **Interpretación**: Si H2D es mucho menor de lo esperado (>20% less), verificar:
> - PCIe link speed: `sudo lspci -vvvs <bus> | grep Speed`
> - Si la GPU está en un slot x8 o x4 en vez de x16
> - Presencia de otros dispositivos compartiendo el mismo PCIe root complex

---

## 2. Compute Throughput (TFLOPS)

### Qué mide

La capacidad de cómputo de la GPU en operaciones de punto flotante.

| Métrica | Descripción | Unidad |
|---------|-------------|--------|
| **FP32 TFLOPS** | Rendimiento en precisión simple | TFLOPS |
| **FP16 TFLOPS** | Rendimiento en media precisión (con Matrix Cores) | TFLOPS |
| **INT8 TOPS** | Rendimiento en enteros de 8 bits (inferencia cuantizada) | TOPS |

### Cómo se mide (GEMM)

```python
# Matrix multiply: C = A @ B, where A, B are N x N
# FLOP count ≈ 2*N^3 (for large N)
a = torch.randn(N, N, device="cuda")
b = torch.randn(N, N, device="cuda")

start = time.perf_counter()
c = torch.mm(a, b)
torch.cuda.synchronize()
elapsed = time.perf_counter() - start

tflops = (2 * N**3 / elapsed) / 1e12
```

### Valores de Referencia (Peak Theoretical)

| GPU | FP32 (TFLOPS) | FP16 (TFLOPS) | INT8 (TOPS) | Matrix Cores/Tensor Cores |
|-----|:------------:|:-------------:|:-----------:|:-------------------------:|
| **MI300X** | 163.4 | **~261.4** (Matrix) | ~522.8 | 4th gen Matrix Cores |
| **MI250** | 95.4 | 191.0 (Matrix) | 381.9 | 3rd gen Matrix Cores |
| **MI100** | 46.1 | 92.3 (Matrix) | 184.6 | 2nd gen Matrix Cores |
| **A100** | 77.9 | **~312** (Tensor) | **~624** | 3rd gen Tensor Cores |
| **H100** | 100.1 | **~494** (Tensor) | **~988** | 4th gen Tensor Cores |
| **RX 7900 XTX** | 61.4 | 122.9 (Matrix) | 245.8 | RDNA3 Matrix Cores |

### Valores de Referencia (Reales — GEMM 4096)

Los valores reales suelen ser 60-85% del pico teórico:

| GPU | FP32 Real | % Peak | FP16 Real | % Peak |
|-----|:---------:|:------:|:---------:|:------:|
| MI300X | ~81 TFLOPS | ~50% | ~253 TFLOPS | ~97% |
| A100 SXM | ~78 TFLOPS | ~100% | ~290 TFLOPS | ~93% |
| H100 SXM | ~95 TFLOPS | ~95% | ~450 TFLOPS | ~91% |
| RX 7900 XTX | ~55 TFLOPS | ~90% | ~110 TFLOPS | ~89% |

> **Nota**: MI300X FP32 está por debajo del pico porque usa un pipeline FP32
> diferente al de Matrix Cores. En FP16 con Matrix Cores alcanza ~97% del pico.
> A100 FP32 alcanza el pico porque usa Tensor Cores para FP32 desde Ampere.

### Interpretación

- **Alta utilización de Matrix/Tensor Cores** (>90%): indica que el benchmark
  está bien optimizado y la GPU está siendo usada eficientemente
- **Baja utilización FP32** (~50% en MI300X): normal para ciertas arquitecturas;
  el benchmark de FP32 refleja el rendimiento de shaders/CUDA cores
- **Si FP16 es mucho menor que el pico**: verificar que el dtype realmente
  esté usando Matrix Cores (no siempre ocurre automáticamente)

### FFT Throughput (GB/s)

La FFT 2D mide throughput de datos transformados por segundo. Valores de
referencia para transformada 2D de 2048x2048:

| GPU | FFT 2048 (GB/s) |
|-----|:---------------:|
| MI300X | ~1.2 TB/s |
| A100 | ~1.0 TB/s |
| H100 | ~1.5 TB/s |

### Convolution Throughput (TFLOPS)

Convolución 2D con kernel 3×3, input 1024×1024×64, output 128 canales:

| GPU | Conv2D (TFLOPS) |
|-----|:---------------:|
| MI300X | ~12.4 TFLOPS |
| A100 | ~14.1 TFLOPS |
| H100 | ~18.2 TFLOPS |

---

## 3. Inference Throughput (FPS / tokens/s)

### Qué mide

Cuántas inferencias por segundo puede procesar la GPU.

| Métrica | Descripción | Unidad |
|---------|-------------|--------|
| **FPS** (Frames Per Second) | Inferencias completadas por segundo | 1/s |
| **tokens/s** | Tokens generados por segundo (LLMs) | tokens/s |
| **Throughput** | Muestras procesadas por segundo (batch > 1) | samples/s |

### Cómo se mide

```python
model = MyModel().to("cuda")
input_data = torch.randn(batch_size, ...).to("cuda")
model.eval()

latencies = []
for _ in range(N):
    torch.cuda.synchronize()
    start = time.perf_counter()
    output = model(input_data)
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start
    latencies.append(elapsed)

avg_latency = mean(latencies)
fps = batch_size / avg_latency  # per-sample throughput
```

### Valores de Referencia (Dummy CNN — batch 32, 224×224×3)

| GPU | FPS | Latency p50 | Latency p95 |
|-----|:---:|:-----------:|:-----------:|
| MI300X | ~4,500 | ~7 ms | ~8 ms |
| A100 | ~5,200 | ~6 ms | ~7 ms |
| H100 | ~6,800 | ~4.7 ms | ~5.5 ms |
| RTX 4090 | ~3,200 | ~10 ms | ~11 ms |
| RX 7900 XTX | ~2,800 | ~11.4 ms | ~12.5 ms |

### Valores de Referencia (Dummy Transformer — batch 32, seq_len 128)

| GPU | FPS | Latency p50 | Latency p95 |
|-----|:---:|:-----------:|:-----------:|
| MI300X | ~950 | ~34 ms | ~38 ms |
| A100 | ~1,100 | ~29 ms | ~32 ms |
| H100 | ~1,500 | ~21 ms | ~24 ms |
| RTX 4090 | ~700 | ~46 ms | ~50 ms |

### Valores de Referencia (YOLOv8n — batch 1, 640×640)

| GPU | FPS | Latency p50 |
|-----|:---:|:-----------:|
| MI300X | ~1,800 | ~0.55 ms |
| A100 | ~2,100 | ~0.48 ms |
| H100 | ~2,800 | ~0.36 ms |
| RTX 4090 | ~1,400 | ~0.71 ms |

### Interpretación

- **Alto FPS + baja latencia**: GPU óptima para inferencia
- **Alto FPS + latencia alta pero estable**: buena para batch processing
- **Bajo FPS + alta latencia**: posible bottleneck en memory bandwidth o
  compute saturation
- **Variabilidad alta (p95 >> p50)**: indica problemas de scheduling,
  memory fragmentation, o thermal throttling

---

## 4. Latency (ms)

### Qué mide

El tiempo que tarda una operación individual en completarse.

| Métrica | Descripción |
|---------|-------------|
| **p50** (mediana) | Latencia típica — el 50% de las inferencias son más rápidas |
| **p95** | Latencia en el percentil 95 — impacto de outliers |
| **p99** | Latencia en el percentil 99 — peor caso (sin incluir extremos) |
| **Min/Max** | Valores extremos (min puede ser warming, max puede ser outlier) |

### Cómo interpretar

- **p50 ≈ p95 ≈ p99**: distribución muy homogénea → GPU estable, buena para
  aplicaciones en tiempo real
- **p95 >> p50**: hay factores intermitentes que causan lentitud:
  - Memory paging / swapping
  - Contention por recursos
  - Thermal throttling incipiente
  - Process scheduling noise
- **p99 >> p95**: outliers extremos → posible:
  - PCIe bandwidth contention
  - CPU no puede alimentar la GPU suficientemente rápido
  - Jitter del sistema operativo

### Regla general

| Aplicación | Latencia máxima aceptable |
|------------|:-------------------------:|
| Tiempo real (autonomous driving) | <10 ms |
| Interactive (chat, API) | <100 ms |
| Batch (offline processing) | <10 s |
| Training | Depende del step time |

---

## 5. VRAM Usage (GB)

### Qué mide

La memoria de la GPU utilizada por el modelo y los datos.

| Métrica | Descripción |
|---------|-------------|
| **Peak** | Máximo de VRAM usada durante el benchmark |
| **Delta** | VRAM adicional usada por el modelo (total - baseline) |
| **Utilization** | Porcentaje de VRAM total usado |

### Valores de Referencia

| Modelo | VRAM (FP32) | VRAM (FP16) |
|--------|:----------:|:-----------:|
| CNN dummy (4 conv layers) | ~0.8 GB | ~0.4 GB |
| Transformer dummy (4 layers, 768d) | ~1.2 GB | ~0.6 GB |
| YOLOv8n | ~0.8 GB | ~0.5 GB |
| YOLOv8x | ~7.2 GB | ~3.6 GB |
| LLaMA-7B (batch 1) | ~28 GB | ~14 GB |
| LLaMA-70B (batch 1) | ~280 GB | ~140 GB |

### Interpretación

- **Peak ≈ Total VRAM**: riesgo de OOM (Out of Memory). Reducir batch size
  o usar FP16/INT8.
- **Delta < 10% de VRAM total**: modelo pequeño para la GPU. Considerar
  aumentar batch size para mejor throughput.
- **VRAM usage creciente durante benchmark**: memory leak potencial en
  el modelo o en PyTorch.

---

## 6. Power Draw (W)

### Qué mide

El consumo eléctrico de la GPU.

| Métrica | Descripción |
|---------|-------------|
| **Idle** | Consumo sin carga (~25-50W para GPUs grandes) |
| **Load** | Consumo durante benchmark |
| **Peak** | Máximo consumo sostenido |
| **TDP** (Thermal Design Power) | Consumo máximo de diseño |

### Valores de Referencia

| GPU | Idle (W) | Load (W) | Peak (W) | TDP (W) |
|-----|:--------:|:--------:|:--------:|:-------:|
| MI300X | ~50W | ~300-350W | ~375W | 350W |
| MI250 | ~45W | ~450-500W | ~530W | 500W |
| A100 | ~40W | ~300-350W | ~380W | 400W |
| H100 | ~50W | ~350-650W | ~700W | 700W |
| RX 7900 XTX | ~25W | ~280-320W | ~340W | 355W |

### Interpretación

- **Power << TDP**: benchmark no está ejerciendo la GPU al máximo
- **Power = TDP sostenido**: GPU está siendo usada al máximo de su capacidad
- **Power > TDP**: posible overclocking o medición con tolerancia
- **Power cae durante stress test**: probable thermal throttling

---

## 7. Temperature (°C)

### Qué mide

La temperatura del die de la GPU (junction temperature).

| Métrica | Descripción |
|---------|-------------|
| **Idle** | Temperatura sin carga (~30-45°C) |
| **Load** | Temperatura durante benchmark |
| **Throttle point** | Temperatura donde el GPU comienza a reducir clock |
| **Critical** | Temperatura de shutdown de seguridad |

### Puntos de Throttle por GPU

| GPU | Throttle Start | Max Safe | Shutdown |
|-----|:--------------:|:--------:|:--------:|
| MI300X | ~85°C | ~95°C | ~100°C |
| MI250 | ~85°C | ~95°C | ~100°C |
| A100 | ~83°C | ~90°C | ~95°C |
| H100 | ~85°C | ~90°C | ~95°C |
| RX 7900 XTX | ~95°C | ~105°C (hotspot) | ~110°C |

### Interpretación

- **Temp < 70°C**: refrigeración adecuada
- **70-85°C**: rango normal bajo carga
- **85°C+**: cerca del throttle point. Verificar refrigeración.
- **Throttling confirmed**: si temp > throttle point Y clock baja

---

## 8. Clock Speed (MHz)

### Qué mide

La frecuencia de operación del GPU.

| Métrica | Descripción |
|---------|-------------|
| **Base clock** | Frecuencia mínima garantizada |
| **Boost clock** | Frecuencia máxima con refrigeración adecuada |
| **Sustained clock** | Frecuencia sostenida bajo carga continua |
| **Memory clock** | Frecuencia de la memoria HBM/GDDR |

### Valores de Referencia

| GPU | Base (MHz) | Boost (MHz) | Sustained (MHz) | Mem Clock (MHz) |
|-----|:----------:|:-----------:|:---------------:|:---------------:|
| MI300X | 1,000 | 1,750 | 1,650-1,700 | 1,200 (HBM3) |
| MI250 | 1,000 | 1,700 | 1,500-1,600 | 1,200 (HBM2e) |
| A100 | 765 | 1,410 | 1,380-1,410 | 1,215 (HBM2e) |
| H100 | 1,080 | 1,800 | 1,750-1,800 | 1,593 (HBM3) |
| RX 7900 XTX | 1,855 | 2,500 | 2,200-2,400 | 1,200 (GDDR6) |

### Interpretación

- **Sustained close to boost**: refrigeración excelente
- **Sustained ~10-15% below boost**: refrigeración adecuada
- **Sustained >> 15% below boost**: thermal throttling o power capping
- **Clock fluctuante**: posible power throttling o limitación de corriente
- **Memory clock bajo**: puede limitar bandwidth HBM

---

## Referencias

- [ROCm Documentation — rocm-smi](https://rocm.docs.amd.com/projects/rocm_smi_lib/en/latest/)
- [NVIDIA — nvidia-smi](https://developer.nvidia.com/nvidia-system-management-interface)
- [PyTorch — CUDA Semantics](https://pytorch.org/docs/stable/notes/cuda.html)
- [AMD — MI300X Architecture](https://www.amd.com/en/products/accelerators/instinct/mi300x.html)
