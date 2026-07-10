#!/usr/bin/env python3
"""
PPE Detection Pipeline.

Pipeline completo de detección de Elementos de Protección Personal (EPP) en
video para minería e industria pesada. Usa YOLOv8x sobre ROCm/CUDA para detectar
casco, chaleco reflectante, guantes, lentes de seguridad y botas de seguridad en
tiempo real sobre streams RTSP, archivos de video o cámaras USB.

Incluye:
  - Detección automática de backend GPU (ROCm / CUDA / CPU)
  - Tracking de personas con asignación de EPP por individuo (IoU matching)
  - Alertas configurables por EPP faltante (log, webhook, MQTT)
  - Multi-cámara con threads independientes
  - Multi-GPU con asignación manual de dispositivos
  - Output a video anotado con bounding boxes coloreados por estado EPP
  - Output a JSON estructurado por frame
  - Benchmark integrado de FPS, latencia y utilización VRAM
  - Dashboard HTML de cumplimiento

Uso:
  # Video local
  python3 ppe-pipeline.py --source video.mp4 --output ./output

  # RTSP stream
  python3 ppe-pipeline.py --source "rtsp://user:pass@192.168.1.100:554/stream1"

  # Multi-cámara
  python3 ppe-pipeline.py --source "rtsp://cam1" "rtsp://cam2" --multi-camera

  # Benchmark
  python3 ppe-pipeline.py --source video.mp4 --benchmark-only --frames 500
"""

import argparse
import csv
import json
import logging
import os
import queue
import sys
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
from ultralytics import YOLO

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PPE_CLASSES: Dict[int, str] = {
    0: "hardhat",
    1: "safety_vest",
    2: "gloves",
    3: "safety_glasses",
    4: "safety_boots",
    5: "person",
}

PPE_CLASSES_INV: Dict[str, int] = {v: k for k, v in PPE_CLASSES.items()}

PPE_REQUIRED_ALL: List[str] = [
    "hardhat", "safety_vest", "gloves", "safety_glasses", "safety_boots",
]

PPE_COLORS: Dict[str, Tuple[int, int, int]] = {
    "hardhat":        (0, 165, 255),       # Naranja (BGR)
    "safety_vest":    (0, 255, 255),       # Amarillo
    "gloves":         (128, 0, 128),       # Púrpura
    "safety_glasses": (255, 255, 0),       # Cyan
    "safety_boots":   (139, 69, 19),       # Café
    "person":         (255, 0, 0),         # Azul
}

STATUS_COLORS: Dict[str, Tuple[int, int, int]] = {
    "complete": (0, 255, 0),      # Verde
    "partial":  (0, 255, 255),    # Amarillo
    "missing":  (0, 0, 255),      # Rojo
    "unknown":  (128, 128, 128),  # Gris
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("ppe-pipeline")

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]


@dataclass
class PersonTrack:
    person_id: int
    bbox: List[int]
    person_bbox: List[int]
    ppe_status: Dict[str, bool] = field(default_factory=dict)
    ppe_items: List[Detection] = field(default_factory=list)
    lost_frames: int = 0
    alert_sent: bool = False
    last_alert_time: float = 0.0


@dataclass
class FrameResult:
    frame_id: int
    timestamp_s: float
    camera_id: str
    people_count: int
    people: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]
    all_detections: List[Dict[str, Any]]
    fps: float = 0.0


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

def detect_backend() -> Tuple[str, str, bool]:
    """
    Detecta el backend GPU disponible.

    Returns:
        (backend, device, half_supported)
        backend: "rocm", "cuda", or "cpu"
        device: "cuda:0" or "cpu"
        half_supported: True if FP16 is supported
    """
    if not torch.cuda.is_available():
        return "cpu", "cpu", False

    device = "cuda:0"
    cuda_version = torch.version.cuda
    hip_version = torch.version.hip

    if hip_version is not None:
        backend = "rocm"
    elif cuda_version is not None:
        backend = "cuda"
    else:
        backend = "cuda"  # fallback genérico

    # FP16 es soportado en GPU con compute capability >= 7.0 (NVIDIA)
    # o en cualquier GPU ROCm moderna
    half_supported = True
    try:
        props = torch.cuda.get_device_properties(0)
        if backend == "cuda" and props.major + props.minor / 10 < 7.0:
            half_supported = False
    except Exception:
        half_supported = False

    return backend, device, half_supported


def print_backend_info():
    """Imprime información detallada del backend detectado."""
    backend, device, half = detect_backend()
    print("=" * 55)
    print("  PPE Pipeline — Backend Detection")
    print("=" * 55)
    print(f"  Backend:            {backend.upper()}")
    print(f"  Device:             {device}")
    print(f"  FP16 supported:     {half}")
    print(f"  torch.version.hip:  {torch.version.hip or 'N/A'}")
    print(f"  torch.version.cuda: {torch.version.cuda or 'N/A'}")

    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            print(f"  GPU {i}:               {props.name} ({props.total_memory / 1e9:.1f} GB)")
    else:
        print("  GPU:                N/A (CPU mode)")
    print("=" * 55)


# ---------------------------------------------------------------------------
# Video source
# ---------------------------------------------------------------------------

class VideoSource:
    """Maneja la captura de video desde múltiples tipos de fuente."""

    def __init__(self, source: str, camera_id: str = None,
                 width: int = 640, height: int = 640,
                 fps_limit: float = 30.0, rtsp_transport: str = "tcp"):
        self.source = source
        self.camera_id = camera_id or f"cam_{abs(hash(source)) % 10000:04d}"
        self.width = width
        self.height = height
        self.fps_limit = fps_limit
        self.rtsp_transport = rtsp_transport
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_rtsp = source.startswith("rtsp://") or source.startswith("rtmp://")
        self.is_camera = source.startswith("/dev/video") or source.isdigit()
        self.is_file = not self.is_rtsp and not self.is_camera
        self.frame_count = 0
        self.start_time = time.time()
        self._open()

    def _open(self):
        if self.is_rtsp:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                f"rtsp_transport;{self.rtsp_transport}"
            )
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        elif self.is_camera:
            src = int(self.source) if self.source.isdigit() else self.source
            self.cap = cv2.VideoCapture(src)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        else:
            self.cap = cv2.VideoCapture(self.source)

        if not self.cap or not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {self.source}")

        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        log.info(
            "Camera %s opened: %dx%d @ %.1f FPS",
            self.camera_id, actual_width, actual_height, actual_fps,
        )

    def read(self) -> Optional[np.ndarray]:
        if self.cap is None:
            return None

        ret, frame = self.cap.read()
        if not ret:
            return None

        self.frame_count += 1

        # Limitar FPS
        if self.fps_limit > 0:
            elapsed = time.time() - self.start_time
            expected_time = self.frame_count / self.fps_limit
            if elapsed < expected_time:
                time.sleep(expected_time - elapsed)

        return frame

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    @property
    def fps_actual(self) -> float:
        elapsed = time.time() - self.start_time
        if elapsed < 0.01:
            return 0.0
        return self.frame_count / elapsed


