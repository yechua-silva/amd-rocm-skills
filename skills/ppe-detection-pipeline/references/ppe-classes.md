# PPE Classes — Definición y Normativa

## Overview

Este documento define cada clase de Elemento de Protección Personal (EPP) detectada por el pipeline `ppe-detection-pipeline`, las combinaciones válidas por zona de trabajo, y la normativa chilena aplicable.

El pipeline detecta 6 clases: `hardhat`, `safety_vest`, `gloves`, `safety_glasses`, `safety_boots`, `person`.

## Clases PPE

### 0. hardhat — Casco de Seguridad

| Propiedad | Descripción |
|-----------|-------------|
| **Clase** | `hardhat` |
| **Elemento** | Casco de seguridad industrial |
| **Propósito** | Protección craneana contra impacto, penetración y descarga eléctrica |
| **Colores típicos** | Blanco (supervisor), amarillo (operador), azul (mantención), rojo (emergencia), naranja (visitante) |
| **Barbiquejo** | Obligatorio en minería chilena (DS 132) |
| **Material** | Polietileno de alta densidad (HDPE), policarbonato o fibra de vidrio |
| **Vida útil** | 5 años desde fabricación (NCh 461) |

**Qué detecta el modelo:**
- Casco puesto en la cabeza del trabajador
- Casco visto desde cualquier ángulo (frontal, lateral, superior)
- Casco con o sin barbiquejo visible

**Qué NO detecta (casos límite):**
- Casco colgado en la mochila o en la mano (no puesto)
- Casco de color similar al fondo (ej. casco blanco en pared blanca)
- Casco parcialmente oculto por maquinaria

### 1. safety_vest — Chaleco Reflectante

| Propiedad | Descripción |
|-----------|-------------|
| **Clase** | `safety_vest` |
| **Elemento** | Chaleco de alta visibilidad con bandas reflectantes |
| **Propósito** | Hacer visible al trabajador en entornos de baja luz y maquinaria en movimiento |
| **Colores típicos** | Naranja fluorescente o amarillo limón con bandas plateadas |
| **Norma** | DS 132, NCh 2193 |
| **Clase de reflectancia** | Clase 2 (minería) o Clase 3 (alta visibilidad, noche) |

**Qué detecta el modelo:**
- Chaleco puesto sobre la ropa de trabajo
- Chaleco con bandas reflectantes visibles
- Chaleco visto de frente, perfil o espalda

**Qué NO detecta:**
- Chaleco debajo de chaqueta abierta (parcialmente visible)
- Chaleco sucio que ha perdido reflectividad
- Arnés de seguridad (similar pero no es chaleco reflectante)

### 2. gloves — Guantes de Seguridad

| Propiedad | Descripción |
|-----------|-------------|
| **Clase** | `gloves` |
| **Elemento** | Guantes de protección industrial |
| **Propósito** | Protección contra cortes, abrasión, químicos, vibración o descarga eléctrica |
| **Tipos** | Anti-corte (kevlar), anti-vibración, dieléctricos, de cuero, de nitrilo |
| **Norma** | NCh 2193, EN 388 (anti-corte), EN 407 (térmico) |

**Qué detecta el modelo:**
- Guantes puestos en ambas manos
- Guantes visibles al menos parcialmente

**Qué NO detecta (dificultad alta):**
- Guantes del mismo color que la piel (ej. guantes de látex beige)
- Guantes en manos que están dentro de los bolsillos
- Guantes pequeños en manos grandes (el color y forma se confunden)
- Guantes de tela delgada (muy similar a la mano sin guante)

**Nota**: Esta es la clase con mayor tasa de falsos negativos. Se recomienda:
- Usar guantes de colores vivos (naranja, azul) en lugar de beige/negro
- Aumentar peso de clase `gloves` en el loss durante fine-tuning
- Recopilar imágenes con guantes en posiciones de trabajo reales

### 3. safety_glasses — Lentes de Seguridad

| Propiedad | Descripción |
|-----------|-------------|
| **Clase** | `safety_glasses` |
| **Elemento** | Lentes de seguridad anti-impacto |
| **Propósito** | Protección ocular contra partículas, polvo, salpicaduras y radiación |
| **Norma** | NCh 328, ANSI Z87.1 |
| **Tipos** | Transparentes (interior), oscuros (exterior), espejados (alta radiación), overgafas (sobre lentes ópticos) |

