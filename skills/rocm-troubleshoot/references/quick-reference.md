# ROCm Quick Reference — 1-Page Reference

Comandos, variables y equivalencias rápidas para el ecosistema AMD ROCm.
Para imprimir o tener en terminal como referencia rápida.

---

## Comandos Esenciales

```bash
# ── Diagnóstico Rápido ────────────────────────────────────────
rocminfo                    # Info detallada de GPUs AMD
rocm-smi                    # Monitoreo de GPUs AMD (nvidia-smi equivalent)
rocm-smi --showproductname  # Nombres de GPUs
rocm-smi --showmeminfo vram # VRAM usage
rocm-smi --showtemp         # Temperaturas
rocm-smi --showusage        # GPU utilization
rocm-smi --showpower        # Consumo eléctrico
rocm-smi --showtopo         # Topología GPU
hipconfig                   # Configuración HIP
hipconfig --version         # Versión HIP
clinfo                      # OpenCL info

# ── NVIDIA equivalents (si aplica) ────────────────────────────
nvidia-smi                  # Monitoreo NVIDIA
nvidia-smi -L               # Listar GPUs NVIDIA

# ── Módulo Kernel ──────────────────────────────────────────────
lsmod | grep amdgpu         # Verificar módulo cargado
sudo modprobe amdgpu        # Cargar módulo manualmente

# ── Dispositivos ───────────────────────────────────────────────
ls -la /dev/kfd             # KFD device (AMD GPU)
ls -la /dev/dri/render*     # Render nodes (AMD GPU)
ls -la /dev/dri/card*       # Card nodes (AMD GPU)

# ── PCIe ───────────────────────────────────────────────────────
lspci | grep -iE "vga|3d|display"  # Ver GPUs en PCIe
lspci -nn | grep -i amd             # Dispositivos AMD en PCIe

# ── ROCm Version ───────────────────────────────────────────────
cat /opt/rocm/share/doc/rocm-version/version
dpkg -l rocm-libs | grep rocm-libs | awk '{print $3}'

# ── PyTorch ────────────────────────────────────────────────────
python3 -c "
import torch
print(f'Torch: {torch.__version__}')
print(f'HIP: {torch.version.hip}')
print(f'CUDA: {torch.version.cuda}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print(f'  [{i}] {torch.cuda.get_device_name(i)}')
    f, t = torch.cuda.mem_get_info()
    print(f'VRAM: {f/1e9:.2f} GB free / {t/1e9:.2f} GB total')
"

# ── vLLM ───────────────────────────────────────────────────────
python3 --version           # Debe ser 3.12.x para vLLM ROCm
pip list | grep -i vllm     # Ver vLLM instalado
```

---

## Variables de Entorno Clave

| Variable | Propósito | Valor Típico | Notas |
|----------|-----------|-------------|-------|
| `HIP_VISIBLE_DEVICES` | Seleccionar GPUs AMD | `0,1,2,3` | Más específica de ROCm |
| `ROCR_VISIBLE_DEVICES` | Alternativa selección | `0,1,2,3` | Equivalente a HIP_VISIBLE_DEVICES |
| `CUDA_VISIBLE_DEVICES` | Portátil AMD/NVIDIA | `0,1` | Funciona en ambos backends |
| `HSA_OVERRIDE_GFX_VERSION` | Override GFX arch | `9.4.2` (MI300X) | Solo si necesario |
| `HIPBLAS_WORKSPACE_CONFIG` | Config HIPBLAS | `:512:8` | Mejora rendimiento GEMM |
| `ROCM_HOME` | Ruta ROCm | `/opt/rocm` | Usado por herramientas ROCm |
| `ROCM_PATH` | Ruta ROCm | `/opt/rocm` | Alternativa a ROCM_HOME |
| `LD_LIBRARY_PATH` | Librerías dinámicas | `/opt/rocm/lib` | Debe incluir ROCm libs |
| `NCCL_SOCKET_IFNAME` | Interfaz multi-GPU | `ib0` o `eth0` | Para RCCL/NCCL |
| `TORCH_ALLOW_TF32_CUBLAS_OVERRIDE` | TF32 override | No usar en ROCm | TF32 es solo NVIDIA |

### Orden de Precedencia (selección de GPUs):
1. `HIP_VISIBLE_DEVICES` (más específica)
2. `ROCR_VISIBLE_DEVICES` (alternativa)
3. `CUDA_VISIBLE_DEVICES` (portátil)
4. Si ninguna: todas las GPUs detectadas son visibles

---

## Equivalencias Rápidas NVIDIA ↔ AMD

