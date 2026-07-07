# ROCm Optimization Checklist

Checklist completa de optimización para cargas de trabajo ML/AI en GPUs
AMD ROCm. Prioriza MI300X (gfx942) y PyTorch/vLLM.

---

## 1. Hardware — BIOS Settings

- [ ] **Above 4G Decoding**: HABILITADO (Above 4G MMIO BIOS Assignment)
  - Necesario para GPUs con >4GB VRAM. Sin esto, la GPU no asigna memoria correctamente.
- [ ] **Resizable BAR**: HABILITADO (Re-Size BAR Support)
  - Mejora rendimiento PCIe permitiendo acceso completo a VRAM.
- [ ] **Secure Boot**: DESHABILITADO
  - Bloquea módulos del kernel como amdgpu si no están firmados.
- [ ] **PCIe Generation**: AUTO o FORZAR Gen4/Gen5
  - No forzar Gen3 si la GPU y slot soportan Gen4/Gen5.
- [ ] **4G Decoding**: HABILITADO (si la opción existe separada de Above 4G)
- [ ] **SR-IOV**: DESHABILITADO (a menos que se use virtualización)
- [ ] **IOMMU**: HABILITADO si usas virtualización, DESHABILITADO para rendimiento máximo bare-metal

### Verificación BIOS:

```bash
# Verificar configuración actual (algunas settings son visibles desde Linux)
sudo dmesg | grep -i "above 4g\|resizable\|rebar"
sudo dmesg | grep -i amdgpu | grep -i "PCIe"

# Verificar versión de PCIe activa
lspci -vvv -s $(lspci | grep -i amd | grep -iE "vga|3d" | head -1 | cut -d' ' -f1) | grep -i "Speed"
```

---

## 2. Software — ROCm

- [ ] **ROCm versión correcta**: 7.2.x para MI300X (gfx942)
  - Verificar: `cat /opt/rocm/share/doc/rocm-version/version`
  - No usar versiones antiguas (< 6.0) para GPUs modernas.
- [ ] **amdgpu module**: Cargado y funcionando
  - Verificar: `lsmod | grep amdgpu`
  - Configurar carga automática: `echo "amdgpu" | sudo tee /etc/modules-load.d/amdgpu.conf`
- [ ] **Grupos de usuario**: `video` y `render`
  - Verificar: `groups $USER`
  - Agregar: `sudo usermod -a -G video,render $USER`
- [ ] **HSA_OVERRIDE_GFX_VERSION**: NO USAR a menos que sea estrictamente necesario
  - Si se usa, verificar valor correcto (MI300X: `9.4.2`, RX 7900: `11.0.0`)
- [ ] **HIPBLAS_WORKSPACE_CONFIG**: Configurado
  ```bash
  export HIPBLAS_WORKSPACE_CONFIG=:512:8
  ```
- [ ] **Variables de entorno**: Configuradas óptimamente
  ```bash
  export ROCM_HOME=/opt/rocm
  export ROCM_PATH=/opt/rocm
  export HIP_VISIBLE_DEVICES=0,1,2,3  # o las que correspondan
  export HIPBLAS_WORKSPACE_CONFIG=:512:8
  ```

---

## 3. PyTorch Optimization

- [ ] **dtype correcto**: `float16` (NO bfloat16)
  ```python
  model = model.half()  # o model.to(torch.float16)
  ```
  - ROCm no soporta bfloat16 nativamente. Usar float16 siempre.
- [ ] **torch.compile**: HABILITADO (PyTorch 2.0+)
  ```python
  model = torch.compile(model, mode="reduce-overhead")
  # mode="max-autotune" para máximo rendimiento (más lento al compilar)
  ```
- [ ] **memory_format**: `channels_last` para CNNs
  ```python
  model = model.to(memory_format=torch.channels_last)
  ```
- [ ] **DataLoader num_workers**: Aumentado
  ```python
  DataLoader(..., num_workers=8, pin_memory=True, prefetch_factor=2)
  ```
- [ ] **Gradient accumulation**: Usar si batch size es pequeño
  ```python
  trainer = Trainer(..., gradient_accumulation_steps=4)
  ```
- [ ] **Mixed precision**: Usar AMP con float16
  ```python
  with torch.cuda.amp.autocast(dtype=torch.float16):
      output = model(input)
  ```
- [ ] **TF32**: DESHABILITADO (no aplica a ROCm, solo NVIDIA)
  ```bash
  unset TORCH_ALLOW_TF32_CUBLAS_OVERRIDE
  ```
- [ ] **Cache de kernels**: Habilitado (reduce overhead en compilación)
  ```bash
  export ROCM_HOME=/opt/rocm
  # Primera ejecución compila kernels, las siguientes usan cache
  ```

---

## 4. vLLM Optimization

- [ ] **dtype**: `float16` explícitamente
  ```bash
  python3 -m vllm.entrypoints.openai.api_server \
    --model mistralai/Mistral-7B-Instruct-v0.3 \
    --dtype float16
  ```
- [ ] **gpu_memory_utilization**: Ajustado según VRAM
  ```bash
  # MI300X (192 GB): 0.90-0.95
  # RX 7900 XTX (24 GB): 0.80-0.85
  --gpu-memory-utilization 0.90
  ```
- [ ] **max_model_len**: Ajustado para caber en VRAM
  ```bash
  # Modelos pequeños (7B): 4096-8192
  # Modelos grandes (70B): 2048-4096 en MI300X
  --max-model-len 4096
  ```
