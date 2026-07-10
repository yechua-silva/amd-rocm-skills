# Patrones Multi-GPU — Skills que Funcionan en CUALQUIER Hardware

> Documento consolidado de investigación Fase 0 para el your project.
> Define patrones de detección y ejecución multi-GPU compatibles con NVIDIA CUDA, AMD ROCm y CPU fallback.

---

## 1. Detección de GPU — Script Python con 3 Niveles

### 1.1 Código Completo: detect_gpu_backend()

```python
#!/usr/bin/env python3
"""
Detecta el backend de GPU disponible: NVIDIA CUDA, AMD ROCm, o CPU fallback.
Uso: python detect_gpu_backend.py
Retorna: código de salida 0 (GPU detectada) o 1 (solo CPU)
"""

import os
import sys
import subprocess
import json


def detect_gpu_backend() -> dict:
    """
    Detecta el backend GPU disponible en el sistema.
    
    Returns:
        dict con keys:
          - available: bool, True si hay GPU
          - backend: str, "cuda" | "rocm" | "cpu"
          - device_count: int, número de GPUs detectadas
          - device_name: str, nombre del primer dispositivo
          - driver_version: str, versión del driver
          - torch_cuda: bool, si torch.cuda está disponible
          - torch_version: str, versión de torch
          - hip_version: str, versión de HIP (solo ROCm)
          - cuda_version: str, versión de CUDA (solo NVIDIA)
          - gfx_arch: str, arquitectura GFX (solo ROCm)
    """
    result = {
        "available": False,
        "backend": "cpu",
        "device_count": 0,
        "device_name": "",
        "driver_version": "",
        "torch_cuda": False,
        "torch_version": "",
        "hip_version": "",
        "cuda_version": "",
        "gfx_arch": "",
    }

    # ─────────────────────────────────────────────
    # Nivel 1: Detección via PyTorch
    # ─────────────────────────────────────────────
    try:
        import torch

        result["torch_version"] = torch.__version__
        result["torch_cuda"] = torch.cuda.is_available()

        if torch.cuda.is_available():
            result["available"] = True
            result["device_count"] = torch.cuda.device_count()
            result["device_name"] = torch.cuda.get_device_name(0)

            # Detectar si es ROCm o CUDA
            hip_ver = getattr(torch.version, "hip", None)
            cuda_ver = getattr(torch.version, "cuda", None)

            if hip_ver:
                result["backend"] = "rocm"
                result["hip_version"] = hip_ver
            elif cuda_ver:
                result["backend"] = "cuda"
                result["cuda_version"] = cuda_ver
            else:
                # Sin info de versión, asumir CUDA
                result["backend"] = "cuda"

            return result
    except ImportError:
        result["torch_version"] = "no instalado"

    # ─────────────────────────────────────────────
    # Nivel 2: Detección via comandos del sistema
    # ─────────────────────────────────────────────

    # Probar nvidia-smi (NVIDIA)
    try:
        nvidia_out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        if nvidia_out.returncode == 0 and nvidia_out.stdout.strip():
            lines = nvidia_out.stdout.strip().split("\n")
            result["available"] = True
            result["backend"] = "cuda"
            result["device_count"] = len(lines)
            first = lines[0].split(",")
            result["device_name"] = first[0].strip()
            result["driver_version"] = first[1].strip() if len(first) > 1 else ""
            return result
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Probar rocm-smi (AMD)
    try:
        rocm_out = subprocess.run(
            ["rocm-smi", "--showproductname", "--json"],
            capture_output=True, text=True, timeout=10
        )
        if rocm_out.returncode == 0 and rocm_out.stdout.strip():
            try:
                rocm_data = json.loads(rocm_out.stdout)
                card_list = rocm_data.get("list", [])
                if not card_list:
                    card_list = list(rocm_data.keys())
                result["available"] = True
                result["backend"] = "rocm"
                result["device_count"] = len(card_list)
                result["driver_version"] = rocm_data.get("version", "")
                return result
            except json.JSONDecodeError:
                pass
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Probar rocminfo para detectar arquitectura GFX (AMD)
    try:
        rocm_info = subprocess.run(
            ["rocminfo"],
            capture_output=True, text=True, timeout=10
        )
        if rocm_info.returncode == 0:
            for line in rocm_info.stdout.split("\n"):
                if "gfx" in line.lower():
                    # Extraer nombre de arquitectura
                    import re
                    match = re.search(r'(gfx\d+)', line)
                    if match:
                        result["gfx_arch"] = match.group(1)
            if result["gfx_arch"]:
                result["available"] = True
                result["backend"] = "rocm"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # ─────────────────────────────────────────────
    # Nivel 3: Fallback CPU
    # ─────────────────────────────────────────────
    return result


def print_report(info: dict) -> None:
    """Imprime un reporte legible de detección de GPU."""
    print("=" * 60)
    print("  AMD ROCm — GPU Detection Report")
    print("=" * 60)
    
    status = "✅ GPU DETECTADA" if info["available"] else "⚠️  SOLO CPU"
    print(f"  Estado:    {status}")
    print(f"  Backend:   {info['backend'].upper()}")
    print(f"  Device:    {info['device_name'] or 'N/A'}")
    print(f"  Devices:   {info['device_count']}")
    print(f"  Driver:    {info['driver_version'] or 'N/A'}")
    print(f"  Torch:     {info['torch_version'] or 'N/A'}")
    print(f"  Torch CUDA: {info['torch_cuda']}")
    
    if info["hip_version"]:
        print(f"  HIP ver:   {info['hip_version']}")
    if info["cuda_version"]:
        print(f"  CUDA ver:  {info['cuda_version']}")
    if info["gfx_arch"]:
        print(f"  GFX arch:  {info['gfx_arch']}")
    
    print("=" * 60)


if __name__ == "__main__":
    report = detect_gpu_backend()
    print_report(report)
    sys.exit(0 if report["available"] else 1)
```

