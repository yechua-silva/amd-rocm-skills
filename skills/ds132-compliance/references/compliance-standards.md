# Estándares de Cumplimiento — Normativa Chilena e Internacional

## Estándares Chilenos Relacionados con EPP para Minería

### NCh 461 — EPP para Minería (Norma General)

**Título**: Elementos de Protección Personal para la Industria Minera
**Organismo**: Instituto Nacional de Normalización (INN)
**Estado**: Vigente

Establece los requisitos generales que deben cumplir los EPP utilizados en
faenas mineras, incluyendo:

- Clasificación de EPP por tipo de riesgo
- Requisitos de certificación
- Marcado y etiquetado
- Vida útil y almacenamiento
- Procedimientos de ensayo

**Relación con DS 132**: El Artículo 12 exige que los EPP cumplan con las
normas chilenas oficiales. NCh 461 es la norma marco que remite a normas
específicas por tipo de EPP.

### NCh 1411 — Cascos de Seguridad

**Título**: Cascos de seguridad para uso industrial
**Norma específica**: NCh 1411.OfXX
**Equivalente ISO**: ISO 3873

| Requisito | Especificación |
|-----------|---------------|
| Resistencia al impacto | ≤ 5000 N transmitidos |
| Penetración | Sin contacto con la cabeza |
| Retención del arnés | Desplazamiento ≤ 25 mm |
| Rango temperatura | −10 °C a +50 °C |
| Marcado | Fabricante, fecha, norma, talla |

**Application-specific classes**: `hardhat`

### NCh 1436 — Chalecos Reflectantes

**Título**: Chalecos de alta visibilidad para uso profesional
**Norma específica**: NCh 1436.OfXX
**Equivalente ISO**: ISO 20471

| Clase | Área mínima material fluorescente | Área mínima material reflectante | Uso recomendado |
|-------|----------------------------------|----------------------------------|-----------------|
| Clase 1 | 0.14 m² | 0.10 m² | Baja velocidad, fondos simples |
| Clase 2 | 0.50 m² | 0.13 m² | Minería, zonas de riesgo medio |
| Clase 3 | 0.80 m² | 0.20 m² | Minería nocturna, alta velocidad |

**Recomendado para minería**: Clase 2 o 3

**Application-specific classes**: `vest`

### NCh 461 (Sección Guantes) — Guantes de Seguridad

**Título**: Guantes de protección contra riesgos mecánicos
**Norma específica**: NCh 461/1
**Equivalente ISO**: ISO 21420, EN 388

| Nivel | Resistencia a la abrasión | Corte | Desgarro | Perforación |
|-------|--------------------------|-------|----------|-------------|
| 1 | ≥ 100 ciclos | ≥ 1.2 N | ≥ 10 N | ≥ 20 N |
| 2 | ≥ 500 ciclos | ≥ 2.5 N | ≥ 25 N | ≥ 60 N |
| 3 | ≥ 2000 ciclos | ≥ 5.0 N | ≥ 50 N | ≥ 100 N |
| 4 | ≥ 8000 ciclos | ≥ 10 N | ≥ 75 N | ≥ 150 N |
| 5 | — | ≥ 20 N | ≥ 90 N | — |

**Recomendado para minería**: Nivel 3 o superior para manipulación de materiales

**Application-specific classes**: `gloves`

### NCh 461 (Sección Calzado) — Botas de Seguridad

**Título**: Calzado de seguridad para uso profesional
**Norma específica**: NCh 461/2
**Equivalente ISO**: ISO 20345

| Propiedad | SB (Básico) | S1 | S2 | S3 | S5 |
|-----------|-------------|-----|-----|-----|-----|
| Punta de seguridad | ✅ | ✅ | ✅ | ✅ | ✅ |
| Antiestática | ❌ | ✅ | ✅ | ✅ | ✅ |
| Absorción de energía talón | ❌ | ✅ | ✅ | ✅ | ✅ |
| Impermeabilidad | ❌ | ❌ | ✅ | ✅ | ✅ |
| Resistencia a perforación | ❌ | ❌ | ❌ | ✅ | ✅ |
| Suela resistente a hidrocarburos | ❌ | ❌ | ❌ | ❌ | ✅ |

