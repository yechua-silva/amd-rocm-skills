# PPE Dataset Guide

## Overview

Esta guía describe los datasets disponibles para entrenar modelos de detección de Elementos de Protección Personal (EPP), el formato esperado, y las recomendaciones de data augmentation específica para minería.

El pipeline `ppe-detection-pipeline` espera datasets en **formato YOLO** con 6 clases: `hardhat`, `safety_vest`, `gloves`, `safety_glasses`, `safety_boots`, `person`.

## Datasets Públicos

### 1. PPE Dataset (Kaggle)

| Propiedad | Valor |
|-----------|-------|
| **URL** | https://www.kaggle.com/datasets/arnabmishra/ppe-dataset |
| **Imágenes** | ~3,200 |
| **Clases** | hardhat, safety_vest, gloves, safety_glasses, safety_boots, person, mask, ear_protection |
| **Formato** | COCO JSON |
| **Resolución** | Variable (640×480 a 1920×1080) |
| **Entornos** | Construcción, almacenes, exterior |
| **Licencia** | CC BY 4.0 |

**Notas**: Dataset general de EPP con cobertura parcial para minería. Las clases mask y ear_protection no se usan en Munin. Requiere conversión de COCO a YOLO.

### 2. Hard Hat Workers Dataset (Makesense.ai)

| Propiedad | Valor |
|-----------|-------|
| **URL** | https://www.kaggle.com/datasets/andrewmvd/hard-hat-workers |
| **Imágenes** | ~5,000 |
| **Clases** | hardhat, head (persona sin casco), person, vest, boots |
| **Formato** | COCO JSON + VOC XML |
| **Resolución** | Variable |
| **Entornos** | Construcción civil |
| **Licencia** | CC BY-SA 4.0 |

**Notas**: Buen dataset para casco y chaleco. No incluye guantes ni lentes. Útil como base para fine-tuning con datos adicionales.

### 3. Safety PPE Dataset (Roboflow Universe)

| Propiedad | Valor |
|-----------|-------|
| **URL** | https://universe.roboflow.com/ |
| **Búsqueda** | "safety ppe", "hardhat detection", "ppe mining" |
| **Formatos** | COCO JSON, YOLO TXT, TFRecord, Pascal VOC |
| **Clases** | Variables según dataset |
| **Licencia** | Varía por dataset |

**Notas**: Roboflow tiene múltiples datasets de EPP. Algunos específicos para minería. Se puede exportar directamente a formato YOLO.

### 4. MEX (Mining Equipment and eXplosives) Dataset

| Propiedad | Valor |
|-----------|-------|
| **URL** | Repositorios académicos (búsqueda: MEX dataset mining) |
| **Imágenes** | ~1,500 |
| **Clases** | hardhat, person, truck, excavator, etc. |
| **Formato** | COCO JSON |
| **Entornos** | Minería a cielo abierto |
| **Licencia** | Académica |

**Notas**: Enfocado en minería pero con pocas clases PPE. Útil para complementar otros datasets.

### 5. Chile Mining PPE (Propio)

Se recomienda crear un dataset propio con imágenes de faenas mineras chilenas debido a las diferencias en EPP usado localmente vs. datasets internacionales.

| Propiedad | Recomendación |
|-----------|---------------|
| **Mínimo imágenes** | 500 por clase (3,000 total) |
| **Condiciones** | Día, noche, subterráneo, superficie, polvo, lluvia |
| **Equipos chilenos** | Cascos 3M modelo chileno, botas nacionales, chalecos con logo faena |
| **Ángulos** | Frontal, lateral, superior (dron), cenital |
| **Formato** | YOLO TXT |

## Formato de Dataset

### Estructura de Directorios (YOLO)

```
dataset/
├── dataset.yaml
├── images/
│   ├── train/
│   │   ├── img_0001.jpg
│   │   ├── img_0002.jpg
│   │   └── ...
│   └── val/
│       ├── img_1001.jpg
│       ├── img_1002.jpg
│       └── ...
└── labels/
    ├── train/
    │   ├── img_0001.txt
    │   ├── img_0002.txt
    │   └── ...
    └── val/
        ├── img_1001.txt
        ├── img_1002.txt
        └── ...
```

### dataset.yaml

```yaml
path: ./dataset
train: images/train
val: images/val

nc: 6
names:
  - hardhat
  - safety_vest
  - gloves
  - safety_glasses
  - safety_boots
  - person
```

### Formato YOLO TXT (por imagen)

Cada archivo `.txt` contiene una línea por objeto:

```
<class_id> <x_center> <y_center> <width> <height>
```

Coordenadas normalizadas a [0, 1] respecto al ancho/alto de la imagen.

```
0 0.52 0.31 0.18 0.22
1 0.50 0.55 0.30 0.35
5 0.50 0.60 0.25 0.70
```

### Conversión COCO → YOLO

```python
import json

def coco_to_yolo(coco_path, output_dir, img_width, img_height):
    with open(coco_path) as f:
        coco = json.load(f)

    # Crear mapping de imágenes
    images = {img["id"]: img for img in coco["images"]}

    # Agrupar anotaciones por imagen
    from collections import defaultdict
    annotations = defaultdict(list)
    for ann in coco["annotations"]:
        annotations[ann["image_id"]].append(ann)

    os.makedirs(output_dir, exist_ok=True)

    for img_id, anns in annotations.items():
        img = images[img_id]
        w, h = img["width"], img["height"]
        txt_name = os.path.splitext(img["file_name"])[0] + ".txt"
        txt_path = os.path.join(output_dir, txt_name)

        with open(txt_path, "w") as f:
            for ann in anns:
                cat_id = ann["category_id"]
                bbox = ann["bbox"]  # COCO: [x, y, width, height]
                x, y, bw, bh = bbox
                # Normalizar
                x_center = (x + bw / 2) / w
                y_center = (y + bh / 2) / h
                bw_norm = bw / w
                bh_norm = bh / h
                f.write(f"{cat_id} {x_center:.6f} {y_center:.6f} {bw_norm:.6f} {bh_norm:.6f}\n")
```