### 1.2 Uso del Script

```bash
# Ejecutar detección
python detect_gpu_backend.py

# Salida típica (NVIDIA):
# ============================================================
#   AMD ROCm — GPU Detection Report
# ============================================================
#   Estado:    ✅ GPU DETECTADA
#   Backend:   CUDA
#   Device:    NVIDIA A100 80GB PCIe
#   Devices:   4
#   Driver:    535.154.05
#   Torch:     2.4.0+cu121
#   Torch CUDA: True
#   CUDA ver:  12.1
# ============================================================

# Salida típica (AMD ROCm):
# ============================================================
#   AMD ROCm — GPU Detection Report
# ============================================================
#   Estado:    ✅ GPU DETECTADA
#   Backend:   ROCM
#   Device:    AMD Instinct MI250
#   Devices:   8
#   Torch:     2.4.0+rocm6.1
#   Torch CUDA: True
#   HIP ver:   6.1.0
#   GFX arch:  gfx90a
# ============================================================

# Salida típica (CPU only):
# ============================================================
#   AMD ROCm — GPU Detection Report
# ============================================================
#   Estado:    ⚠️  SOLO CPU
#   Backend:   CPU
#   Device:    N/A
#   Torch:     2.4.0
#   Torch CUDA: False
# ============================================================
```

---

## 2. PyTorch Multi-Backend

### 2.1 La Regla Clave

**En PyTorch no existe `torch.rocm`**. La API `torch.cuda` funciona tanto para NVIDIA CUDA como para AMD ROCm. Esto es porque ROCm implementa la interfaz CUDA de PyTorch directamente.

```python
# ❌ INCORRECTO — No existe torch.rocm
# device = torch.rocm.current_device()  # Error!

# ✅ CORRECTO — Siempre usar torch.cuda
device = 'cuda' if torch.cuda.is_available() else 'cpu'
```

### 2.2 Patrón Universal de Device

