---
name: rocm-troubleshoot
description: >
  Diagnóstico integral de problemas con AMD ROCm (MI300X, MI250, RX 7900,
  RX 9070) y compatibilidad NVIDIA CUDA. Cubre: GPU no detectada,
  torch.cuda.is_available() False, Docker GPU passthrough falla, vLLM sin GPU,
  HSA_OVERRIDE_GFX_VERSION incorrecto, permisos /dev/kfd, OOM, rendimiento
  subóptimo. Incluye diagnóstico automático, checklist y referencia de errores
  con soluciones. Detecta conflictos ROCm vs NVIDIA. Keywords: rocm,
  troubleshoot, debug, diagnostic, gpu, amd, mi300x, mi250, rx7900, driver,
  error, fix, nvidia, cuda, docker, pytorch, vllm, yolo, hip, rocminfo,
  rocm-smi, /dev/kfd, HSA_OVERRIDE_GFX_VERSION, OOM, permission, compatibility,
  version-mismatch. Use this skill when diagnosing ROCm GPU errors, fixing
  PyTorch-ROCm issues, or troubleshooting AMD GPU detection problems. / Útil al
  diagnosticar errores de GPU ROCm, fixear PyTorch-ROCm, o troubleshoot de
  detección de GPU AMD.
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: "yechua-silva"
  tags:
    - amd
    - rocm
    - troubleshoot
    - debug
    - diagnostic
    - gpu
    - driver
    - error
    - fix
    - mi300x
    - nvidia
    - cuda
    - docker
    - pytorch
    - vllm
    - yolo
    - hip
    - compatibility
compatibility: >
  Compatible with Claude Code, OpenCode, Codex, Cursor, Cline, Roo Code,
  Windsurf, Gemini CLI, and Kiro CLI. Requires Linux with AMD or NVIDIA GPU,
  shell access, and package installation permissions.
---

# ROCm Troubleshoot Skill

Diagnóstico y resolución de problemas para el ecosistema **AMD ROCm**.
Esta skill es la guía definitiva para identificar, diagnosticar y solucionar
fallos en GPUs AMD (MI300X, MI250, RX 7900, RX 9070) y entornos mixtos
con NVIDIA CUDA. Construye sobre todas las skills previas del catalog of skills
(rocm-setup, rocm-docker, vllm-rocm-deploy, yolo-rocm-deploy, etc.) para
proporcionar un punto único de troubleshooting.

## Purpose

- **Diagnosticar** problemas GPU en sistemas AMD ROCm y NVIDIA CUDA
- **Resolver** fallos comunes: GPU no detectada, permisos, versiones, Docker, OOM
- **Verificar** compatibilidad entre componentes: ROCm ↔ PyTorch ↔ vLLM ↔ Python
- **Automatizar** la detección de errores con scripts de diagnóstico
- **Documentar** 30+ errores conocidos con causas raíz y soluciones probadas
- **Optimizar** rendimiento de GPUs AMD para cargas de trabajo ML/AI
- **Unificar** el troubleshooting disperso en una sola fuente de verdad

## When to Use / Cuándo Usar

La skill se activa con estos keywords y frases:

| Síntoma / Frase | Problema típico |
|-----------------|----------------|
| "ROCm not working / ROCm no funciona" | Instalación o driver corrupto |
| "GPU not detected / GPU no detectada" | amdgpu module, BIOS, PCIe |
| "torch.cuda.is_available() returns False" | PyTorch wheel incorrecto |
| "Docker GPU passthrough fails / Docker no ve GPU" | Flags faltantes, permisos |
| "vLLM ROCm error / vLLM no encuentra GPU" | Python version, wheel, dtype |
| "rocm-smi not found" | ROCm no instalado o PATH incorrecto |
| "HSA_OVERRIDE_GFX_VERSION incorrecto" | Valor wrong para la GPU |
| "permission denied /dev/kfd" | Grupos video/render |
| "ROCm performance bad / rendimiento bajo" | dtype, TF32, HIP_VISIBLE_DEVICES |
| "OOM ROCm / out of memory AMD GPU" | VRAM insuficiente, config |
| "debug AMD GPU / depurar GPU AMD" | Diagnóstico general |
| "troubleshoot ROCm / solucionar ROCm" | Entrada genérica |
| "YOLO ROCm not detecting GPU" | YOLO + ROCm incompatibilidad |
| "CUDA error: no kernel image" | Arquitectura GFX incorrecta |
| "Bfloat16 is not supported ROCm" | dtype float16 obligatorio en AMD |

## Prerequisites

