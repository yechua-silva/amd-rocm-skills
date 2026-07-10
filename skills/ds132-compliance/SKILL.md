---
name: ds132-compliance
description: >
  Sistema de cumplimiento normativo DS 132 (Chile) para detección automatizada
  de EPP en minería. Integra con ppe-detection-pipeline para verificar en tiempo
  real el uso de casco (hardhat), chaleco reflectante (vest), guantes (gloves),
  lentes de seguridad (safety glasses) y botas de seguridad (boots) según
  normativa minera chilena. Genera reportes de cumplimiento (PDF/HTML/JSON) con
  métricas por zona, turno y persona. Audita infracciones con log inmutable
  (Art. 52 DS 132). Evalúa zonas de riesgo según Art. 38 (señalización y EPP).
  Produce alertas regulatorias para SERNAGEOMIN cuando el compliance cae bajo
  90%. Configura requisitos de EPP por zona minera (extracción, procesamiento,
  oficina, mantención) con umbrales de confianza ajustables. Compatible con
  faenas multi-site y distingue personal visitante de trabajador. Multi-GPU
  ROCm/CUDA con ppe-detection-pipeline. Almacenamiento SQLite para histórico de
  infracciones y tendencias. Exportación a formatos SERNAGEOMIN. Use this skill
  when checking DS 132 compliance, auditing PPE requirements by zone, or
  generating compliance reports for Chilean mining operations. / Útil al
  verificar cumplimiento DS 132, auditar EPP por zona, o generar reportes de
  compliance. Keywords: ds 132,
  decreto supremo 132, mining compliance chile, epp compliance,
  ppe regulations, seguridad minera, normativa chilena, sernageomin, ds132,
  occupational safety, mining regulations, chilean mining law
license: Apache-2.0
metadata:
  version: "1.1.0"
  author: "yechua-silva"
  tags:
    - amd
    - rocm
    - ds132
    - chile
    - mining
    - safety
    - compliance
    - sernageomin
    - epp
    - ppe
    - nvidia
    - cuda
    - regulatory
    - mining-safety
    - audit
    - reporting
    - zona-riesgo
    - normativa-chilena
compatibility: >
  Compatible with Claude Code, OpenCode, Codex, Cursor, Cline, Roo Code,
  Windsurf, Gemini CLI, and Kiro CLI. Requires Linux with AMD ROCm or
  NVIDIA CUDA GPU (CPU fallback supported).
---

# DS 132 Compliance — Normativa Minera Chilena

Sistema de cumplimiento normativo para el **Decreto Supremo 132** del Ministerio de Minería de Chile, que regula la seguridad minera. Integra con `ppe-detection-pipeline` para verificar en tiempo real el uso de Elementos de Protección Personal (EPP) según la normativa chilena, y genera reportes de compliance listos para SERNAGEOMIN.

La skill detecta automáticamente el backend GPU disponible (ROCm o CUDA) a través de su integración con el pipeline de detección, configura zonas mineras con requisitos de EPP específicos, evalúa el cumplimiento por persona y zona, mantiene un log de auditoría inmutable, y produce alertas regulatorias cuando el compliance cae bajo el umbral exigido.

## Purpose

- **Cumplimiento normativo DS 132**: verificar uso obligatorio de EPP en faenas mineras según Art. 12, Art. 38, Art. 43, Art. 46 y Art. 52
- **Integración con ppe-detection-pipeline**: consumir detecciones en tiempo real (cascos, chalecos, guantes, lentes, botas) y evaluar compliance
- **Configuración por zonas mineras**: definir requisitos de EPP específicos para cada zona (extracción, procesamiento, oficina, mantención) con umbrales de confianza ajustables
- **Auditoría inmutable**: registro inviolable de todas las evaluaciones de cumplimiento con timestamp, zona, persona, EPP detectado vs requerido, y evidencia (imagen)
- **Reportes SERNAGEOMIN-ready**: exportación a PDF/HTML/JSON con métricas de cumplimiento por zona, turno, día y persona
- **Alertas regulatorias**: notificación automática cuando una zona cae bajo 90% de cumplimiento (Art. 38 — zonas de peligro)
- **Histórico de infracciones**: tendencias, EPP faltante recurrente por persona, patrones por turno
- **Multi-faena**: soporte para múltiples sitios mineros con configuración independiente
- **Privacidad de datos**: cumplimiento con Ley 19.628 (protección de datos personales de trabajadores)

## When to Use / Cuándo Usar

La skill se activa con frases como:

