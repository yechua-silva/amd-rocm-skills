# Guía de Integración — Sistemas Existentes en Faena Minera

## Visión General

Esta guía describe cómo integrar el sistema de compliance DS 132 con los
sistemas existentes en una faena minera típica: SCADA, control de acceso,
reloj control, sistemas de gestión de seguridad, y plataformas SERNAGEOMIN.

---

## Arquitectura de Integración

```
                    ┌─────────────────────────────┐
                    │   ppe-detection-pipeline     │
                    │  (YOLO/VLM en GPU ROCm/CUDA) │
                    └──────────┬──────────────────┘
                               │ Detecciones JSON
                               ▼
                    ┌─────────────────────────────┐
                    │   DS 132 Compliance Engine  │
                    │  (compliance-report.py,      │
                    │   zone-config.py,            │
                    │   audit-log.py)              │
                    └──────┬──────┬──────┬────────┘
                           │      │      │
              ┌────────────┼──────┼──────┼──────────────┐
              │            │      │      │              │
              ▼            ▼      ▼      ▼              ▼
       ┌──────────┐ ┌────────┐ ┌────┐ ┌──────┐ ┌────────────┐
       │  SCADA   │ │ Acceso │ │API │ │MQTT  │ │SERNAGEOMIN │
       │ Industrial│ │Personas│ │REST│ │Events│ │  Portal    │
       └──────────┘ └────────┘ └────┘ └──────┘ └────────────┘
```

---

## 1. Integración con SCADA (Supervisory Control and Data Acquisition)

### Descripción

Los sistemas SCADA monitorean y controlan procesos mineros (chancado,
molienda, transporte). Pueden consumir alertas de compliance paraactivar
protocolos de seguridad.

### Métodos de Integración

#### Opción A: OPC-UA (Recomendado para SCADA modernos)

```python
# Ejemplo: Publicar alertas compliance vía OPC-UA
from opcua import Client

def publicar_alerta_scada(alerta, url_scada="opc.tcp://scada.faena:4840"):
    client = Client(url_scada)
    client.connect()
    try:
        node = client.get_node("ns=2;s=Compliance.Alerts")
        node.set_value(str(json.dumps(alerta)))
    finally:
        client.disconnect()
```

#### Opción B: Modbus TCP (Sistemas legacy)

```bash
# Usar script puente Modbus
python3 tools/modbus-bridge.py \
  --input alertas.json \
  --modbus-host 192.168.1.100 \
  --modbus-port 502 \
  --register-start 40001 \
  --mapping mappings/scada_alerts.json
```

#### Opción C: Archivo compartido (SMB/CIFS)

```bash
# Escribir alertas en carpeta compartida SCADA
python3 scripts/compliance-report.py \
  --input detecciones.json \
  --zones zonas.json \
  --alerts \
  --output /mnt/scada/compliance/alertas_$(date +%Y%m%d_%H%M).json
```

### Datos Compartidos con SCADA

| Variable SCADA | Fuente | Tipo | Descripción |
|---------------|--------|------|-------------|
| `COMPLIANCE_ZONA_XX` | compliance-report | Float 0–100 | % compliance por zona |
| `ALERTA_ACTIVA` | compliance-report | Boolean | True si hay alertas activas |
| `PERSONAS_EN_ZONA` | ppe-pipeline | Integer | Conteo de personas por zona |
| `EPP_FALTANTE_GLOBAL` | audit-log | Integer | Infracciones activas |

---

## 2. Integración con Sistemas de Acceso y Reloj Control

### Descripción

Los sistemas de control de acceso registran entrada/salida de trabajadores
y visitantes. Al integrarse, permiten correlacionar presencia con compliance.

### Integración vía API REST

```python
import requests

# Consultar personal en faena desde sistema de acceso
def obtener_personal_en_faena(api_url="https://acceso.faena.cl/api/v1"):
    response = requests.get(
        f"{api_url}/personal/activo",
        headers={"Authorization": "Bearer <token>"},
        timeout=10,
    )
    return response.json()  # Lista de {persona_id, nombre, zona, ingreso}

# Correlacionar con compliance
def correlacionar_personal_compliance(personal, compliance_results):
    for p in personal:
        pid = p["persona_id"]
        if pid in compliance_results["por_persona"]:
            p["compliance"] = compliance_results["por_persona"][pid]
    return personal
```

### Formato de Intercambio