- **Shell**: Acceso a terminal Bash (Linux)
- **ROCm**: Instalado o con posibilidad de instalar (`/opt/rocm`)
- **GPU**: AMD con soporte ROCm (MI300X, MI250, MI100, RX 7900, RX 9070)
  o NVIDIA con CUDA. La skill funciona sin GPU (modo CPU limitado).
- **Python 3.10+** recomendado (3.12 obligatorio para vLLM ROCm)
- **sudo**: Para instalación de drivers, módulos kernel y udev rules
- **Docker** (opcional): Para diagnosticar problemas en contenedores
- **Permisos**: Usuario en grupos `video` y `render` para acceso a GPU AMD

## Quickstart

### 1. Ejecutar Diagnóstico Automático

```bash
bash scripts/rocm-diagnostic.sh
```

Este script ejecuta TODAS las verificaciones disponibles y produce un
reporte completo del estado del sistema ROCm. Exit code: 0 = OK, 1 = warnings,
2 = errors. Para salida JSON: `bash scripts/rocm-diagnostic.sh --json`.

### 2. Identificar el Problema

Revisa el reporte. Las secciones en rojo (`❌`) son problemas críticos.
Las amarillas (`⚠️`) son advertencias. Busca el código de error en
[references/error-codes.md](references/error-codes.md) para causa raíz y
solución detallada.

### 3. Aplicar Solución

Usa el script de quick-fix para problemas comunes:

```bash
# Ver permisos /dev/kfd (sin -y solo muestra, con -y ejecuta)
bash scripts/quick-fix.sh --fix-kfd -y

# Agregar usuario a grupos video/render
bash scripts/quick-fix.sh --fix-groups -y

# Verificar compatibilidad de componentes
python3 scripts/check-compatibility.py
```

## Step-by-Step — Organizado por Problema

### 1. GPU no detectada por ROCm

**Síntomas:**
- `rocminfo` no lista ninguna GPU
- `rocm-smi` muestra "No AMD GPU detected"
- `lspci` sí muestra una GPU AMD pero ROCm no la ve

**Causas posibles:**
1. Módulo kernel `amdgpu` no cargado
2. BIOS sin Above 4G Decoding o Resizable BAR
3. Secure Boot bloqueando módulos del kernel
4. GPU no soportada por la versión ROCm instalada
5. GPU mal seated en el slot PCIe

**Pasos de diagnóstico:**

```bash
# 1. Verificar GPU en bus PCIe
lspci -nn | grep -iE "amd|radeon|nvidia" | grep -iE "vga|3d|display"

# 2. Verificar módulo amdgpu
lsmod | grep amdgpu || echo "amdgpu module NOT loaded"

# 3. Cargar módulo si es necesario
sudo modprobe amdgpu

# 4. Revisar firmware/mensajes del kernel
sudo dmesg | grep -i amdgpu | tail -30

# 5. Verificar BIOS recomendaciones
#    - Enable: Above 4G Decoding / Above 4G MMIO BIOS Assignment
#    - Enable: Resizable BAR / Re-Size BAR Support
#    - Disable: Secure Boot (firma módulos)
#    - PCIe Gen: Auto o forzar Gen4/Gen5
```

**Si la GPU aparece en lspci pero no en rocminfo**, puede ser:
- ROCm versión no soporta esa GPU → ver [references/error-codes.md](references/error-codes.md)
- GPU RDNA3+ necesita `HSA_OVERRIDE_GFX_VERSION` (ver problema 4)

**Solución:**

```bash
# Cargar módulo permanentemente
echo "amdgpu" | sudo tee /etc/modules-load.d/amdgpu.conf
sudo update-initramfs -u

# Verificar después de reinicio
sudo modprobe amdgpu && rocminfo | grep -E "Name:|gfx"
```

---

### 2. torch.cuda.is_available() = False

**Síntomas:**
- `torch.cuda.is_available()` devuelve `False`
- `torch.version.hip` es `None`
- La GPU se ve con `rocminfo` pero PyTorch no la detecta

**Causas posibles:**
1. PyTorch instalado desde rueda CUDA (default) en vez de ROCm
2. ROCm version mismatch con la rueda PyTorch
3. El usuario no tiene permisos sobre `/dev/kfd`
4. `HSA_OVERRIDE_GFX_VERSION` incorrecto bloqueando la detección

**Diagnóstico:**

```bash
# Verificar qué PyTorch está instalado
python3 -c "
import torch
print(f'Versión: {torch.__version__}')
print(f'HIP: {torch.version.hip}')
print(f'CUDA: {torch.version.cuda}')
print(f'CUDA available: {torch.cuda.is_available()}')
"

# Si ves "+cu118" o "+cu121" en la versión, es rueda CUDA
# Si ves "+rocm6.x", es rueda ROCm
```

