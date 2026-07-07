# ROCm Error Codes Database

Base de datos de errores comunes en el ecosistema AMD ROCm, organizados
por componente. Cada error incluye código/mensaje, causa raíz, solución y
skill relacionada del catálogo Munin.

> **Prioridad**: MI300X (gfx942), ROCm 7.2.x, PyTorch 2.4+, vLLM 0.6+.

---

## Índice

- [System Errors](#system-errors)
- [ROCm Errors](#rocm-errors)
- [PyTorch Errors](#pytorch-errors)
- [vLLM Errors](#vllm-errors)
- [Docker Errors](#docker-errors)
- [YOLO Errors](#yolo-errors)

---

## System Errors

### ERR-SYS-001: GPU no detectada en PCIe

| Campo | Valor |
|-------|-------|
| **Código** | `lspci: no AMD/NVIDIA GPU found` |
| **Mensaje** | `lspci | grep -iE "vga|3d|display"` no muestra GPUs |
| **Causa Raíz** | GPU mal seated, PCIe slot deshabilitado en BIOS, o GPU muerta |
| **Solución** | 1) Reseat GPU físicamente. 2) Verificar BIOS: slot habilitado. 3) Probar en otro slot PCIe. 4) Verificar fuente de poder (8-pin/12VHPWR). |
| **Skill** | rocm-setup |

### ERR-SYS-002: amdgpu module not loaded

| Campo | Valor |
|-------|-------|
| **Código** | `lsmod: amdgpu not found` |
| **Mensaje** | `lsmod | grep amdgpu` no muestra el módulo del kernel |
| **Causa Raíz** | Drivers AMDGPU no instalados, Secure Boot bloqueando el módulo, o kernel too new/old |
| **Solución** | 1) `sudo modprobe amdgpu`. 2) Verificar Secure Boot deshabilitado en BIOS. 3) Reinstalar drivers: `sudo amdgpu-install --usecase=rocm`. 4) Verificar kernel: `uname -r` |
| **Skill** | rocm-setup |

### ERR-SYS-003: /dev/kfd no existe

| Campo | Valor |
|-------|-------|
| **Código** | `ls -la /dev/kfd: No such file or directory` |
| **Mensaje** | El dispositivo KFD (Kernel Fusion Driver) no está presente |
| **Causa Raíz** | Módulo amdgpu no cargado, o ROCm no instalado |
| **Solución** | 1) `sudo modprobe amdgpu`. 2) `sudo amdgpu-install --usecase=rocm`. 3) Verificar con `ls -la /dev/kfd` |
| **Skill** | rocm-setup |

### ERR-SYS-004: Permission denied /dev/kfd

| Campo | Valor |
|-------|-------|
| **Código** | `Permission denied` al abrir `/dev/kfd` |
| **Mensaje** | `rocminfo: could not open /dev/kfd: Permission denied` |
| **Causa Raíz** | Usuario no pertenece al grupo `render` (dueño de /dev/kfd) |
| **Solución** | 1) `sudo usermod -a -G render $USER`. 2) `newgrp render`. 3) Verificar: `ls -la /dev/kfd` (debe mostrar grupo `render`). 4) En Docker: `--group-add=render` |
| **Skill** | rocm-troubleshoot |

### ERR-SYS-005: BIOS configuracion incorrecta

| Campo | Valor |
|-------|-------|
| **Código** | `BIOS: GPU no detectada en ROCm` |
| **Mensaje** | GPU visible en lspci pero ROCm no la detecta |
| **Causa Raíz** | Above 4G Decoding o Resizable BAR deshabilitados en BIOS |
| **Solución** | 1) Entrar a BIOS/UEFI. 2) Habilitar "Above 4G Decoding" / "Above 4G MMIO BIOS Assignment". 3) Habilitar "Resizable BAR" / "Re-Size BAR Support". 4) Deshabilitar "Secure Boot". 5) Guardar y reiniciar. |
| **Skill** | rocm-setup |

### ERR-SYS-006: nvidia-smi not found

| Campo | Valor |
|-------|-------|
| **Código** | `nvidia-smi: command not found` |
| **Mensaje** | NVIDIA driver no instalado o no en PATH |
| **Causa Raíz** | NVIDIA driver no instalado, o instalado incorrectamente |
| **Solución** | 1) `sudo apt install nvidia-driver-545` (o 550/560 según GPU). 2) Reiniciar. 3) Verificar: `nvidia-smi` |
| **Skill** | rocm-setup |

---

## ROCm Errors

### ERR-ROC-001: No AMD GPU detected by rocminfo