```json
{
  "persona_id": "TRAB-7890",
  "nombre": "Juan Pérez",
  "rut": "12.345.678-9",
  "tipo": "trabajador",
  "zona_autorizada": ["zona_extraccion", "zona_oficina"],
  "turno": "diurno",
  "ingreso": "2026-06-27T06:30:00-04:00",
  "epp_asignado": ["hardhat", "vest", "gloves", "boots", "safety-glasses"],
  "ultima_capacitacion": "2026-03-15",
  "capacitacion_vigente": true
}
```

### Flujo de Integración

```
1. Trabajador ingresa a faena
   └── Sistema de acceso registra ingreso
   └── API notifica a compliance engine
2. Cámara detecta al trabajador en zona
   └── ppe-detection-pipeline genera detección
   └── compliance-report evalúa contra requisitos de zona
3. Si no compliant:
   └── Alerta en tiempo real vía MQTT
   └── Registro en audit-log (Art. 52)
   └── Notificación a supervisor vía sistema de acceso
```

---

## 3. API REST para Compartir Alertas

### Descripción

API REST para que sistemas externos consuman alertas de compliance en
tiempo real o bajo demanda.

### Endpoints

```
GET  /api/v1/compliance/resumen
  → Resumen global de compliance

GET  /api/v1/compliance/zonas
  → Compliance por zona

GET  /api/v1/compliance/persona/{persona_id}
  → Historial de compliance de una persona

GET  /api/v1/alertas?severidad=alta&activas=true
  → Alertas regulatorias activas

GET  /api/v1/auditoria?desde=2026-06-01&hasta=2026-06-27&zona=zona_extraccion
  → Registros de auditoría filtrados

POST /api/v1/compliance/evaluar
  → Evaluar compliance de una detección (endpoint síncrono)
  Body: { "deteccion": {...}, "zona": "zona_extraccion" }
  Response: { "compliant": true/false, "score": 0.95, "faltante": [] }
```

### Ejemplo de Implementación (Flask)

```python
from flask import Flask, jsonify, request
import sqlite3
import json

app = Flask(__name__)
DB_PATH = "/var/ds132/auditoria.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/api/v1/compliance/resumen", methods=["GET"])
def resumen_compliance():
    conn = get_db()
    cursor = conn.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN compliant = 1 THEN 1 ELSE 0 END) as compliant,
            ROUND(AVG(score), 4) as score_promedio
        FROM auditoria_epp
    """)
    row = dict(cursor.fetchone())
    conn.close()
    row["compliance_pct"] = round(row["compliant"] / row["total"] * 100, 1) if row["total"] else 0
    return jsonify(row)

@app.route("/api/v1/alertas", methods=["GET"])
def alertas():
    severidad = request.args.get("severidad")
    activas = request.args.get("activas", "true").lower() == "true"
    conn = get_db()
    
    query = """
        SELECT persona_id, zona, timestamp, epp_faltante, score
        FROM auditoria_epp
        WHERE compliant = 0
    """
    params = []
    
    if severidad:
        # Severidad se mapea por score: < 0.5 = alta, 0.5-0.8 = media
        if severidad == "alta":
            query += " AND score < 0.5"
        elif severidad == "media":
            query += " AND score BETWEEN 0.5 AND 0.8"
    
    query += " ORDER BY timestamp DESC LIMIT 50"
    cursor = conn.execute(query, params)
    alertas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(alertas)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
```

---

## 4. MQTT para Notificaciones en Tiempo Real

### Descripción

MQTT (Message Queue Telemetry Transport) permite enviar alertas de compliance
a dispositivos móviles, estaciones de supervisión, y sistemas de notificación
en tiempo real.

### Tópicos MQTT

| Tópico | QoS | Payload | Frecuencia |
|--------|-----|---------|------------|
| `rocm/compliance/alerta` | 2 | Alerta JSON | Por evento (infracción) |
| `rocm/compliance/zona/{zona_id}` | 1 | Compliance actualizado | Cada 60s |
| `rocm/compliance/persona/{persona_id}` | 1 | Infracción detectada | Por evento |
| `rocm/compliance/resumen` | 0 | Resumen diario | Cada hora |

### Ejemplo: Publicar Alertas vía MQTT

```python
import paho.mqtt.client as mqtt
import json

def publicar_alerta(alerta, broker="mqtt.faena.cl", port=1883):
    client = mqtt.Client()
    client.connect(broker, port, 60)
    
    topic = f"rocm/compliance/alerta"
    payload = json.dumps(alerta, ensure_ascii=False)
    
    client.publish(topic, payload, qos=2)
    client.disconnect()
    
    print(f"Alerta publicada en {topic}")

# Uso
publicar_alerta({
    "tipo": "ZONA_BAJO_UMBRAL",
    "severidad": "alta",
    "zona": "zona_extraccion",
    "compliance_pct": 82.0,
    "timestamp": "2026-06-27T10:30:00-04:00",
    "mensaje": "Zona de Extracción bajo umbral de cumplimiento (82%)",
})
```