```python
import torch

def get_device(prefer: str = "cuda") -> torch.device:
    """
    Obtiene el dispositivo óptimo disponible.
    
    Args:
        prefer: Dispositivo preferido ("cuda", "cpu")
    
    Returns:
        torch.device configurado
    """
    if prefer == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def get_device_info() -> dict:
    """Retorna información detallada del dispositivo actual."""
    import torch
    
    device = get_device()
    info = {
        "device": str(device),
        "is_cuda": device.type == "cuda",
        "device_count": torch.cuda.device_count() if device.type == "cuda" else 0,
        "device_name": "",
        "capability": "",
    }
    
    if device.type == "cuda":
        info["device_name"] = torch.cuda.get_device_name(0)
        info["capability"] = torch.cuda.get_device_capability(0)
        
        # Detectar backend
        if hasattr(torch.version, "hip") and torch.version.hip:
            info["backend"] = f"rocm-{torch.version.hip}"
        elif hasattr(torch.version, "cuda") and torch.version.cuda:
            info["backend"] = f"cuda-{torch.version.cuda}"
        else:
            info["backend"] = "cuda-unknown"
    
    return info
```

### 2.3 Diferencias CUDA vs ROCm

| Feature | NVIDIA CUDA | AMD ROCm | Notas |
|---------|-------------|----------|-------|
| **API principal** | `torch.cuda` | `torch.cuda` | Misma API, sin `torch.rocm` |
| **TF32** | ✅ Soportado | ❌ No soportado | `torch.backends.cuda.matmul.allow_tf32` |
| **bfloat16** | ✅ Nativo | ✅ Desde ROCm 5.0 | ROCm 6.x tiene soporte completo |
| **float16** | ✅ Soportado | ✅ Soportado | Recomendado en ROCm para training |
| **FP8** | ✅ H100+ | ❌ No soportado | Requiere hardware específico |
| **Flash Attention** | ✅ Nativo | ✅ Via flash-attn-rocm fork | Requiere compilar desde fuente |
| **torch.compile** | ✅ Inductor | ✅ Inductor (rocm-backend) | ROCm 6+ mejora significativa |
| **CUDA Graphs** | ✅ Soportado | ⚠️ Experimental | No estable en ROCm |
| **NCCL** | ✅ Nativo | ⚠️ RCCL (compatible) | RCCL implementa subset de NCCL API |
| **Tensor Cores** | ✅ Sí | ✅ Matrix Cores | MI300X tiene Matrix Cores |

### 2.4 Tensor Float 32 (TF32) — Solo CUDA

```python
# Activar TF32 (SOLO NVIDIA)
if torch.cuda.is_available() and torch.version.cuda:
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    # Mejora rendimiento ~50% en NVIDIA Ampere+
```

### 2.5 Detección de Backend en Código

```python
def is_rocm() -> bool:
    """Retorna True si el backend es AMD ROCm."""
    return hasattr(torch.version, "hip") and torch.version.hip is not None

def is_cuda_nvidia() -> bool:
    """Retorna True si el backend es NVIDIA CUDA (no ROCm)."""
    return (torch.cuda.is_available() and 
            not hasattr(torch.version, "hip"))

def get_torch_backend() -> str:
    """Retorna 'cuda' | 'rocm' | 'cpu'."""
    if not torch.cuda.is_available():
        return "cpu"
    if hasattr(torch.version, "hip") and torch.version.hip:
        return "rocm"
    return "cuda"
```

---

## 3. vLLM Multi-GPU

### 3.1 Imágenes Docker

| Backend | Imagen Docker | Tags |
|---------|--------------|------|
| **NVIDIA CUDA** | `vllm/vllm-openai` | `latest`, `v0.6.3`, `v0.6.2` |
| **AMD ROCm** | `vllm/vllm-openai-rocm` | `latest`, `rocm6.3`, `rocm6.2` |
| **CPU** | `vllm/vllm-openai` | `cpu` |

### 3.2 Comandos Docker

**NVIDIA CUDA:**
```bash
docker run --runtime nvidia --gpus all \
    -p 8000:8000 \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    vllm/vllm-openai:latest \
    --model mistralai/Mistral-7B-Instruct-v0.3
```