| Concepto | NVIDIA CUDA | AMD ROCm |
|----------|-------------|----------|
| Driver | nvidia-smi | rocm-smi |
| GPU info | nvidia-smi -q | rocminfo |
| Toolkit | CUDA Toolkit | ROCm |
| GPU language | CUDA | HIP (≈ CUDA) |
| Compiler | nvcc | hipcc |
| Library | cuBLAS | rocBLAS |
| DNN | cuDNN | MIOpen |
| FFT | cuFFT | rocFFT |
| Random | cuRAND | rocRAND |
| Sparse | cuSPARSE | rocSPARSE |
| Multi-GPU | NCCL | RCCL |
| TensorRT | TensorRT | MIGraphX |
| Device selection | CUDA_VISIBLE_DEVICES | HIP_VISIBLE_DEVICES |
| TF32 | ✅ Soportado | ❌ No soportado |
| bfloat16 | ✅ Nativo | ⚠️ Limitado |
| float16 | ✅ | ✅ Recomendado |
| PyTorch dtype | bfloat16 | float16 |
| Docker flag | --gpus all | --device=/dev/kfd --device=/dev/dri |

---

## Arquitecturas GFX de GPU AMD

| GPU | GFX | ROCm mínimo | Override |
|-----|:---:|:-----------:|:--------:|
| MI300X | gfx942 | 6.1 | 9.4.2 |
| MI250 | gfx90a | 5.3 | 9.0.6 |
| MI100 | gfx908 | 5.0 | 9.0.8 |
| RX 7900 XTX | gfx1100 | 6.0 | 11.0.0 |
| RX 9070 XT | gfx1201 | 6.4 | 12.0.1 |
| RX 6800 XT | gfx1030 | 5.0 | 10.3.0 |

Verificación: `rocminfo | grep -E "^\s*Name:\s+gfx"`

---

## Tabla Compatibilidad ROCm ↔ PyTorch

| ROCm | PyTorch Wheel | URL |
|:----:|:-------------:|-----|
| 7.2.x | rocm6.2 | `https://download.pytorch.org/whl/rocm6.2` |
| 7.1.x | rocm6.2 | `https://download.pytorch.org/whl/rocm6.2` |
| 7.0.x | rocm6.2 | `https://download.pytorch.org/whl/rocm6.2` |
| 6.3.x | rocm6.2 | `https://download.pytorch.org/whl/rocm6.2` |
| 6.2.x | rocm6.1 | `https://download.pytorch.org/whl/rocm6.1` |
| 6.1.x | rocm6.1 | `https://download.pytorch.org/whl/rocm6.1` |
| 6.0.x | rocm6.0 | `https://download.pytorch.org/whl/rocm6.0` |

```bash
# Instalación genérica:
pip install torch --index-url https://download.pytorch.org/whl/rocm6.2
```

---

## Docker ROCm — Flags Esenciales

```bash
docker run \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  --group-add=render \
  --ipc=host \
  --shm-size=128g \
  --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  -e HIP_VISIBLE_DEVICES=0 \
  -e HIPBLAS_WORKSPACE_CONFIG=:512:8 \
  <imagen> <comando>
```

### Imágenes Docker Útiles

| Propósito | Imagen |
|-----------|--------|
| ROCm base | `rocm/dev-ubuntu-22.04:latest` |
| PyTorch ROCm | `rocm/pytorch:rocm7.2.4_ubuntu24.04_py3.12_pytorch_2.10.0` |
| vLLM ROCm | `vllm/vllm-openai-rocm:latest` |
| NVIDIA CUDA | `nvidia/cuda:12.6.3-runtime-ubuntu22.04` |
| NVIDIA PyTorch | `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` |

---

## URLs de Documentación

| Recurso | URL |
|---------|-----|
| ROCm Documentation | https://rocm.docs.amd.com/ |
| ROCm Installation | https://rocm.docs.amd.com/projects/install-on-linux/ |
| ROCm Supported GPUs | https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/system-requirements.html |
| PyTorch ROCm | https://pytorch.org/get-started/locally/ |
| vLLM AMD Installation | https://docs.vllm.ai/en/latest/getting_started/amd-installation.html |
| Ultralytics YOLO ROCm | https://docs.ultralytics.com/guides/rocm/ |
| HuggingFace AMD | https://huggingface.co/docs/transformers/installation#amd |
| ROCm GitHub | https://github.com/RadeonOpenCompute/ROCm |
| ROCm Flash Attention | https://github.com/ROCm/flash-attention |

---

## Troubleshooting Rápido (3 pasos)

```bash
# 1. Diagnosticar
bash <(curl -s https://raw.githubusercontent.com/...)  # O local:
bash scripts/rocm-diagnostic.sh

# 2. Verificar compatibilidad
python3 scripts/check-compatibility.py

# 3. Aplicar fix rápido
bash scripts/quick-fix.sh --fix-groups --fix-kfd -y
```
