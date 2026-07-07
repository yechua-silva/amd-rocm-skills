# Despliegue Industrial — PPE Detection Pipeline

## Overview

Guía de despliegue del pipeline de detección de EPP en entornos industriales reales: minería, construcción, plantas de proceso. Cubre selección de hardware, integración con sistemas existentes, dimensionamiento de servidores, latencia end-to-end, y estrategias de alta disponibilidad.

## Cámaras

### Especificaciones Recomendadas

| Propiedad | Mínimo | Recomendado | Óptimo |
|-----------|--------|-------------|--------|
| **Resolución** | 720p (1280×720) | 1080p (1920×1080) | 4K (3840×2160) |
| **FPS** | 15 FPS | 25–30 FPS | 30+ FPS |
| **IR / Visión nocturna** | No esencial | Sí (30m alcance) | Sí (50m+) |
| **WDR (Wide Dynamic Range)** | No | Sí (120 dB) | Sí (140 dB) |
| **Compresión** | H.264 | H.264/H.265 | H.265 |
| **Protocolo** | RTSP | RTSP + ONVIF | RTSP + ONVIF |
| **PoE** | No esencial | Sí (802.3af) | Sí (802.3at) |
| **Certificación** | IP66 | IP67 (polvo/agua) | IP69K (lavado industrial) |

### Cámaras Recomendadas para Minería

| Modelo | Resolución | IR | WDR | IP | PoE | Uso |
|--------|-----------|----|-----|----|-----|-----|
| **Hikvision DS-2CD2T87G2-LSU** | 8MP (4K) | 40m | 140 dB | IP67 | 802.3af | Exteriores, rajo abierto |
| **Dahua IPC-HFW5849T1-ASE-LED** | 8MP (4K) | 50m | 140 dB | IP67 | 802.3at | Interior, planta |
| **Axis Q1786-LE** | 5MP | 30m | 120 dB | IP67 | 802.3af | Subterránea (ATEX) |
| **Mobotix M73** | 6MP | 20m | 120 dB | IP66 | 802.3af | Subterránea, zonas húmedas |
| **Vivotek IB9389-H** | 5MP | 50m | 140 dB | IP69K | 802.3at | Lavado industrial, polvo extremo |

**Nota para minería chilena**: Se recomienda IP67 o superior debido al polvo en suspensión en faenas del norte (Atacama) y la humedad en minería subterránea.

### Posicionamiento de Cámaras

**Zonas críticas para monitoreo EPP:**
1. **Ingreso a faena**: Control de acceso con EPP completo obligatorio
2. **Boca de túnel/subida a rajo**: Transición a zona de alto riesgo
3. **Zonas de carguío**: Interacción persona-maquinaria
4. **Talleres de mantención**: Alta concentración de personal
5. **Zonas de tránsito vehicular**: Riesgo de atropello
6. **Polvorines y zonas de explosivos**: EPP específico requerido

**Ángulos recomendados:**
- **Frontal**: Ideal para detección de casco, lentes y chaleco
- **Lateral (45°)**: Bueno para detección de guantes y botas
- **Cenital (vista superior)**: Reduce oclusión, ideal para tracking
- **Múltiples ángulos**: Cobertura completa de zona crítica

## Servidor

### Requisitos de Hardware

| Componente | Mínimo (1 cámara) | Recomendado (4 cámaras) | Óptimo (16+ cámaras) |
|-----------|-------------------|------------------------|----------------------|
| **GPU** | 1× GPU 8 GB VRAM | 1× GPU 24+ GB VRAM | 2–4× GPU 48+ GB VRAM |
| **CPU** | 4 cores | 8 cores | 16+ cores |
| **RAM** | 16 GB | 32 GB | 64–128 GB |
| **Almacenamiento** | 256 GB SSD | 1 TB NVMe | 4 TB NVMe + RAID |
| **Red** | 1 Gbps | 1 Gbps | 10 Gbps |
| **Fuente de poder** | 750W | 1000W | 2000W+ |

### GPUs Compatibles

| GPU | VRAM | FP16 TFLOPS | Cámaras (YOLOv8x @ 15 FPS) | Backend |
|-----|------|-------------|---------------------------|---------|
| **AMD MI300X** | 192 GB | 653 | 16+ | ROCm |
| **AMD MI250** | 128 GB | 383 | 10+ | ROCm |
| **AMD RX 7900 XTX** | 24 GB | 61 | 4 | ROCm |
| **NVIDIA A100 80GB** | 80 GB | 312 | 12+ | CUDA |
| **NVIDIA H100 80GB** | 80 GB | 989 | 16+ | CUDA |
| **NVIDIA RTX 4090** | 24 GB | 82 | 4 | CUDA |
| **NVIDIA RTX 6000 Ada** | 48 GB | 146 | 8 | CUDA |