**AMD ROCm:**
```bash
docker run \
    --device=/dev/kfd \
    --device=/dev/dri \
    --group-add=render \
    -p 8000:8000 \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    vllm/vllm-openai-rocm:latest \
    --model mistralai/Mistral-7B-Instruct-v0.3
```

**⚠️ ROCm requiere Python 3.12:**
```bash
# Verificar versión de Python dentro del contenedor
docker run --device=/dev/kfd --device=/dev/dri \
    vllm/vllm-openai-rocm:latest \
    python3 --version
# Debe mostrar Python 3.12.x
```

**CPU Fallback:**
```bash
docker run -p 8000:8000 \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    vllm/vllm-openai:latest \
    vllm serve mistralai/Mistral-7B-Instruct-v0.3 --device cpu
```

### 3.3 Flags de Tensor Parallelism

```bash
# NVIDIA — TP funciona con NCCL
docker run --runtime nvidia --gpus all \
    vllm/vllm-openai:latest \
    --model meta-llama/Llama-2-70b-hf \
    --tensor-parallel-size 4

# AMD ROCm — TP funciona con RCCL
docker run --device=/dev/kfd --device=/dev/dri --group-add=render \
    vllm/vllm-openai-rocm:latest \
    --model meta-llama/Llama-2-70b-hf \
    --tensor-parallel-size 4
```

### 3.4 vLLM Config por Backend

```python
from vllm import LLM, SamplingParams

def create_llm(model_name: str, gpu_memory_utilization: float = 0.9):
    """
    Crea instancia vLLM con configuración óptima según backend disponible.
    """
    import torch
    
    # Detectar backend
    if torch.cuda.is_available():
        if hasattr(torch.version, "hip") and torch.version.hip:
            # Configuración ROCm
            return LLM(
                model=model_name,
                tensor_parallel_size=torch.cuda.device_count(),
                gpu_memory_utilization=gpu_memory_utilization,
                dtype="float16",  # ROCm prefiere float16 sobre bfloat16
                max_model_len=4096,
            )
        else:
            # Configuración NVIDIA
            return LLM(
                model=model_name,
                tensor_parallel_size=torch.cuda.device_count(),
                gpu_memory_utilization=gpu_memory_utilization,
                dtype="bfloat16",  # NVIDIA prefiere bfloat16
                max_model_len=4096,
            )
    else:
        # Fallback CPU
        return LLM(
            model=model_name,
            device="cpu",
            dtype="float32",
            max_model_len=2048,  # Menor longitud en CPU
        )
```

---

## 4. YOLO/Ultralytics Multi-Backend

### 4.1 Auto-detección via Device Parameter

Ultralytics YOLO detecta automáticamente el backend disponible:

```python
from ultralytics import YOLO

# Auto-detección: usa GPU si está disponible (NVIDIA o AMD)
model = YOLO("yolo11n.pt")
results = model("image.jpg")  # Usa GPU si disponible

# Explícito: forzar CUDA (funciona en NVIDIA y AMD ROCm)
model = YOLO("yolo11n.pt")
results = model("image.jpg", device="cuda:0")

# CPU fallback
model = YOLO("yolo11n.pt")
results = model("image.jpg", device="cpu")

# Múltiples GPUs
model = YOLO("yolo11n.pt")
results = model.train(data="coco8.yaml", device="cuda:0,1,2,3")
```

### 4.2 Export Formats

| Formato | NVIDIA CUDA | AMD ROCm | Intel | Notas |
|---------|-------------|----------|-------|-------|
| **ONNX** | ✅ | ✅ | ✅ | Universal, funciona en todos |
| **TensorRT** | ✅ | ❌ | ❌ | Exclusivo NVIDIA |
| **OpenVINO** | ❌ | ❌ | ✅ | Exclusivo Intel |
| **CoreML** | ✅ | ✅ | ✅ | Apple Silicon |
| **TorchScript** | ✅ | ✅ | ✅ | Universal |
| **NCNN** | ❌ | ❌ | ✅ | ARM/Embedded |