- "DS 132 compliance check / verificar cumplimiento normativo minero"
- "Normativa chilena minería / Chilean mining safety regulation"
- "SERNAGEOMIN report / reporte para SERNAGEOMIN"
- "Cumplimiento EPP / PPE compliance audit"
- "Seguridad minera Chile / mining safety Chile regulation"
- "Regulación minera Chile / Chilean mining regulation DS 132"
- "Artículo 12 seguridad / Article 12 PPE obligation"
- "Informe compliance EPP / compliance report PPE mining"
- "Auditoría EPP faena / PPE audit mining site"
- "Zonas de riesgo minería / mining risk zones Article 38"
- "Multas DS 132 / DS 132 fines and penalties"
- "Fiscalización SERNAGEOMIN / SERNAGEOMIN inspection support"
- Keywords: ds 132, normativa chilena minería, sernageomin, cumplimiento epp, seguridad minera, regulación minera chile, artículo 12 seguridad, informe compliance, auditoría epp, mining regulation chile, chilean mining safety, zonas riesgo, faena minera, ppe detection, normativa epp, ley 16744, nch 461

## Prerequisites

- **ppe-detection-pipeline** funcionando con detección de clases EPP: hardhat, vest, gloves, safety-glasses, boots
- **GPU con ROCm o CUDA**: para inferencia del pipeline de detección (MI300X, A100, H100, o GPUs compatibles)
- **Python 3.10+** con dependencias: `numpy`, `pandas`, `jinja2`, `weasyprint` (PDF), `sqlite3`, `pyyaml`
- **Conocimiento de DS 132**: familiaridad con los artículos clave (12, 38, 43, 46, 52) y el proceso de fiscalización SERNAGEOMIN
- **Datos de zonas mineras**: mapa de zonas con requisitos EPP y horarios (archivo YAML/JSON)
- **Base de datos SQLite**: para almacenar histórico de auditoría e infracciones
- **Permisos de acceso**: a cámaras o streams de video de las zonas a monitorear (a través del pipeline)
- **Registro de personal**: lista de trabajadores y visitantes con identificador único por faena

## Quickstart

### 1. Configurar Zonas y Requisitos EPP

```bash
# Crear archivo de configuración de zonas
python3 scripts/zone-config.py \
  --config zonas.yaml \
  --validate \
  --export zonas.json
```

Ejemplo de `zonas.yaml`:
```yaml
zonas:
  zona_extraccion:
    nombre: "Zona de Extracción"
    required: [hardhat, vest, gloves, boots, safety-glasses]
    min_confidence: 0.7
    horario: "06:00-22:00"
    riesgo: alto
  zona_procesamiento:
    nombre: "Zona de Procesamiento"
    required: [hardhat, vest, boots, safety-glasses]
    min_confidence: 0.7
    horario: "00:00-23:59"
    riesgo: alto
  zona_oficina:
    nombre: "Oficina Administrativa"
    required: [hardhat, vest]
    min_confidence: 0.6
    horario: "07:00-19:00"
    riesgo: bajo
  zona_mantencion:
    nombre: "Taller de Mantención"
    required: [hardhat, vest, gloves, boots, safety-glasses]
    min_confidence: 0.75
    horario: "08:00-20:00"
    riesgo: medio
```

### 2. Integrar con ppe-detection-pipeline

```bash
# Compartir detecciones con el módulo de compliance
python3 scripts/compliance-report.py \
  --input detecciones.json \
  --zones zonas.json \
  --period daily \
  --output reporte_diario.json
```

### 3. Generar Reporte de Compliance

```bash
# Reporte completo en PDF
python3 scripts/compliance-report.py \
  --input detecciones.json \
  --zones zonas.json \
  --period daily \
  --company "Minera Los Pelambres" \
  --site "Faena Principal" \
  --format pdf \
  --output reporte_compliance.pdf

# Reporte JSON para integración con sistemas SERNAGEOMIN
python3 scripts/compliance-report.py \
  --input detecciones.json \
  --zones zonas.json \
  --period weekly \
  --format json \
  --output compliance_sernageomin.json
```

## Step-by-Step Guide

### 1. Configurar Mapa de Zonas Mineras con Requisitos EPP

Cada zona minera tiene requisitos de EPP específicos según el riesgo evaluado. El artículo 12 del DS 132 establece la obligación del empleador de proporcionar EPP adecuado al riesgo, y el artículo 38 define las zonas de peligro donde el uso de EPP es obligatorio.

```bash
# Crear configuración inicial
python3 scripts/zone-config.py \
  --config zonas.yaml \
  --validate \
  --export zonas.json \
  --verbose

# Validar que todas las clases EPP existen en el pipeline
# El script verifica contra la lista de clases soportadas:
# hardhat, vest, gloves, safety-glasses, boots
```