### Ejemplo: Suscriptor para Notificaciones Mobile

```python
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    alerta = json.loads(msg.payload)
    print(f"🚨 Alerta: {alerta['tipo']} — {alerta['mensaje']}")
    # Enviar notificación push (Firebase, APNs, etc.)
    enviar_notificacion_push(alerta)

client = mqtt.Client()
client.on_message = on_message
client.connect("mqtt.faena.cl", 1883, 60)
client.subscribe("rocm/compliance/alerta", qos=2)
client.loop_forever()
```

---

## 5. Exportación a Formato SERNAGEOMIN

### Descripción

SERNAGEOMIN requiere informes estandarizados para fiscalización electrónica.
El sistema de compliance puede exportar reportes en el formato esperado.

### Schema de Exportación SERNAGEOMIN

```json
{
  "encabezado": {
    "tipo_reporte": "cumplimiento_epp",
    "version_formato": "1.0",
    "sernageomin_codigo_faena": "F-1234",
    "razon_social": "Minera Los Pelambres SpA",
    "rut_empresa": "76.123.456-7",
    "faena": "Faena Principal",
    "comuna": "Los Vilos",
    "region": "Coquimbo",
    "periodo_inicio": "2026-06-01",
    "periodo_fin": "2026-06-27",
    "fecha_generacion": "2026-06-27T18:00:00-04:00",
    "sistema": "DS 132 Compliance v1.0.0"
  },
  "cumplimiento_global": {
    "total_evaluaciones": 15420,
    "evaluaciones_compliant": 14280,
    "porcentaje_cumplimiento": 92.6,
    "personas_evaluadas": 245,
    "zonas_monitoreadas": 6,
    "periodo": "mensual"
  },
  "cumplimiento_por_zona": [
    {
      "zona_id": "zona_extraccion",
      "nombre": "Zona de Extracción",
      "evaluaciones": 5230,
      "compliant": 4680,
      "porcentaje": 89.5,
      "riesgo": "alto",
      "epp_faltante_top": ["safety-glasses (320)", "gloves (145)"],
      "alertas_activas": 2
    }
  ],
  "infracciones_por_articulo": [
    {
      "articulo": "Art. 12",
      "descripcion": "Obligación de usar EPP según riesgo",
      "infracciones": 45,
      "personas_involucradas": 12,
      "multa_estimada_utm": "10-50"
    },
    {
      "articulo": "Art. 38",
      "descripcion": "Zonas de peligro y señalización",
      "infracciones": 28,
      "personas_involucradas": 8,
      "multa_estimada_utm": "5-30"
    }
  ],
  "alertas": [
    {
      "tipo": "ZONA_BAJO_UMBRAL",
      "severidad": "alta",
      "zona": "zona_extraccion",
      "detalle": "Zona de Extracción bajo umbral de cumplimiento (89.5% < 90%)",
      "fecha_deteccion": "2026-06-27T18:00:00-04:00",
      "medidas_correctivas": "Reforzar supervisión. Verificar suministro de lentes de seguridad."
    }
  ],
  "adjuntos": {
    "reporte_pdf": "reporte_compliance_junio2026.pdf",
    "log_auditoria_csv": "auditoria_junio2026.csv",
    "evidencias": "evidencias_junio2026.zip"
  }
}
```

### Generación del Reporte SERNAGEOMIN

```bash
# Generar reporte en formato SERNAGEOMIN
python3 scripts/compliance-report.py \
  --input detecciones_mensuales.json \
  --zones zonas.json \
  --period monthly \
  --format json \
  --company "Minera Los Pelambres" \
  --site "Faena Principal" \
  --output reporte_sernageomin.json

# Generar adjuntos
python3 scripts/audit-log.py \
  --db auditoria.db \
  --export csv \
  --output auditoria_mensual.csv

# Empaquetar para envío
zip envio_sernageomin_junio2026.zip \
  reporte_sernageomin.json \
  auditoria_mensual.csv \
  evidencias/
```

---

## 6. Privacidad de Datos (Ley 19.628)

### Descripción

La Ley 19.628 sobre Protección de la Vida Privada regula el tratamiento de
datos personales en Chile. Las imágenes de trabajadores capturadas por las
cámaras constituyen datos personales sensibles.