**Recomendado para minería**: S3 (uso general) o S5 (ambientes con hidrocarburos)

**Application-specific classes**: `boots`

### NCh 461 (Sección Lentes) — Lentes de Seguridad

**Título**: Protectores oculares para uso profesional
**Norma específica**: NCh 461/3
**Equivalente ISO**: ISO 16321

| Tipo | Aplicación | Resistencia al impacto |
|------|------------|----------------------|
| Lentes básicos | Protección frontal | 45 m/s (partícula 6 mm) |
| Lentes envolventes | Protección frontal y lateral | 45 m/s (partícula 6 mm) |
| Careta facial | Protección completa rostro | 120 m/s (partícula 6 mm) |

**Recomendado para minería**: Lentes envolventes o careta facial en zonas de
procesamiento (partículas en suspensión)

**Application-specific classes**: `safety-glasses`

---

### DS 594 — Condiciones Sanitarias Básicas

**Título**: Reglamento sobre condiciones sanitarias y ambientales básicas en
los lugares de trabajo
**Ministerio**: Ministerio de Salud
**Relación**: Complementa al DS 132 en aspectos de higiene y salud ocupacional

**Artículos relevantes para EPP:**

| Artículo | Tema | Relación con DS 132 |
|----------|------|---------------------|
| Art. 9 | Obligación de mantener lugares de trabajo limpios | Indirecta (condiciones sanitarias) |
| Art. 12 | Protección contra riesgos químicos | Complementa EPP respiratorio |
| Art. 18 | Ruido y vibraciones | EPP auditivo (no cubierto por DS 132 directamente) |
| Art. 22 | Iluminación | Afecta detección automatizada (cámaras) |

### Ley 16.744 — Seguro Social contra Accidentes

**Título**: Establece normas sobre accidentes del trabajo y enfermedades
profesionales
**Ministerio**: Ministerio del Trabajo y Previsión Social
**Año**: 1968 (con modificaciones)

**Relevancia para DS 132:**

- Establece el seguro social obligatorio contra accidentes laborales
- Las mutuales de seguridad (ACHS, IST, Mutual) fiscalizan condiciones de seguridad
- Los empleadores cotizan según tasa de accidentabilidad
- Un buen compliance EPP reduce la tasa de accidentabilidad y la cotización

**Conexión con el sistema de compliance:**
- Los reportes de compliance pueden usarse para demostrar debida diligencia
- La reducción de infracciones EPP impacta directamente en la tasa de
  accidentabilidad
- Las mutuales pueden requerir los reportes para auditorías

---

## Equivalentes Internacionales

### Tabla de Correspondencia Normativa

| Chile | OSHA (EEUU) | ISO | Unión Europea | Descripción |
|-------|-------------|-----|---------------|-------------|
| DS 132 | 30 CFR Part 56/57 | ISO 45001 | Directive 92/104/EEC | Seguridad minera |
| NCh 461 | 29 CFR 1910 Subpart I | ISO 45001 | EU 2016/425 | EPP general |
| NCh 1411 | ANSI Z89.1 | ISO 3873 | EN 397 | Cascos seguridad |
| NCh 1436 | ANSI/ISEA 107 | ISO 20471 | EN 20471 | Chalecos reflectantes |
| NCh 461/1 | ANSI/ISEA 105 | ISO 21420 | EN 388 | Guantes seguridad |
| NCh 461/2 | ASTM F2413 | ISO 20345 | EN ISO 20345 | Calzado seguridad |
| NCh 461/3 | ANSI Z87.1 | ISO 16321 | EN 166 | Lentes seguridad |
| DS 594 | 29 CFR 1910 | ISO 45001 | EU 89/654 | Condiciones sanitarias |
| Ley 16.744 | — | — | — | Seguro accidentes |

