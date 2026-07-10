#!/usr/bin/env python3
"""
Alert Manager — Sistema de alertas de EPP para minería e industria.

Gestiona alertas de Elementos de Protección Personal (EPP) con soporte
multi-canal: log local, webhook HTTP POST, MQTT, archivo CSV.

Incluye:
  - Rate limiting para evitar spam de alertas
  - Umbrales configurables: tiempo sin EPP, zonas peligrosas, infracciones múltiples
  - Modo servicio standalone (procesa alertas desde JSON o stdin)
  - Historial de alertas por persona
  - Agrupación de alertas por turno/zona

Uso:
  # Modo servicio (escucha alertas desde stdin)
  python3 alert-manager.py --mode service --alert-log --alert-webhook "https://..."

  # Procesar archivo JSON con alertas
  python3 alert-manager.py --mode file --input alerts.json --output processed.json

  # Generar reporte de alertas
  python3 alert-manager.py --mode report --input alerts_history.csv --output report.html
"""

import argparse
import csv
import json
import logging
import os
import signal
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | [AlertManager] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("alert-manager")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PPE_REQUIRED = [
    "hardhat", "safety_vest", "gloves", "safety_glasses", "safety_boots",
]

DEFAULT_RATE_LIMIT_SECONDS = 30.0
DEFAULT_MIN_INTERVAL_PERSON = 60.0
DEFAULT_ALERT_COOLDOWN = 300.0  # 5 minutos sin repetir misma persona

SEVERITY_LEVELS = {
    "critical": {"min_missing": 4, "color": "#f85149", "label": "Crítico"},
    "high":     {"min_missing": 3, "color": "#d29922", "label": "Alto"},
    "medium":   {"min_missing": 2, "color": "#db6d28", "label": "Medio"},
    "low":      {"min_missing": 1, "color": "#58a6ff", "label": "Bajo"},
}


# ---------------------------------------------------------------------------
# Alert record
# ---------------------------------------------------------------------------

class AlertRecord:
    """Representa una alerta de EPP."""

    def __init__(self, person_id: int, camera_id: str,
                 ppe_missing: List[str], ppe_present: List[str],
                 bbox: List[int], status: str = "missing",
                 zone: str = "unknown", timestamp: float = None):
        self.person_id = person_id
        self.camera_id = camera_id
        self.ppe_missing = ppe_missing
        self.ppe_present = ppe_present
        self.bbox = bbox
        self.status = status
        self.zone = zone
        self.timestamp = timestamp or time.time()
        self.id = f"{int(self.timestamp * 1000)}-P{person_id}-{camera_id}"

    @property
    def severity(self) -> str:
        missing_count = len(self.ppe_missing)
        for level, config in SEVERITY_LEVELS.items():
            if missing_count >= config["min_missing"]:
                return level
        return "low"

    @property
    def datetime_str(self) -> str:
        return datetime.fromtimestamp(self.timestamp).isoformat()

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.datetime_str,
            "timestamp_unix": self.timestamp,
            "camera_id": self.camera_id,
            "person_id": self.person_id,
            "status": self.status,
            "severity": self.severity,
            "zone": self.zone,
            "ppe_missing": self.ppe_missing,
            "ppe_present": self.ppe_present,
            "bbox": self.bbox,
        }

    def to_csv_row(self) -> List:
        return [
            self.datetime_str,
            self.camera_id,
            str(self.person_id),
            self.status,
            self.severity,
            self.zone,
            "|".join(self.ppe_missing),
            "|".join(self.ppe_present),
            str(self.bbox[0]), str(self.bbox[1]),
            str(self.bbox[2]), str(self.bbox[3]),
        ]

    @staticmethod
    def csv_header() -> List[str]:
        return [
            "timestamp", "camera_id", "person_id", "status",
            "severity", "zone", "ppe_missing", "ppe_present",
            "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
        ]


# ---------------------------------------------------------------------------
# Alert Manager
# ---------------------------------------------------------------------------