**Solución:**

```bash
# Desinstalar PyTorch actual
pip uninstall torch torchvision torchaudio -y
pip cache purge

# Instalar desde el index ROCm correcto (match con ROCm versión)
pip install torch torchvision torchaudio \
  --index-url https://download.pytorch.org/whl/rocm6.2

# Verificar
python3 -c "import torch; print(torch.__version__); print(torch.version.hip)"
```

> **Importante**: No existe `torch.rocm`. ROCm usa `torch.cuda` API.
> Si `torch.cuda.is_available()` es True y `torch.version.hip` tiene valor,
> estás en ROCm. Si solo `torch.version.cuda` tiene valor, estás en CUDA.

**Tabla de compatibilidad ROCm ↔ PyTorch:**

| ROCm | PyTorch Wheel |
|------|---------------|
| 7.2.x | rocm6.2 |
| 7.1.x | rocm6.2 |
| 7.0.x | rocm6.2 |
| 6.3.x | rocm6.2 |
| 6.2.x | rocm6.1 |
| 6.1.x | rocm6.1 |
| 6.0.x | rocm6.0 |

---

### 3. Docker GPU Passthrough Falla

**Síntomas:**
- Contenedor no ve GPU AMD (`rocminfo` sin GPUs)
- Error: "permission denied while trying to connect to /dev/kfd"
- `torch.cuda.is_available()` es False dentro del contenedor

**Causas posibles:**
1. Se usó `--gpus all` (sintaxis NVIDIA, NO funciona en AMD)
2. Faltan flags `--device=/dev/kfd --device=/dev/dri`
3. Falta `--group-add=video` y `--group-add=render`
4. Módulo `amdgpu` no cargado en el host
5. Docker Engine sin soporte para dispositivos

**Solución — Flags correctos para AMD:**

```bash
docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --group-add=render \
  --ipc=host \
  --shm-size=16g \
  -e HIP_VISIBLE_DEVICES=0 \
  rocm/dev-ubuntu-22.04:latest \
  rocminfo
```

**Solución — Flags correctos para NVIDIA:**

```bash
docker run --rm \
  --runtime nvidia \
  --gpus all \
  nvidia/cuda:12.6.3-runtime-ubuntu22.04 \
  nvidia-smi
```

**Verificación dentro del contenedor:**

```bash
# AMD
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add=video \
  rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_2.10.0 \
  python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'Count: {torch.cuda.device_count()}')"

# NVIDIA
docker run --rm --runtime nvidia --gpus all \
  pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime \
  python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'Count: {torch.cuda.device_count()}')"
```

**docker-compose.yml para AMD:**

```yaml
services:
  rocm-app:
    image: rocm/pytorch:latest
    devices:
      - /dev/kfd
      - /dev/dri
    group_add:
      - video
      - render
    ipc: host
    shm_size: 16g
    environment:
      - HIP_VISIBLE_DEVICES=0,1
      - ROCM_HOME=/opt/rocm
```

**Diagnóstico Docker:**

```bash
# Verificar Docker Engine
docker --version

# Verificar que los dispositivos existen en host
ls -la /dev/kfd /dev/dri/render*

# Verificar grupos del usuario
groups $USER  # debe incluir video y render

# Verificar módulo amdgpu
lsmod | grep amdgpu
```

---

### 4. HSA_OVERRIDE_GFX_VERSION Incorrecto

**Síntomas:**
- PyTorch crashea al crear tensores en GPU
- Error: "HIP error: unknown error" o "invalid argument"
- `torch.cuda.is_available()` es True pero operaciones fallan
- vLLM falla con "no kernel image is available"

**Causas posibles:**
1. Valor de override incorrecto para la GPU
2. Override innecesario (GPU ya soportada por ROCm instalado)
3. Formato incorrecto (debe ser X.Y.Z, no gfxXXXX)

**Valores correctos:**

| GPU | GFX Real | ROCm mínimo | Override correcto |
|-----|:--------:|:-----------:|:-----------------:|
| MI300X | gfx942 | 6.1 | `9.4.2` (casi nunca necesario) |
| MI250 | gfx90a | 5.3 | `9.0.6` |
| MI100 | gfx908 | 5.0 | `9.0.8` |
| RX 7900 XTX | gfx1100 | 6.0 | `11.0.0` o `10.3.0` |
| RX 9070 XT | gfx1201 | 6.4 | `12.0.1` o `11.0.0` |
| RX 6800 XT | gfx1030 | 5.0 | `10.3.0` |