| Campo | Valor |
|-------|-------|
| **Código** | `rocminfo: No AMD GPU detected` |
| **Mensaje** | `rocminfo` muestra agents CPU-only, sin GPUs |
| **Causa Raíz** | amdgpu module no cargado, GPU no soportada, o versión ROCm incorrecta |
| **Solución** | 1) `sudo modprobe amdgpu && rocminfo`. 2) Verificar GPU soportada (ver supported-gpus.md). 3) Actualizar ROCm. 4) Verificar BIOS settings. |
| **Skill** | rocm-setup |

### ERR-ROC-002: rocm-smi not found

| Campo | Valor |
|-------|-------|
| **Código** | `rocm-smi: command not found` |
| **Mensaje** | El comando rocm-smi no está disponible |
| **Causa Raíz** | ROCm no instalado, o paquete `rocm-smi-lib` no instalado |
| **Solución** | 1) `sudo amdgpu-install --usecase=rocm`. 2) Verificar PATH: `echo $PATH | grep rocm`. 3) Añadir `/opt/rocm/bin` al PATH. |
| **Skill** | rocm-setup |

### ERR-ROC-003: ROCm version mismatch

| Campo | Valor |
|-------|-------|
| **Código** | `ROCm version mismatch` |
| **Mensaje** | Diferencia entre versión ROCm instalada y esperada por PyTorch/vLLM |
| **Causa Raíz** | ROCm drivers versión X, pero software espera versión Y |
| **Solución** | 1) `cat /opt/rocm/share/doc/rocm-version/version`. 2) Match PyTorch: `pip install torch --index-url https://download.pytorch.org/whl/rocm6.2`. 3) Si hay múltiples ROCm: `sudo apt remove --purge rocm-* && reinstalar`. |
| **Skill** | rocm-troubleshoot |

### ERR-ROC-004: rocminfo segmentation fault

| Campo | Valor |
|-------|-------|
| **Código** | `rocminfo: Segmentation fault` |
| **Mensaje** | rocminfo crashea con segfault |
| **Causa Raíz** | Múltiples versiones de ROCm instaladas, o librerías incompatibles |
| **Solución** | 1) `sudo apt remove --purge rocm-* rocm-libs-*`. 2) `sudo rm -rf /opt/rocm*`. 3) `sudo apt autoremove`. 4) Reinstalar ROCm desde cero con `amdgpu-install`. |
| **Skill** | rocm-setup |

### ERR-ROC-005: hipconfig not found

| Campo | Valor |
|-------|-------|
| **Código** | `hipconfig: command not found` |
| **Mensaje** | Herramienta hipconfig no disponible |
| **Causa Raíz** | Paquete ROCm hip no instalado |
| **Solución** | 1) `sudo amdgpu-install --usecase=rocm`. 2) Verificar `/opt/rocm/hip/bin/hipconfig`. 3) Añadir al PATH. |
| **Skill** | rocm-setup |

---

## PyTorch Errors

### ERR-TOR-001: torch.cuda.is_available() is False

| Campo | Valor |
|-------|-------|
| **Código** | `torch.cuda.is_available() returns False` |
| **Mensaje** | PyTorch no detecta GPU aunque ROCm/SMI funciona |
| **Causa Raíz** | PyTorch instalado desde rueda CUDA (default de PyPI) en vez de ROCm |
| **Solución** | `pip uninstall torch torchvision torchaudio -y && pip cache purge && pip install torch --index-url https://download.pytorch.org/whl/rocm6.2` |
| **Skill** | rocm-setup |

### ERR-TOR-002: HIP error: hipErrorNoDevice

| Campo | Valor |
|-------|-------|
| **Código** | `RuntimeError: HIP error: hipErrorNoDevice` |
| **Mensaje** | No HIP-capable device detected |
| **Causa Raíz** | GPU no visible para HIP (permisos, driver, o HSA_OVERRIDE_GFX_VERSION incorrecto) |
| **Solución** | 1) Verificar `rocminfo`. 2) Verificar `/dev/kfd` permisos. 3) Verificar `HSA_OVERRIDE_GFX_VERSION`. 4) `sudo usermod -a -G video,render $USER`. |
| **Skill** | rocm-troubleshoot |

### ERR-TOR-003: HIP error: hipErrorOutOfMemory