# ---------------------------------------------------------------------------
# Person Tracker (IoU matching)
# ---------------------------------------------------------------------------

def compute_iou(bbox_a: List[int], bbox_b: List[int]) -> float:
    """Computa Intersection over Union entre dos bounding boxes [x1,y1,x2,y2]."""
    x1 = max(bbox_a[0], bbox_b[0])
    y1 = max(bbox_a[1], bbox_b[1])
    x2 = min(bbox_a[2], bbox_b[2])
    y2 = min(bbox_a[3], bbox_b[3])

    if x2 < x1 or y2 < y1:
        return 0.0

    inter = (x2 - x1) * (y2 - y1)
    area_a = (bbox_a[2] - bbox_a[0]) * (bbox_a[3] - bbox_a[1])
    area_b = (bbox_b[2] - bbox_b[0]) * (bbox_b[3] - bbox_b[1])
    union = area_a + area_b - inter

    if union <= 0:
        return 0.0
    return inter / union


def bbox_center(bbox: List[int]) -> Tuple[float, float]:
    """Retorna (cx, cy) del bounding box."""
    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0
    return cx, cy


def bbox_distance(bbox_a: List[int], bbox_b: List[int]) -> float:
    """Distancia euclidiana entre centros de dos bounding boxes."""
    ca = bbox_center(bbox_a)
    cb = bbox_center(bbox_b)
    return np.sqrt((ca[0] - cb[0]) ** 2 + (ca[1] - cb[1]) ** 2)