**⚠️ ERROR COMÚN**: Para MI300X (gfx942), el override es `9.4.2`, **NO** `11.0.0`.
`11.0.0` es para RDNA3 (RX 7900), no para CDNA3 (MI300X).

**Solución:**

```bash
# 1. Verificar arquitectura real
rocminfo | grep -E "^\s*Name:\s+gfx"

# 2. Si no necesitas override, eliminarlo
unset HSA_OVERRIDE_GFX_VERSION

# 3. Si necesitas override, usar valor correcto
export HSA_OVERRIDE_GFX_VERSION=9.4.2  # MI300X
# export HSA_OVERRIDE_GFX_VERSION=11.0.0  # RX 7900 XTX

# 4. Verificar en Python
python3 -c "
import torch
x = torch.randn(100, 100, device='cuda')
y = torch.mm(x, x)
print(f'Tensor en: {x.device}')
print(f'Matmul OK: {y.shape}')
"
```

**Regla de oro**: Si tu GPU está en la tabla de soporte de tu versión ROCm,
NO uses `HSA_OVERRIDE_GFX_VERSION`. Es solo para GPUs más nuevas que ROCm
instalado.

---

### 5. vLLM no Detecta GPU

**Síntomas:**
- `vllm serve ...` falla con "No ROCm GPU available"
- "ValueError: Bfloat16 is not supported on current device"
- vLLM se ejecuta pero usa CPU (muy lento)

**Causas posibles:**
1. Python no es 3.12.x (vLLM ROCm wheels solo para Python 3.12)
2. Se instaló la rueda vLLM CUDA en vez de ROCm
3. Falta `--dtype float16` (ROCm no soporta bfloat16)
4. GPU no visible por problemas de permisos

**Diagnóstico:**

```bash
# 1. Verificar Python version (DEBE ser 3.12.x)
python3 --version

# 2. Verificar qué vLLM está instalado
pip list 2>/dev/null | grep -i vllm

# 3. Verificar dtype
python3 -c "
import torch
print(f'Torch: {torch.__version__}')
print(f'HIP: {torch.version.hip}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'Device count: {torch.cuda.device_count()}')
"
```

**Solución:**

```bash
# 1. Usar Python 3.12 (OBLIGATORIO para vLLM ROCm)
uv venv --python 3.12  # o pyenv/conda
source .venv/bin/activate

# 2. Instalar vLLM ROCm wheel
pip install vllm --extra-index-url https://wheels.vllm.ai/rocm/

# 3. Ejecutar con dtype correcto
python3 -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.3 \
  --dtype float16 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 4096
```

**En Docker:**

```bash
# Usar imagen oficial ROCm
docker run --rm \
  --device=/dev/kfd --device=/dev/dri --group-add=render \
  --cap-add=SYS_PTRACE --security-opt seccomp=unconfined \
  -p 8000:8000 \
  vllm/vllm-openai-rocm:latest \
  --model mistralai/Mistral-7B-Instruct-v0.3 \
  --dtype float16
```

> **Nota**: Si `pip install vllm` instala silenciosamente la rueda CUDA,
> es porque NO estás en Python 3.12. Las ruedas ROCm de vLLM solo existen
> para Python 3.12. Verifica con `python3 --version`.

---

### 6. PyTorch Instaló Rueda CUDA en Vez de ROCm

**Síntomas:**
- `pip install torch` instala versión `+cu121` o `+cu118`
- `torch.version.hip` es `None`
- GPU AMD funciona con `rocminfo` pero PyTorch no la usa

**Causas:**
- Por defecto PyPI distribuye ruedas CUDA
- No se usó `--index-url` con el wheel ROCm
- Incluso con NVIDIA driver presente, pip puede elegir la rueda equivocada

**Solución:**

```bash
# 1. Desinstalar todo
pip uninstall torch torchvision torchaudio -y
pip cache purge

# 2. Instalar desde AMD index
pip install torch torchvision torchaudio \
  --index-url https://download.pytorch.org/whl/rocm6.2

# 3. Verificar
python3 -c "
import torch
print(f'Version: {torch.__version__}')   # Debe decir +rocm6.2
print(f'HIP: {torch.version.hip}')        # Debe ser 6.2.0
print(f'CUDA: {torch.version.cuda}')      # Debe ser None
print(f'CUDA available: {torch.cuda.is_available()}')
"
```

**Para requirements.txt:**

```bash
# No se puede especificar index-url por paquete en requirements.txt
# Usar un script de instalación:
pip install -r requirements.txt \
  --index-url https://download.pytorch.org/whl/rocm6.2
```