| Campo | Valor |
|-------|-------|
| **Código** | `RuntimeError: HIP error: hipErrorOutOfMemory` |
| **Mensaje** | Out of memory on AMD GPU |
| **Causa Raíz** | VRAM insuficiente para operación. Batch size, modelo o resolución demasiado grandes. |
| **Solución** | 1) Reducir batch size. 2) `torch.cuda.empty_cache()`. 3) Usar `.half()` o `.bfloat16()`. 4) En vLLM: `--gpu-memory-utilization 0.80`. 5) Verificar VRAM: `rocm-smi --showmeminfo vram`. |
| **Skill** | rocm-troubleshoot |

### ERR-TOR-004: CUDA error: no kernel image is available

| Campo | Valor |
|-------|-------|
| **Código** | `CUDA error: no kernel image is available for execution on the device` |
| **Mensaje** | Kernel compilado para GFX diferente a la GPU actual |
| **Causa Raíz** | `HSA_OVERRIDE_GFX_VERSION` incorrecto o mismatch de arquitectura |
| **Solución** | 1) Verificar GFX real: `rocminfo | grep gfx`. 2) Ajustar/eliminar `HSA_OVERRIDE_GFX_VERSION`. 3) Para MI300X: `9.4.2`. 4) Para RX 7900: `11.0.0`. |
| **Skill** | rocm-troubleshoot |

### ERR-TOR-005: HIP error: unknown error / invalid argument

| Campo | Valor |
|-------|-------|
| **Código** | `RuntimeError: HIP error: unknown error` |
| **Mensaje** | Error genérico de HIP sin código específico |
| **Causa Raíz** | `HSA_OVERRIDE_GFX_VERSION` incorrecto causando instrucciones inválidas |
| **Solución** | 1) `unset HSA_OVERRIDE_GFX_VERSION`. 2) Si el problema persiste, actualizar ROCm. 3) `sudo amdgpu-install --usecase=rocm --no-dkms`. |
| **Skill** | rocm-troubleshoot |

### ERR-TOR-006: Torch not compiled with CUDA enabled

| Campo | Valor |
|-------|-------|
| **Código** | `AssertionError: Torch not compiled with CUDA enabled` |
| **Mensaje** | PyTorch compilado sin soporte CUDA/CUDA |
| **Causa Raíz** | PyTorch instalado desde wheel CPU-only (sin CUDA ni ROCm) |
| **Solución** | 1) `pip uninstall torch -y`. 2) `pip install torch --index-url https://download.pytorch.org/whl/rocm6.2`. 3) Verificar: `python3 -c "import torch; print(torch.cuda.is_available())"`. |
| **Skill** | rocm-setup |

### ERR-TOR-007: flash-attn: nvcc not found / CUDA_HOME not set

| Campo | Valor |
|-------|-------|
| **Código** | `nvcc not found` o `CUDA_HOME not set` |
| **Mensaje** | Error al compilar flash-attention (código CUDA nativo) |
| **Causa Raíz** | flash-attention original tiene código CUDA que no compila en HIP |
| **Solución** | Usar fork oficial ROCm: `pip install git+https://github.com/ROCm/flash-attention.git` |
| **Skill** | rocm-troubleshoot |

---

## vLLM Errors

### ERR-VLLM-001: Bfloat16 is not supported

| Campo | Valor |
|-------|-------|
| **Código** | `ValueError: Bfloat16 is not supported on current device` |
| **Mensaje** | vLLM falla al iniciar porque selecciona bfloat16 por defecto |
| **Causa Raíz** | ROCm no soporta bfloat16 nativamente en todas las operaciones |
| **Solución** | Forzar dtype: `--dtype float16` al iniciar vLLM. También: `export VLLM_USE_FP16=1`. |
| **Skill** | vllm-rocm-deploy |

### ERR-VLLM-002: No ROCm GPU available

| Campo | Valor |
|-------|-------|
| **Código** | `ValueError: No ROCm GPU available` |
| **Mensaje** | vLLM no encuentra GPUs AMD ROCm |
| **Causa Raíz** | Python no es 3.12 (ruedas ROCm solo para 3.12), o wheel incorrecto |
| **Solución** | 1) `python3 --version` debe ser 3.12.x. 2) Reinstalar: `pip install vllm --extra-index-url https://wheels.vllm.ai/rocm/`. 3) En Docker: usar `vllm/vllm-openai-rocm:latest`. |
| **Skill** | vllm-rocm-deploy |

### ERR-VLLM-003: pip install vllm instala CUDA en ROCm

