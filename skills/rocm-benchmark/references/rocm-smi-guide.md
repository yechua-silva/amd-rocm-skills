# ROCm SMI Guide (`rocm-smi`)

Guía completa de `rocm-smi` (ROCm System Management Interface) para
monitorear y administrar GPUs AMD. Incluye comandos útiles, parseo
para scripts, y equivalentes NVIDIA `nvidia-smi`.

---

## 1. Introducción

`rocm-smi` es la herramienta de línea de comandos para monitorear y
controlar GPUs AMD compatibles con ROCm. Proporciona información sobre:

- Estado de la GPU (temperatura, clock, power, VRAM, fan)
- Producto y versión de driver
- Control de clocks y fans (con permisos de root)

### Verificar instalación

```bash
rocm-smi --version
# o simplemente:
rocm-smi --showallinfo
```

Si no está instalado:
```bash
# Instalar desde paquete ROCm
sudo apt install rocm-libs

# O verificar que ROCm está completo
which rocm-smi
# Debería estar en: /opt/rocm/bin/rocm-smi
```

---

## 2. Comandos Esenciales

### Información del Producto

```bash
# Nombre del producto GPU
rocm-smi --showproductname

# Salida típica:
# ======================== ROCm System Management Interface ========================
# ============================ Product Information ================================
# GPU[0]          : Card series: AMD Instinct MI300X
# GPU[0]          : Card model: 0x0c34
# GPU[0]          : Card vendor: Advanced Micro Devices, Inc. [AMD/ATI]
# GPU[0]          : Card SKU: NA
#
# =================================================================================
```

Equivalente NVIDIA:
```bash
nvidia-smi --query-gpu=name --format=csv,noheader
```

### Información Completa

```bash
# Todas las métricas disponibles
rocm-smi --showallinfo

# Salida típica (abreviada):
# GPU[0]          : Temperature (Sensor edge) (C): 45.0
# GPU[0]          : Temperature (Sensor junction) (C): 48.0
# GPU[0]          : Average Graphics Package Power (W): 75.0
# GPU[0]          : sclk (Mhz): 1650
# GPU[0]          : mclk (Mhz): 1200
# GPU[0]          : GPU use (%) (UNSUPPORTED)
# GPU[0]          : VRAM Total Memory (MB): 196608
# GPU[0]          : VRAM Total Used Memory (MB): 512
# GPU[0]          : Fan Speed (%) (UNSUPPORTED)
```

### Temperatura

```bash
# Temperatura actual
rocm-smi --showtemp

# Temperatura en JSON (ideal para scripts)
rocm-smi --showtemp --json

# Salida JSON:
# {
#   "card0": {
#     "Temperature (Sensor edge) (C)": "45.0",
#     "Temperature (Sensor junction) (C)": "48.0"
#   },
#   "card1": { ... }
# }
```

Equivalente NVIDIA:
```bash
nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits
```

### Consumo Eléctrico (Power)

```bash
# Power draw actual
rocm-smi --showpower

# Con límite de potencia
rocm-smi --showpowercap

# JSON
rocm-smi --showpower --json
```

Equivalente NVIDIA:
```bash
nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits
```

### Clock Speeds

```bash
# Frecuencias actuales (sclk = shader clock, mclk = memory clock)
rocm-smi --showclk

# Niveles de clock disponibles
rocm-smi --showclklevels

# JSON
rocm-smi --showclk --json
```

Equivalente NVIDIA:
```bash
nvidia-smi --query-gpu=clocks.gr,clocks.mem --format=csv,noheader,nounits
```

### Memoria VRAM

```bash
# Uso de VRAM
rocm-smi --showmeminfo vram

# VRAM total y usada
rocm-smi --showmeminfo vram --json

# Salida JSON:
# {
#   "card0": {
#     "VRAM Total Memory (MB)": "196608",
#     "VRAM Total Used Memory (MB)": "512"
#   }
# }
```

Equivalente NVIDIA:
```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits
```

### Ventiladores

```bash
# Velocidad del fan
rocm-smi --showfan

# Niveles de fan disponibles
rocm-smi --showfanlevel
```

Equivalente NVIDIA:
```bash
nvidia-smi --query-gpu=fan.speed --format=csv,noheader,nounits
```

### Uso de GPU

```bash
# Porcentaje de uso (puede no estar soportado en algunas GPUs)
rocm-smi --showusage
```