**Qué detecta el modelo:**
- Lentes puestos en el rostro
- Lentes sobre los ojos, con las patas visibles

**Qué NO detecta (dificultad muy alta):**
- Lentes transparentes sobre rostro (el color se confunde con la piel)
- Lentes colgados en el cuello (no están protegiendo)
- Lentes empañados (pierden el reflejo característico)
- Lentes oscuros en mina subterránea (confundidos con sombra)

**Nota**: Esta es la clase más difícil de detectar con visión computacional. Recomendaciones:
- Usar lentes con montura de color visible (azul, rojo, naranja)
- Fine-tune con imágenes de lentes en condiciones reales de iluminación
- Considerar detección por calor si se usan cámaras térmicas

### 4. safety_boots — Botas de Seguridad

| Propiedad | Descripción |
|-----------|-------------|
| **Clase** | `safety_boots` |
| **Elemento** | Botas de seguridad con puntera de acero/composite |
| **Propósito** | Protección podal contra caída de objetos, perforación, resbalones y químicos |
| **Color típico** | Café oscuro o negro |
| **Norma** | NCh 2111, ASTM F2413 |
| **Características** | Puntera de acero o composite, suela anti-resbalo, resistente a hidrocarburos |

**Qué detecta el modelo:**
- Botas en los pies del trabajador
- Botas visibles al menos parcialmente

**Qué NO detecta:**
- Botas del mismo color que el pantalón de trabajo
- Botas cubiertas por polvo o barro
- Botas que están debajo de equipo de protección de piernas
- Zapatos de seguridad (bajos) — no confundir con botas

### 5. person — Persona

| Propiedad | Descripción |
|-----------|-------------|
| **Clase** | `person` |
| **Elemento** | Trabajador (cuerpo completo o torso) |
| **Propósito** | Base para tracking y asignación de EPP |
| **Qué detecta** | Persona de pie o caminando, vista desde cualquier ángulo |

**Importante**: La clase `person` es el ancla del sistema. Sin detectar a la persona, no se puede verificar su EPP. El pipeline necesita `person` para:
1. Asignar ID de tracking
2. Asociar elementos EPP a la persona
3. Evaluar cumplimiento
4. Generar alertas

## Combinaciones Válidas por Zona

### Mina Subterránea

| Elemento | Obligatorio | Norma |
|----------|-------------|-------|
| Casco | ✅ Siempre | DS 132 |
| Chaleco reflectante | ✅ Siempre | DS 132 |
| Guantes | ✅ Siempre | NCh 2193 |
| Lentes de seguridad | ✅ Siempre | NCh 328 |
| Botas de seguridad | ✅ Siempre | NCh 2111 |
| **EPP mínimo** | **Completo (5 elementos)** | |

### Mina a Cielo Abierto / Rajo

| Elemento | Obligatorio | Norma |
|----------|-------------|-------|
| Casco | ✅ Siempre | DS 132 |
| Chaleco reflectante | ✅ Siempre | DS 132 |
| Guantes | ✅ Siempre (operación) | NCh 2193 |
| Lentes de seguridad | ✅ Siempre | NCh 328 |
| Botas de seguridad | ✅ Siempre | NCh 2111 |
| **EPP mínimo** | **Completo (5 elementos)** | |

### Planta de Proceso

| Elemento | Obligatorio | Notas |
|----------|-------------|-------|
| Casco | ✅ Siempre | |
| Chaleco reflectante | ✅ En zonas de tránsito vehicular | |
| Guantes | ✅ En áreas de manipulación | Puede variar por área |
| Lentes de seguridad | ✅ Siempre | |
| Botas de seguridad | ✅ Siempre | |
| **EPP mínimo** | **5 elementos (guantes según área)** | |

### Taller de Mantención