---

### 7. Permission Denied /dev/kfd

**Síntomas:**
- `rocminfo` falla con "Permission denied"
- Error al importar PyTorch: "could not open /dev/kfd"
- `python3 -c "import torch; torch.cuda.is_available()"` retorna False

**Causas:**
- Usuario no pertenece a los grupos `video` o `render`
- Los dispositivos `/dev/kfd` y `/dev/dri/render*` pertenecen al grupo `render`

**Diagnóstico:**

```bash
# Verificar permisos de dispositivos
ls -la /dev/kfd
# Debe mostrar: crw-rw---- 1 root render ...

ls -la /dev/dri/render*
# Debe mostrar: crw-rw---- 1 root render ...

# Verificar grupos del usuario
groups $USER
# Debe incluir "video" y "render"
```

**Solución:**

```bash
# Agregar usuario a grupos
sudo usermod -a -G video,render $USER

# Aplicar cambios sin cerrar sesión
newgrp video
newgrp render

# Verificar acceso
ls -la /dev/kfd
python3 -c "import torch; print(torch.cuda.is_available())"
```

**Para Docker:**

```bash
docker run --rm \
  --device=/dev/kfd --device=/dev/dri \
  --group-add=video --group-add=render \
  rocm/dev-ubuntu-22.04:latest \
  ls -la /dev/kfd
```

**Si el problema persiste**, reinstalar udev rules:

```bash
bash scripts/quick-fix.sh --fix-kfd -y
```

---

### 8. ROCm Version Mismatch

**Síntomas:**
- Error al compilar kernels ROCm
- Advertencias de versión al iniciar PyTorch
- `rocminfo` muestra una versión pero PyTorch espera otra

**Causas posibles:**
1. ROCm drivers versión X pero PyTorh compilado para ROCm Y
2. Múltiples versiones de ROCm instaladas
3. `LD_LIBRARY_PATH` apunta a versión incorrecta

**Diagnóstico:**

```bash
# Versión instalada de ROCm (drivers)
cat /opt/rocm/share/doc/rocm-version/version 2>/dev/null || \
  dpkg -l rocm-libs 2>/dev/null | grep rocm-libs | awk '{print $3}'

# Versión que PyTorch espera
python3 -c "import torch; print(f'HIP: {torch.version.hip}')"

# Ejecutar compatibility check
python3 scripts/check-compatibility.py
```

**Solución:**

```bash
# Si hay mismatch, reinstalar PyTorch con la versión correcta
# ROCm 7.2.x → rocm6.2 wheels
pip install torch --index-url https://download.pytorch.org/whl/rocm6.2

# Si hay múltiples instalaciones, limpiar y reinstalar
sudo apt remove --purge rocm-* rocm-libs-* amdgpu-install
sudo rm -rf /opt/rocm*
sudo apt autoremove
# Reinstalar desde cero
```

---

### 9. OOM (Out of Memory)

**Síntomas:**
- Error: "CUDA out of memory" o "HIP out of memory"
- vLLM falla con "OutOfMemoryError"
- Contenedor se mata con exit code 137 (OOM killer)
- YOLO falla al cargar modelo en GPU

**Causas posibles:**
1. VRAM insuficiente para el modelo y batch size
2. `gpu_memory_utilization` demasiado alto
3. `max_model_len` demasiado grande para la VRAM disponible
4. Fragmentación de memoria

**Solución para PyTorch:**

```bash
# Reducir batch size
python3 train.py --batch-size 4  # en vez de 16 o 32

# Liberar memoria
python3 -c "
import torch
torch.cuda.empty_cache()
print(f'Memoria liberada. Free: {torch.cuda.mem_get_info()[0]/1e9:.2f} GB')
"

# Usar gradient accumulation
# trainer = Trainer(..., gradient_accumulation_steps=4)
```

**Solución para vLLM:**

```bash
# Reducir utilización de VRAM
python3 -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.3 \
  --gpu-memory-utilization 0.80 \
  --max-model-len 2048 \
  --max-num-seqs 128

# En Docker con límite
docker run ... --memory=64g --memory-swap=64g \
  vllm/vllm-openai-rocm:latest \
  --gpu-memory-utilization 0.75
```

**Solución para YOLO ROCm:**

```bash
# Reducir batch e imagen size
python3 train.py --batch 8 --img 640

# Usar half precision
python3 train.py --batch 8 --img 640 --half
```

**Verificar VRAM disponible:**