### Almacenamiento de Video

| Resolución | FPS | Almacenamiento/día (1 cámara) | 7 días (16 cámaras) |
|-----------|-----|------------------------------|--------------------|
| 720p H.264 | 15 | ~25 GB | ~2.8 TB |
| 1080p H.264 | 30 | ~80 GB | ~9.0 TB |
| 1080p H.265 | 30 | ~40 GB | ~4.5 TB |
| 4K H.264 | 30 | ~300 GB | ~33.6 TB |
| 4K H.265 | 30 | ~150 GB | ~16.8 TB |

**Recomendación**: Usar H.265 para ahorrar 50% de almacenamiento. Almacenar solo clips con alertas (detección de EPP faltante) para reducir requisitos.

## Integración con Sistemas Existentes

### SCADA

El pipeline puede integrarse con sistemas SCADA vía:

**Modbus TCP:**
```python
# Ejemplo de integración Modbus
from pymodbus.client import ModbusTcpClient

def send_alert_to_scada(person_id, missing_items):
    client = ModbusTcpClient("192.168.1.200", port=502)
    client.connect()
    # Escribir en registros Modbus
    client.write_register(0, person_id)  # Registro 0: ID persona
    client.write_register(1, len(missing_items))  # Registro 1: cantidad faltante
    client.close()
```

**OPC UA:**
```python
from opcua import Client

def send_to_opcua(alert_data):
    client = Client("opc.tcp://192.168.1.200:4840")
    client.connect()
    node = client.get_node("ns=2;i=100")  # Nodo PPE Alerts
    node.set_value(json.dumps(alert_data))
    client.disconnect()
```

**Webhook (API REST):**
```bash
python3 scripts/ppe-pipeline.py \
  --alert-webhook "http://scada-server:8080/api/ppe-alerts" \
  --alert-webhook-header "X-API-Key: secret123"
```

### Sistemas de Seguridad Existentes

**Integración con control de acceso:**
- Alertas cuando persona sin EPP pasa por puerta de acceso
- Bloquear acceso si EPP incompleto (vía relé o API)
- Registrar infracción en sistema de control de acceso

**Integración con sistema de alarmas:**
- Enviar alertas a panel de alarmas (SNMP, HTTP, serial)
- Activar sirenas/luces en zona cuando se detecta infracción
- Escalamiento automático si la infracción persiste >N minutos

**Integración con DVR/NVR:**
- Recibir stream RTSP desde NVR existente
- Enviar video anotado de vuelta al NVR
- Marcar footage con infracciones de EPP para búsqueda rápida

## Latencia End-to-End

### Desglose de Latencia

| Etapa | Descripción | Latencia típica (ms) | Optimizable |
|-------|-------------|---------------------|-------------|
| **Captura** | Leer frame desde fuente | 5–15 | Usar decode HW |
| **Decode** | Decodificar JPEG/H.264 | 2–8 (HW) / 10–30 (SW) | Decode HW siempre |
| **Preprocess** | Redimensionar, normalizar | 1–3 | GPU preprocess |
| **Inferencia** | YOLOv8x forward pass | 10–18 (GPU) / 200+ (CPU) | FP16, TensorRT |
| **Postprocess** | NMS, filtrado | 1–2 | Batch processing |
| **Tracking** | IoU matching, asignación | 2–5 | Optimizar con numpy |
| **Alerta** | Evaluación y envío | 1–3 | Async dispatch |
| **Anotación** | Dibujar bounding boxes | 2–5 | GPU drawing |
| **Total** | | **~25–60 ms** | |

### Benchmark por Configuración

| Configuración | GPU | Resolución | Precision | FPS | Latencia End-to-End |
|--------------|-----|-----------|-----------|-----|-------------------|
| Óptimo | MI300X | 640×640 | FP16 | 42 | 24 ms |
| Alta calidad | MI300X | 1280×1280 | FP16 | 18 | 56 ms |
| Balanceado | A100 | 640×640 | FP16 | 55 | 18 ms |
| Alta calidad | A100 | 1280×1280 | FP16 | 22 | 45 ms |
| Edge | RTX 4090 | 640×640 | FP16 | 48 | 21 ms |
| CPU | Ryzen 9 | 640×640 | FP32 | 2 | 500 ms |

### Recomendaciones de Latencia