**Estructura del archivo de zonas:**

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `nombre` | string | Nombre descriptivo de la zona | "Zona de Extracción" |
| `required` | list | Lista de EPP requeridos | ["hardhat", "vest", "gloves"] |
| `min_confidence` | float | Umbral de confianza mínimo (0.0–1.0) | 0.7 |
| `horario` | string | Horario de operación | "06:00-22:00" |
| `riesgo` | string | Nivel de riesgo (bajo/medio/alto) | alto |
| `tolerancia_minutos` | int | Tolerancia para ingreso sin EPP (min) | 5 |
| `requiere_visitante` | bool | Si aplica también a visitantes | true |

### 2. Integrar con ppe-detection-pipeline

La integración se realiza compartiendo el archivo de detecciones que produce el pipeline. El formato esperado es JSON con la siguiente estructura:

```json
{
  "metadata": {
    "pipeline_version": "1.2.0",
    "backend": "rocm",
    "device": "AMD Instinct MI300X",
    "timestamp": "2026-06-27T10:30:00-04:00"
  },
  "detecciones": [
    {
      "frame_id": "frame_001042",
      "timestamp": "2026-06-27T10:30:00-04:00",
      "zona": "zona_extraccion",
      "persona_id": "TRAB-1234",
      "tipo_persona": "trabajador",
      "epp_detectado": {
        "hardhat": {"presente": true, "confidence": 0.95},
        "vest": {"presente": true, "confidence": 0.88},
        "gloves": {"presente": true, "confidence": 0.72},
        "boots": {"presente": true, "confidence": 0.91},
        "safety-glasses": {"presente": false, "confidence": 0.0}
      },
      "imagen_evidencia": "frame_001042.jpg",
      "bbox_persona": [320, 150, 180, 420]
    }
  ]
}
```

**Modos de integración:**

| Modo | Método | Latencia | Descripción |
|------|--------|----------|-------------|
| Batch | Archivo JSON | Minutos | Procesar detecciones acumuladas cada período |
| Streaming | MQTT | Tiempo real | Recibir detecciones vía MQTT topic |
| API | REST | Segundos | Consultar detecciones por endpoint REST |
| Archivo | File watch | Configurable | Monitorear directorio de detecciones |

```bash
# Modo batch: archivo JSON
python3 scripts/compliance-report.py \
  --input /var/ppe-pipeline/detecciones/2026-06-27.json \
  --zones zonas.json \
  --output compliance.json

# Modo archivo: monitorear directorio
python3 scripts/compliance-report.py \
  --watch-dir /var/ppe-pipeline/detecciones/ \
  --zones zonas.json \
  --output compliance.json \
  --interval 60
```

### 3. Evaluar Compliance por Persona por Zona

La evaluación de compliance compara el EPP detectado contra el EPP requerido para cada zona, aplicando el umbral de confianza configurado.

```python
# Lógica de evaluación (implementada en compliance-report.py)
def evaluar_compliance(deteccion, zona_config):
    requerido = zona_config["required"]
    min_conf = zona_config["min_confidence"]
    faltante = []
    presente = []
    
    for epp in requerido:
        det = deteccion["epp_detectado"].get(epp, {})
        if det.get("presente") and det.get("confidence", 0) >= min_conf:
            presente.append(epp)
        else:
            faltante.append(epp)
    
    compliant = len(faltante) == 0
    return {
        "persona_id": deteccion["persona_id"],
        "zona": deteccion["zona"],
        "timestamp": deteccion["timestamp"],
        "epp_requerido": requerido,
        "epp_detectado": presente,
        "epp_faltante": faltante,
        "compliant": compliant,
        "score": len(presente) / len(requerido) if requerido else 1.0
    }
```

**Reglas de evaluación:**

- Una persona es **compliant** si todos los EPP requeridos están presentes con confianza ≥ umbral
- El **score de compliance** es la proporción de EPP requeridos detectados correctamente
- Si una persona aparece en múltiples frames del mismo período, se usa el promedio o el peor caso (configurable)
- Visitantes pueden tener requisitos distintos (configurable en `requiere_visitante`)
- Si no se detecta a una persona (ej: está fuera del frame), no se evalúa (no cuenta como infracción)

```bash
# Evaluar con peor caso (default)
python3 scripts/compliance-report.py \
  --input detecciones.json \
  --zones zonas.json \
  --scoring worst \
  --output compliance.json

# Evaluar con promedio
python3 scripts/compliance-report.py \
  --input detecciones.json \
  --zones zonas.json \
  --scoring average \
  --output compliance.json
```