| Campo | Valor |
|-------|-------|
| **Código** | `pip install vllm` instala rueda CUDA silenciosamente |
| **Mensaje** | Después de instalar vLLM, falla con "No ROCm GPU" |
| **Causa Raíz** | Python no es 3.12 → no hay rueda ROCm disponible → pip instala la CUDA por defecto |
| **Solución** | 1) `python3 --version` (debe ser 3.12). 2) Crear entorno 3.12: `uv venv --python 3.12 && source .venv/bin/activate`. 3) `pip install vllm --extra-index-url https://wheels.vllm.ai/rocm/`. |
| **Skill** | vllm-rocm-deploy |

### ERR-VLLM-004: The model's max model length is too long

| Campo | Valor |
|-------|-------|
| **Código** | `ValueError: The model's max model length is at least ...` |
| **Mensaje** | El modelo requiere más memoria de la disponible |
| **Causa Raíz** | `max_position_embeddings` del modelo excede la VRAM disponible |
| **Solución** | Forzar: `--max-model-len 4096` (o menor según VRAM). Monitorear con `rocm-smi --showmeminfo vram`. |
| **Skill** | vllm-rocm-deploy |

### ERR-VLLM-005: OutOfMemoryError en vLLM

| Campo | Valor |
|-------|-------|
| **Código** | `torch.cuda.OutOfMemoryError` |
| **Mensaje** | vLLM se queda sin VRAM durante inferencia |
| **Causa Raíz** | `gpu_memory_utilization` demasiado alto. `max_num_seqs` muy grande. |
| **Solución** | 1) `--gpu-memory-utilization 0.80`. 2) `--max-model-len 2048`. 3) `--max-num-seqs 128`. 4) Ver VRAM: `rocm-smi --showmeminfo vram`. |
| **Skill** | vllm-rocm-deploy |

### ERR-VLLM-006: ModuleNotFoundError: No module named 'vllm'

| Campo | Valor |
|-------|-------|
| **Código** | `ModuleNotFoundError: No module named 'vllm'` |
| **Mensaje** | vLLM no está instalado en el contenedor o entorno |
| **Causa Raíz** | Imagen Docker incorrecta o entorno virtual no activado |
| **Solución** | 1) Usar `vllm/vllm-openai-rocm:latest`. 2) O instalar: `pip install vllm --extra-index-url https://wheels.vllm.ai/rocm/`. |
| **Skill** | vllm-rocm-deploy |

### ERR-VLLM-007: ValueError: Bfloat16 is not supported (YOLO + vLLM)

| Campo | Valor |
|-------|-------|
| **Código** | `ValueError: Bfloat16 is not supported on ROCm` |
| **Mensaje** | Similar a ERR-VLLM-001 pero en contexto YOLO |
| **Causa Raíz** | YOLO o vLLM intenta usar bfloat16 en ROCm |
| **Solución** | Forzar float16: `--dtype float16` o `model = model.half()`. |
| **Skill** | yolo-rocm-deploy |

---

## Docker Errors

### ERR-DOCK-001: Permission denied /dev/kfd in container

| Campo | Valor |
|-------|-------|
| **Código** | `docker: permission denied while trying to connect to /dev/kfd` |
| **Mensaje** | El contenedor no puede acceder a /dev/kfd |
| **Causa Raíz** | Falta `--group-add=render` o `--device=/dev/kfd` |
| **Solución** | `docker run --device=/dev/kfd --device=/dev/dri --group-add=video --group-add=render ...` |
| **Skill** | rocm-docker |

### ERR-DOCK-002: Docker unknown flag --device

| Campo | Valor |
|-------|-------|
| **Código** | `docker: unknown flag: --device` |
| **Mensaje** | Docker no reconoce el flag --device |
| **Causa Raíz** | Versión antigua de Docker Engine (pre-24) |
| **Solución** | Actualizar Docker: `sudo apt-get update && sudo apt-get install docker-ce docker-ce-cli containerd.io` |
| **Skill** | rocm-docker |

### ERR-DOCK-003: Docker unknown runtime nvidia

| Campo | Valor |
|-------|-------|
| **Código** | `docker: unknown or invalid runtime name: nvidia` |
| **Mensaje** | Runtime nvidia no registrado en Docker |
| **Causa Raíz** | NVIDIA Container Toolkit no instalado o no configurado |
| **Solución** | 1) `sudo apt-get install -y nvidia-container-toolkit`. 2) `sudo nvidia-ctk runtime configure --runtime=docker`. 3) `sudo systemctl restart docker`. |
| **Skill** | rocm-docker |

### ERR-DOCK-004: Docker container sees no AMD GPU