```bash
# AMD
rocm-smi --showmeminfo vram

# NVIDIA
nvidia-smi --query-gpu=memory.free,memory.total --format=csv

# PyTorch
python3 -c "
import torch
free, total = torch.cuda.mem_get_info()
print(f'VRAM: {free/1e9:.2f} GB free / {total/1e9:.2f} GB total')
"
```

---

### 10. Rendimiento Subóptimo

**Síntomas:**
- GPU AMD rinde significativamente menos que NVIDIA comparable
- Throughput bajo en inferencia vLLM
- Training lento comparado con benchmarks
- GPU utilization baja (< 80%)

**Causas posibles:**
1. `dtype` incorrecto (bfloat16 no es óptimo en ROCm)
2. TF32 no está soportado en ROCm (es NVIDIA-only)
3. `HIP_VISIBLE_DEVICES` limita GPUs disponibles
4. Falta `torch.compile` optimización
5. Kernel compilation overhead en primera ejecución

**Diagnóstico:**

```bash
# Verificar utilización GPU
rocm-smi  # AMD
watch -n 1 rocm-smi  # Monitoreo en tiempo real

# Verificar dtype disponible
python3 -c "
import torch
print(f'ROCm soporta bf16: {torch.cuda.is_bf16_supported()}')
print(f'ROCm soporta fp16: {torch.cuda.is_bf16_supported()}')  # Sí, siempre
"
```

**Soluciones:**

```bash
# 1. Usar float16 SIEMPRE en ROCm (nunca bfloat16)
--dtype float16  # vLLM
model.half()     # PyTorch

# 2. Habilitar torch.compile (reduce overhead)
model = torch.compile(model)

# 3. Configurar HIPBLAS workspace
export HIPBLAS_WORKSPACE_CONFIG=:512:8

# 4. Usar channels_last memory format
model = model.to(memory_format=torch.channels_last)

# 5. Desactivar TF32 (no usado en ROCm pero evita confusión)
unset TORCH_ALLOW_TF32_CUBLAS_OVERRIDE

# 6. Aumentar num_workers en DataLoader
DataLoader(..., num_workers=8, pin_memory=True)
```

**Tabla de dtype recomendado:**

| Backend | dtype óptimo | dtype soportados | Notas |
|---------|-------------|------------------|-------|
| AMD ROCm | float16 | float16, float32 | bfloat16 no recomendado (sin soporte nativo) |
| NVIDIA CUDA | bfloat16 | float16, bfloat16, float32, TF32 | TF32 exclusive NVIDIA |
| CPU | float32 | float32 | Único dtype universal |

---

### 11. YOLO no Detecta GPU con ROCm

**Síntomas:**
- `yolo train` o `yolo predict` falla con error de CUDA
- Ultralytics YOLO no ve GPU AMD
- Error: "torch.cuda.is_available() is False" al ejecutar YOLO

**Causas:**
- Ultralytics YOLO espera CUDA API (funciona con ROCm pero necesita configuración)
- PyTorch no detecta ROCm (rueda incorrecta)
- `device='cuda'` explícito pero HIP no disponible

**Solución:**

```bash
# 1. Verificar PyTorch ROCm
python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'HIP: {torch.version.hip}')"

# 2. Si torch.cuda disponible, YOLO debería funcionar
yolo train model=yolo11n.pt data=coco8.yaml device=0 epochs=1

# 3. Si falla, forzar device explícitamente
python3 -c "
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
results = model.train(data='coco8.yaml', device='cuda:0', epochs=1)
"

# 4. Verificar dtype (usar float16)
python3 -c "
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
model.to('cuda').half()  # Usar half precision
"
```

---

### 12. Variables de Entorno Mal Configuradas

**Síntomas:**
- La app ve más o menos GPUs de las esperadas
- Error: "HIP_VISIBLE_DEVICES is set but no matching devices"
- GPUs no visibles en orden esperado
- Conflictos entre HIP_VISIBLE_DEVICES y CUDA_VISIBLE_DEVICES

**Variables clave:**

| Variable | Propósito | Ejemplo |
|----------|-----------|---------|
| `HIP_VISIBLE_DEVICES` | Selecciona GPUs AMD | `0,1,2,3` |
| `ROCR_VISIBLE_DEVICES` | Alternativa (equivalente) | `0,1` |
| `CUDA_VISIBLE_DEVICES` | Portátil AMD/NVIDIA | `0,1` |
| `HSA_OVERRIDE_GFX_VERSION` | Override arquitectura | `9.4.2` |
| `HIPBLAS_WORKSPACE_CONFIG` | Config workspace HIPBLAS | `:512:8` |
| `ROCM_HOME` / `ROCM_PATH` | Ruta instalación ROCm | `/opt/rocm` |
| `LD_LIBRARY_PATH` | Librerías ROCm | debe incluir `/opt/rocm/lib` |