Equivalente NVIDIA:
```bash
nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits
```

---

## 3. Monitoreo Continuo

### Loop Básico

```bash
# Actualizar cada 2 segundos
rocm-smi --showallinfo --loop 2

# Solo métricas esenciales cada 1 segundo
rocm-smi --showtemp --showpower --showclk --showmeminfo vram --loop 1
```

### Loop con Salida JSON (para scripts)

```bash
# Monitoreo continuo en JSON (1 línea por muestra)
rocm-smi --showtemp --showpower --showclk --loop 1 --json

# Redirigir a archivo
rocm-smi --showtemp --showpower --loop 1 --json > monitor.log
```

### Equivalente NVIDIA

```bash
# Monitoreo continuo nvidia-smi
nvidia-smi --query-gpu=temperature.gpu,power.draw,clocks.gr,memory.used \
  --format=csv --loop-ms=1000
```

---

## 4. Parseo de Output para Scripts

### Parseo JSON (recomendado)

```python
import json
import subprocess

result = subprocess.run(
    ["rocm-smi", "--showtemp", "--showpower", "--showclk", "--json"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)

for card_key, card_info in data.items():
    if not card_key.startswith("card"):
        continue
    temp = card_info.get("Temperature (Sensor edge) (C)", "N/A")
    power = card_info.get("Power Draw (W)", "N/A")
    sclk = card_info.get("sclk", "N/A")
    print(f"{card_key}: {temp}°C, {power}W, {sclk} MHz")
```

### Parseo Bash

```bash
# Extraer temperatura de GPU 0
rocm-smi --showtemp --json | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('card0', {}).get('Temperature (Sensor edge) (C)', 'N/A'))
"

# Extraer power de todas las GPUs
rocm-smi --showpower --json | python3 -c "
import sys, json
d = json.load(sys.stdin)
for k, v in d.items():
    if k.startswith('card'):
        print(f'{k}: {v.get(\"Power Draw (W)\", \"N/A\")} W')
"
```

### Una Línea para Alertas

```bash
# Alerta si temperatura > 85°C
rocm-smi --showtemp --json | python3 -c "
import sys, json
d = json.load(sys.stdin)
for k, v in d.items():
    if k.startswith('card'):
        t = float(v.get('Temperature (Sensor edge) (C)', 0))
        if t > 85:
            print(f'🔥 {k}: {t}°C OVER TEMP')
"
```

---

## 5. Control de GPU (Requiere Root)

### Fijar Clock

```bash
# Ver niveles de clock disponibles
rocm-smi --showclklevels

# Fijar clock de shader (sclk) al nivel más alto (ej: nivel 7)
sudo rocm-smi --setsclk 7

# Fijar clock de memoria (mclk) al nivel más alto
sudo rocm-smi --setmclk 3

# Restablecer a automático
sudo rocm-smi --resetclocks
```

### Control de Ventiladores

```bash
# Fijar fan al 80%
sudo rocm-smi --setfan 80

# Restablecer fan a automático
sudo rocm-smi --resetfans
```

### Límite de Potencia

```bash
# Ver límite actual
rocm-smi --showpowercap

# Fijar límite a 300W (ejemplo)
sudo rocm-smi --setpowercap 300
```

### Equivalente NVIDIA

```bash
# NVIDIA: fijar clock (persistence mode required)
sudo nvidia-smi -pm 1
sudo nvidia-smi -lgc 1500,1500  # lock GPU clock to 1500 MHz
sudo nvidia-smi -lmc 5000,5000  # lock memory clock
sudo nvidia-smi -rgc            # reset GPU clocks
sudo nvidia-smi -pl 300         # set power limit to 300W
```

---

## 6. Equivalencia Completa ROCm ↔ NVIDIA