- [ ] **max_num_seqs**: Ajustado para throughput
  ```bash
  # Valores típicos: 128-512
  --max-num-seqs 256
  ```
- [ ] **tensor_parallel_size**: = número de GPUs (multi-GPU)
  ```bash
  --tensor-parallel-size 8  # para 8 GPUs
  ```
- [ ] **Python 3.12**: OBLIGATORIO para vLLM ROCm
  - Verificar: `python3 --version`
  - Si no: `uv venv --python 3.12`

---

## 5. Docker Optimization

- [ ] **--ipc=host**: HABILITADO (memoria compartida para IPC)
  ```bash
  docker run --ipc=host ...
  ```
- [ ] **--shm-size**: Configurado (mínimo 16 GB para cargas ML)
  ```bash
  docker run --shm-size=128g ...
  ```
- [ ] **--ulimit memlock**: Configurado (evita swapping)
  ```bash
  docker run --ulimit memlock=-1 ...
  ```
- [ ] **--cap-add=SYS_PTRACE**: HABILITADO (necesario para ROCm)
  ```bash
  docker run --cap-add=SYS_PTRACE ...
  ```
- [ ] **--security-opt seccomp=unconfined**: Para vLLM
  ```bash
  docker run --security-opt seccomp=unconfined ...
  ```
- [ ] **Montar /opt/rocm**: Opcional, mejora compatibilidad
  ```bash
  docker run -v /opt/rocm:/opt/rocm:ro ...
  ```
- [ ] **Límite de memoria**: Configurado para evitar OOM
  ```bash
  docker run --memory=512g --memory-swap=512g ...
  ```

---

## 6. Storage Optimization

- [ ] **SSD rápido**: Para cache de modelos HuggingFace
  - NVMe PCIe 4.0+ recomendado (3500 MB/s+)
  - Ruta típica: `~/.cache/huggingface` → montar en SSD
- [ ] **Espacio suficiente**: 50 GB+ para modelos grandes
  - Modelos 7B: ~15 GB
  - Modelos 70B: ~140 GB
  - Modelos 405B: ~800 GB
- [ ] **Filesystem**: ext4 o xfs (no NTFS/FAT para cache)
- [ ] **RAM suficiente**: 2-4x el tamaño del modelo en RAM
  - MI300X + modelo 70B: mínimo 256 GB RAM

---

## 7. Network Optimization (Multi-GPU)

- [ ] **InfiniBand**: Para comunicación multi-GPU (>400 GB/s)
  - Alternativa: 100GbE+ Ethernet con RDMA
- [ ] **NCCL/RCCL**: Configurado correctamente
  ```bash
  export NCCL_SOCKET_IFNAME=ib0  # o eth0 según red
  export NCCL_IB_HCA=mlx5_0:1    # para InfiniBand
  export RCCL_SOCKET_IFNAME=ib0
  ```
- [ ] **NUMA binding**: GPUs y CPU en mismo NUMA node
  - Verificar: `rocm-smi --showtoponuma`
  - Binding: `numactl --cpunodebind=0 --membind=0 python3 train.py`
- [ ] **Topología**: Verificar conectividad GPU-GPU
  ```bash
  rocm-smi --showtopo
  ```

---

## 8. Monitoring

- [ ] **rocm-smi**: Monitoreo en tiempo real
  ```bash
  watch -n 1 rocm-smi
  ```
- [ ] **GPU utilization**: Debe ser > 80% para workloads óptimos
  ```bash
  rocm-smi --showusage
  ```
- [ ] **VRAM usage**: Monitorear para evitar OOM
  ```bash
  rocm-smi --showmeminfo vram
  ```
- [ ] **Temperature**: Monitorear para evitar throttling
  ```bash
  rocm-smi --showtemp
  # MI300X max: 100°C, recomiendo < 85°C sostenido
  ```
- [ ] **Power draw**: Verificar consumo
  ```bash
  rocm-smi --showpower
  # MI300X típico: 300-750W (dependiendo de carga)
  ```

---

## 9. Benchmarking

```bash
# ROCm bandwidth test
rocm-bandwidth-test

# PyTorch benchmark simple
python3 -c "
import torch, time
x = torch.randn(4096, 4096, device='cuda')
y = torch.randn(4096, 4096, device='cuda')
# Warmup
for _ in range(10): torch.mm(x, y)
torch.cuda.synchronize()
# Benchmark
t0 = time.time()
for _ in range(100): torch.mm(x, y)
torch.cuda.synchronize()
t = time.time() - t0
print(f'Matmul 4096x4096: {100/t:.1f} iter/s, {2*4096**3*4/t/1e12:.2f} TFLOPS')
"
```

---

## Quick Reference Card

| Componente | Setting | Valor |
|-----------|---------|-------|
| ROCm | Versión | 7.2.x (MI300X) |
| PyTorch | dtype | float16 (NO bfloat16) |
| PyTorch | compile | mode="reduce-overhead" |
| vLLM | dtype | --dtype float16 |
| vLLM | GPU mem | 0.90 |
| Docker | ipc/shm | --ipc=host --shm-size=128g |
| HIPBLAS | workspace | :512:8 |
| GPU | BIOS | Above 4G + Resizable BAR |
| Python | vLLM ROCm | 3.12.x |