```python
from ultralytics import YOLO

model = YOLO("yolo11n.pt")

# Exportar a ONNX (funciona en cualquier backend)
model.export(format="onnx")

# Exportar a TensorRT (solo NVIDIA)
if torch.cuda.is_available() and not (hasattr(torch.version, "hip") and torch.version.hip):
    model.export(format="engine")  # TensorRT

# Exportar a OpenVINO (solo Intel CPU)
model.export(format="openvino")
```

### 4.3 Detección de Backend para YOLO

```python
def get_yolo_device() -> str:
    """Retorna el device óptimo para YOLO según backend disponible."""
    import torch
    
    if torch.cuda.is_available():
        return "cuda:0"  # Funciona con NVIDIA y AMD
    return "cpu"


# Uso
model = YOLO("yolo11n.pt")
results = model("video.mp4", device=get_yolo_device())
```

---

## 5. Docker Multi-GPU

### 5.1 Dockerfile Multi-Stage

```dockerfile
# ============================================================
# Dockerfile Multi-Stage: NVIDIA CUDA + AMD ROCm + CPU
# ============================================================

# ---- Base común ----
FROM python:3.12-slim AS base

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ---- Target: NVIDIA CUDA ----
FROM base AS cuda

# CUDA runtime ya incluido en imagen base con soporte CUDA
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=$CUDA_HOME/bin:$PATH
ENV LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

CMD ["python", "run.py"]

# ---- Target: AMD ROCm ----
FROM base AS rocm

# Instalar ROCm runtime
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/rocm6.2

ENV HCC_HOME=/opt/rocm
ENV ROCM_HOME=/opt/rocm
ENV PATH=$ROCM_HOME/bin:$PATH
ENV LD_LIBRARY_PATH=$ROCM_HOME/lib:$LD_LIBRARY_PATH

CMD ["python", "run.py"]

# ---- Target: CPU Fallback ----
FROM base AS cpu

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

CMD ["python", "run.py"]
```

**Build y uso:**

```bash
# Construir para NVIDIA
docker build --target cuda -t rocm-app:cuda .

# Construir para AMD
docker build --target rocm -t rocm-app:rocm .

# Construir para CPU
docker build --target cpu -t rocm-app:cpu .
```

### 5.2 Entrypoint.sh con Detección Automática

```bash
#!/bin/bash
# entrypoint.sh — Detecta backend y ejecuta comando correcto

set -e

echo "=== the application: Detectando backend GPU ==="

# Detectar NVIDIA
if command -v nvidia-smi &> /dev/null; then
    echo "✅ Backend NVIDIA CUDA detectado"
    export BACKEND=cuda
    exec python run.py --backend cuda "$@"
fi

# Detectar AMD ROCm
if command -v rocm-smi &> /dev/null || [ -d /opt/rocm ]; then
    echo "✅ Backend AMD ROCm detectado"
    export BACKEND=rocm
    exec python run.py --backend rocm "$@"
fi

# Detectar por dispositivos
if [ -e /dev/kfd ] || [ -e /dev/dri/render* ]; then
    # Podría ser ROCm incluso sin rocm-smi
    echo "⚠️  Posible GPU AMD detectada (dispositivos /dev/kfd o /dev/dri)"
    if python -c "import torch; print(torch.cuda.is_available())" 2>/dev/null | grep -q True; then
        echo "✅ PyTorch detecta GPU via torch.cuda"
        export BACKEND=rocm
        exec python run.py --backend rocm "$@"
    fi
fi

# Fallback CPU
echo "⚠️  No se detectó GPU — usando CPU"
export BACKEND=cpu
exec python run.py --backend cpu "$@"
```

### 5.3 docker-compose con Profiles