**Orden de precedencia:**
1. `HIP_VISIBLE_DEVICES` (más específica de ROCm)
2. `ROCR_VISIBLE_DEVICES` (alternativa equivalente)
3. `CUDA_VISIBLE_DEVICES` (portátil, funciona en ambos)

**Solución:**

```bash
# Verificar variables actuales
env | grep -iE "hip|rocm|cuda|hsa" || echo "No ROCm/CUDA env vars"

# Configurar en ~/.bashrc o entrypoint
export HIP_VISIBLE_DEVICES=0,1,2,3
export ROCR_VISIBLE_DEVICES=0,1,2,3
export HIPBLAS_WORKSPACE_CONFIG=:512:8
export ROCM_HOME=/opt/rocm
export ROCM_PATH=/opt/rocm

# Verificar efecto
python3 -c "
import os, torch
print('HIP_VISIBLE_DEVICES:', os.environ.get('HIP_VISIBLE_DEVICES', '(not set)'))
print('Devices:', torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    print(f'  [{i}] {torch.cuda.get_device_name(i)}')
"
```

---

## Tabla de Errores Comunes

| Código / Mensaje | Causa Raíz | Solución | Skill Relacionada |
|-----------------|------------|----------|-------------------|
| `rocminfo: No AMD GPU detected` | amdgpu module no cargado, GPU no visible | `sudo modprobe amdgpu`, verificar BIOS | rocm-setup |
| `CUDA error: no kernel image is available` | GFX arch mismatch en compilación de kernels | Verificar `HSA_OVERRIDE_GFX_VERSION` | rocm-setup |
| `torch.cuda.is_available() = False` | PyTorch wheel CUDA en vez de ROCm | `pip install --index-url https://download.pytorch.org/whl/rocm6.2` | rocm-setup |
| `HIP error: hipErrorNoDevice` | No GPU visible para HIP | Verificar `/dev/kfd`, grupos, `rocminfo` | rocm-troubleshoot |
| `HIP error: hipErrorOutOfMemory` | VRAM insuficiente | Reducir batch, `gpu_memory_utilization` | rocm-troubleshoot |
| `ValueError: Bfloat16 is not supported` | ROCm no soporta bfloat16 | Usar `--dtype float16` | vllm-rocm-deploy |
| `vLLM: No ROCm GPU available` | Python no es 3.12 o wheel incorrecto | Usar Python 3.12, `--extra-index-url` ROCm | vllm-rocm-deploy |
| `Docker: permission denied /dev/kfd` | Usuario no en grupo render | `sudo usermod -aG render $USER` | rocm-docker |
| `Docker: unknown flag: --device` | Versión antigua de Docker | Actualizar Docker Engine 24+ | rocm-docker |
| `RuntimeError: HIP error: invalid argument` | `HSA_OVERRIDE_GFX_VERSION` incorrecto | Usar valor correcto para la GPU (ej: `9.4.2` para MI300X) | rocm-troubleshoot |
| `pyTorch: version 'rocm6.x' not found` | Mismatch ROCm vs PyTorch wheel | Match versiones (ROCm 7.2 → rocm6.2 wheels) | rocm-setup |
| `YOLO: CUDA unavailable` | PyTorch no detecta GPU ROCm | Instalar PyTorch ROCm wheel | yolo-rocm-deploy |
| `OOM killer: exit code 137` | Contenedor sin límite de memoria | `--memory=64g --memory-swap=64g` | rocm-docker |
| `ModuleNotFoundError: vllm` | vLLM no instalado en contenedor | Usar `vllm/vllm-openai-rocm:latest` | vllm-rocm-deploy |
| `flash-attn: nvcc not found` | Código CUDA nativo incompatible con ROCm | Usar fork ROCm: `git clone https://github.com/ROCm/flash-attention.git` | rocm-troubleshoot |
| `HSA_OVERRIDE_GFX_VERSION=11.0.0` crash | MI300X con override de RDNA3 | Cambiar a `9.4.2` o eliminar override | rocm-troubleshoot |
| `rocm-smi not found` | ROCm tools no instalados | `sudo amdgpu-install --usecase=rocm` | rocm-setup |
| `nvidia-smi not found` | NVIDIA driver no instalado | `sudo apt install nvidia-driver-545` | rocm-setup |

## Reference Documents

