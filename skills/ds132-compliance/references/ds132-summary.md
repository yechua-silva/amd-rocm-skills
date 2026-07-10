# Decreto Supremo 132 — Seguridad Minera (Chile)

## Visión General

El **Decreto Supremo N° 132** del Ministerio de Minería de Chile aprueba el
**Reglamento de Seguridad Minera**, estableciendo las condiciones mínimas de
seguridad que deben cumplir todas las faenas de la industria extractiva minera
en Chile. Fue promulgado el 7 de febrero de 2004 y ha tenido múltiples
modificaciones desde entonces.

**Ministerio**: Ministerio de Minería
**Promulgación**: 07/02/2004
**Publicación**: 11/05/2004
**Versión actual**: 2026 (con modificaciones incorporadas)
**Fuente oficial**: [Biblioteca del Congreso Nacional de Chile](https://www.bcn.cl/leychile/navegar?idNorma=226458)

---

## Artículos Clave para EPP y Detección Automatizada

### Artículo 12 — Obligación de usar EPP según riesgo

> "El empleador deberá proporcionar a sus trabajadores los elementos de
> protección personal adecuados al riesgo de la faena y exigir su uso
> obligatorio. Los elementos de protección personal deberán cumplir con las
> normas chilenas oficiales o las que las sustituyan."

**Implicancias para detección automatizada:**
- Es base legal para exigir verificación de EPP en cada zona
- El empleador debe **proveer y exigir** — la detección automatizada ayuda a
  verificar el cumplimiento de la "exigencia"
- Cada EPP debe cumplir norma chilena (NCh) — ver `compliance-standards.md`
- Aplica a trabajadores propios, contratistas y subcontratistas

**Relación con ppe-detection-pipeline:**
- Las clases EPP detectadas deben corresponder a EPP certificados NCh
- El sistema verifica que el empleador esté exigiendo el uso (Art. 12)
- Infracciones detectadas deben registrarse como incumplimiento del empleador

---

### Artículo 38 — Zonas de peligro y señalización

> "Las zonas de peligro en la faena deberán estar claramente señalizadas y
> contar con las medidas de seguridad necesarias para evitar accidentes. El
> acceso a estas zonas sin los elementos de protección personal requeridos
> queda prohibido."

**Implicancias para detección automatizada:**
- Las zonas configuradas como `riesgo: alto` son "zonas de peligro" según Art. 38
- El umbral de compliance del 90% se aplica rigurosamente a estas zonas
- La señalización debe ser verificable (el sistema puede auditar si las señales
  están visibles en las cámaras)
- El acceso sin EPP a zona de peligro es falta grave

**Zonas típicas consideradas de peligro:**
| Zona | Riesgo | EPP Obligatorio |
|------|--------|-----------------|
| Extracción (tajo abierto/subterránea) | Alto | Casco, chaleco, guantes, botas, lentes |
| Procesamiento (chancado, molienda) | Alto | Casco, chaleco, botas, lentes |
| Mantención de equipos | Medio | Casco, chaleco, guantes, botas, lentes |
| Bodega de insumos | Medio | Casco, chaleco, botas |
| Talleres | Medio | Casco, chaleco, guantes, botas, lentes |

---

### Artículo 43 — Plan de emergencia y rescate

> "Toda faena minera deberá contar con un plan de emergencia actualizado,
> aprobado por el SERNAGEOMIN, que considere los riesgos específicos de la
> faena, incluyendo procedimientos de rescate, primeros auxilios y evacuación."

**Implicancias para detección automatizada:**
- Los reportes de compliance pueden integrarse con el plan de emergencia
- Zonas con bajo compliance histórico deben ser priorizadas en simulacros
- Durante una emergencia real, el sistema puede verificar que todos llevan EPP
  completo durante la evacuación
- Los datos de auditoría (Art. 52) sirven como insumo para actualizar el plan

---

### Artículo 46 — Capacitación en seguridad

> "Los trabajadores deberán recibir capacitación periódica en seguridad minera,
> de acuerdo a los riesgos específicos de la faena. La capacitación deberá
> incluir el uso correcto de los elementos de protección personal."

**Implicancias para detección automatizada:**
- Patrones de infracciones por persona pueden indicar necesidad de recapacitación
- El sistema puede generar recomendaciones de capacitación basadas en datos:
  - Persona reincidente en no usar lentes → capacitación específica en lentes
  - Turno completo con bajo compliance → capacitación grupal
- El registro de capacitaciones debe ser auditable (Art. 52)

---

### Artículo 52 — Registro de accidentes e incidentes

> "Toda faena minera deberá mantener un registro actualizado de accidentes e
> incidentes, disponible para SERNAGEOMIN, que contenga a lo menos: fecha,
> hora, lugar, personas involucradas, descripción de los hechos, causas y
> medidas correctivas."

**Implicancias para detección automatizada:**
- El log de auditoría (`audit-log.py`) extiende este registro a evaluaciones
  de cumplimiento de EPP
- Cada entrada debe contener: timestamp, zona, persona_id, EPP detectado vs
  requerido, compliant, imagen de evidencia
- El registro debe ser **inmutable** (hash chain) para garantizar integridad
- Debe estar disponible para SERNAGEOMIN durante fiscalizaciones
- Las infracciones de EPP recurrente pueden predecir accidentes

**Estructura mínima del registro (Art. 52):**
| Campo | Descripción | Equivalente en auditoría EPP |
|-------|-------------|------------------------------|
| Fecha | Fecha del evento | `timestamp` |
| Hora | Hora del evento | `timestamp` |
| Lugar | Zona de la faena | `zona` |
| Personas | Involucrados | `persona_id` |
| Descripción | Qué ocurrió | EPP faltante vs requerido |
| Causas | Por qué ocurrió | Análisis de patrón |
| Medidas correctivas | Acciones tomadas | Alertas y recomendaciones |

---

## Tabla de Infracciones y Multas

| Tipo de Infracción | Artículo | Rango Multa (UTM) | Rango Multa (CLP aprox.) | Gravedad |
|--------------------|----------|------------------|--------------------------|----------|
| No usar EPP en zona de peligro | Art. 12 + Art. 38 | 10–50 UTM | $650.000–$3.250.000 | Grave |
| Falta de señalización en zona de riesgo | Art. 38 | 5–30 UTM | $325.000–$1.950.000 | Grave |
| No registrar accidente/incidente | Art. 52 | 20–100 UTM | $1.300.000–$6.500.000 | Grave |
| Falta de capacitación en seguridad | Art. 46 | 5–20 UTM | $325.000–$1.300.000 | Menos grave |
| No tener plan de emergencia | Art. 43 | 30–150 UTM | $1.950.000–$9.750.000 | Gravísima |
| Reincidencia en misma infracción | Art. 12 | 2× multa anterior | 2× multa base | Agravante |
| Incumplimiento de medidas correctivas | Art. 52 | 50–200 UTM | $3.250.000–$13.000.000 | Gravísima |

> **Nota**: 1 UTM ≈ $65.000 CLP (valor 2026). La UTM se reajusta semestralmente.
> SERNAGEOMIN determina el monto exacto según factores como:
> - Tamaño de la faena (número de trabajadores)
> - Historial de infracciones del empleador
> - Gravedad del riesgo asociado
> - Número de trabajadores afectados

---

## SERNAGEOMIN: Rol y Facultades

**Servicio Nacional de Geología y Minería** — organismo fiscalizador del
cumplimiento del DS 132.

### Facultades principales
1. **Fiscalizar** faenas mineras en materia de seguridad
2. **Exigir** el cumplimiento de las normas de seguridad minera
3. **Aplicar multas** por infracciones al DS 132
4. **Ordenar paralización** de faenas en caso de riesgo inminente
5. **Aprobar** planes de emergencia y programas de capacitación
6. **Mantener registro** de accidentes mortales y graves

### Proceso de Fiscalización

```
1. Programación
   ├── Fiscalización ordinaria (programada anualmente)
   └── Fiscalización extraordinaria (denuncia o accidente)
        │
2. Inspección en Terreno
   ├── Revisión de documentación (Art. 52, planes, capacitaciones)
   ├── Recorrido por zonas de la faena
   ├── Verificación de EPP en uso
   └── Entrevistas con trabajadores
        │
3. Evaluación
   ├── Cumplimiento / No Cumplimiento por artículo
   ├── Clasificación de infracciones (leve, menos grave, grave, gravísima)
   └── Determinación de multas
        │
4. Notificación
   ├── Acta de fiscalización
   ├── Plazo de corrección (si aplica)
   └── Citación a descargos
        │
5. Seguimiento
   ├── Verificación de correcciones
   ├── Seguimiento de medidas correctivas
   └── Multa ejecutoriada si no hay corrección
```

### Cómo apoya esta skill la fiscalización

| Aspecto | Sin Automatización | Con DS 132 Compliance |
|---------|-------------------|------------------------------|
| Registro de EPP | Papel, fotos sueltas | Log inmutable con hash chain |
| Reportes | Manuales, inconsistentes | PDF/HTML/JSON estandarizados |
| Datos históricos | Archivos físicos | SQLite con consultas rápidas |
| Alertas | Reactivas (post-accidente) | Proactivas (< 90% compliance) |
| Evidencia | Fotos individuales | Imágenes con timestamp y metadata |
| Multi-faena | Dificultad de consolidación | Reportes multi-site |

---

## Referencias

- **Texto oficial DS 132**: [Biblioteca del Congreso Nacional](https://www.bcn.cl/leychile/navegar?idNorma=226458)
- **SERNAGEOMIN**: [https://www.sernageomin.cl/](https://www.sernageomin.cl/)
- **Normas chilenas (NCh)**: [https://www.inn.cl/](https://www.inn.cl/) (Instituto Nacional de Normalización)
- **Ley 16.744**: [https://www.bcn.cl/leychile/navegar?idNorma=28627](https://www.bcn.cl/leychile/navegar?idNorma=28627)
- **DS 594**: [https://www.bcn.cl/leychile/navegar?idNorma=128237](https://www.bcn.cl/leychile/navegar?idNorma=128237)
- **Ley 19.628 (Datos personales)**: [https://www.bcn.cl/leychile/navegar?idNorma=141599](https://www.bcn.cl/leychile/navegar?idNorma=141599)

---

## Historial de Modificaciones del DS 132

| Fecha | Modificación | Contenido |
|-------|-------------|-----------|
| 07/02/2004 | DS 132 original | Promulgación del Reglamento de Seguridad Minera |
| 2012 | Ley 20.593 | Modifica disposiciones sobre seguridad minera |
| 2015 | DS 28 | Actualiza artículos sobre plan de emergencia |
| 2018 | Ley 21.122 | Fortalece facultades fiscalizadoras de SERNAGEOMIN |
| 2022 | DS 18 | Actualiza estándares de EPP y señalización |
| 2024 | DS 7 | Modifica Art. 52: registro digital obligatorio |
| 2026 | Versión consolidada | Texto refundido con todas las modificaciones |

> **Importante**: Verificar siempre la versión vigente en [BCN](https://www.bcn.cl/leychile).
> Esta skill se actualiza con cada modificación del reglamento.