### Diferencias Clave con Estándares Internacionales

| Aspecto | Chile (DS 132) | OSHA (30 CFR) | ISO 45001 |
|---------|---------------|---------------|-----------|
| Enfoque | Prescriptivo (artículos detallados) | Performance-based | Sistema de gestión |
| Fiscalización | SERNAGEOMIN | MSHA | Auditoría externa |
| Multas | UTM (fijas por tipo) | USD (variables) | Depende del país |
| Registro | Art. 52 obligatorio | 29 CFR Part 50 | Documentación SMS |
| Capacitación | Art. 46 periódica | 30 CFR Part 48 | Competencia y formación |
| EPP | Exigido por zona de riesgo | Hazard assessment | Evaluación de riesgos |

---

## Mapeo de PPE classes a Normativa Chilena

| Application-specific classes | Nombre Español | Norma Chilena | Artículo DS 132 | EPP Relacionado |
|-------------|----------------|---------------|-----------------|-----------------|
| `hardhat` | Casco de seguridad | NCh 1411 | Art. 12, Art. 38 | Casco minero con barbiquejo |
| `vest` | Chaleco reflectante | NCh 1436 | Art. 12, Art. 38 | Chaleco Clase 2 o 3 |
| `gloves` | Guantes de seguridad | NCh 461/1 | Art. 12 | Guantes anticorte nivel 3+ |
| `safety-glasses` | Lentes de seguridad | NCh 461/3 | Art. 12 | Lentes envolventes o careta |
| `boots` | Botas de seguridad | NCh 461/2 | Art. 12, Art. 38 | Bota S3 con puntera y plantilla |

### Validación de EPP en el Pipeline

Para cada clase detectada, el pipeline debe verificar:

```python
# Mapeo de validación (implementado en zone-config.py)
VALIDACION_EPP = {
    "hardhat": {
        "norma": "NCh 1411",
        "articulo": "Art. 12, Art. 38",
        "colores_seguridad": ["amarillo", "naranja", "blanco", "rojo", "azul"],
        "validate_color": True,        # Algunas faenas usan colores por rol
        "require_chin_strap": False,   # Barbiquejo (opcional según zona)
    },
    "vest": {
        "norma": "NCh 1436",
        "articulo": "Art. 12, Art. 38",
        "clase_minima": 2,             # Clase 2 o 3 para minería
        "colores_permitidos": ["amarillo", "naranja", "rojo"],
    },
    "gloves": {
        "norma": "NCh 461/1",
        "articulo": "Art. 12",
        "nivel_minimo_corte": 3,
        "tipo": "mecanico",            # También podría ser químico, térmico
    },
    "safety-glasses": {
        "norma": "NCh 461/3",
        "articulo": "Art. 12",
        "tipo": "envolvente",          # O careta facial
        "proteccion_lateral": True,
    },
    "boots": {
        "norma": "NCh 461/2",
        "articulo": "Art. 12, Art. 38",
        "clase_minima": "S3",
        "puntera": "acero/compuesto",
        "altura_minima_mm": 150,
    },
}
```

---

## Referencias

- Instituto Nacional de Normalización (INN): [https://www.inn.cl/](https://www.inn.cl/)
- Ley Chile — Biblioteca del Congreso Nacional: [https://www.bcn.cl/leychile](https://www.bcn.cl/leychile)
- OSHA Mining Safety: [https://www.msha.gov/](https://www.msha.gov/)
- ISO 45001: [https://www.iso.org/standard/63787.html](https://www.iso.org/standard/63787.html)
- EU Directive 92/104/EEC: [https://eur-lex.europa.eu/](https://eur-lex.europa.eu/)
- ANSI/ISEA 107: [https://www.isea.org/](https://www.isea.org/)