| Documento | Descripción |
|-----------|-------------|
| [references/error-codes.md](references/error-codes.md) | Base de datos de 30+ errores ROCm con causas y soluciones |
| [references/optimization-checklist.md](references/optimization-checklist.md) | Checklist de optimización: BIOS, software, PyTorch, Docker |
| [references/quick-reference.md](references/quick-reference.md) | Referencia rápida de 1 página: comandos, variables, equivalencias |

## Scripts

| Script | Propósito | Uso |
|--------|-----------|-----|
| `scripts/rocm-diagnostic.sh` | Diagnóstico maestro: GPU, kernel, ROCm, Docker, PyTorch, vLLM, env vars. Exit 0=ok, 1=warnings, 2=errors. | `bash scripts/rocm-diagnostic.sh` |
| `scripts/rocm-diagnostic.sh --json` | Igual que arriba pero con salida JSON parseable | `bash scripts/rocm-diagnostic.sh --json` |
| `scripts/quick-fix.sh` | Soluciones rápidas: `--fix-kfd`, `--fix-groups`, `--fix-hip-version`, `--fix-docker`. Sin `-y` solo muestra. | `bash scripts/quick-fix.sh --fix-groups --fix-kfd -y` |
| `scripts/check-compatibility.py` | Verifica compatibilidad ROCm ↔ PyTorch ↔ vLLM ↔ Python ↔ GPU. Reporta qué match y qué no. | `python3 scripts/check-compatibility.py` |

## Common Issues

### 1. GPU no detectada por ROCm
- **Causa**: Módulo amdgpu no cargado, BIOS mal configurada, GPU no soportada
- **Solución**: `sudo modprobe amdgpu`, verificar Above 4G Decoding + Resizable BAR en BIOS

### 2. torch.cuda.is_available() retorna False con GPU AMD
- **Causa**: PyTorch instaló rueda CUDA (default de PyPI)
- **Solución**: `pip install torch --index-url https://download.pytorch.org/whl/rocm6.2`

### 3. Docker container no ve GPU AMD
- **Causa**: Se usó `--gpus all` (NVIDIA syntax) en vez de `--device=/dev/kfd --device=/dev/dri`
- **Solución**: Usar los flags correctos para AMD

### 4. vLLM falla con "Bfloat16 is not supported"
- **Causa**: ROCm no soporta bfloat16 nativamente
- **Solución**: Forzar `--dtype float16` en vLLM

### 5. Permission denied al acceder a /dev/kfd
- **Causa**: Usuario no está en grupo `render`
- **Solución**: `sudo usermod -aG video,render $USER && newgrp render`

### 6. vLLM no detecta GPU ROCm
- **Causa**: Python no es 3.12.x (ruedas ROCm solo para 3.12)
- **Solución**: Crear entorno con Python 3.12 y reinstalar vLLM

### 7. HSA_OVERRIDE_GFX_VERSION incorrecto para MI300X
- **Causa**: Usar `11.0.0` (RDNA3) en vez de `9.4.2` (CDNA3)
- **Solución**: `export HSA_OVERRIDE_GFX_VERSION=9.4.2` o eliminar override

### 8. ROCm version mismatch con PyTorch
- **Causa**: ROCm 7.2 pero PyTorch espera ROCm 6.1 (o viceversa)
- **Solución**: Usar `python3 scripts/check-compatibility.py` para detectar mismatch

### 9. OOM en inferencia vLLM
- **Causa**: `gpu_memory_utilization` demasiado alto para VRAM disponible
- **Solución**: Reducir a `--gpu-memory-utilization 0.80` y `--max-model-len 2048`

### 10. Rendimiento GPU AMD bajo comparado con NVIDIA
- **Causa**: Uso de bfloat16 o falta de `torch.compile`
- **Solución**: Usar `--dtype float16`, habilitar `torch.compile`, configurar `HIPBLAS_WORKSPACE_CONFIG`

### 11. YOLO no detecta GPU con ROCm
- **Causa**: PyTorch sin soporte ROCm o Ultralytics configurado para CUDA
- **Solución**: Verificar `torch.cuda.is_available()` y usar `device='cuda:0'` explícito

### 12. Error al compilar flash-attention en ROCm
- **Causa**: Código CUDA nativo incompatible con HIP
- **Solución**: Usar fork oficial de ROCm: `pip install git+https://github.com/ROCm/flash-attention.git`

## Related Skills

- [`rocm-setup`](../rocm-setup/SKILL.md) — ROCm installation and verification
- [`rocm-docker`](../rocm-docker/SKILL.md) — Docker with AMD GPU passthrough
- [`rocm-benchmark`](../rocm-benchmark/SKILL.md) — GPU benchmarking and monitoring