## Clases Recomendadas para Munin

| ID | Clase | Elemento | Prioridad | Dataset principal | Dataset complementario |
|----|-------|----------|-----------|-------------------|----------------------|
| 0 | `hardhat` | Casco de seguridad | Crítica | PPE Kaggle | Hard Hat Workers |
| 1 | `safety_vest` | Chaleco reflectante | Crítica | PPE Kaggle | Hard Hat Workers |
| 2 | `gloves` | Guantes de seguridad | Alta | PPE Kaggle | Dataset propio |
| 3 | `safety_glasses` | Lentes de seguridad | Alta | PPE Kaggle | Dataset propio |
| 4 | `safety_boots` | Botas de seguridad | Alta | Hard Hat Workers | Dataset propio |
| 5 | `person` | Persona | Requerida | Cualquiera | Cualquiera |

**Nota**: Para producción en minería chilena, se recomienda complementar con al menos 500 imágenes por clase del sitio específico.

## Data Augmentation para Minería

La minería presenta condiciones visuales únicas que requieren aumentación específica:

### Parámetros Recomendados

| Augmentación | Valor Estándar | Valor Minería | Efecto |
|-------------|----------------|---------------|--------|
| `hsv_h` | 0.015 | 0.015–0.02 | Variación de luz natural (día/noche) |
| `hsv_s` | 0.7 | 0.7–0.9 | Polvo en suspensión, suciedad en lentes |
| `hsv_v` | 0.4 | 0.4–0.6 | Baja luz subterránea, sombras de maquinaria |
| `degrees` | 0.0 | 5.0–15.0 | Cabezas inclinadas, terreno irregular |
| `translate` | 0.1 | 0.1–0.2 | Vibración de cámara en maquinaria |
| `scale` | 0.5 | 0.3–0.6 | Distancias variables en galerías |
| `flipud` | 0.0 | 0.3–0.5 | Visión desde altura (drones, grúas) |
| `mosaic` | 1.0 | 1.0 | Escenas complejas con múltiples personas |
| `mixup` | 0.0 | 0.1–0.2 | Combinar condiciones de luz |
| `copy_paste` | 0.0 | 0.1–0.2 | Insertar EPP en contextos mineros |
| `erasing` | 0.0 | 0.3–0.5 | Oclusión por polvo, maquinaria, pilares |
| `blur` (opcional) | 0.0 | 2–5 px | Desenfoque por movimiento o polvo en lente |

### Técnicas Específicas para Minería

**Simulación de polvo:**
```python
import cv2
import numpy as np

def add_dust_overlay(image, intensity=0.3):
    """Agrega efecto de polvo en suspensión."""
    h, w = image.shape[:2]
    dust = np.random.randint(0, 255, (h, w), dtype=np.uint8)
    dust = cv2.GaussianBlur(dust, (51, 51), 0)
    dust = cv2.cvtColor(dust, cv2.COLOR_GRAY2BGR)
    dust = dust.astype(np.float32) * intensity
    result = cv2.addWeighted(image.astype(np.float32), 1.0, dust, 1.0, 0)
    return np.clip(result, 0, 255).astype(np.uint8)
```

**Simulación de baja luz:**
```python
def simulate_low_light(image, factor=0.5):
    """Reduce iluminación simulando condiciones subterráneas."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * factor, 0, 255).astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
```

**Simulación de lente sucia:**
```python
def add_lens_dirt(image, num_spots=50):
    """Simula suciedad/barro en la lente de la cámara."""
    result = image.copy()
    h, w = image.shape[:2]
    for _ in range(num_spots):
        x, y = np.random.randint(0, w), np.random.randint(0, h)
        radius = np.random.randint(3, 15)
        color = (np.random.randint(30, 80),) * 3
        cv2.circle(result, (x, y), radius, color, -1)
    return result
```

### Pipeline de Aumentación para Fine-Tuning

El script `train-ppe.py` aplica estas aumentaciones automáticamente cuando se usan los flags `--augment-light`, `--augment-dust` y `--augment-occlusion`.

```bash
python3 train-ppe.py \
  --data dataset.yaml \
  --model yolov8x.pt \
  --epochs 100 \
  --augment-light \
  --augment-dust \
  --augment-occlusion
```

## Recomendaciones de Tamaño de Dataset

| Escenario | Imágenes totales | Por clase | Expected mAP@50 |
|-----------|-----------------|-----------|-----------------|
| Baseline (COCO pre-entrenado) | 0 (solo COCO) | 0 | ~0.40 (persona solamente) |
| Fine-tuning rápido | 1,000 | ~150 | ~0.70 |
| Producción básica | 5,000 | ~800 | ~0.85 |
| Producción minería chilena | 10,000+ | ~1,500 | ~0.92 |
| Producción + condiciones extremas | 20,000+ | ~3,000 | ~0.95 |

## Referencias

- [PPE Dataset on Kaggle](https://www.kaggle.com/datasets/arnabmishra/ppe-dataset)
- [Hard Hat Workers Dataset](https://www.kaggle.com/datasets/andrewmvd/hard-hat-workers)
- [Roboflow Universe — Safety PPE](https://universe.roboflow.com/)
- [Ultralytics Dataset Format](https://docs.ultralytics.com/datasets/detect/)
- [Data Augmentation for Object Detection](https://docs.ultralytics.com/reference/data/augment/)