class AlertManager:
    """
    Gestor central de alertas de EPP.

    Características:
      - Rate limiting: evita spam de alertas repetidas
      - Umbrales por tiempo sin EPP: alerta si persona sigue sin EPP por N segundos
      - Zonas peligrosas: diferente nivel de exigencia por zona
      - Múltiples canales de salida: log, webhook, MQTT, CSV
      - Persistencia: guarda historial de alertas
    """

    def __init__(self, alert_log: bool = False,
                 alert_webhook: Optional[str] = None,
                 alert_webhook_headers: Optional[Dict[str, str]] = None,
                 alert_mqtt: Optional[str] = None,
                 alert_mqtt_topic: Optional[str] = None,
                 alert_mqtt_username: Optional[str] = None,
                 alert_mqtt_password: Optional[str] = None,
                 alert_csv: Optional[str] = None,
                 rate_limit_seconds: float = DEFAULT_RATE_LIMIT_SECONDS,
                 min_interval_person: float = DEFAULT_MIN_INTERVAL_PERSON,
                 alert_cooldown: float = DEFAULT_ALERT_COOLDOWN,
                 threshold_time_without_ppe: float = 10.0,
                 zone_rules: Optional[Dict[str, List[str]]] = None,
                 zones: Optional[Dict[str, List[int]]] = None):
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
        self.alert_cooldown = alert_cooldown
        self.threshold_time_without_ppe = threshold_time_without_ppe
        self.zone_rules = zone_rules or {}
        self.zones = zones or {}

        # Estado interno
        self._last_global_alert: float = 0.0
        self._person_last_alert: Dict[int, float] = {}
        self._person_first_violation: Dict[int, float] = {}
        self._person_active_violations: Set[int] = set()
        self._alert_history: List[AlertRecord] = []
        self._csv_writer = None
        self._csv_file = None
        self._mqtt_client = None
        self._running = False

        self._init_csv()
        self._init_mqtt()
        self._init_signals()

    def _init_csv(self):
        """Inicializa escritura a CSV."""
        if self.alert_csv:
            file_exists = os.path.exists(self.alert_csv)
            self._csv_file = open(self.alert_csv, "a", newline="")
            self._csv_writer = csv.writer(self._csv_file)
            if not file_exists:
                self._csv_writer.writerow(AlertRecord.csv_header())
            log.info("CSV output: %s", self.alert_csv)

    def _init_mqtt(self):
        """Inicializa cliente MQTT."""
        if self.alert_mqtt:
            try:
                import paho.mqtt.client as mqtt
                self._mqtt_client = mqtt.Client(
                    client_id=f"ppe-alert-{int(time.time())}"
                )
                if self.alert_mqtt_username and self.alert_mqtt_password:
                    self._mqtt_client.username_pw_set(
                        self.alert_mqtt_username, self.alert_mqtt_password
                    )
                # Parsear broker URL
                broker = self.alert_mqtt.replace("mqtt://", "").replace("mqtts://", "")
                if ":" in broker:
                    host, port = broker.split(":")
                    port = int(port)
                else:
                    host = broker
                    port = 1883
                self._mqtt_client.connect(host, port, keepalive=60)
                self._mqtt_client.loop_start()
                log.info("MQTT connected: %s:%d (topic: %s)",
                         host, port, self.alert_mqtt_topic)
            except ImportError:
                log.warning("paho-mqtt not installed. Install with: pip install paho-mqtt")
                self.alert_mqtt = None
            except Exception as e:
                log.warning("MQTT connection failed: %s", e)
                self.alert_mqtt = None

    def _init_signals(self):
        """Maneja señales para cierre graceful."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        log.info("Received signal %d, shutting down...", signum)
        self._running = False

    # -----------------------------------------------------------------------
    # Zone management
    # -----------------------------------------------------------------------

    def get_zone_for_bbox(self, bbox: List[int], frame_width: int = 640,
                          frame_height: int = 640) -> str:
        """
        Determina en qué zona está una persona según su bounding box.

        Args:
            bbox: [x1, y1, x2, y2]
            frame_width: Ancho del frame
            frame_height: Alto del frame

        Returns:
            Nombre de la zona, o "unknown" si no coincide con ninguna.
        """
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0

        for zone_name, zone_bbox in self.zones.items():
            if (zone_bbox[0] <= cx <= zone_bbox[2] and
                zone_bbox[1] <= cy <= zone_bbox[3]):
                return zone_name

        return "unknown"

    def get_required_ppe_for_zone(self, zone: str) -> List[str]:
        """
        Retorna la lista de EPP requeridos para una zona.

        Args:
            zone: Nombre de la zona

        Returns:
            Lista de elementos EPP requeridos. Si la zona no tiene reglas,
            retorna todos los elementos PPE_REQUIRED.
        """
        if zone in self.zone_rules:
            return self.zone_rules[zone]
        return PPE_REQUIRED

    # -----------------------------------------------------------------------
    # Alert evaluation
    # -----------------------------------------------------------------------

    def evaluate_person(self, person_id: int, camera_id: str,
                        ppe_missing: List[str], ppe_present: List[str],
                        bbox: List[int], timestamp: float = None,
                        frame_size: Tuple[int, int] = (640, 640)) -> Optional[AlertRecord]:
        """
        Evalúa si una persona necesita una alerta.

        Considera:
          - Rate limiting global y por persona
          - Tiempo mínimo sin EPP antes de alertar
          - Zona de la persona y requisitos específicos

        Args:
            person_id: ID de la persona trackeada
            camera_id: ID de la cámara
            ppe_missing: Lista de EPP faltantes
            ppe_present: Lista de EPP presentes
            bbox: Bounding box de la persona
            timestamp: Timestamp de la evaluación
            frame_size: (width, height) del frame

        Returns:
            AlertRecord si se debe alertar, None en caso contrario.
        """
        now = timestamp or time.time()

        # Sin infracción
        if not ppe_missing:
            if person_id in self._person_active_violations:
                log.info("Person %d resolved all PPE violations", person_id)
                self._person_active_violations.discard(person_id)
                self._person_first_violation.pop(person_id, None)
            return None

        # Determinar zona
        zone = self.get_zone_for_bbox(bbox, frame_size[0], frame_size[1])

        # Filtrar EPP no requerido en esta zona
        required = self.get_required_ppe_for_zone(zone)
        relevant_missing = [item for item in ppe_missing if item in required]

        if not relevant_missing:
            # La persona no tiene EPP faltante relevante para esta zona
            return None

        # Rate limiting global
        if now - self._last_global_alert < self.rate_limit_seconds:
            return None

        # Rate limiting por persona
        last_person = self._person_last_alert.get(person_id, 0.0)
        if now - last_person < self.min_interval_person:
            return None

        # Tiempo mínimo sin EPP antes de alertar
        if person_id not in self._person_first_violation:
            self._person_first_violation[person_id] = now
            return None  # Esperar a la próxima evaluación

        time_without_ppe = now - self._person_first_violation[person_id]
        if time_without_ppe < self.threshold_time_without_ppe:
            return None  # Aún no supera el umbral

        # Crear alerta
        status = self._determine_status(relevant_missing, required)
        alert = AlertRecord(
            person_id=person_id,
            camera_id=camera_id,
            ppe_missing=relevant_missing,
            ppe_present=ppe_present,
            bbox=bbox,
            status=status,
            zone=zone,
            timestamp=now,
        )

        return alert

    def _determine_status(self, missing: List[str],
                          required: List[str]) -> str:
        """Determina el estado de la alerta según cantidad de EPP faltante."""
        missing_count = len(missing)
        total_required = len(required)

        if missing_count == total_required:
            return "critical"
        elif missing_count >= total_required * 0.6:
            return "high"
        elif missing_count >= total_required * 0.3:
            return "medium"
        else:
            return "low"

    # -----------------------------------------------------------------------
    # Alert dispatch
    # -----------------------------------------------------------------------

    def dispatch_alert(self, alert: AlertRecord):
        """
        Envía una alerta por todos los canales configurados.

        Args:
            alert: AlertRecord a enviar.
        """
        now = alert.timestamp
        self._last_global_alert = now
        self._person_last_alert[alert.person_id] = now
        self._person_active_violations.add(alert.person_id)
        self._alert_history.append(alert)

        # Log
        if self.alert_log:
            missing_str = ", ".join(alert.ppe_missing)
            log.warning(
                "ALERT [%s] | Camera: %s | Person: %d | Zone: %s | "
                "Status: %s | Missing: %s",
                alert.severity.upper(),
                alert.camera_id,
                alert.person_id,
                alert.zone,
                alert.status,
                missing_str,
            )

        # Webhook
        if self.alert_webhook:
            self._send_webhook(alert)

        # MQTT
        if self.alert_mqtt and self._mqtt_client:
            self._send_mqtt(alert)

        # CSV
        if self._csv_writer:
            self._csv_writer.writerow(alert.to_csv_row())
            self._csv_file.flush()

    def _send_webhook(self, alert: AlertRecord):
        """Envía alerta vía HTTP POST."""
        try:
            import requests
            resp = requests.post(
                self.alert_webhook,
                json=alert.to_dict(),
                headers={
                    "Content-Type": "application/json",
                    **self.alert_webhook_headers,
                },
                timeout=5.0,
            )
            if resp.status_code not in (200, 201, 202, 204):
                log.warning("Webhook returned HTTP %d: %s",
                            resp.status_code, resp.text[:200])
        except ImportError:
            log.warning("requests not installed. Install with: pip install requests")
        except requests.exceptions.Timeout:
            log.warning("Webhook timeout (>5s): %s", self.alert_webhook)
        except Exception as e:
            log.warning("Webhook failed: %s", e)

    def _send_mqtt(self, alert: AlertRecord):
        """Envía alerta vía MQTT."""
        try:
            payload = json.dumps(alert.to_dict())
            self._mqtt_client.publish(
                self.alert_mqtt_topic,
                payload,
                qos=1,
                retain=False,
            )
        except Exception as e:
            log.warning("MQTT publish failed: %s", e)

    # -----------------------------------------------------------------------
    # Bulk processing
    # -----------------------------------------------------------------------

    def process_frame_detections(self, frame_data: Dict[str, Any],
                                 frame_size: Tuple[int, int] = (640, 640)) -> List[AlertRecord]:
        """
        Procesa detecciones de un frame y genera alertas.

        Args:
            frame_data: Diccionario con datos del frame
               {
                   "frame_id": int,
                   "camera_id": str,
                   "people": [
                       {
                           "person_id": int,
                           "bbox": [x1, y1, x2, y2],
                           "ppe_missing": [str, ...],
                           "ppe_present": [str, ...],
                       }
                   ]
               }
            frame_size: (width, height) del frame

        Returns:
            Lista de alertas generadas en este frame.
        """
        alerts = []
        timestamp = frame_data.get("timestamp", time.time())
        camera_id = frame_data.get("camera_id", "unknown")

        for person in frame_data.get("people", []):
            alert = self.evaluate_person(
                person_id=person["person_id"],
                camera_id=camera_id,
                ppe_missing=person.get("ppe_missing", []),
                ppe_present=person.get("ppe_present", []),
                bbox=person.get("bbox", [0, 0, 0, 0]),
                timestamp=timestamp,
                frame_size=frame_size,
            )
            if alert:
                self.dispatch_alert(alert)
                alerts.append(alert)

        return alerts

    def process_json_file(self, input_path: str, output_path: str = None):
        """
        Procesa un archivo JSON con resultados de detección.

        El JSON debe tener la estructura generada por ppe-pipeline.py.
        """
        log.info("Processing JSON file: %s", input_path)
        try:
            with open(input_path) as f:
                data = json.load(f)
        except Exception as e:
            log.error("Cannot read input file: %s", e)
            return

        all_alerts = []
        for frame in data.get("frames", []):
            alerts = self.process_frame_detections({
                "frame_id": frame["frame_id"],
                "camera_id": frame.get("camera_id", "unknown"),
                "timestamp": frame.get("timestamp_s", 0),
                "people": frame.get("people", []),
            })
            all_alerts.extend(alerts)

        log.info("Processed %d frames, generated %d alerts",
                 len(data.get("frames", [])), len(all_alerts))

        if output_path:
            output = {
                "metadata": {
                    "source": input_path,
                    "total_frames": len(data.get("frames", [])),
                    "total_alerts": len(all_alerts),
                    "processed_at": datetime.now().isoformat(),
                    "config": {
                        "rate_limit_seconds": self.rate_limit_seconds,
                        "min_interval_person": self.min_interval_person,
                        "threshold_time_without_ppe": self.threshold_time_without_ppe,
                    },
                },
                "alerts": [a.to_dict() for a in all_alerts],
                "summary": self.get_summary(all_alerts),
            }
            with open(output_path, "w") as f:
                json.dump(output, f, indent=2)
            log.info("Output saved: %s", output_path)

    # -----------------------------------------------------------------------
    # Service mode
    # -----------------------------------------------------------------------

    def run_service(self):
        """
        Ejecuta el gestor en modo servicio.

        Lee alertas desde stdin (líneas JSON) o desde un archivo JSON
        que se actualiza periódicamente.
        """
        self._running = True
        log.info("Alert Manager service started (PID: %d)", os.getpid())

        # Estadísticas del servicio
        start_time = time.time()
        alerts_processed = 0

        while self._running:
            try:
                # Leer línea desde stdin
                if sys.stdin.isatty():
                    # No hay stdin, modo idle
                    time.sleep(1)
                    continue

                line = sys.stdin.readline().strip()
                if not line:
                    time.sleep(0.1)
                    continue

                # Parsear JSON
                try:
                    frame_data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Procesar
                alerts = self.process_frame_detections(frame_data)
                alerts_processed += len(alerts)

                # Reporte periódico
                elapsed = time.time() - start_time
                if elapsed >= 60:  # Cada minuto
                    log.info(
                        "Service stats: %d alerts in %.0f seconds (%.1f alerts/min)",
                        alerts_processed, elapsed,
                        alerts_processed / (elapsed / 60),
                    )

            except KeyboardInterrupt:
                break
            except Exception as e:
                log.error("Service error: %s", e)
                time.sleep(1)

        self.shutdown()

    # -----------------------------------------------------------------------
    # Reporting
    # -----------------------------------------------------------------------

    def get_summary(self, alerts: List[AlertRecord] = None) -> Dict[str, Any]:
        """Genera resumen estadístico de alertas."""
        if alerts is None:
            alerts = self._alert_history

        if not alerts:
            return {
                "total_alerts": 0,
                "unique_persons": 0,
                "by_status": {},
                "by_severity": {},
                "by_zone": {},
                "by_camera": {},
                "most_missing_items": [],
                "time_span_seconds": 0,
            }

        by_status = defaultdict(int)
        by_severity = defaultdict(int)
        by_zone = defaultdict(int)
        by_camera = defaultdict(int)
        missing_items_counter = defaultdict(int)
        persons = set()

        for alert in alerts:
            by_status[alert.status] += 1
            by_severity[alert.severity] += 1
            by_zone[alert.zone] += 1
            by_camera[alert.camera_id] += 1
            persons.add(alert.person_id)
            for item in alert.ppe_missing:
                missing_items_counter[item] += 1

        timestamps = [a.timestamp for a in alerts if a.timestamp > 0]
        time_span = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0

        most_missing = sorted(
            missing_items_counter.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return {
            "total_alerts": len(alerts),
            "unique_persons": len(persons),
            "by_status": dict(by_status),
            "by_severity": dict(by_severity),
            "by_zone": dict(by_zone),
            "by_camera": dict(by_camera),
            "most_missing_items": [
                {"item": item, "count": count}
                for item, count in most_missing[:5]
            ],
            "time_span_seconds": time_span,
        }

    def generate_report(self, alerts: List[AlertRecord] = None,
                        output_path: str = "alert_report.html"):
        """Genera reporte HTML con estadísticas de alertas."""
        if alerts is None:
            alerts = self._alert_history

        summary = self.get_summary(alerts)
        now = datetime.now().isoformat()

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PPE Alert Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0f1117; color: #e1e4e8; padding: 20px; }}
  h1 {{ font-size: 24px; margin-bottom: 20px; color: #58a6ff; }}
  h2 {{ font-size: 18px; margin: 24px 0 12px; color: #c9d1d9; }}
  .summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                    gap: 12px; margin-bottom: 24px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }}
  .card .value {{ font-size: 28px; font-weight: 700; }}
  .card .label {{ font-size: 11px; color: #8b949e; text-transform: uppercase; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #30363d; }}
  th {{ color: #8b949e; font-size: 11px; text-transform: uppercase; }}
  .severity {{ display: inline-block; padding: 2px 10px; border-radius: 12px;
              font-size: 11px; font-weight: 600; }}
  .bar-container {{ background: #21262d; border-radius: 4px; height: 20px; margin: 4px 0; }}
  .bar {{ height: 20px; border-radius: 4px; display: flex; align-items: center;
          padding-left: 8px; font-size: 11px; color: white; }}
</style>
</head>
<body>
<h1>🛡️ PPE Alert Report</h1>
<p style="color: #8b949e; margin-bottom: 20px;">Generated: {now}</p>

<div class="summary-cards">
  <div class="card">
    <div class="value" style="color: #f85149;">{summary["total_alerts"]}</div>
    <div class="label">Total Alertas</div>
  </div>
  <div class="card">
    <div class="value" style="color: #58a6ff;">{summary["unique_persons"]}</div>
    <div class="label">Personas Únicas</div>
  </div>
  <div class="card">
    <div class="value" style="color: #d29922;">{summary["time_span_seconds"] / 60:.0f}</div>
    <div class="label">Minutos Cubiertos</div>
  </div>
  <div class="card">
    <div class="value" style="color: #3fb950;">{len(self._alert_history)}</div>
    <div class="label">Historial Total</div>
  </div>
</div>

<h2>Alertas por Severidad</h2>
<table>
<thead><tr><th>Severidad</th><th>Alertas</th></tr></thead>
<tbody>
"""
        for sev, config in SEVERITY_LEVELS.items():
            count = summary["by_severity"].get(sev, 0)
            total = max(summary["total_alerts"], 1)
            pct = count / total * 100
            html += f"""
  <tr>
    <td><span class="severity" style="background: {config['color']}20; color: {config['color']}; border: 1px solid {config['color']};">{config['label']}</span></td>
    <td>
      <div class="bar-container">
        <div class="bar" style="width: {pct:.0f}%; background: {config['color']};">{count}</div>
      </div>
    </td>
  </tr>"""

        html += """
</tbody>
</table>

<h2>Alertas por Cámara</h2>
<table>
<thead><tr><th>Cámara</th><th>Alertas</th></tr></thead>
<tbody>
"""
        for cam, count in sorted(summary["by_camera"].items(), key=lambda x: x[1], reverse=True):
            html += f"<tr><td>{cam}</td><td>{count}</td></tr>"

        html += """
</tbody>
</table>

<h2>Elementos Faltantes Más Frecuentes</h2>
<table>
<thead><tr><th>Elemento EPP</th><th>Veces Faltante</th></tr></thead>
<tbody>
"""
        for item in summary["most_missing_items"]:
            html += f"<tr><td>{item['item']}</td><td>{item['count']}</td></tr>"

        html += """
</tbody>
</table>

<h2>Últimas 50 Alertas</h2>
<table>
<thead><tr><th>Tiempo</th><th>Cámara</th><th>Persona</th><th>Severidad</th><th>Zona</th><th>Faltante</th></tr></thead>
<tbody>
"""
        for alert in alerts[-50:]:
            sev_config = SEVERITY_LEVELS.get(alert.severity, SEVERITY_LEVELS["low"])
            missing_str = ", ".join(alert.ppe_missing)
            time_str = datetime.fromtimestamp(alert.timestamp).strftime("%H:%M:%S")
            html += f"""
  <tr>
    <td>{time_str}</td>
    <td>{alert.camera_id}</td>
    <td>P{alert.person_id}</td>
    <td><span class="severity" style="background: {sev_config['color']}20; color: {sev_config['color']}; border: 1px solid {sev_config['color']};">{sev_config['label']}</span></td>
    <td>{alert.zone}</td>
    <td>{missing_str}</td>
  </tr>"""

        html += """
</tbody>
</table>
</body>
</html>
"""
        with open(output_path, "w") as f:
            f.write(html)
        log.info("Report saved: %s", output_path)

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def shutdown(self):
        """Cierra todos los canales y libera recursos."""
        log.info("Shutting down Alert Manager...")
        if self._csv_file:
            self._csv_file.close()
            log.info("CSV file closed")
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
            log.info("MQTT disconnected")
        log.info(
            "Alert Manager stopped. Total alerts processed: %d",
            len(self._alert_history),
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Alert Manager — Sistema de alertas de EPP para minería",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--mode", "-m", default="service",
                        choices=["service", "file", "report"],
                        help="Operation mode (default: service)")

    # Input/Output
    parser.add_argument("--input", "-i",
                        help="Input JSON file (mode: file)")
    parser.add_argument("--output", "-o", default="./alert_output",
                        help="Output directory or file path")

    # Alert channels
    parser.add_argument("--alert-log", action="store_true", default=True,
                        help="Log alerts to console (default: True)")
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
                        help="CSV file for alert history")

    # Rate limiting
    parser.add_argument("--rate-limit", type=float,
                        default=DEFAULT_RATE_LIMIT_SECONDS,
                        help="Minimum seconds between global alerts (default: 30)")
    parser.add_argument("--min-interval-person", type=float,
                        default=DEFAULT_MIN_INTERVAL_PERSON,
                        help="Minimum seconds between alerts for same person (default: 60)")
    parser.add_argument("--alert-cooldown", type=float,
                        default=DEFAULT_ALERT_COOLDOWN,
                        help="Alert cooldown per person in seconds (default: 300)")
    parser.add_argument("--threshold-time", type=float, default=10.0,
                        help="Seconds without PPE before alerting (default: 10)")

    # Zone rules
    parser.add_argument("--zone-rule", action="append",
                        help="Zone rule: 'zone_name:item1,item2'")
    parser.add_argument("--zone-bbox", action="append",
                        help="Zone bounding box: 'zone_name:x1,y1,x2,y2'")

    return parser.parse_args()