| Elemento | Obligatorio | Notas |
|----------|-------------|-------|
| Casco | ✅ Siempre | |
| Chaleco reflectante | ⚠️ En áreas de tránsito | No siempre requerido |
| Guantes | ✅ Siempre | Anti-corte o dieléctricos |
| Lentes de seguridad | ✅ Siempre | |
| Botas de seguridad | ✅ Siempre | Con puntera de acero |
| **EPP mínimo** | **4–5 elementos** | |

### Zona Administrativa / Casino / Baños

| Elemento | Obligatorio | Notas |
|----------|-------------|-------|
| Casco | ❌ | Excepto en zonas de visita |
| Chaleco reflectante | ❌ | Excepto en zonas de visita |
| Guantes | ❌ | No requerido |
| Lentes de seguridad | ❌ | No requerido |
| Botas de seguridad | ❌ | Zapatos cerrados mínimos |
| **EPP mínimo** | **Ninguno** | |

### Zonas de Visita

| Elemento | Obligatorio | Notas |
|----------|-------------|-------|
| Casco | ✅ Siempre | Con barbiquejo |
| Chaleco reflectante | ✅ Siempre | |
| Guantes | ❌ | No requerido para visitas |
| Lentes de seguridad | ⚠️ Recomendado | |
| Botas de seguridad | ✅ Siempre | |
| **EPP mínimo** | **3–4 elementos** | |

## Configuración de Reglas por Zona en el Pipeline

```bash
# Definir zonas con EPP requerido
python3 scripts/ppe-pipeline.py \
  --zone-rules "subterranea:hardhat,safety_vest,gloves,safety_glasses,safety_boots" \
  --zone-rules "taller:hardhat,gloves,safety_glasses,safety_boots" \
  --zone-rules "oficina:none"
```

## Normativa Chilena

### DS 132 — Reglamento de Seguridad Minera

El **Decreto Supremo 132** del Ministerio de Minería de Chile establece las obligaciones de seguridad en faenas mineras, incluyendo:

- **Artículo 15**: Obligación de usar EPP en todas las áreas de trabajo
- **Artículo 18**: El empleador debe proporcionar EPP certificado
- **Artículo 22**: Prohibición de ingresar a zonas de trabajo sin EPP
- **Artículo 25**: Los EPP deben cumplir con normativa chilena (NCh)

### NCh 461 — Cascos de Seguridad Industrial

- Define requisitos de fabricación, ensayo y uso de cascos
- Clasificación: Tipo I (impacto vertical), Tipo II (impacto vertical y lateral)
- El casco debe tener barbiquejo en minería (DS 132 Art. 18)

### NCh 2111 — Calzado de Seguridad

- Define requisitos para botas de seguridad con puntera de protección
- Clasificación: Clase I (cuero), Clase II (otros materiales)
- Resistencia a la penetración, compresión, y anti-resbalo

### NCh 328 — Protectores Oculares

- Define requisitos para lentes de seguridad industrial
- Clasificación por tipo de protección: impacto, radiación, químicos, polvo

### NCh 2193 — Ropa de Protección

- Define requisitos para ropa de alta visibilidad (chalecos reflectantes)
- Clase 1, 2 y 3 según nivel de reflectancia y área cubierta

## Mapeo a Normativa en Alertas

El pipeline puede incluir la normativa en las alertas:

```json
{
  "timestamp": "2026-06-27T14:23:05.123Z",
  "person_id": 3,
  "ppe_missing": ["hardhat", "safety_glasses"],
  "violations": [
    {"item": "hardhat", "norm": "DS 132 Art. 18", "severity": "critical"},
    {"item": "safety_glasses", "norm": "NCh 328", "severity": "high"}
  ]
}
```

## Referencias

- [DS 132 — Reglamento de Seguridad Minera (Chile)](https://www.sernageomin.cl/ds-132/)
- [NCh 461 — Cascos de Seguridad Industrial](https://www.inn.cl/)
- [NCh 2111 — Calzado de Seguridad](https://www.inn.cl/)
- [NCh 328 — Protectores Oculares](https://www.inn.cl/)
- [NCh 2193 — Ropa de Protección Alta Visibilidad](https://www.inn.cl/)
- [EN 388 — Guantes de Protección contra Riesgos Mecánicos](https://www.iso.org/)
- [ANSI Z87.1 — Occupational and Educational Eye Protection](https://www.ansi.org/)