```yaml
# docker-compose.yml
version: "3.9"

services:
  rocm-app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    profiles:
      - nvidia
      - rocm
      - cpu

  # Perfil NVIDIA
  rocm-nvidia:
    extends: rocm-app
    build:
      target: cuda
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - BACKEND=cuda
    profiles: ["nvidia"]

  # Perfil AMD
  rocm-backend:
    extends: rocm-app
    build:
      target: rocm
    devices:
      - /dev/kfd
      - /dev/dri
    group_add:
      - render
    environment:
      - BACKEND=rocm
      - HSA_OVERRIDE_GFX_VERSION=11.0.0
    profiles: ["rocm"]

  # Perfil CPU
  generic-cpu:
    extends: rocm-app
    build:
      target: cpu
    environment:
      - BACKEND=cpu
    profiles: ["cpu"]
```

**Uso:**

```bash
# Levantar con NVIDIA
docker compose --profile nvidia up

# Levantar con AMD ROCm
docker compose --profile rocm up

# Levantar con CPU
docker compose --profile cpu up
```

---

## 6. Variables de Entorno

### 6.1 Tabla Completa

| Variable | Backend | Descripción | Ejemplo |
|----------|---------|-------------|---------|
| `CUDA_VISIBLE_DEVICES` | NVIDIA | Selecciona GPUs NVIDIA visibles | `0,1,2,3` |
| `HIP_VISIBLE_DEVICES` | AMD/ROCm | Selecciona GPUs AMD visibles | `0,1` |
| `ROCR_VISIBLE_DEVICES` | AMD/ROCm | Alternativa a HIP_VISIBLE_DEVICES | `0,1` |
| `HSA_OVERRIDE_GFX_VERSION` | AMD/ROCm | Override de arquitectura GFX | `11.0.0` (RX 7900) |
| `PYTORCH_ROCM_ARCH` | AMD/ROCm | Arquitecturas ROCm para compilación | `gfx90a;gfx942` |
| `HIPBLAS_WORKSPACE_CONFIG` | AMD/ROCm | Configuración de workspace HIPBLAS | `:512:8` |
| `ROCM_PATH` | AMD/ROCm | Ruta de instalación ROCm | `/opt/rocm` |
| `ROCM_HOME` | AMD/ROCm | Ruta home de ROCm | `/opt/rocm` |
| `NVIDIA_DRIVER_CAPABILITIES` | NVIDIA | Capacidades del driver NVIDIA | `compute,utility` |
| `NVIDIA_VISIBLE_DEVICES` | NVIDIA (Docker) | GPUs visibles en contenedor Docker | `all` |
| `OMP_NUM_THREADS` | CPU | Número de hilos OpenMP | `8` |
| `TORCH_HOME` | All | Cache de modelos PyTorch | `/app/cache/torch` |
| `XDG_CACHE_HOME` | All | Cache general | `/app/cache` |
| `HF_HOME` | All | Cache de HuggingFace | `/app/cache/huggingface` |
| `TRANSFORMERS_CACHE` | All | Cache de transformers | `/app/cache/transformers` |

### 6.2 Script de Configuración de Variables

```python
#!/usr/bin/env python3
"""
Configura variables de entorno óptimas según el backend detectado.
"""

import os
import torch


def configure_env():
    """Configura variables de entorno según backend disponible."""
    
    if not torch.cuda.is_available():
        # CPU — optimizar para CPU
        os.environ.setdefault("OMP_NUM_THREADS", str(os.cpu_count()))
        os.environ.setdefault("MKL_NUM_THREADS", str(os.cpu_count()))
        print(f"🔧 CPU: OMP_NUM_THREADS={os.environ['OMP_NUM_THREADS']}")
        return
    
    device_count = torch.cuda.device_count()
    device_name = torch.cuda.get_device_name(0)
    
    is_rocm = hasattr(torch.version, "hip") and torch.version.hip
    is_nvidia = not is_rocm
    
    if is_nvidia:
        # NVIDIA CUDA
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", ",".join(str(i) for i in range(device_count)))
        # TF32 optimizations
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        print(f"🔧 NVIDIA: CUDA_VISIBLE_DEVICES={os.environ['CUDA_VISIBLE_DEVICES']}")
        print(f"🔧 NVIDIA: TF32 activado")
    
    if is_rocm:
        # AMD ROCm
        os.environ.setdefault("HIP_VISIBLE_DEVICES", ",".join(str(i) for i in range(device_count)))
        os.environ.setdefault("HIPBLAS_WORKSPACE_CONFIG", ":512:8")
        print(f"🔧 AMD: HIP_VISIBLE_DEVICES={os.environ['HIP_VISIBLE_DEVICES']}")
        print(f"🔧 AMD: HIPBLAS_WORKSPACE_CONFIG={os.environ['HIPBLAS_WORKSPACE_CONFIG']}")
    
    print(f"🔧 GPU: {device_count}x {device_name}")
```