| Aplicación | Latencia máxima | Configuración recomendada |
|-----------|----------------|--------------------------|
| **Alerta en tiempo real** | <100 ms | GPU dedicada, FP16, decode HW, async alerts |
| **Dashboard en vivo** | <500 ms | GPU compartida, FP16, frame skipping |
| **Revisión forense** | <5 s | CPU, batch processing, post-hoc analysis |
| **Reporte diario** | <1 h | Batch offline, máxima resolución |

## Redundancia y Alta Disponibilidad

### Arquitectura Recomendada

```
                      ┌──────────────────┐
                      │   Load Balancer   │
                      │   (HAProxy/Nginx) │
                      └────────┬─────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
     │  Pipeline Node 1 │ │  Pipeline Node 2 │ │  Pipeline Node 3 │
     │  (GPU MI300X)    │ │  (GPU MI300X)    │ │  (GPU MI300X)    │
     │  8 cámaras       │ │  8 cámaras       │ │  (standby)       │
     └────────┬─────────┘ └────────┬─────────┘ └─────────────────┘
              │                    │
              └────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │    Message Queue     │
              │  (RabbitMQ/Kafka)    │
              └──────────┬──────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
     ┌─────────────────┐ ┌─────────────────┐
     │  Alert Manager   │ │  Storage/DVR     │
     │  (Primary/Standby)│ │  (RAID 5/6)      │
     └─────────────────┘ └─────────────────┘
              │
              ▼
     ┌─────────────────┐
     │  Dashboard/API   │
     │  (Web Server)    │
     └─────────────────┘
```

### Estrategias de HA

**1. Pipeline Activo-Pasivo (N+1):**
- N nodos activos procesando cámaras
- 1 nodo en standby caliente
- Heartbeat entre nodos (cada 5s)
- Si un nodo falla, el standby toma sus cámaras en <30s

**2. Cámaras Distribuidas:**
- Cada cámara asignada a 2 nodos (primario y secundario)
- Si el primario falla, el secundario continúa procesando
- No hay pérdida de detección

**3. Alert Manager Dúplex:**
- Dos instancias de alert-manager (activo/standby)
- Cola de mensajes persistente (RabbitMQ/Kafka)
- Si el activo falla, el standby consume desde donde quedó

**4. Almacenamiento Redundante:**
- RAID 5/6 para almacenamiento de video
- Almacenamiento local + envío a NAS/cloud
- Backup diario de alertas y metadatos

### Plan de Recuperación ante Desastres

| Escenario | Tiempo de recuperación | Acción |
|-----------|----------------------|--------|
| Falla de GPU | <5 min | Switchear a nodo standby |
| Corte eléctrico | <10 min | UPS + generador, auto-start del pipeline |
| Pérdida de cámara | <1 min | Alertar a operaciones, saltar fuente |
| Corrupción de modelo | <2 min | Cargar modelo backup desde disco |
| Error de software | <30 s | Systemd auto-restart |

## Red y Conectividad

### Ancho de Banda por Cámara

| Resolución | FPS | Codec | Ancho de banda |
|-----------|-----|-------|---------------|
| 720p | 15 | H.264 | ~3 Mbps |
| 1080p | 30 | H.264 | ~8 Mbps |
| 1080p | 30 | H.265 | ~4 Mbps |
| 4K | 30 | H.264 | ~25 Mbps |
| 4K | 30 | H.265 | ~12 Mbps |

Para 16 cámaras en 1080p H.265: **~64 Mbps** → 1 Gbps es suficiente.

### Recomendaciones de Red

- **VLAN separada** para cámaras de seguridad (tráfico aislado)
- **QoS** con prioridad alta para RTSP, baja para dashboard
- **Red redundante** con switch stacking o RSTP
- **PoE switch** con respaldo de energía (PoE+ para cámaras PTZ)
- **Firewall** solo permitir RTSP desde IPs del pipeline

## Monitoreo del Sistema

### Métricas Clave

| Métrica | Umbral crítico | Frecuencia | Acción |
|---------|---------------|-----------|--------|
| FPS por cámara | <5 FPS | 10s | Reducir resolución o alertar |
| Latencia de inferencia | >100 ms | 10s | Revisar GPU, reducir batch |
| VRAM usage | >90% | 30s | Reducir batch, liberar memoria |
| GPU temperatura | >85°C | 30s | Revisar cooling, reducir carga |
| Personas sin EPP | >0 | 1s | Activar alertas |
| Caída de cámara | >30s sin frame | 5s | Reconectar o alertar |

### Dashboard de Monitoreo