### 4. Generar Alertas Regulatorias (DS 132 Art. 12, Art. 38)

Cuando el cumplimiento de una zona cae bajo el 90%, se genera una alerta regulatoria automática. Esto está alineado con:

- **Artículo 12**: Obligación del empleador de proporcionar y exigir el uso de EPP
- **Artículo 38**: Zonas de peligro donde el incumplimiento constituye falta grave

```bash
# Generar alertas del período actual
python3 scripts/compliance-report.py \
  --input detecciones.json \
  --zones zonas.json \
  --alerts \
  --alert-threshold 0.9 \
  --output compliance_con_alertas.json
```

**Tipos de alertas:**

| Tipo | Descripción | Acción Recomendada |
|------|-------------|-------------------|
| `ZONA_BAJO_UMBRAL` | Zona con compliance < 90% | Reforzar señalización y supervisión |
| `PERSONA_REINCIDENTE` | Misma persona falta mismo EPP 3+ veces | Amonestación escrita (Art. 12) |
| `TURNO_CRITICO` | Turno completo con compliance < 80% | Investigación de causas y plan correctivo |
| `EPP_FALTANTE_SISTEMICO` | Un EPP falta en > 30% de detecciones de la zona | Revisar suministro y tallas de EPP |
| `VISITANTE_SIN_EPP` | Visitante sin EPP completo | Reforzar procedimiento de ingreso |

```json
{
  "alerts": [
    {
      "tipo": "ZONA_BAJO_UMBRAL",
      "severidad": "alta",
      "zona": "zona_extraccion",
      "compliance": 0.82,
      "umbral": 0.9,
      "timestamp": "2026-06-27T18:00:00-04:00",
      "detalle": "Zona de Extracción bajo umbral de cumplimiento (82% < 90%)",
      "articulo_ds132": "Art. 12, Art. 38",
      "accion_sugerida": "Reforzar supervisión y verificar suministro de EPP en zona de extracción"
    }
  ]
}
```

### 5. Log de Auditoría Inmutable (DS 132 Art. 52)

El artículo 52 del DS 132 exige el registro de accidentes e incidentes. Este log de auditoría extiende ese requisito a todas las evaluaciones de cumplimiento, proporcionando un registro inviolable.

```bash
# Registrar evaluaciones en el log de auditoría
python3 scripts/audit-log.py \
  --input compliance.json \
  --db auditoria.db \
  --export csv \
  --output auditoria_export.csv
```

**Estructura del log de auditoría (SQLite):**

```sql
CREATE TABLE auditoria_epp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    zona TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    tipo_persona TEXT DEFAULT 'trabajador',
    epp_detectado TEXT NOT NULL,       -- JSON
    epp_requerido TEXT NOT NULL,       -- JSON
    epp_faltante TEXT NOT NULL,        -- JSON
    compliant INTEGER NOT NULL,
    score REAL NOT NULL,
    imagen_evidencia TEXT,             -- path o base64
    hash_anterior TEXT,                -- SHA256 del registro anterior
    hash_registro TEXT UNIQUE NOT NULL,-- SHA256 de este registro
    faena TEXT,
    turno TEXT,
    fuente TEXT DEFAULT 'ppe-pipeline'
);
```

**Inmutabilidad:**

Cada registro contiene un `hash_anterior` que apunta al SHA256 del registro previo, formando una cadena de hash. Esto impide la modificación retroactiva de registros sin romper la cadena.

```bash
# Verificar integridad de la cadena de auditoría
python3 scripts/audit-log.py \
  --db auditoria.db \
  --verify-chain
```

### 6. Reporte Diario/Semanal/Mensual de Cumplimiento

```bash
# Reporte diario
python3 scripts/compliance-report.py \
  --input detecciones_diarias.json \
  --zones zonas.json \
  --period daily \
  --format pdf \
  --company "Minera Escondida" \
  --site "Faena Principal" \
  --output compliance_diario.pdf

# Reporte semanal
python3 scripts/compliance-report.py \
  --input detecciones_semanales.json \
  --zones zonas.json \
  --period weekly \
  --format html \
  --output compliance_semanal.html

# Reporte mensual consolidado
python3 scripts/compliance-report.py \
  --input detecciones_mensuales.json \
  --zones zonas.json \
  --period monthly \
  --format json \
  --output compliance_mensual.json
```

**Métricas incluidas en cada reporte:**