---

## 7. Compatibilidad ROCm por Arquitectura

### 7.1 Tabla de GPUs AMD Soportadas

| Arquitectura GFX | GPU | Nombre | ROCm Mínimo | Estado |
|:---:|------|--------|:---:|:------:|
| gfx900 | Vega 10 | MI25, WX 9100 | 5.0 | ✅ Soportado |
| gfx906 | Vega 20 | MI50, MI60 | 5.0 | ✅ Soportado |
| gfx908 | CDNA1 | MI100 | 5.0 | ✅ Soportado |
| gfx90a | CDNA2 | MI250, MI210 | 5.3 | ✅ Soportado |
| gfx940 | CDNA3 | MI300A | 6.0 | ✅ Soportado |
| gfx941 | CDNA3 | MI300X | 6.0 | ✅ Soportado |
| gfx942 | CDNA3 | MI300X (full) | 6.1 | ✅ Soportado |
| gfx950 | CDNA4 | MI350 | 6.3 | ✅ Soportado |
| gfx1030 | RDNA2 | RX 6800, 6900 | 5.0 | ✅ Soportado |
| gfx1031 | RDNA2 | RX 6700 | 5.0 | ⚠️ Parcial |
| gfx1100 | RDNA3 | RX 7600, 7700, 7800, 7900 XT/XTX | 6.0 | ✅ Soportado |
| gfx1101 | RDNA3 | RX 7900 GRE | 6.0 | ✅ Soportado |
| gfx1102 | RDNA3 | RX 7700 | 6.0 | ⚠️ Parcial |
| gfx1150 | RDNA3.5 | RX 8600, 8700 | 6.3 | ✅ Soportado |
| gfx1151 | RDNA3.5 | RX 8800, 8900 | 6.3 | ✅ Soportado |
| gfx1200 | RDNA4 | RX 9060 | 6.4 | ✅ Soportado |
| gfx1201 | RDNA4 | RX 9070, 9070 XT | 6.4 | ✅ Soportado |

### 7.2 Cómo Detectar la Arquitectura GFX

```bash
# Método 1: rocminfo (recomendado)
rocminfo | grep gfx

# Salida típica:
#   Name:                    gfx90a
#   Name:                    gfx90a

# Método 2: /proc/cpuinfo (no recomendado, inconsistente)
cat /proc/cpuinfo | grep gfx

# Método 3: Python con subprocess
python3 -c "
import subprocess
out = subprocess.run(['rocminfo'], capture_output=True, text=True)
for line in out.stdout.split('\n'):
    if 'gfx' in line.lower():
        print(line.strip())
"
```

### 7.3 HSA_OVERRIDE_GFX_VERSION

Para GPUs más nuevas no oficialmente soportadas, se puede usar `HSA_OVERRIDE_GFX_VERSION`:

```bash
# RX 7900 XTX (gfx1100) → simular gfx1030
export HSA_OVERRIDE_GFX_VERSION=10.3.0

# RX 9070 XT (gfx1201) → simular gfx1100
export HSA_OVERRIDE_GFX_VERSION=11.0.0

# Ejecutar con override
HSA_OVERRIDE_GFX_VERSION=11.0.0 python train.py
```

⚠️ **Advertencia**: Usar override puede causar inestabilidad o rendimiento subóptimo. Preferir siempre la versión oficial de ROCm que soporte la GPU.

---

## 8. Patrones de Fallback CPU

Cuando no hay GPU disponible, el sistema debe degradar gracefulmente. Aquí hay 4 capas de fallback.