| Función | ROCm (`rocm-smi`) | NVIDIA (`nvidia-smi`) |
|---------|-------------------|----------------------|
| Product name | `--showproductname` | `--query-gpu=name` |
| All info | `--showallinfo` | `--query` |
| Temperature | `--showtemp` | `--query-gpu=temperature.gpu` |
| Power draw | `--showpower` | `--query-gpu=power.draw` |
| Power limit | `--showpowercap` / `--setpowercap` | `-pl` / `--query-gpu=power.limit` |
| GPU clock | `--showclk` (sclk) | `--query-gpu=clocks.gr` |
| Memory clock | `--showclk` (mclk) | `--query-gpu=clocks.mem` |
| VRAM total | `--showmeminfo vram` (Total) | `--query-gpu=memory.total` |
| VRAM used | `--showmeminfo vram` (Used) | `--query-gpu=memory.used` |
| Fan speed | `--showfan` | `--query-gpu=fan.speed` |
| GPU utilization | `--showusage` | `--query-gpu=utilization.gpu` |
| Set clock | `--setsclk` | `-lgc` |
| Set memory clock | `--setmclk` | `-lmc` |
| Reset clocks | `--resetclocks` | `-rgc` |
| Set fan | `--setfan` | (via nvidia-settings) |
| Power cap | `--setpowercap` | `-pl` |
| List processes | `--showpid` | `--query-compute-apps` |
| Loop/continuous | `--loop N` | `--loop-ms=N` |

---

## 7. Variables de Entorno que Afectan Benchmark

### Selección de GPUs

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `HIP_VISIBLE_DEVICES` | GPUs AMD visibles para HIP | `0,1,2` |
| `ROCR_VISIBLE_DEVICES` | Alternativa (mismo efecto) | `0,1` |
| `CUDA_VISIBLE_DEVICES` | Funciona también en ROCm (portátil) | `0` |

### Override de Arquitectura

| Variable | Descripción | Uso |
|----------|-------------|-----|
| `HSA_OVERRIDE_GFX_VERSION` | Simular arquitectura GFX | `9.4.2` para gfx942 |

> **Advertencia**: Usar solo si es necesario. Preferir ROCm que soporte
> la GPU nativamente.

### Ajustes de Rendimiento

| Variable | Descripción | Recomendado |
|----------|-------------|:-----------:|
| `HIPBLAS_WORKSPACE_CONFIG` | Configuración de workspace para rocBLAS | `:512:8` |
| `ROCM_HOME` | Ruta de instalación ROCm | `/opt/rocm` |
| `ROCM_PATH` | Alternativa a ROCM_HOME | `/opt/rocm` |
| `HIP_FORCE_DEV_KERNARG` | Forzar kernel arguments en device | `1` (MI300X) |

### Ejemplo de Configuración Óptima para Benchmark

```bash
# Benchmark en MI300X
export HIP_VISIBLE_DEVICES=0
export HSA_OVERRIDE_GFX_VERSION=9.4.2  # solo si es necesario
export HIPBLAS_WORKSPACE_CONFIG=:512:8
export ROCM_HOME=/opt/rocm

# Ejecutar benchmark
python3 benchmark-gpu.py --all --iterations 200 --json --output results.json
```

---

## 8. Troubleshooting de `rocm-smi`

### `rocm-smi: command not found`

```bash
# ROCm no está en PATH o no está instalado
which rocminfo  # verificar si ROCm está instalado

# Si ROCm está en /opt/rocm pero no en PATH:
export PATH=$PATH:/opt/rocm/bin

# Instalar herramientas ROCm:
sudo apt install rocm-libs
```

### `No AMD GPU detected`

```bash
# 1. Verificar que el módulo amdgpu está cargado
lsmod | grep amdgpu

# 2. Verificar GPUs en PCIe
lspci | grep -iE "amd|radeon" | grep -iE "vga|3d|display"

# 3. Verificar permisos
ls -la /dev/kfd
# Debe mostrar: crw-rw---- 1 root render ...

# 4. Verificar grupos de usuario
groups
# Debe incluir "video" y "render"
```

### JSON Output Vacio o Incorrecto

```bash
# Algunas versiones de rocm-smi tienen bugs con --json
# Probar sin --json primero:
rocm-smi --showtemp

# Si funciona sin JSON pero no con JSON, actualizar ROCm
# o usar parseo manual del output de texto

# Parseo de texto como fallback:
rocm-smi --showtemp | grep "GPU\[0\]" | grep -oP '\d+\.\d+' | head -1
```

---

## Referencias

- [ROCm SMI Documentation](https://rocm.docs.amd.com/projects/rocm_smi_lib/en/latest/)
- [ROCm SMI GitHub](https://github.com/ROCm/rocm_smi_lib)
- [NVIDIA SMI Documentation](https://developer.nvidia.com/nvidia-system-management-interface)