| Métrica | Descripción | Nivel |
|---------|-------------|-------|
| **% Cumplimiento global** | Proporción de detecciones compliant sobre total | Faena |
| **% Cumplimiento por zona** | Compliance desagregado por cada zona minera | Zona |
| **% Cumplimiento por turno** | Compliance desagregado por turno (diurno/nocturno) | Turno |
| **% Cumplimiento por persona** | Compliance individual por trabajador | Persona |
| **Tendencia diaria** | Evolución del compliance en los últimos N días | Temporal |
| **EPP faltante más común** | Ranking de EPP que más faltan (ej: safety-glasses 45%) | EPP |
| **Tasa de reincidencia** | Personas que repiten la misma infracción | Persona |
| **Alertas activas** | Zonas bajo umbral de compliance | Zona |
| **Infracciones por artículo** | Mapeo de infracciones a artículos del DS 132 | Legal |

### 7. Dashboard SERNAGEOMIN-ready

El reporte en formato HTML incluye un dashboard interactivo listo para ser presentado a SERNAGEOMIN durante fiscalizaciones.

```bash
# Generar dashboard HTML completo
python3 scripts/compliance-report.py \
  --input detecciones.json \
  --zones zonas.json \
  --period monthly \
  --format html \
  --dashboard \
  --company "Minera Los Pelambres" \
  --site "Faena Principal" \
  --output dashboard_sernageomin.html
```

**El dashboard incluye:**
- Resumen ejecutivo con indicadores clave
- Tabla de cumplimiento por zona con semáforo (verde ≥ 90%, amarillo ≥ 80%, rojo < 80%)
- Gráfico de tendencia diaria/semanal/mensual
- Top 5 EPP faltantes con gráfico de barras
- Lista de alertas activas con severidad
- Historial de infracciones por persona
- Tabla resumen para fiscalización SERNAGEOMIN
- Exportación a PDF desde el navegador

### 8. Histórico de Infracciones y Tendencias

```bash
# Consultar histórico de infracciones por persona
python3 scripts/audit-log.py \
  --db auditoria.db \
  --query-persona TRAB-1234 \
  --export json \
  --output historial_persona.json

# Tendencias por zona (últimos 30 días)
python3 scripts/audit-log.py \
  --db auditoria.db \
  --query-zona zona_extraccion \
  --period 30d \
  --export csv \
  --output tendencias_zona.csv

# EPP faltante más frecuente por turno
python3 scripts/audit-log.py \
  --db auditoria.db \
  --query-epp-faltante \
  --group-by turno \
  --output epp_faltante_turno.json
```

**Análisis de tendencias disponibles:**

| Análisis | Descripción | Comando |
|----------|-------------|---------|
| Por persona | Historial completo de infracciones de un trabajador | `--query-persona` |
| Por zona | Evolución del compliance en una zona específica | `--query-zona` |
| Por EPP | Frecuencia de falta de cada tipo de EPP | `--query-epp-faltante` |
| Por turno | Comparación de compliance entre turnos | `--group-by turno` |
| Reincidencia | Patrones de infracciones repetidas por persona | `--query-reincidencia` |
| Horas críticas | Horas del día con más infracciones | `--query-horas-criticas` |

### 9. Integración con Sistema de Multas/Amonestaciones

```bash
# Generar reporte de infracciones para multas
python3 scripts/compliance-report.py \
  --input detecciones.json \
  --zones zonas.json \
  --period weekly \
  --penalties \
  --format json \
  --output infracciones_para_multas.json
```

**Mapeo de infracciones a multas según DS 132:**

| Tipo de Infracción | Artículo DS 132 | Rango Multa UTM | Gravedad |
|--------------------|-----------------|-----------------|----------|
| No usar EPP en zona de peligro | Art. 12 + Art. 38 | 10–50 UTM | Grave |
| Falta de señalización en zona riesgo | Art. 38 | 5–30 UTM | Grave |
| No registrar accidente/incidente | Art. 52 | 20–100 UTM | Grave |
| Falta de capacitación en seguridad | Art. 46 | 5–20 UTM | Menos grave |
| No tener plan de emergencia | Art. 43 | 30–150 UTM | Gravísima |
| Reincidencia en misma infracción | Art. 12 | 2× multa anterior | Agravante |

> **Nota**: Las multas son referenciales. SERNAGEOMIN determina el monto exacto según la gravedad, reincidencia y tamaño de la faena. 1 UTM ≈ $65.000 CLP (valor 2026).

El output de `--penalties` incluye para cada infracción: persona, zona, EPP faltante, artículos aplicables, rango de multa estimada, y recomendación de acción.

## Artículos Clave del DS 132

### Artículo 12: Obligación de usar EPP según riesgo

El empleador debe proporcionar a todos los trabajadores los Elementos de Protección Personal adecuados al riesgo de la faena, y exigir su uso obligatorio. Los EPP deben cumplir con las normas chilenas (NCh) correspondientes.