```bash
# Usar rocm-smi para monitoreo GPU
watch -n 2 rocm-smi

# O script de monitoreo integrado
python3 scripts/ppe-pipeline.py --monitor
```

Salida típica del monitor:
```
[10:32:15] Camera cam1 | 28.5 FPS | 24 ms lat | 6.2 GB VRAM | 5 personas | 0 alerts
[10:32:15] Camera cam2 | 27.1 FPS | 26 ms lat | 6.8 GB VRAM | 3 personas | 1 alert
[10:32:15] GPU 0 | MI300X | 245W | 62°C | 6.8 GB / 192 GB
```

## Costos Estimados

### Hardware (Capital Expenditure)

| Componente | Especificación | Costo estimado (USD) |
|-----------|---------------|---------------------|
| GPU AMD MI300X | 192 GB HBM3 | $25,000–$30,000 |
| GPU NVIDIA A100 80GB | 80 GB HBM2e | $15,000–$20,000 |
| GPU NVIDIA RTX 4090 | 24 GB GDDR6X | $2,000–$2,500 |
| Servidor 4U (8× GPU ready) | Dual EPYC, 256 GB RAM | $8,000–$12,000 |
| Cámara IP 4K IP67 | Hikvision/Dahua | $400–$800 |
| PoE Switch 24 puertos | Cisco/HP | $500–$1,500 |
| NAS 48 TB RAID 5 | Synology/QNAP | $3,000–$5,000 |
| UPS 3000VA | APC/Eaton | $1,000–$2,000 |

### Operación (Operational Expenditure)

| Concepto | Costo mensual estimado |
|---------|----------------------|
| Electricidad (servidor 1500W) | $150–$300 |
| Electricidad (cámaras PoE × 16) | $50–$100 |
| Mantenimiento de hardware | $200–$500 |
| Ancho de banda internet | $100–$300 |
| Personal de operación | Incluido en operación minera |

**Costo total estimado para 16 cámaras:**
- CAPEX: ~$40,000–$80,000 (dependiendo de GPU)
- OPEX: ~$500–$1,200/mes

## Checklist de Despliegue

### Pre-despliegue
- [ ] Verificar compatibilidad GPU (ROCm/CUDA)
- [ ] Instalar dependencias: PyTorch, ultralytics, OpenCV
- [ ] Descargar o fine-tune modelo PPE
- [ ] Verificar acceso a cámaras vía RTSP
- [ ] Probar pipeline con video de prueba
- [ ] Configurar alertas y canales de salida
- [ ] Definir zonas y reglas de EPP
- [ ] Benchmark de rendimiento con cámaras reales

### Despliegue
- [ ] Instalar servidor en sala de operaciones
- [ ] Conectar cámaras a PoE switch
- [ ] Configurar VLAN y reglas de firewall
- [ ] Iniciar pipeline como servicio (systemd)
- [ ] Verificar alertas en dashboard
- [ ] Configurar backups y monitoreo
- [ ] Documentar topología de red y configuración

### Post-despliegue
- [ ] Monitorear métricas primeras 48 horas
- [ ] Ajustar umbrales de confianza y tracking
- [ ] Recopilar datos para fine-tuning adicional
- [ ] Capacitar operadores en dashboard y alertas
- [ ] Establecer procedimiento de respuesta a alertas
- [ ] Programar mantenimiento semanal de sistema

## Seguridad

### Seguridad de Red
- Cámaras en VLAN aislada (sin acceso a internet)
- Pipeline en VLAN separada con acceso controlado
- API dashboard con autenticación (JWT/API Key)
- Firewall: solo puertos necesarios (RTSP:554, API:443)

### Seguridad de Datos
- Video almacenado con cifrado en reposo
- Alertas transmitidas vía HTTPS/TLS
- MQTT con TLS y autenticación
- Logs de alertas inmutables (append-only)
- Retención de video: 30 días mínimo (regulatorio)

### Seguridad Física
- Servidor en sala cerrada con control de acceso
- Cámaras protegidas contra vandalismo (jaulas, domos anti-golpes)
- UPS con generador de respaldo
- Cableado en conduit metálico

## Referencias

- [DS 132 — Reglamento de Seguridad Minera (Chile)](https://www.sernageomin.cl/ds-132/)
- [AMD ROCm Deployment Guide](https://rocm.docs.amd.com/)
- [NVIDIA DeepStream SDK](https://developer.nvidia.com/deepstream-sdk)
- [ONVIF Camera Standard](https://www.onvif.org/)
- [Ultralytics YOLO Deployment](https://docs.ultralytics.com/modes/benchmark/)