class PersonTracker:
    """
    Tracker simple basado en IoU matching.

    Asigna IDs a personas y mantiene tracking a través de frames.
    También asigna detecciones de EPP a cada persona basado en IoU.
    """

    def __init__(self, iou_threshold: float = 0.3,
                 max_lost_frames: int = 30,
                 distance_threshold: float = 200.0):
        self.next_id = 0
        self.tracks: Dict[int, PersonTrack] = OrderedDict()
        self.iou_threshold = iou_threshold
        self.max_lost_frames = max_lost_frames
        self.distance_threshold = distance_threshold
        self.frame_count = 0

    def update(self, detections: List[Detection],
               frame_shape: Tuple[int, int]) -> Dict[int, PersonTrack]:
        """
        Actualiza tracks con nuevas detecciones.

        Args:
            detections: Lista de Detection del frame actual.
            frame_shape: (height, width) del frame.

        Returns:
            Dict de track_id -> PersonTrack actualizado.
        """
        self.frame_count += 1

        persons = [d for d in detections if d.class_name == "person"]
        ppe_items = [d for d in detections if d.class_name != "person"]

        # Matchear personas con tracks existentes
        matched_tracks = set()
        matched_person_indices = set()

        # Para cada track existente, buscar la persona con mejor IoU
        for track_id, track in list(self.tracks.items()):
            if track.lost_frames > self.max_lost_frames:
                continue

            best_iou = self.iou_threshold
            best_idx = -1

            for i, person in enumerate(persons):
                if i in matched_person_indices:
                    continue
                iou = compute_iou(track.bbox, person.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_idx = i

            if best_idx >= 0:
                matched_tracks.add(track_id)
                matched_person_indices.add(best_idx)
                person = persons[best_idx]
                self.tracks[track_id].bbox = person.bbox
                self.tracks[track_id].person_bbox = person.bbox
                self.tracks[track_id].lost_frames = 0
                # Asignar EPP
                self._assign_ppe(track_id, ppe_items)
            else:
                self.tracks[track_id].lost_frames += 1

        # Nuevas personas (no matcheadas) -> nuevos tracks
        for i, person in enumerate(persons):
            if i in matched_person_indices:
                continue

            track_id = self.next_id
            self.next_id += 1
            self.tracks[track_id] = PersonTrack(
                person_id=track_id,
                bbox=person.bbox,
                person_bbox=person.bbox,
                ppe_status={},
                ppe_items=[],
                lost_frames=0,
                alert_sent=False,
                last_alert_time=0.0,
            )
            self._assign_ppe(track_id, ppe_items)

        # Limpiar tracks perdidos y tracks fantasma
        to_remove = []
        for track_id, track in self.tracks.items():
            if track.lost_frames > self.max_lost_frames:
                to_remove.append(track_id)
        for tid in to_remove:
            del self.tracks[tid]

        return self.tracks

    def _assign_ppe(self, track_id: int, ppe_items: List[Detection]):
        """Asigna items de EPP a una persona basado en IoU."""
        track = self.tracks[track_id]
        person_bbox = track.person_bbox

        # Resetear PPE status
        for ppe in PPE_REQUIRED_ALL:
            track.ppe_status[ppe] = False
        track.ppe_items = []

        for item in ppe_items:
            iou = compute_iou(person_bbox, item.bbox)
            # El EPP debe estar dentro o muy cerca de la persona
            if iou > 0.05 or self._is_inside(person_bbox, item.bbox):
                track.ppe_status[item.class_name] = True
                track.ppe_items.append(item)

    @staticmethod
    def _is_inside(outer: List[int], inner: List[int]) -> bool:
        """Verifica si inner está dentro de outer (con margen)."""
        margin = 20
        return (
            inner[0] >= outer[0] - margin
            and inner[1] >= outer[1] - margin
            and inner[2] <= outer[2] + margin
            and inner[3] <= outer[3] + margin
        )

    def check_compliance(self, track: PersonTrack,
                         required: List[str] = None) -> Tuple[str, List[str], List[str]]:
        """
        Verifica cumplimiento de EPP para una persona.

        Returns:
            (status, faltantes, presentes)
            status: "complete", "partial", "missing"
        """
        if required is None:
            required = PPE_REQUIRED_ALL

        presentes = [item for item in required if track.ppe_status.get(item, False)]
        faltantes = [item for item in required if item not in presentes]

        if len(faltantes) == 0:
            return "complete", faltantes, presentes
        elif len(presentes) >= len(required) * 0.5:
            return "partial", faltantes, presentes
        else:
            return "missing", faltantes, presentes

    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas del tracker."""
        total = len(self.tracks)
        if total == 0:
            return {"total": 0, "complete": 0, "partial": 0, "missing": 0}

        complete = sum(
            1 for t in self.tracks.values()
            if self.check_compliance(t)[0] == "complete"
        )
        partial = sum(
            1 for t in self.tracks.values()
            if self.check_compliance(t)[0] == "partial"
        )
        missing = total - complete - partial

        return {
            "total": total,
            "complete": complete,
            "partial": partial,
            "missing": missing,
        }


# ---------------------------------------------------------------------------
# Alert Manager
# ---------------------------------------------------------------------------

class AlertManager:
    """
    Gestiona alertas de EPP con soporte multi-canal.

    Canales soportados: log, webhook (HTTP POST), MQTT, archivo CSV.
    Incluye rate limiting para evitar spam de alertas.
    """

    def __init__(self, alert_log: bool = False,
                 alert_webhook: Optional[str] = None,
                 alert_webhook_headers: Optional[Dict[str, str]] = None,
                 alert_mqtt: Optional[str] = None,
                 alert_mqtt_topic: Optional[str] = None,
                 alert_mqtt_username: Optional[str] = None,
                 alert_mqtt_password: Optional[str] = None,
                 alert_csv: Optional[str] = None,
                 rate_limit_seconds: float = 30.0,
                 min_interval_person: float = 60.0):
        self.alert_log = alert_log
        self.alert_webhook = alert_webhook
        self.alert_webhook_headers = alert_webhook_headers or {}
        self.alert_mqtt = alert_mqtt
        self.alert_mqtt_topic = alert_mqtt_topic or "mining/ppe/alerts"
        self.alert_mqtt_username = alert_mqtt_username
        self.alert_mqtt_password = alert_mqtt_password
        self.alert_csv = alert_csv
        self.rate_limit_seconds = rate_limit_seconds
        self.min_interval_person = min_interval_person

        self._last_alert_time: float = 0.0
        self._person_last_alert: Dict[int, float] = {}
        self._csv_writer = None
        self._csv_file = None
        self._mqtt_client = None

        self._init_csv()
        self._init_mqtt()

    def _init_csv(self):
        if self.alert_csv:
            self._csv_file = open(self.alert_csv, "a", newline="")
            self._csv_writer = csv.writer(self._csv_file)
            self._csv_writer.writerow([
                "timestamp", "camera_id", "person_id",
                "status", "ppe_missing", "ppe_present",
                "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
            ])

    def _init_mqtt(self):
        if self.alert_mqtt:
            try:
                import paho.mqtt.client as mqtt
                self._mqtt_client = mqtt.Client()
                if self.alert_mqtt_username and self.alert_mqtt_password:
                    self._mqtt_client.username_pw_set(
                        self.alert_mqtt_username, self.alert_mqtt_password
                    )
                self._mqtt_client.connect(self.alert_mqtt)
                self._mqtt_client.loop_start()
            except ImportError:
                log.warning("paho-mqtt not installed. MQTT alerts disabled.")
                self.alert_mqtt = None
            except Exception as e:
                log.warning("MQTT connection failed: %s. Alerts disabled.", e)
                self.alert_mqtt = None

    def should_alert(self, person_id: int) -> bool:
        """Rate limiting: verifica si se debe enviar alerta para esta persona."""
        now = time.time()

        # Rate limit global
        if now - self._last_alert_time < self.rate_limit_seconds:
            return False

        # Rate limit por persona
        last_person = self._person_last_alert.get(person_id, 0.0)
        if now - last_person < self.min_interval_person:
            return False

        return True

    def send_alert(self, person_id: int, status: str,
                   faltantes: List[str], presentes: List[str],
                   bbox: List[int], camera_id: str,
                   timestamp: float = None):
        """Envía alerta por todos los canales configurados."""
        if not self.should_alert(person_id):
            return

        now = timestamp or time.time()
        self._last_alert_time = now
        self._person_last_alert[person_id] = now

        alert_data = {
            "timestamp": datetime.fromtimestamp(now).isoformat(),
            "camera_id": camera_id,
            "person_id": person_id,
            "status": status,
            "ppe_missing": faltantes,
            "ppe_present": presentes,
            "location": {"bbox": bbox},
        }

        # Log
        if self.alert_log:
            items_missing = ", ".join(faltantes) if faltantes else "none"
            log.warning(
                "ALERT | Camera %s | Person %d | Status: %s | Missing: %s",
                camera_id, person_id, status, items_missing,
            )

        # Webhook
        if self.alert_webhook:
            self._send_webhook(alert_data)

        # MQTT
        if self.alert_mqtt and self._mqtt_client:
            self._send_mqtt(alert_data)

        # CSV
        if self._csv_writer:
            self._csv_writer.writerow([
                alert_data["timestamp"],
                camera_id,
                person_id,
                status,
                "|".join(faltantes),
                "|".join(presentes),
                bbox[0], bbox[1], bbox[2], bbox[3],
            ])
            self._csv_file.flush()

    def _send_webhook(self, alert_data: Dict):
        try:
            import requests
            resp = requests.post(
                self.alert_webhook,
                json=alert_data,
                headers=self.alert_webhook_headers,
                timeout=5.0,
            )
            if resp.status_code not in (200, 201, 202, 204):
                log.warning("Webhook alert returned %d", resp.status_code)
        except Exception as e:
            log.warning("Webhook alert failed: %s", e)

    def _send_mqtt(self, alert_data: Dict):
        try:
            payload = json.dumps(alert_data)
            self._mqtt_client.publish(self.alert_mqtt_topic, payload, qos=1)
        except Exception as e:
            log.warning("MQTT publish failed: %s", e)

    def close(self):
        if self._csv_file:
            self._csv_file.close()
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()


# ---------------------------------------------------------------------------
# Annotator
# ---------------------------------------------------------------------------

class Annotator:
    """Dibuja bounding boxes, etiquetas y estado EPP en frames."""

    def __init__(self, font_scale: float = 0.5, thickness: int = 2):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = font_scale
        self.thickness = thickness

    def annotate_frame(self, frame: np.ndarray,
                       tracks: Dict[int, PersonTrack],
                       tracker: PersonTracker,
                       fps: float,
                       camera_id: str,
                       detections: List[Detection] = None) -> np.ndarray:
        """Anota un frame completo con bounding boxes y estado."""
        vis = frame.copy()

        for track_id, track in tracks.items():
            if track.lost_frames > 5:
                continue  # No dibujar tracks muy perdidos

            status, faltantes, presentes = tracker.check_compliance(track)
            color = STATUS_COLORS.get(status, STATUS_COLORS["unknown"])
            bbox = track.bbox

            # Bounding box de persona
            cv2.rectangle(vis, (bbox[0], bbox[1]), (bbox[2], bbox[3]),
                          color, self.thickness)

            # ID de persona + estado
            label = f"P{track.person_id} [{status.upper()}]"
            label_size = cv2.getTextSize(label, self.font, self.font_scale, 1)[0]
            cv2.rectangle(vis,
                          (bbox[0], bbox[1] - label_size[1] - 6),
                          (bbox[0] + label_size[0] + 4, bbox[1]),
                          color, -1)
            cv2.putText(vis, label,
                        (bbox[0] + 2, bbox[1] - 4),
                        self.font, self.font_scale, (255, 255, 255), 1, cv2.LINE_AA)

            # Items EPP detectados
            y_offset = bbox[1] - label_size[1] - 14
            for ppe_name, detected in track.ppe_status.items():
                if detected:
                    ppe_color = PPE_COLORS.get(ppe_name, (255, 255, 255))
                    text = f"{ppe_name}: OK"
                    cv2.putText(vis, text,
                                (bbox[0], y_offset),
                                self.font, self.font_scale * 0.7, ppe_color,
                                1, cv2.LINE_AA)
                    y_offset -= 12

            # Items EPP individuales
            for item in track.ppe_items:
                color_item = PPE_COLORS.get(item.class_name, (255, 255, 255))
                cv2.rectangle(vis,
                              (item.bbox[0], item.bbox[1]),
                              (item.bbox[2], item.bbox[3]),
                              color_item, 1)

        # Header info
        h, w = vis.shape[:2]

        # FPS y timestamp
        cv2.putText(vis, f"{fps:.1f} FPS | {camera_id}",
                    (10, 25), self.font, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        # Estadísticas de cumplimiento
        stats = tracker.get_stats()
        stats_text = (
            f"People: {stats['total']} | "
            f"OK: {stats['complete']} | "
            f"Partial: {stats['partial']} | "
            f"Missing: {stats['missing']}"
        )
        cv2.putText(vis, stats_text,
                    (10, 50), self.font, 0.5,
                    (200, 200, 200), 1, cv2.LINE_AA)

        # Estado general de la escena
        if stats["missing"] > 0:
            alert_text = "ALERTA: Personas sin EPP detectadas"
            cv2.putText(vis, alert_text,
                        (w // 2 - 200, 25), self.font, 0.7,
                        (0, 0, 255), 2, cv2.LINE_AA)
        elif stats["partial"] > 0:
            warn_text = "PRECAUCION: EPP incompleto detectado"
            cv2.putText(vis, warn_text,
                        (w // 2 - 200, 25), self.font, 0.7,
                        (0, 255, 255), 2, cv2.LINE_AA)
        else:
            ok_text = "OK: Todos con EPP completo"
            cv2.putText(vis, ok_text,
                        (w // 2 - 150, 25), self.font, 0.7,
                        (0, 255, 0), 2, cv2.LINE_AA)

        return vis


# ---------------------------------------------------------------------------
# Inference engine
# ---------------------------------------------------------------------------

class InferenceEngine:
    """Maneja la carga del modelo YOLO y la inferencia."""

    def __init__(self, model_path: str, device: str = "auto",
                 confidence: float = 0.5, iou: float = 0.45,
                 batch_size: int = 8, half: bool = False,
                 imgsz: int = 640):
        self.model_path = model_path
        self.confidence = confidence
        self.iou = iou
        self.batch_size = batch_size
        self.half = half
        self.imgsz = imgsz

        # Detectar device
        if device == "auto":
            backend, self.device, half_supported = detect_backend()
        else:
            self.device = device

        self.backend = self._get_backend_name()

        # Cargar modelo
        log.info("Loading model %s on %s...", model_path, self.device)
        self.model = YOLO(model_path)

        # FP16
        if half and self.device != "cpu":
            try:
                self.model.model.half()
                log.info("FP16 mode enabled")
                self.half = True
            except Exception as e:
                log.warning("FP16 not available: %s", e)
                self.half = False
        else:
            self.half = False

        # Warmup
        self._warmup()

    def _get_backend_name(self) -> str:
        if self.device == "cpu":
            return "cpu"
        if torch.version.hip:
            return "rocm"
        if torch.version.cuda:
            return "cuda"
        return "cuda"

    def _warmup(self):
        """Ejecuta warmup para cargar kernels CUDA/ROCm."""
        if self.device == "cpu":
            return
        try:
            dummy = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
            self.model.predict(dummy, device=self.device, verbose=False)
            log.info("Warmup complete")
        except Exception as e:
            log.warning("Warmup failed (non-critical): %s", e)

    def predict(self, frames: List[np.ndarray]) -> List[List[Detection]]:
        """
        Ejecuta inferencia sobre una lista de frames.

        Args:
            frames: Lista de frames en BGR (OpenCV format).

        Returns:
            Lista de listas de Detection por frame.
        """
        if not frames:
            return []

        batch_results = self.model.predict(
            frames,
            device=self.device,
            batch=min(len(frames), self.batch_size),
            imgsz=self.imgsz,
            conf=self.confidence,
            iou=self.iou,
            verbose=False,
        )

        all_detections = []
        for r in batch_results:
            frame_dets = []
            if r.boxes is None:
                all_detections.append(frame_dets)
                continue

            for box in r.boxes:
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                if cls_id not in PPE_CLASSES:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                frame_dets.append(Detection(
                    class_id=cls_id,
                    class_name=PPE_CLASSES[cls_id],
                    confidence=conf,
                    bbox=[x1, y1, x2, y2],
                ))

            all_detections.append(frame_dets)

        return all_detections

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model": self.model_path,
            "backend": self.backend,
            "device": self.device,
            "half": self.half,
            "imgsz": self.imgsz,
            "confidence": self.confidence,
            "iou": self.iou,
        }


# ---------------------------------------------------------------------------
# Video Writer
# ---------------------------------------------------------------------------

class VideoWriter:
    """Escribe video anotado."""

    def __init__(self, output_path: str, fps: float = 30.0,
                 width: int = 640, height: int = 640):
        self.output_path = output_path
        self.fps = fps
        self.width = width
        self.height = height
        self.writer: Optional[cv2.VideoWriter] = None

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if not self.writer.isOpened():
            raise RuntimeError(f"Cannot create video writer: {output_path}")
        log.info("Video writer opened: %s (%dx%d @ %.1f FPS)",
                 output_path, width, height, fps)

    def write(self, frame: np.ndarray):
        if self.writer:
            self.writer.write(frame)

    def close(self):
        if self.writer:
            self.writer.release()
            self.writer = None
            log.info("Video writer closed: %s", self.output_path)


# ---------------------------------------------------------------------------
# Frame preprocessor
# ---------------------------------------------------------------------------

def letterbox(img: np.ndarray, target_size: Tuple[int, int] = (640, 640),
              color: Tuple[int, int, int] = (114, 114, 114)) -> np.ndarray:
    """Redimensiona manteniendo aspect ratio (letterbox)."""
    h, w = img.shape[:2]
    target_w, target_h = target_size
    scale = min(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((target_h, target_w, 3), color, dtype=np.uint8)
    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2
    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
    return canvas


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

class JsonOutput:
    """Escribe resultados a JSON estructurado."""

    def __init__(self, output_path: str):
        self.output_path = output_path
        self.frames: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

    def add_frame(self, result: FrameResult):
        self.frames.append({
            "frame_id": result.frame_id,
            "timestamp_s": round(result.timestamp_s, 3),
            "camera_id": result.camera_id,
            "people_count": result.people_count,
            "people": result.people,
            "alerts": result.alerts,
            "all_detections": result.all_detections,
            "fps": round(result.fps, 1),
        })

    def set_metadata(self, **kwargs):
        self.metadata.update(kwargs)

    def save(self):
        if not self.frames:
            log.warning("No frames to save to JSON")
            return

        output = {
            "metadata": self.metadata,
            "total_frames": len(self.frames),
            "frames": self.frames,
        }

        os.makedirs(os.path.dirname(self.output_path) or ".", exist_ok=True)
        with open(self.output_path, "w") as f:
            json.dump(output, f, indent=2, default=str)
        log.info("JSON output saved: %s (%d frames)", self.output_path, len(self.frames))


# ---------------------------------------------------------------------------
# Dashboard HTML
# ---------------------------------------------------------------------------

def generate_dashboard(results: List[FrameResult], metadata: Dict[str, Any],
                       output_path: str):
    """Genera un dashboard HTML simple con estadísticas de cumplimiento."""
    if not results:
        return

    total_frames = len(results)
    total_alerts = sum(len(r.alerts) for r in results)
    total_people = sum(r.people_count for r in results)

    # Estadísticas por estado
    status_counts = {"complete": 0, "partial": 0, "missing": 0, "unknown": 0}
    for r in results:
        for p in r.people:
            s = p.get("ppe_status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1

    compliance_rate = 0.0
    total_ppe_checks = sum(status_counts.values())
    if total_ppe_checks > 0:
        compliance_rate = (
            (status_counts["complete"] + status_counts["partial"] * 0.5)
            / total_ppe_checks * 100
        )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PPE Compliance Dashboard</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0f1117; color: #e1e4e8; padding: 20px; }}
  h1 {{ font-size: 24px; margin-bottom: 20px; color: #58a6ff; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px; margin-bottom: 24px; }}
  .stat-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
               padding: 16px; }}
  .stat-card .value {{ font-size: 32px; font-weight: 700; }}
  .stat-card .label {{ font-size: 12px; color: #8b949e; text-transform: uppercase; }}
  .stat-card.complete .value {{ color: #3fb950; }}
  .stat-card.partial .value {{ color: #d29922; }}
  .stat-card.missing .value {{ color: #f85149; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
  th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #30363d; }}
  th {{ color: #8b949e; font-size: 12px; text-transform: uppercase; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px;
            font-size: 11px; font-weight: 600; }}
  .badge.complete {{ background: #3fb95020; color: #3fb950; border: 1px solid #3fb950; }}
  .badge.partial {{ background: #d2992220; color: #d29922; border: 1px solid #d29922; }}
  .badge.missing {{ background: #f8514920; color: #f85149; border: 1px solid #f85149; }}
  .summary {{ display: flex; gap: 24px; margin: 16px 0; padding: 16px;
              background: #161b22; border-radius: 8px; border: 1px solid #30363d; }}
  .summary-item {{ text-align: center; }}
  .summary-item .num {{ font-size: 28px; font-weight: 700; }}
  .summary-item .desc {{ font-size: 11px; color: #8b949e; }}
</style>
</head>
<body>
<h1>🛡️ PPE Compliance Dashboard</h1>
<div class="summary">
  <div class="summary-item"><div class="num">{total_frames}</div><div class="desc">Frames procesados</div></div>
  <div class="summary-item"><div class="num">{total_people}</div><div class="desc">Personas detectadas</div></div>
  <div class="summary-item"><div class="num">{total_alerts}</div><div class="desc">Alertas generadas</div></div>
  <div class="summary-item"><div class="num">{compliance_rate:.1f}%</div><div class="desc">Tasa de cumplimiento</div></div>
</div>

<div class="stats">
  <div class="stat-card complete">
    <div class="value">{status_counts["complete"]}</div>
    <div class="label">EPP Complete</div>
  </div>
  <div class="stat-card partial">
    <div class="value">{status_counts["partial"]}</div>
    <div class="label">EPP Parcial</div>
  </div>
  <div class="stat-card missing">
    <div class="value">{status_counts["missing"]}</div>
    <div class="label">EPP Faltante</div>
  </div>
</div>

<h2 style="margin-top: 24px;">Últimas Alertas</h2>
<table>
<thead><tr><th>Frame</th><th>Persona</th><th>Estado</th><th>EPP Faltante</th></tr></thead>
<tbody>
"""
    # Últimas 50 alertas
    alert_count = 0
    for r in reversed(results):
        for alert in r.alerts:
            if alert_count >= 50:
                break
            status = alert.get("type", "missing")
            missing = ", ".join(alert.get("missing_items", []))
            html += f"<tr><td>{r.frame_id}</td><td>P{alert.get('person_id', '?')}</td>"
            html += f'<td><span class="badge {status}">{status}</span></td>'
            html += f"<td>{missing}</td></tr>\n"
            alert_count += 1
        if alert_count >= 50:
            break

    html += """</tbody>
</table>
<p style="margin-top: 16px; color: #8b949e; font-size: 12px;">
  Generado por AMD ROCm PPE Detection Pipeline — """
    html += f"{datetime.now().isoformat()}</p>"
    html += """</body>
</html>
"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)
    log.info("Dashboard saved: %s", output_path)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

class PPEPipeline:
    """
    Pipeline principal de detección de EPP.

    Orquesta captura, inferencia, tracking, alertas y output.
    """

    def __init__(self, args):
        self.args = args
        self.running = False
        self.frame_count = 0
        self.total_alerts = 0
        self.latencies: List[float] = []

        # Detectar backend
        self.backend, self.device, self.half_supported = detect_backend()
        if args.device != "auto":
            self.device = args.device

        log.info("Backend: %s | Device: %s | FP16: %s",
                 self.backend, self.device,
                 args.fp16 and self.half_supported)

        # Inferencia
        self.engine = InferenceEngine(
            model_path=args.model,
            device=self.device,
            confidence=args.confidence,
            iou=args.iou,
            batch_size=args.batch,
            half=args.fp16 and self.half_supported,
            imgsz=args.imgsz,
        )

        # Tracker
        self.tracker = PersonTracker(
            iou_threshold=args.iou_threshold,
            max_lost_frames=args.max_lost_frames,
        )

        # Alert Manager
        webhook_headers = {}
        if args.alert_webhook_header:
            for h in args.alert_webhook_header:
                if ":" in h:
                    k, v = h.split(":", 1)
                    webhook_headers[k.strip()] = v.strip()

        self.alert_manager = AlertManager(
            alert_log=args.alert_log,
            alert_webhook=args.alert_webhook,
            alert_webhook_headers=webhook_headers,
            alert_mqtt=args.alert_mqtt,
            alert_mqtt_topic=args.alert_mqtt_topic,
            alert_mqtt_username=args.alert_mqtt_username,
            alert_mqtt_password=args.alert_mqtt_password,
            alert_csv=args.alert_csv,
            rate_limit_seconds=args.alert_rate_limit,
        )

        # Annotator
        self.annotator = Annotator()

        # Outputs
        self.json_output = None
        self.video_writer = None
        if args.output:
            os.makedirs(args.output, exist_ok=True)
            if args.output_json:
                self.json_output = JsonOutput(
                    os.path.join(args.output, "ppe_results.json")
                )
            if args.output_video:
                self.video_writer = VideoWriter(
                    os.path.join(args.output, "ppe_annotated.mp4"),
                    fps=args.fps,
                    width=args.imgsz,
                    height=args.imgsz,
                )

        self.all_results: List[FrameResult] = []
        self.metadata = {
            "source": args.source,
            "model": args.model,
            "backend": self.backend,
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
            "classes": list(PPE_CLASSES.values()),
            "args": vars(args),
        }

    def process_source(self, source: str, camera_id: str = None) -> Dict[str, Any]:
        """Procesa una fuente de video."""
        vs = VideoSource(
            source=source,
            camera_id=camera_id,
            width=self.args.imgsz,
            height=self.args.imgsz,
            fps_limit=self.args.fps,
            rtsp_transport=self.args.rtsp_transport,
        )

        stats = {"frames": 0, "alerts": 0, "fps": 0.0}
        frame_buffer = []
        last_log_time = time.time()

        while self.running:
            frame = vs.read()
            if frame is None:
                break

            self.frame_count += 1
            frame_resized = letterbox(frame, (self.args.imgsz, self.args.imgsz))
            frame_buffer.append(frame_resized)

            # Inferencia por batch
            if len(frame_buffer) >= self.args.batch:
                t0 = time.time()
                batch_dets = self.engine.predict(frame_buffer)
                latencies = []

                for i, detections in enumerate(batch_dets):
                    t1 = time.time()
                    latency = (t1 - t0) / len(batch_dets) * 1000
                    latencies.append(latency)
                    self.latencies.append(latency)

                    # Tracking
                    tracks = self.tracker.update(
                        detections, frame_resized.shape[:2]
                    )

                    # Verificar cumplimiento y alertar
                    alerts = []
                    for track_id, track in tracks.items():
                        if track.lost_frames > 0:
                            continue
                        status, faltantes, presentes = self.tracker.check_compliance(track)
                        if status in ("missing", "partial"):
                            self.alert_manager.send_alert(
                                person_id=track_id,
                                status=status,
                                faltantes=faltantes,
                                presentes=presentes,
                                bbox=track.bbox,
                                camera_id=camera_id or vs.camera_id,
                            )
                            if self.alert_manager.should_alert(track_id):
                                alerts.append({
                                    "person_id": track_id,
                                    "type": status,
                                    "missing_items": faltantes,
                                    "present_items": presentes,
                                })
                                stats["alerts"] += 1
                                self.total_alerts += 1

                    # Construir resultado del frame
                    people_info = []
                    for track_id, track in tracks.items():
                        if track.lost_frames > 5:
                            continue
                        status, faltantes, presentes = self.tracker.check_compliance(track)
                        people_info.append({
                            "person_id": track_id,
                            "bbox": track.bbox,
                            "ppe_status": status,
                            "ppe_present": presentes,
                            "ppe_missing": faltantes,
                            "ppe_items": [
                                {
                                    "class": item.class_name,
                                    "confidence": round(item.confidence, 3),
                                    "bbox": item.bbox,
                                }
                                for item in track.ppe_items
                            ],
                        })

                    all_dets = [
                        {
                            "class": d.class_name,
                            "confidence": round(d.confidence, 3),
                            "bbox": d.bbox,
                        }
                        for d in detections
                    ]

                    result = FrameResult(
                        frame_id=self.frame_count,
                        timestamp_s=self.frame_count / max(vs.fps_actual, 1),
                        camera_id=camera_id or vs.camera_id,
                        people_count=len(people_info),
                        people=people_info,
                        alerts=alerts,
                        all_detections=all_dets,
                        fps=vs.fps_actual,
                    )
                    self.all_results.append(result)

                    if self.json_output:
                        self.json_output.add_frame(result)

                    # Anotar video
                    if self.video_writer:
                        annotated = self.annotator.annotate_frame(
                            frame_resized, tracks, self.tracker,
                            vs.fps_actual, vs.camera_id, detections,
                        )
                        self.video_writer.write(annotated)

                frame_buffer = []

            # Log periódico
            elapsed = time.time() - last_log_time
            if elapsed >= 5.0:
                stats["frames"] = self.frame_count
                stats["fps"] = vs.fps_actual
                log.info(
                    "Camera %s | %d frames | %.1f FPS | %d alerts | %d people tracked",
                    vs.camera_id, self.frame_count, vs.fps_actual,
                    self.total_alerts, len(self.tracker.tracks),
                )
                last_log_time = time.time()

        # Procesar frames restantes
        if frame_buffer:
            batch_dets = self.engine.predict(frame_buffer)
            for detections in batch_dets:
                self.tracker.update(detections, (self.args.imgsz, self.args.imgsz))

        vs.release()
        stats["frames"] = self.frame_count
        stats["fps"] = vs.fps_actual
        return stats

    def run(self):
        """Ejecuta el pipeline."""
        self.running = True
        sources = self.args.source
        multi = self.args.multi_camera

        if multi:
            threads = []
            for i, src in enumerate(sources):
                device_idx = i % max(torch.cuda.device_count(), 1)
                cam_id = f"cam_{i:04d}"
                log.info("Spawning thread for camera %s: %s (device cuda:%d)",
                         cam_id, src, device_idx)
                t = threading.Thread(
                    target=self._run_single,
                    args=(src, cam_id),
                    daemon=True,
                )
                t.start()
                threads.append(t)

            for t in threads:
                t.join()
        else:
            for src in sources:
                self._run_single(src)

        self._finalize()

    def _run_single(self, source: str, camera_id: str = None):
        """Ejecuta pipeline para una sola fuente."""
        try:
            stats = self.process_source(source, camera_id)
            log.info("Camera %s completed: %d frames, %.1f FPS, %d alerts",
                     camera_id or source, stats["frames"], stats["fps"], stats["alerts"])
        except Exception as e:
            log.error("Camera %s failed: %s", camera_id or source, e, exc_info=True)

    def _finalize(self):
        """Finaliza el pipeline y guarda outputs."""
        self.running = False

        # Metadata final
        mean_latency = np.mean(self.latencies) if self.latencies else 0
        self.metadata.update({
            "total_frames": self.frame_count,
            "total_alerts": self.total_alerts,
            "fps_pipeline": 1000.0 / mean_latency if mean_latency > 0 else 0,
            "latency_avg_ms": round(mean_latency, 2),
            "latency_p50_ms": round(float(np.percentile(self.latencies, 50)), 2) if self.latencies else 0,
            "latency_p95_ms": round(float(np.percentile(self.latencies, 95)), 2) if self.latencies else 0,
            "latency_p99_ms": round(float(np.percentile(self.latencies, 99)), 2) if self.latencies else 0,
            "people_tracked": len(self.tracker.tracks),
        })

        if self.json_output:
            self.json_output.set_metadata(**self.metadata)
            self.json_output.save()

        if self.video_writer:
            self.video_writer.close()

        if self.args.dashboard and self.all_results:
            dash_path = os.path.join(self.args.output, "dashboard.html")
            generate_dashboard(self.all_results, self.metadata, dash_path)

        self.alert_manager.close()

        # Print summary
        print("\n" + "=" * 55)
        print("  PPE Pipeline — Summary")
        print("=" * 55)
        print(f"  Source:             {', '.join(self.args.source)}")
        print(f"  Model:              {self.args.model}")
        print(f"  Backend:            {self.backend.upper()}")
        print(f"  Device:             {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
        print(f"  Total frames:       {self.frame_count}")
        print(f"  FPS:                {1000.0 / mean_latency:.1f}" if mean_latency > 0 else "  FPS:                N/A")
        print(f"  Latency avg:        {mean_latency:.1f} ms")
        print(f"  Latency p95:        {np.percentile(self.latencies, 95):.1f} ms" if self.latencies else "  Latency p95:        N/A")
        print(f"  Total alerts:       {self.total_alerts}")
        print(f"  People tracked:     {len(self.tracker.tracks)}")
        print(f"  Output:             {self.args.output}")
        print("=" * 55)

    def benchmark(self):
        """Ejecuta benchmark y reporta métricas."""
        self.running = True
        sources = self.args.source
        max_frames = self.args.frames
        frame_count = 0
        latencies = []

        log.info("Benchmark mode: %d frames max", max_frames)

        for src in sources:
            vs = VideoSource(src, fps_limit=9999)
            while self.running and frame_count < max_frames:
                frame = vs.read()
                if frame is None:
                    break

                frame_resized = letterbox(frame, (self.args.imgsz, self.args.imgsz))
                t0 = time.time()

                detections = self.engine.predict([frame_resized])[0]

                t1 = time.time()
                latency = (t1 - t0) * 1000
                latencies.append(latency)

                self.tracker.update(detections, frame_resized.shape[:2])
                frame_count += 1

            vs.release()

        self.running = False

        if not latencies:
            log.error("No frames processed in benchmark")
            return

        mean_lat = np.mean(latencies)
        fps = 1000.0 / mean_lat if mean_lat > 0 else 0

        vram_gb = 0
        if torch.cuda.is_available():
            vram_gb = torch.cuda.memory_allocated(0) / 1e9

        stats = self.tracker.get_stats()
        violations = stats["missing"] + stats["partial"]

        print("\n" + "=" * 55)
        print("  PPE Pipeline Benchmark")
        print("=" * 55)
        print(f"  Backend:            {self.backend.upper()}")
        print(f"  Device:             {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
        print(f"  Model:              {self.args.model}")
        print(f"  Resolution:         {self.args.imgsz}x{self.args.imgsz}")
        print(f"  Batch Size:         {self.args.batch}")
        print(f"")
        print(f"  FPS:                {fps:.1f}")
        print(f"  Latency avg:        {mean_lat:.1f} ms")
        print(f"  Latency p50:        {np.percentile(latencies, 50):.1f} ms")
        print(f"  Latency p95:        {np.percentile(latencies, 95):.1f} ms")
        print(f"  Latency p99:        {np.percentile(latencies, 99):.1f} ms")
        print(f"  VRAM usage:         {vram_gb:.1f} GB")
        print(f"  Detections/frame:   {len(latencies) / max(frame_count, 1):.1f}")
        print(f"  People tracked:     {stats['total']}")
        print(f"  PPE violations:     {violations}")
        print("=" * 55)

        if self.args.json:
            bench_output = {
                "system": {
                    "backend": self.backend,
                    "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
                    "model": self.args.model,
                },
                "performance": {
                    "fps": round(fps, 1),
                    "latency_avg_ms": round(mean_lat, 1),
                    "latency_p50_ms": round(float(np.percentile(latencies, 50)), 1),
                    "latency_p95_ms": round(float(np.percentile(latencies, 95)), 1),
                    "latency_p99_ms": round(float(np.percentile(latencies, 99)), 1),
                    "vram_gb": round(vram_gb, 1),
                },
                "tracking": stats,
            }
            output_path = self.args.output or "."
            os.makedirs(output_path, exist_ok=True)
            bench_file = os.path.join(output_path, "benchmark.json")
            with open(bench_file, "w") as f:
                json.dump(bench_output, f, indent=2)
            log.info("Benchmark results saved: %s", bench_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PPE Detection Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Source
    parser.add_argument("--source", "-s", nargs="+", required=True,
                        help="Video source(s): file path, RTSP URL, or camera device")
    parser.add_argument("--multi-camera", action="store_true",
                        help="Enable multi-camera threading")
    parser.add_argument("--max-threads", type=int, default=4,
                        help="Maximum threads for multi-camera (default: 4)")
    parser.add_argument("--rtsp-transport", default="tcp",
                        choices=["tcp", "udp", "http"],
                        help="RTSP transport protocol (default: tcp)")

    # Model
    parser.add_argument("--model", "-m", default="yolov8x.pt",
                        help="YOLO model path (default: yolov8x.pt)")
    parser.add_argument("--confidence", "-c", type=float, default=0.5,
                        help="Confidence threshold (default: 0.5)")
    parser.add_argument("--iou", type=float, default=0.45,
                        help="NMS IoU threshold (default: 0.45)")
    parser.add_argument("--batch", "-b", type=int, default=8,
                        help="Batch size for inference (default: 8)")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Inference resolution (default: 640)")
    parser.add_argument("--fp16", action="store_true",
                        help="Enable FP16 half precision")
    parser.add_argument("--classes", nargs="*",
                        default=list(PPE_CLASSES.values()),
                        help="Classes to detect (default: all PPE classes)")

    # Device
    parser.add_argument("--device", "-d", default="auto",
                        help="Device: auto, cuda:0, cuda:1, cpu (default: auto)")

    # Tracking
    parser.add_argument("--track", action="store_true", default=True,
                        help="Enable person tracking (default: True)")
    parser.add_argument("--iou-threshold", type=float, default=0.3,
                        help="IoU threshold for tracking (default: 0.3)")
    parser.add_argument("--max-lost-frames", type=int, default=30,
                        help="Max frames before losing track (default: 30)")

    # Video
    parser.add_argument("--fps", type=float, default=30.0,
                        help="Processing FPS limit (default: 30)")
    parser.add_argument("--resolution", default="640x640",
                        help="Capture resolution (default: 640x640)")

    # Output
    parser.add_argument("--output", "-o", default="./output",
                        help="Output directory (default: ./output)")
    parser.add_argument("--output-video", action="store_true", default=True,
                        help="Generate annotated video (default: True)")
    parser.add_argument("--output-json", action="store_true", default=True,
                        help="Generate JSON output (default: True)")
    parser.add_argument("--dashboard", action="store_true",
                        help="Generate HTML compliance dashboard")

    # Alerts
    parser.add_argument("--alert-log", action="store_true",
                        help="Log alerts to console")
    parser.add_argument("--alert-webhook",
                        help="Webhook URL for HTTP POST alerts")
    parser.add_argument("--alert-webhook-header", action="append",
                        help="Custom header for webhook (format: 'Key: Value')")
    parser.add_argument("--alert-mqtt",
                        help="MQTT broker URL (e.g., mqtt://broker:1883)")
    parser.add_argument("--alert-mqtt-topic", default="mining/ppe/alerts",
                        help="MQTT topic (default: mining/ppe/alerts)")
    parser.add_argument("--alert-mqtt-username",
                        help="MQTT username")
    parser.add_argument("--alert-mqtt-password",
                        help="MQTT password")
    parser.add_argument("--alert-csv",
                        help="CSV file path for alert logging")
    parser.add_argument("--alert-rate-limit", type=float, default=30.0,
                        help="Minimum seconds between alerts (default: 30)")

    # Benchmark
    parser.add_argument("--benchmark-only", action="store_true",
                        help="Run benchmark mode only")
    parser.add_argument("--frames", type=int, default=500,
                        help="Number of frames for benchmark (default: 500)")
    parser.add_argument("--benchmark-detailed", action="store_true",
                        help="Detailed benchmark with per-stage timing")
    parser.add_argument("--json", action="store_true",
                        help="Output benchmark results as JSON")

    # Utility
    parser.add_argument("--detect", action="store_true",
                        help="Detect backend and exit")
    parser.add_argument("--show-classes", action="store_true",
                        help="Show PPE classes and exit")

    return parser.parse_args()


def main():
    args = parse_args()

    if args.detect:
        print_backend_info()
        return

    if args.show_classes:
        print("PPE Classes:")
        print("=" * 40)
        for cls_id, cls_name in PPE_CLASSES.items():
            print(f"  {cls_id}: {cls_name}")
        print("=" * 40)
        return

    pipeline = PPEPipeline(args)

    if args.benchmark_only:
        pipeline.benchmark()
    else:
        pipeline.run()


if __name__ == "__main__":
    main()