**Relevancia para la skill**: Este artículo es la base legal para exigir la detección automatizada de EPP. Cada zona debe tener definidos sus requisitos de EPP según la evaluación de riesgos.

### Artículo 38: Zonas de peligro y señalización

Define las zonas de peligro en la faena minera donde el acceso sin EPP completo está prohibido. Exige señalización clara de estas zonas.

**Relevancia para la skill**: Las zonas configuradas con `riesgo: alto` se consideran zonas de peligro según Art. 38. El umbral de compliance del 90% se aplica rigurosamente a estas zonas.

### Artículo 43: Plan de emergencia y rescate

Toda faena minera debe contar con un plan de emergencia actualizado, incluyendo procedimientos de rescate, primeros auxilios y evacuación.

**Relevancia para la skill**: Los reportes de compliance pueden integrarse con el plan de emergencia para identificar zonas críticas durante una evacuación.

### Artículo 46: Capacitación en seguridad

Los trabajadores deben recibir capacitación periódica en seguridad minera, incluyendo uso correcto de EPP.

**Relevancia para la skill**: Los patrones de infracciones por persona pueden indicar necesidad de recapacitación. El reporte incluye recomendaciones de capacitación cuando una persona es reincidente.

### Artículo 52: Registro de accidentes e incidentes

Toda faena debe mantener un registro actualizado de accidentes e incidentes, disponible para SERNAGEOMIN.

**Relevancia para la skill**: El log de auditoría inmutable (`audit-log.py`) extiende este registro a las evaluaciones de cumplimiento de EPP, proporcionando evidencia objetiva para fiscalizaciones.

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/ds132-summary.md](references/ds132-summary.md) | Resumen completo del DS 132: artículos clave, tabla de infracciones, multas, proceso de fiscalización SERNAGEOMIN, enlaces oficiales |
| [references/compliance-standards.md](references/compliance-standards.md) | Estándares chilenos relacionados (NCh 461, NCh 1411, NCh 1436, DS 594, Ley 16.744), equivalentes internacionales (OSHA, ISO 45001), mapeo de clases PPE the application a normativa chilena |
| [references/integration-guide.md](references/integration-guide.md) | Guía de integración con sistemas existentes: SCADA, acceso, reloj control, API REST, MQTT, formato SERNAGEOMIN, privacidad Ley 19.628 |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/zone-config.py` | Configuración de zonas mineras con requisitos EPP. Valida clases PPE, exporta a JSON para integración con pipeline. Soporta YAML y JSON. |
| `scripts/compliance-report.py` | Genera reportes de cumplimiento DS 132 en PDF/HTML/JSON. Métricas por zona, turno, persona, día. Alertas regulatorias para zonas < 90% compliance. Soporte multi-site. |
| `scripts/audit-log.py` | Log de auditoría inmutable para DS 132. Cada entrada con hash chain (SHA256). Export a CSV/JSON/SQLite. Verificación de integridad. Consultas por persona, zona, EPP. |

## Common Issues

### 1. Cambios Normativos en el DS 132

**Síntoma**: El texto del DS 132 cambia (nueva versión o modificación), y los artículos referenciados ya no corresponden a la numeración actual.

**Causa**: El DS 132 ha sido modificado en múltiples ocasiones desde su promulgación. Los números de artículo pueden cambiar entre versiones.

**Solución**:
```bash
# Verificar versión vigente del DS 132
# Fuente oficial: Biblioteca del Congreso Nacional de Chile
# https://www.bcn.cl/leychile

# Actualizar referencias en la configuración
python3 scripts/zone-config.py \
  --config zonas.yaml \
  --update-articles \
  --ds132-version "2026"

# Revisar cambios normativos periódicamente (recomendado: cada 6 meses)
# SERNAGEOMIN publica modificaciones en su sitio web
# https://www.sernageomin.cl/
```

Mantener un proceso de revisión semestral de la normativa vigente. La skill incluye referencias actualizadas a la Biblioteca del Congreso Nacional.

### 2. Zonas Mal Configuradas

**Síntoma**: Alertas falsas de incumplimiento porque los requisitos EPP de una zona no coinciden con la realidad operativa.

**Causa**: La configuración de zonas tiene requirements incorrectos (ej: pedir botas en zona de oficina) o umbrales de confianza muy altos para las condiciones de iluminación/cámara.

**Solución**:
```bash
# Validar configuración actual
python3 scripts/zone-config.py --config zonas.yaml --validate

# Ajustar umbrales de confianza por zona
# Zonas con buena iluminación: min_confidence 0.7
# Zonas con iluminación variable: min_confidence 0.6
# Zonas con cámaras de baja resolución: min_confidence 0.5