| Campo | Valor |
|-------|-------|
| **Código** | Dentro del contenedor: `rocminfo` muestra 0 GPUs |
| **Mensaje** | El contenedor no detecta las GPUs AMD del host |
| **Causa Raíz** | Faltan flags `--device=/dev/kfd --device=/dev/dri` o módulo amdgpu no cargado en host |
| **Solución** | 1) Verificar host: `lsmod | grep amdgpu`. 2) Verificar dispositivos: `ls -la /dev/kfd /dev/dri/`. 3) `docker run --device=/dev/kfd --device=/dev/dri --group-add=video --group-add=render ...` |
| **Skill** | rocm-docker |

### ERR-DOCK-005: OOM killer exit code 137

| Campo | Valor |
|-------|-------|
| **Código** | `exit code 137` / `docker: container killed` |
| **Mensaje** | El contenedor fue matado por OOM killer |
| **Causa Raíz** | Contenedor sin límite de memoria consume toda la RAM del host |
| **Solución** | 1) `docker run --memory=64g --memory-swap=64g ...`. 2) Reducir `gpu_memory_utilization`. 3) Monitorear: `docker stats`. |
| **Skill** | rocm-docker |

### ERR-DOCK-006: docker compose --profile not recognized

| Campo | Valor |
|-------|-------|
| **Código** | `WARNING: Some services use the 'deploy' key` |
| **Mensaje** | Docker Compose v1 no soporta perfiles |
| **Causa Raíz** | Usar `docker-compose` (v1) en vez de `docker compose` (v2) |
| **Solución** | Usar siempre `docker compose` (v2, con espacio): `docker compose --profile rocm up` |
| **Skill** | rocm-docker |

### ERR-DOCK-007: HIP_VISIBLE_DEVICES no tiene efecto en contenedor

| Campo | Valor |
|-------|-------|
| **Código** | `HIP_VISIBLE_DEVICES=0` no limita GPUs visibles |
| **Mensaje** | El contenedor ve todas las GPUs a pesar de la variable |
| **Causa Raíz** | Algunas versiones ROCm usan `ROCR_VISIBLE_DEVICES` en vez de `HIP_VISIBLE_DEVICES` |
| **Solución** | Usar ambas variables: `-e HIP_VISIBLE_DEVICES=0 -e ROCR_VISIBLE_DEVICES=0` |
| **Skill** | rocm-docker |

---

## YOLO Errors

### ERR-YOLO-001: YOLO CUDA unavailable

| Campo | Valor |
|-------|-------|
| **Código** | `Ultralytics: WARNING ⚠️ CUDA is not available` |
| **Mensaje** | YOLO no detecta GPU para training/inference |
| **Causa Raíz** | `torch.cuda.is_available()` es False (rueda PyTorch incorrecta) |
| **Solución** | 1) `pip install torch --index-url https://download.pytorch.org/whl/rocm6.2`. 2) Verificar: `python3 -c "import torch; print(torch.cuda.is_available())"`. |
| **Skill** | yolo-rocm-deploy |

### ERR-YOLO-002: YOLO out of memory

| Campo | Valor |
|-------|-------|
| **Código** | `torch.cuda.OutOfMemoryError` durante training YOLO |
| **Mensaje** | YOLO se queda sin VRAM con batch size o imagen grande |
| **Causa Raíz** | `--batch` o `--img` demasiado grande para VRAM disponible |
| **Solución** | 1) `yolo train --batch 8 --img 640`. 2) `--half` para usar float16. 3) Reducir aún más: `--batch 4 --img 416`. |
| **Skill** | yolo-rocm-deploy |

### ERR-YOLO-003: YOLO device specified but not found

| Campo | Valor |
|-------|-------|
| **Código** | `RuntimeError: Device specified as 'cuda:0' but no devices` |
| **Mensaje** | YOLO no encuentra device cuda:0 |
| **Causa Raíz** | `device=0` o `device=cuda:0` pero PyTorch no detecta GPU |
| **Solución** | 1) Verificar `torch.cuda.is_available()`. 2) `torch.cuda.device_count()`. 3) Si no hay GPU: `device='cpu'` o instalar PyTorch ROCm. |
| **Skill** | yolo-rocm-deploy |

---

## Referencias

- [ROCm Documentation — Troubleshooting](https://rocm.docs.amd.com/en/latest/deploy/troubleshooting.html)
- [PyTorch ROCm — Getting Started](https://pytorch.org/get-started/locally/)
- [vLLM ROCm — Installation](https://docs.vllm.ai/en/latest/getting_started/amd-installation.html)
- [Ultralytics YOLO — ROCm](https://docs.ultralytics.com/guides/rocm/)