### 8.1 PyTorch Genérico

```python
import torch
import torch.nn as nn

class ModelWithFallback:
    """Modelo que funciona en GPU (NVIDIA/AMD) o CPU."""
    
    def __init__(self, model: nn.Module):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = model.to(self.device)
    
    def predict(self, x: torch.Tensor) -> torch.Tensor:
        x = x.to(self.device)
        with torch.no_grad():
            # Reducir tamaño de batch en CPU si hay OOM
            if self.device.type == "cpu" and x.shape[0] > 16:
                outputs = []
                for i in range(0, x.shape[0], 16):
                    batch = x[i:i+16]
                    outputs.append(self.model(batch))
                return torch.cat(outputs, dim=0)
            return self.model(x)
```

### 8.2 vLLM con device="cpu"

```python
from vllm import LLM, SamplingParams

def create_vllm_any_backend(model_name: str):
    """Crea vLLM con el mejor backend disponible."""
    import torch
    
    if torch.cuda.is_available():
        # GPU (NVIDIA o AMD)
        return LLM(
            model=model_name,
            tensor_parallel_size=torch.cuda.device_count(),
            gpu_memory_utilization=0.9,
            dtype="bfloat16" if torch.cuda.is_bf16_supported() else "float16",
        )
    else:
        # CPU fallback
        return LLM(
            model=model_name,
            device="cpu",
            dtype="float32",
            max_model_len=2048,
            enforce_eager=True,  # Necesario para CPU
        )
```

### 8.3 HuggingFace Transformers

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

def load_model_any_backend(model_name: str):
    """Carga modelo HF con el mejor backend disponible."""
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Configuración de dtype según backend
    if device == "cuda":
        is_rocm = hasattr(torch.version, "hip") and torch.version.hip
        if is_rocm:
            dtype = torch.float16  # ROCm prefiere float16
        else:
            dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    else:
        dtype = torch.float32  # CPU siempre float32
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=dtype,
        device_map=device,
        low_cpu_mem_usage=True,
    )
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    return model, tokenizer


# Uso
model, tokenizer = load_model_any_backend("mistralai/Mistral-7B-Instruct-v0.3")
inputs = tokenizer("Hello!", return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=100)
```

### 8.4 ONNX Runtime Multi-Provider

ONNX Runtime permite ejecutar el mismo modelo en múltiples backends:

```python
import onnxruntime as ort

def create_onnx_session(model_path: str):
    """Crea sesión ONNX Runtime con el mejor provider disponible."""
    
    # Providers ordenados por preferencia
    providers = [
        ("CUDAExecutionProvider", {
            "device_id": 0,
        }),
        ("ROCMExecutionProvider", {
            "device_id": 0,
        }),
        ("CPUExecutionProvider", {}),
    ]
    
    # Filtrar providers no disponibles
    available = ort.get_available_providers()
    valid_providers = [
        p for p in providers 
        if any(p[0] in av for av in available)
    ]
    
    if not valid_providers:
        valid_providers = [("CPUExecutionProvider", {})]
    
    print(f"🔧 ONNX Runtime providers: {[p[0] for p in valid_providers]}")
    
    session = ort.InferenceSession(
        model_path,
        providers=valid_providers,
    )
    
    return session


# Uso
session = create_onnx_session("model.onnx")
input_name = session.get_inputs()[0].name
outputs = session.run(None, {input_name: input_data})
```

---

## Referencias

- [PyTorch — CUDA Semantics](https://pytorch.org/docs/stable/notes/cuda.html)
- [ROCm Documentation](https://rocm.docs.amd.com/)
- [vLLM — ROCm Installation](https://docs.vllm.ai/en/latest/getting_started/amd-installation.html)
- [Ultralytics — Multi-GPU Training](https://docs.ultralytics.com/yolov5/tutorials/multi_gpu_training/)
- [ONNX Runtime — Execution Providers](https://onnxruntime.ai/docs/execution-providers/)
- [Docker — GPU Support](https://docs.docker.com/config/containers/resource_constraints/#gpu)