# Verificar que los requisitos EPP corresponden al riesgo evaluado
# La evaluación de riesgos debe ser realizada por un prevencionista de riesgos

# Probar con datos históricos antes de implementar cambios
python3 scripts/compliance-report.py \
  --input detecciones_historial.json \
  --zones zonas_actualizadas.json \
  --period monthly \
  --output validacion_cambios.json
```

### 3. Falsos Positivos en Auditoría

**Síntoma**: El sistema reporta que un trabajador no usa EPP cuando en realidad sí lo usa, generando infracciones falsas y desconfianza en el sistema.

**Causa**: Problemas de detección del pipeline: oclusión (el EPP está detrás de otro objeto), ángulo de cámara (el casco no se ve desde cierto ángulo), iluminación deficiente, o trabajador entrando/saliendo del frame.

**Solución**:

```bash
# 1. Ajustar umbral de confianza (reducir si hay falsos negativos)
python3 scripts/zone-config.py \
  --config zonas.yaml \
  --set-confidence zona_extraccion 0.6

# 2. Configurar ventana de tolerancia (segundos para evaluar múltiples frames)
# En compliance-report.py: --tolerance-window 5
# Evalúa 5 segundos de detecciones antes de declarar infracción

# 3. Habilitar verificación multi-frame
python3 scripts/compliance-report.py \
  --input detecciones.json \
  --zones zonas.json \
  --multi-frame \
  --min-frames 3 \
  --output compliance_multiframe.json

# 4. Revisar imágenes de evidencia para casos dudosos
python3 scripts/audit-log.py \
  --db auditoria.db \
  --query-false-positives \
  --export json \
  --output falsos_positivos_revision.json
```

**Recomendación**: Implementar un proceso de revisión humana para infracciones con score de compliance entre 0.5 y 0.8 (zona gris). Solo las infracciones con score < 0.5 deben ser automáticas.

### 4. Integración con Sistemas Legacy de la Faena

**Síntoma**: No se puede integrar el log de auditoría con el sistema de registro de accidentes existente en la faena (sistema legacy, base de datos propietaria, mainframe, etc.).

**Causa**: Muchas faenas mineras usan sistemas antiguos que no tienen API REST ni exportación JSON. Pueden usar formatos como texto plano, Excel, dBase, o sistemas SAP mineros.

**Solución**:

```bash
# 1. Exportar a CSV (formato universal aceptado por sistemas legacy)
python3 scripts/audit-log.py \
  --db auditoria.db \
  --export csv \
  --delimiter ";" \
  --encoding "latin-1" \
  --output auditoria_legacy.csv

# 2. Usar el formato de integración por archivo plano
# Configurar exportación periódica a carpeta compartida SMB/CIFS
python3 scripts/audit-log.py \
  --db auditoria.db \
  --export csv \
  --output /mnt/servidor_legacy/auditoria_epp/$(date +%Y%m%d).csv

# 3. Para sistemas SAP: generar archivo plano con formato específico
python3 scripts/audit-log.py \
  --db auditoria.db \
  --export sap \
  --sap-format "IDOC" \
  --output /sap/import/epp_audit.txt
```

**Recomendación para nuevas faenas**: Usar SQLite como almacenamiento central y exponer API REST (vía Flask/FastAPI) para integración con sistemas modernos. Ver `references/integration-guide.md` para más detalles.

### 5. Múltiples Faenas (Multi-Site)

**Síntoma**: La configuración y los reportes se mezclan entre distintas faenas de la misma empresa, generando confusión en los reportes consolidados.

**Causa**: Cada faena tiene su propia configuración de zonas, personal, y turnos. Usar una sola base de datos SQLite sin diferenciar por faena mezcla los datos.

**Solución**:

```bash
# 1. Usar una base de datos SQLite por faena
python3 scripts/audit-log.py \
  --db auditoria_faena_norte.db \
  --input detecciones_faena_norte.json \
  --zones zonas_faena_norte.json

python3 scripts/audit-log.py \
  --db auditoria_faena_sur.db \
  --input detecciones_faena_sur.json \
  --zones zonas_faena_sur.json

# 2. O usar una sola base con campo faena
# Configurar en audit-log.py: --multi-site
python3 scripts/audit-log.py \
  --db auditoria_consolidada.db \
  --multi-site \
  --input detecciones_faena_norte.json \
  --site "Faena Norte"

# 3. Reporte consolidado multi-site
python3 scripts/compliance-report.py \
  --input detecciones_consolidadas.json \
  --zones zonas_consolidadas.json \
  --company "Minera Los Pelambres" \
  --multi-site \
  --period monthly \
  --output compliance_multisite.pdf