### Requisitos de Cumplimiento

| Requisito | Implementación en la Skill |
|-----------|---------------------------|
| **Consentimiento** del trabajador para captura de imagen | Configurable en `privacidad.consentimiento_trabajadores` |
| **Finalidad determinada**: solo para seguridad minera DS 132 | Base legal: Art. 52 DS 132 (registro de incidentes) |
| **Proporcionalidad**: solo datos necesarios | Almacenar solo recorte de persona + blur facial |
| **Plazo de retención**: no más del necesario | Configurable: `privacidad.retencion_dias` (default 90) |
| **Seguridad de datos**: cifrado y control de acceso | Cifrado en reposo (`privacidad.cifrar_imagenes`) |
| **Derechos ARCO**: acceso, rectificación, cancelación, oposición | API para consultar y eliminar datos personales |

### Configuración de Privacidad

```yaml
# En zonas.yaml o archivo de configuración separado
privacidad:
  almacenar_imagenes: true
  blur_facial: true
  blur_strength: 15
  retencion_dias: 90
  cifrar_imagenes: true
  algoritmo_cifrado: "AES-256-GCM"
  consentimiento_trabajadores: true
  base_legal: "DS 132 Art. 52 — Registro de incidentes"
  responsable_datos: "prevencion@minera.cl"
  notificar_infraccion: true  # Notificar al trabajador cada infracción
```

### Blur Facial Automático

```bash
# Aplicar blur facial a imágenes almacenadas
python3 scripts/audit-log.py \
  --db auditoria.db \
  --apply-blur \
  --blur-strength 15 \
  --update-db

# Verificar que las imágenes están anonimizadas
python3 scripts/audit-log.py \
  --db auditoria.db \
  --query-false-positives \
  --no-images \
  --output revision_privacidad.json
```

### Consulta y Eliminación de Datos (Derechos ARCO)

```bash
# Consultar qué datos se almacenan de una persona
python3 scripts/audit-log.py \
  --db auditoria.db \
  --query-persona TRAB-1234

# Exportar datos de una persona (derecho de acceso)
python3 scripts/audit-log.py \
  --db auditoria.db \
  --query-persona TRAB-1234 \
  --export json \
  --output datos_persona_TRAB-1234.json

# Eliminar registros de una persona (derecho de cancelación)
# (Requiere implementación adicional)
python3 scripts/audit-log.py \
  --db auditoria.db \
  --delete-persona TRAB-1234 \
  --confirm
```

---

## 7. Integración con Sistemas de Gestión de Seguridad (SGS)

### Descripción

Los sistemas de gestión de seguridad (ISOTools, SGS, software de mutuales)
pueden consumir los reportes de compliance para análisis de indicadores.

### Formatos de Intercambio

| Sistema | Formato | Método | Endpoint |
|---------|---------|--------|----------|
| ISOTools | XML/JSON | API SOAP | `/isotools/import` |
| SGS | CSV | Archivo | Carpeta FTP |
| Mutual ACHS | JSON | API REST | `https://api.achs.cl/v1/seguridad` |
| Mutual IST | XML | Web Service | `https://ws.ist.cl/sgs` |
| ERP (SAP) | IDOC | RFC | `sap://sap.faena/EHP7` |
| Power BI | JSON | API | `https://api.powerbi.com/v1/datasets` |

### Ejemplo: Power BI Dataset

```json
{
  "compliance_diario": [
    {
      "fecha": "2026-06-27",
      "zona": "zona_extraccion",
      "turno": "diurno",
      "total_personas": 42,
      "compliant": 38,
      "compliance_pct": 90.5,
      "epp_faltante_top": "safety-glasses",
      "alertas": 1
    }
  ]
}
```

```bash
# Generar datos para Power BI
python3 scripts/audit-log.py \
  --db auditoria.db \
  --export json \
  --output powerbi_dataset.json
```

---

## Referencias

- **OPC-UA Foundation**: [https://opcfoundation.org/](https://opcfoundation.org/)
- **MQTT Protocol**: [https://mqtt.org/](https://mqtt.org/)
- **Flask REST API**: [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)
- **SERNAGEOMIN — Guía de Fiscalización Electrónica**: [https://www.sernageomin.cl/](https://www.sernageomin.cl/)
- **Ley 19.628 (Datos Personales)**: [https://www.bcn.cl/leychile/navegar?idNorma=141599](https://www.bcn.cl/leychile/navegar?idNorma=141599)
- **Paho MQTT Python**: [https://pypi.org/project/paho-mqtt/](https://pypi.org/project/paho-mqtt/)