def main():
    args = parse_args()

    # Parsear zone rules
    zone_rules = {}
    if args.zone_rule:
        for rule in args.zone_rule:
            if ":" in rule:
                zone, items = rule.split(":", 1)
                zone_rules[zone.strip()] = [i.strip() for i in items.split(",")]

    # Parsear zone bboxes
    zones = {}
    if args.zone_bbox:
        for zb in args.zone_bbox:
            if ":" in zb:
                name, coords = zb.split(":", 1)
                x1, y1, x2, y2 = map(int, coords.split(","))
                zones[name.strip()] = [x1, y1, x2, y2]

    # Headers
    webhook_headers = {}
    if args.alert_webhook_header:
        for h in args.alert_webhook_header:
            if ":" in h:
                k, v = h.split(":", 1)
                webhook_headers[k.strip()] = v.strip()

    manager = AlertManager(
        alert_log=args.alert_log,
        alert_webhook=args.alert_webhook,
        alert_webhook_headers=webhook_headers,
        alert_mqtt=args.alert_mqtt,
        alert_mqtt_topic=args.alert_mqtt_topic,
        alert_mqtt_username=args.alert_mqtt_username,
        alert_mqtt_password=args.alert_mqtt_password,
        alert_csv=args.alert_csv,
        rate_limit_seconds=args.rate_limit,
        min_interval_person=args.min_interval_person,
        alert_cooldown=args.alert_cooldown,
        threshold_time_without_ppe=args.threshold_time,
        zone_rules=zone_rules,
        zones=zones,
    )

    if args.mode == "file":
        if not args.input:
            log.error("--input required for file mode")
            sys.exit(1)
        output_path = None
        if args.output:
            if os.path.isdir(args.output):
                output_path = os.path.join(args.output, "alerts_processed.json")
            else:
                output_path = args.output
        manager.process_json_file(args.input, output_path)

    elif args.mode == "report":
        output_path = args.output
        if os.path.isdir(output_path):
            output_path = os.path.join(output_path, "alert_report.html")
        manager.generate_report(output_path=output_path)

    else:  # service
        log.info("Starting in service mode. Send JSON lines to stdin.")
        manager.run_service()


if __name__ == "__main__":
    main()