```

### 6. Personal Visitante vs Trabajador

**Síntoma**: Visitantes son marcados como infracción por no usar EPP que no les corresponde, o sus requisitos de EPP son diferentes a los de trabajadores regulares.

**Causa**: Los visitantes (contratistas, supervisores externos, fiscalizadores SERNAGEOMIN) pueden tener requisitos de EPP distintos según la duración de su estadía y las zonas que visitan.

**Solución**:

```yaml
# En zonas.yaml, configurar requisitos específicos para visitantes
zonas:
  zona_extraccion:
    nombre: "Zona de Extracción"
    required: [hardhat, vest, gloves, boots, safety-glasses]
    required_visitante: [hardhat, vest, boots, safety-glasses]  # Sin guantes
    min_confidence: 0.7
    requiere_visitante: true
    tolerancia_visitante_minutos: 15  # Más tolerancia para visitantes
```

```bash
# El pipeline debe etiquetar cada detección con tipo_persona:
# "trabajador" o "visitante"

# En compliance-report.py, se evalúa con requisitos distintos según tipo
python3 scripts/compliance-report.py \
  --input detecciones.json \
  --zones zonas.json \
  --distinguish-visitors \
  --output compliance_con_visitantes.json
```

**Reglas para visitantes:**
- Los visitantes siempre deben usar casco y chaleco en zonas de riesgo
- Pueden estar exentos de guantes, lentes o botas si su estadía es < 1 hora
- Los fiscalizadores SERNAGEOMIN están exentos de usar EPP de la faena (portan los propios)
- Configurar `tolerancia_visitante_minutos` para dar tiempo a equiparse al ingresar

### 7. Privacidad de Datos de Trabajadores (Ley 19.628)

**Síntoma**: El registro de imágenes de evidencia con trabajadores identificables puede violar la ley de protección de datos personales chilena.

**Causa**: Las imágenes de evidencia contienen datos personales sensibles (imagen del trabajador). Su almacenamiento y tratamiento debe cumplir con la Ley 19.628.

**Solución**:

```python
# En compliance-report.py y audit-log.py:
# 1. Almacenar solo el frame recortado a la región de la persona
# 2. Aplicar blur facial automático
# 3. No almacenar imágenes por más de 90 días (configurable)
# 4. Cifrar imágenes en reposo

# Configuración de privacidad en zonas.yaml o archivo separado:
privacidad:
  almacenar_imagenes: true
  blur_facial: true
  retencion_dias: 90
  cifrar_imagenes: true
  consentimiento_trabajadores: true  # Los trabajadores firmaron consentimiento
  base_legal: "DS 132 Art. 52 - Registro de incidentes"
```

```bash
# Aplicar blur facial a imágenes de evidencia
python3 scripts/audit-log.py \
  --db auditoria.db \
  --apply-blur \
  --blur-strength 15 \
  --update-db

# Exportar sin imágenes (solo metadatos) para reportes internos
python3 scripts/audit-log.py \
  --db auditoria.db \
  --export json \
  --no-images \
  --output auditoria_sin_imagenes.json
```

## Technical Notes

- **Integración con ppe-detection-pipeline**: La skill consume el output del pipeline de detección. No ejecuta inferencia directamente. El pipeline debe producir detecciones con las clases: `hardhat`, `vest`, `gloves`, `safety-glasses`, `boots`.
- **Multi-GPU**: El pipeline de detección puede distribuirse en múltiples GPUs (ej: una GPU por zona). La skill de compliance es agnóstica al backend.
- **Hash chain**: El log de auditoría usa SHA256 encadenado para garantizar inmutabilidad. El `hash_anterior` del registro N es el SHA256 del registro N-1.
- **Zona "desconocida"**: Si una detección no tiene zona asignada, se evalúa con los requisitos más restrictivos (todas las zonas) o se ignora, según configuración.
- **Tolerancia de ventana**: Para evitar falsos positivos por trabajadores que están transitando entre zonas, se puede configurar una ventana de tolerancia (ej: 30 segundos) antes de evaluar compliance en una zona nueva.
- **Formato SERNAGEOMIN**: El reporte JSON sigue el formato esperado por SERNAGEOMIN para fiscalización electrónica. Ver `references/integration-guide.md` para el schema completo.

## Related Skills

- [`ppe-detection-pipeline`](../ppe-detection-pipeline/SKILL.md) — PPE detection for mining safety
- [`rocm-troubleshoot`](../rocm-troubleshoot/SKILL.md) — Diagnostics and troubleshooting
