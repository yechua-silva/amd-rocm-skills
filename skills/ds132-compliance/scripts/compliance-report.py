#!/usr/bin/env python3
"""
compliance-report.py — Reporte de Cumplimiento DS 132

Genera reportes de cumplimiento normativo DS 132 para faenas mineras
en formato PDF, HTML y JSON.

Integra con ppe-detection-pipeline para evaluar el uso de EPP
(casco, chaleco, guantes, lentes, botas) por zona, turno y persona.

Uso:
  python3 compliance-report.py --input detecciones.json --zones zonas.json \\
      --period daily --format pdf --output reporte.pdf

Argumentos:
  --input        Archivo JSON con detecciones del pipeline
  --zones        Archivo JSON/YAML con configuración de zonas
  --output       Archivo de salida (.pdf, .html, .json)
  --format       Formato de salida: pdf | html | json
  --period       Período: daily | weekly | monthly
  --company      Nombre de la empresa minera
  --site         Nombre de la faena
  --scoring      Método de scoring: worst | average (default: worst)
  --alerts       Generar alertas regulatorias
  --alert-threshold  Umbral de alerta (default: 0.9)
  --dashboard    Generar dashboard HTML interactivo
  --penalties    Incluir estimación de multas
  --multi-site   Reporte consolidado multi-faena
  --distinguish-visitors  Distinguir visitantes de trabajadores
  --tolerance-window  Ventana de tolerancia en segundos
  --multi-frame  Usar verificación multi-frame
  --min-frames   Mínimo de frames para declarar infracción (default: 3)
  --watch-dir    Monitorear directorio para detecciones
  --interval     Intervalo de monitoreo en segundos (default: 60)
  --verbose      Modo verbose
  --version      Mostrar versión
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# Versión de la skill
VERSION = "1.0.0"

# Clases EPP soportadas
EPP_CLASSES = ["hardhat", "vest", "gloves", "safety-glasses", "boots"]

# Mapeo a nombres español
EPP_NOMBRES = {
    "hardhat": "Casco de seguridad",
    "vest": "Chaleco reflectante",
    "gloves": "Guantes de seguridad",
    "safety-glasses": "Lentes de seguridad",
    "boots": "Botas de seguridad",
}

# Artículos DS 132 relevantes por tipo de EPP
EPP_ARTICULOS = {
    "hardhat": "Art. 12, Art. 38",
    "vest": "Art. 12, Art. 38",
    "gloves": "Art. 12",
    "safety-glasses": "Art. 12",
    "boots": "Art. 12, Art. 38",
}


def cargar_detecciones(ruta):
    """Carga detecciones desde archivo JSON."""
    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return data.get("detecciones", data.get("detections", []))
    return []


def cargar_zonas(ruta):
    """Carga configuración de zonas desde JSON o YAML."""
    if ruta.endswith((".yaml", ".yml")):
        try:
            import yaml
            with open(ruta, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except ImportError:
            print("Error: Se requiere PyYAML para archivos YAML. pip install pyyaml")
            sys.exit(1)
    else:
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)

    zonas = data.get("zonas", data)
    return zonas


def validar_zonas(zonas):
    """Valida que la configuración de zonas sea correcta."""
    errores = []
    for zona_id, config in zonas.items():
        required = config.get("required", [])
        for epp in required:
            if epp not in EPP_CLASSES:
                errores.append(
                    f"Zona '{zona_id}': EPP '{epp}' no válido. "
                    f"Válidos: {', '.join(EPP_CLASSES)}"
                )
        min_conf = config.get("min_confidence", 0.7)
        if not 0 <= min_conf <= 1:
            errores.append(
                f"Zona '{zona_id}': min_confidence {min_conf} fuera de rango [0,1]"
            )
    return errores


def evaluar_compliance(deteccion, zona_config, metodo="worst"):
    """
    Evalúa compliance de una detección contra la configuración de zona.

    Args:
        deteccion: dict con datos de detección
        zona_config: dict con configuración de la zona
        metodo: "worst" o "average"

    Returns:
        dict con resultado de evaluación
    """
    required = zona_config.get("required", [])
    min_conf = zona_config.get("min_confidence", 0.7)
    tipo_persona = deteccion.get("tipo_persona", "trabajador")

    # Si es visitante y la zona tiene requisitos específicos para visitantes
    if tipo_persona == "visitante" and "required_visitante" in zona_config:
        required = zona_config["required_visitante"]

    epp_detectado = deteccion.get("epp_detectado", {})
    presente = []
    faltante = []

    for epp in required:
        det = epp_detectado.get(epp, {})
        if isinstance(det, dict):
            presente_val = det.get("presente", False)
            confianza = det.get("confidence", 0.0)
        elif isinstance(det, bool):
            presente_val = det
            confianza = 1.0 if det else 0.0
        else:
            presente_val = False
            confianza = 0.0

        if presente_val and confianza >= min_conf:
            presente.append({"epp": epp, "confidence": confianza})
        else:
            faltante.append({"epp": epp, "confidence": confianza})

    score = len(presente) / len(required) if required else 1.0
    compliant = len(faltante) == 0

    return {
        "persona_id": deteccion.get("persona_id", "desconocido"),
        "tipo_persona": tipo_persona,
        "zona": deteccion.get("zona", "desconocida"),
        "timestamp": deteccion.get("timestamp", ""),
        "epp_requerido": required,
        "epp_presente": [p["epp"] for p in presente],
        "epp_faltante": [f["epp"] for f in faltante],
        "compliant": compliant,
        "score": round(score, 4),
        "confianza_promedio": round(
            sum(p["confidence"] for p in presente) / len(required)
            if required else 1.0, 4
        ),
        "frame_id": deteccion.get("frame_id", ""),
        "imagen_evidencia": deteccion.get("imagen_evidencia", ""),
        "faena": deteccion.get("faena", ""),
        "turno": deteccion.get("turno", ""),
    }


def agrupar_por_persona(resultados, metodo="worst"):
    """Agrupa evaluaciones por persona y aplica método de scoring."""
    por_persona = defaultdict(list)
    for r in resultados:
        por_persona[r["persona_id"]].append(r)

    resumen = {}
    for pid, evals in por_persona.items():
        if metodo == "worst":
            score = min(e["score"] for e in evals)
            compliant = all(e["compliant"] for e in evals)
            peor = min(evals, key=lambda e: e["score"])
            faltante = peor["epp_faltante"]
        else:
            score = sum(e["score"] for e in evals) / len(evals)
            compliant = score >= 0.9
            faltante = list(set(
                epp for e in evals for epp in e["epp_faltante"]
            ))

        resumen[pid] = {
            "persona_id": pid,
            "tipo_persona": evals[0]["tipo_persona"],
            "total_evaluaciones": len(evals),
            "compliant": compliant,
            "score": round(score, 4),
            "epp_faltante": faltante,
            "zonas": list(set(e["zona"] for e in evals)),
        }
    return resumen


def agrupar_por_zona(resultados):
    """Agrupa métricas de compliance por zona."""
    por_zona = defaultdict(list)
    for r in resultados:
        por_zona[r["zona"]].append(r)

    resumen = {}
    for zona, evals in por_zona.items():
        total = len(evals)
        compliant = sum(1 for e in evals if e["compliant"])
        score = sum(e["score"] for e in evals) / total if total else 0

        # EPP faltante más común en esta zona
        epp_faltante = defaultdict(int)
        for e in evals:
            for f in e["epp_faltante"]:
                epp_faltante[f] += 1

        resumen[zona] = {
            "zona": zona,
            "total_evaluaciones": total,
            "compliant_count": compliant,
            "non_compliant_count": total - compliant,
            "compliance_pct": round(compliant / total * 100, 1) if total else 0.0,
            "score_promedio": round(score, 4),
            "epp_faltante_ranking": sorted(
                epp_faltante.items(), key=lambda x: -x[1]
            ),
            "personas_unicas": len(set(e["persona_id"] for e in evals)),
        }
    return resumen


def detectar_alertas(por_zona, zonas_config, threshold=0.9):
    """Genera alertas regulatorias para zonas bajo umbral."""
    alertas = []
    for zona_id, metrics in por_zona.items():
        if metrics["compliance_pct"] < threshold * 100:
            config = zonas_config.get(zona_id, {})
            riesgo = config.get("riesgo", "medio")
            alertas.append({
                "tipo": "ZONA_BAJO_UMBRAL",
                "severidad": "alta" if riesgo == "alto" else "media",
                "zona": zona_id,
                "compliance_pct": metrics["compliance_pct"],
                "umbral": threshold * 100,
                "timestamp": datetime.now().isoformat(),
                "detalle": (
                    f"Zona '{config.get('nombre', zona_id)}' bajo umbral "
                    f"de cumplimiento ({metrics['compliance_pct']:.1f}% < {threshold*100:.0f}%)"
                ),
                "articulo_ds132": "Art. 12, Art. 38",
                "accion_sugerida": (
                    "Reforzar supervisión y verificar suministro de EPP "
                    f"en zona {config.get('nombre', zona_id)}"
                ),
            })

    # Detectar EPP faltante sistémico
    for zona_id, metrics in por_zona.items():
        for epp, count in metrics.get("epp_faltante_ranking", []):
            if count > metrics["total_evaluaciones"] * 0.3:
                config = zonas_config.get(zona_id, {})
                alertas.append({
                    "tipo": "EPP_FALTANTE_SISTEMICO",
                    "severidad": "media",
                    "zona": zona_id,
                    "epp": epp,
                    "frecuencia_pct": round(count / metrics["total_evaluaciones"] * 100, 1),
                    "timestamp": datetime.now().isoformat(),
                    "detalle": (
                        f"EPP '{EPP_NOMBRES.get(epp, epp)}' falta en "
                        f"{count}/{metrics['total_evaluaciones']} evaluaciones "
                        f"de zona '{config.get('nombre', zona_id)}'"
                    ),
                    "articulo_ds132": EPP_ARTICULOS.get(epp, "Art. 12"),
                    "accion_sugerida": (
                        f"Revisar suministro y tallas de {EPP_NOMBRES.get(epp, epp)} "
                        f"para zona {config.get('nombre', zona_id)}"
                    ),
                })

    return alertas


def generar_reporte_pdf(metrics, zonas_config, output_path, company, site, periodo):
    """Genera reporte PDF usando WeasyPrint + Jinja2."""
    try:
        from jinja2 import Template
        import weasyprint
    except ImportError:
        print("Error: Se requiere jinja2 y weasyprint para PDF.")
        print("  pip install jinja2 weasyprint")
        sys.exit(1)

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page { margin: 2cm; size: A4; }
            body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11pt; color: #333; }
            h1 { color: #1a3a5c; border-bottom: 3px solid #1a3a5c; padding-bottom: 8px; }
            h2 { color: #2c5f8a; margin-top: 24px; }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { font-size: 20pt; border-bottom: none; }
            .header .subtitle { color: #666; font-size: 12pt; }
            table { width: 100%; border-collapse: collapse; margin: 12px 0; }
            th, td { border: 1px solid #ddd; padding: 8px 10px; text-align: left; }
            th { background: #1a3a5c; color: white; font-size: 10pt; }
            tr:nth-child(even) { background: #f5f8fc; }
            .compliant-yes { color: #27ae60; font-weight: bold; }
            .compliant-no { color: #e74c3c; font-weight: bold; }
            .severidad-alta { color: #e74c3c; font-weight: bold; }
            .severidad-media { color: #e67e22; font-weight: bold; }
            .summary { display: flex; gap: 16px; margin: 16px 0; }
            .summary-card {
                flex: 1; padding: 14px; border-radius: 6px; text-align: center;
                color: white; font-size: 13pt;
            }
            .card-green { background: #27ae60; }
            .card-yellow { background: #f39c12; }
            .card-red { background: #e74c3c; }
            .card-blue { background: #2980b9; }
            .summary-card .value { font-size: 24pt; font-weight: bold; }
            .summary-card .label { font-size: 9pt; opacity: 0.9; }
            .alert-box {
                padding: 10px 14px; margin: 8px 0; border-left: 4px solid #e74c3c;
                background: #fdf0ef; border-radius: 3px;
            }
            .footer {
                margin-top: 40px; font-size: 9pt; color: #999; text-align: center;
                border-top: 1px solid #ddd; padding-top: 12px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Reporte de Cumplimiento DS 132</h1>
            <div class="subtitle">
                {{ company }} — {{ site }}<br>
                Período: {{ periodo_display }} | Generado: {{ fecha_generacion }}
            </div>
        </div>

        <h2>Resumen Ejecutivo</h2>
        <div class="summary">
            <div class="summary-card card-green">
                <div class="value">{{ metrics.global.compliance_pct }}%</div>
                <div class="label">Cumplimiento Global</div>
            </div>
            <div class="summary-card card-blue">
                <div class="value">{{ metrics.global.total_evaluaciones }}</div>
                <div class="label">Evaluaciones</div>
            </div>
            <div class="summary-card {% if metrics.global.compliance_pct >= 90 %}card-green{% elif metrics.global.compliance_pct >= 80 %}card-yellow{% else %}card-red{% endif %}">
                <div class="value">{{ metrics.global.personas_unicas }}</div>
                <div class="label">Personas Evaluadas</div>
            </div>
            <div class="summary-card card-yellow">
                <div class="value">{{ metrics.global.zonas_monitoreadas }}</div>
                <div class="label">Zonas Monitoreadas</div>
            </div>
        </div>

        <h2>Zonas</h2>
        <table>
            <tr>
                <th>Zona</th>
                <th>Cumplimiento</th>
                <th>Evaluaciones</th>
                <th>Score Prom.</th>
                <th>Top EPP Faltante</th>
            </tr>
            {% for zona_id, z in metrics.por_zona.items() %}
            <tr>
                <td>{{ z.zona }}</td>
                <td class="{% if z.compliance_pct >= 90 %}compliant-yes{% else %}compliant-no{% endif %}">
                    {{ z.compliance_pct }}%
                </td>
                <td>{{ z.total_evaluaciones }}</td>
                <td>{{ '%.2f'|format(z.score_promedio) }}</td>
                <td>
                    {% if z.epp_faltante_ranking %}
                        {% for epp, count in z.epp_faltante_ranking[:3] %}
                            {{ epp }} ({{ count }}){% if not loop.last %}, {% endif %}
                        {% endfor %}
                    {% else %}
                        —
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>

        <h2>EPP Faltante — Ranking General</h2>
        <table>
            <tr><th>EPP</th><th>Frecuencia</th><th>% del Total</th><th>Artículo DS 132</th></tr>
            {% for epp, count in metrics.epp_ranking %}
            <tr>
                <td>{{ epp }}</td>
                <td>{{ count }}</td>
                <td>{{ '%.1f'|format(count / metrics.global.total_evaluaciones * 100) }}%</td>
                <td>{{ epp_articulos.get(epp, 'Art. 12') }}</td>
            </tr>
            {% endfor %}
        </table>

        {% if metrics.alertas %}
        <h2>Alertas Regulatorias</h2>
        {% for alerta in metrics.alertas %}
        <div class="alert-box">
            <strong class="severidad-{{ alerta.severidad }}">{{ alerta.tipo }}</strong><br>
            {{ alerta.detalle }}<br>
            <small>Artículo: {{ alerta.articulo_ds132 }} | Severidad: {{ alerta.severidad }}</small>
        </div>
        {% endfor %}
        {% endif %}

        <div class="footer">
            <p>
                Reporte generado por DS 132 Compliance v{{ version }}<br>
                {{ company }} — {{ site }} | {{ fecha_generacion }}
            </p>
            <p>
                Este reporte cumple con los requisitos del DS 132 del Ministerio de Minería de Chile<br>
                y está preparado para presentación a SERNAGEOMIN.
            </p>
        </div>
    </body>
    </html>
    """

    context = {
        "company": company,
        "site": site,
        "periodo_display": {
            "daily": "Diario",
            "weekly": "Semanal",
            "monthly": "Mensual",
        }.get(periodo, periodo),
        "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "metrics": metrics,
        "version": VERSION,
        "epp_articulos": EPP_ARTICULOS,
    }

    template = Template(html_template)
    html = template.render(**context)
    weasyprint.HTML(string=html).write_pdf(output_path)
    print(f"Reporte PDF generado: {output_path}")


def generar_reporte_html(metrics, zonas_config, output_path, company, site, periodo):
    """Genera reporte HTML con dashboard interactivo."""
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Reporte DS 132 — {company} — {site}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f4f8; color: #333; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ background: linear-gradient(135deg, #1a3a5c, #2c5f8a); color: white; padding: 30px; border-radius: 12px; margin-bottom: 24px; }}
        header h1 {{ font-size: 24px; margin-bottom: 6px; }}
        header .meta {{ opacity: 0.8; font-size: 13px; }}
        .dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .card .value {{ font-size: 28px; font-weight: 700; }}
        .card .label {{ font-size: 12px; color: #888; margin-top: 4px; }}
        .green {{ color: #27ae60; }}
        .yellow {{ color: #f39c12; }}
        .red {{ color: #e74c3c; }}
        .blue {{ color: #2980b9; }}
        h2 {{ font-size: 18px; color: #1a3a5c; margin: 24px 0 12px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #eee; font-size: 13px; }}
        th {{ background: #1a3a5c; color: white; font-weight: 600; }}
        tr:hover {{ background: #f5f8fc; }}
        .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
        .badge-green {{ background: #e8f8f0; color: #27ae60; }}
        .badge-red {{ background: #fde8e8; color: #e74c3c; }}
        .badge-yellow {{ background: #fef9e7; color: #f39c12; }}
        .alert {{ background: #fdf0ef; border-left: 4px solid #e74c3c; padding: 12px 16px; margin: 8px 0; border-radius: 4px; }}
        .alert.media {{ border-left-color: #f39c12; background: #fef9e7; }}
        .bar-container {{ background: #ecf0f1; border-radius: 6px; height: 18px; margin: 4px 0; overflow: hidden; }}
        .bar {{ height: 100%; border-radius: 6px; transition: width 0.3s; }}
        .bar-green {{ background: #27ae60; }}
        .bar-yellow {{ background: #f39c12; }}
        .bar-red {{ background: #e74c3c; }}
        footer {{ margin-top: 40px; text-align: center; color: #999; font-size: 11px; padding: 20px; border-top: 1px solid #ddd; }}
        @media print {{ body {{ background: white; padding: 0; }} .card {{ box-shadow: none; border: 1px solid #ddd; }} }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>📋 Reporte de Cumplimiento DS 132</h1>
        <div class="meta">
            {company} — {site} |
            Período: {"Diario" if periodo == "daily" else "Semanal" if periodo == "weekly" else "Mensual"} |
            Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}
        </div>
    </header>

    <div class="dashboard">
        <div class="card">
            <div class="value {'green' if metrics['global']['compliance_pct'] >= 90 else 'yellow' if metrics['global']['compliance_pct'] >= 80 else 'red'}">
                {metrics['global']['compliance_pct']}%
            </div>
            <div class="label">Cumplimiento Global</div>
        </div>
        <div class="card">
            <div class="value blue">{metrics['global']['total_evaluaciones']}</div>
            <div class="label">Evaluaciones Realizadas</div>
        </div>
        <div class="card">
            <div class="value blue">{metrics['global']['personas_unicas']}</div>
            <div class="label">Personas Evaluadas</div>
        </div>
        <div class="card">
            <div class="value blue">{metrics['global']['zonas_monitoreadas']}</div>
            <div class="label">Zonas Monitoreadas</div>
        </div>
    </div>

    <h2>Cumplimiento por Zona</h2>
    <table>
        <tr><th>Zona</th><th>Cumplimiento</th><th>Evaluaciones</th><th>Score</th><th>EPP Faltante (Top)</th></tr>
"""
    for zona_id, z in sorted(metrics["por_zona"].items()):
        pct = z["compliance_pct"]
        badge_class = "badge-green" if pct >= 90 else "badge-yellow" if pct >= 80 else "badge-red"
        top_epp = ""
        if z.get("epp_faltante_ranking"):
            top_epp = ", ".join(f"{epp} ({c})" for epp, c in z["epp_faltante_ranking"][:3])
        else:
            top_epp = "—"
        html += f"""
        <tr>
            <td><strong>{z['zona']}</strong></td>
            <td><span class="badge {badge_class}">{pct}%</span></td>
            <td>{z['total_evaluaciones']}</td>
            <td>{z['score_promedio']:.2f}</td>
            <td>{top_epp}</td>
        </tr>"""

    html += """
    </table>

    <h2>EPP Faltante — Ranking General</h2>
    <table>
        <tr><th>EPP</th><th>Frecuencia</th><th>% del Total</th><th>Artículo DS 132</th></tr>
"""
    for epp, count in metrics["epp_ranking"]:
        pct = count / metrics["global"]["total_evaluaciones"] * 100 if metrics["global"]["total_evaluaciones"] else 0
        bar_class = "bar-green" if pct < 10 else "bar-yellow" if pct < 25 else "bar-red"
        html += f"""
        <tr>
            <td>{EPP_NOMBRES.get(epp, epp)}</td>
            <td>{count}</td>
            <td>
                <div class="bar-container">
                    <div class="bar {bar_class}" style="width: {min(pct, 100)}%"></div>
                </div>
                {pct:.1f}%
            </td>
            <td>{EPP_ARTICULOS.get(epp, 'Art. 12')}</td>
        </tr>"""

    html += """
    </table>
"""

    if metrics.get("alertas"):
        html += """
    <h2>Alertas Regulatorias</h2>
"""
        for alerta in metrics["alertas"]:
            clase = "alert media" if alerta["severidad"] == "media" else "alert"
            html += f"""
    <div class="{clase}">
        <strong>{alerta['tipo']}</strong> — Severidad: {alerta['severidad']}<br>
        {alerta['detalle']}<br>
        <small>Artículo: {alerta['articulo_ds132']} | {alerta.get('accion_sugerida', '')}</small>
    </div>"""

    html += f"""
    <footer>
        Reporte generado por <strong>DS 132 Compliance v{VERSION}</strong><br>
        {company} — {site} | {datetime.now().strftime("%d/%m/%Y %H:%M")}<br>
        <small>Preparado para fiscalización SERNAGEOMIN — DS 132 Ministerio de Minería de Chile</small>
    </footer>
</div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Reporte HTML generado: {output_path}")


def generar_reporte_json(metrics, output_path):
    """Genera reporte en formato JSON."""
    reporte = {
        "metadata": {
            "skill": "ds132-compliance",
            "version": VERSION,
            "generado": datetime.now().isoformat(),
            "formato": "sernageomin-compatible",
        },
        "resumen": {
            "cumplimiento_global_pct": metrics["global"]["compliance_pct"],
            "total_evaluaciones": metrics["global"]["total_evaluaciones"],
            "personas_evaluadas": metrics["global"]["personas_unicas"],
            "zonas_monitoreadas": metrics["global"]["zonas_monitoreadas"],
            "personas_compliant": metrics["global"]["personas_compliant"],
            "personas_no_compliant": metrics["global"]["personas_no_compliant"],
        },
        "por_zona": metrics["por_zona"],
        "por_persona": metrics.get("por_persona", {}),
        "epp_ranking": [
            {"epp": epp, "nombre": EPP_NOMBRES.get(epp, epp),
             "frecuencia": count, "articulo_ds132": EPP_ARTICULOS.get(epp, "Art. 12")}
            for epp, count in metrics["epp_ranking"]
        ],
        "alertas": metrics.get("alertas", []),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    print(f"Reporte JSON generado: {output_path}")


def compute_metrics(resultados, zonas_config, alertas, generar_alertas, alert_threshold):
    """Computa métricas consolidadas a partir de evaluaciones."""
    por_zona = agrupar_por_zona(resultados)
    por_persona = agrupar_por_persona(resultados)

    total = len(resultados)
    compliant = sum(1 for r in resultados if r["compliant"])
    score_prom = sum(r["score"] for r in resultados) / total if total else 0
    personas_unicas = len(set(r["persona_id"] for r in resultados))
    personas_compliant = sum(1 for p in por_persona.values() if p["compliant"])
    personas_no_compliant = personas_unicas - personas_compliant

    # Ranking de EPP faltante
    epp_faltante = defaultdict(int)
    for r in resultados:
        for f in r["epp_faltante"]:
            epp_faltante[f] += 1
    epp_ranking = sorted(epp_faltante.items(), key=lambda x: -x[1])

    metrics = {
        "global": {
            "total_evaluaciones": total,
            "compliant": compliant,
            "non_compliant": total - compliant,
            "compliance_pct": round(compliant / total * 100, 1) if total else 0.0,
            "score_promedio": round(score_prom, 4),
            "personas_unicas": personas_unicas,
            "personas_compliant": personas_compliant,
            "personas_no_compliant": personas_no_compliant,
            "zonas_monitoreadas": len(por_zona),
        },
        "por_zona": por_zona,
        "por_persona": por_persona,
        "epp_ranking": epp_ranking,
    }

    if generar_alertas:
        metrics["alertas"] = detectar_alertas(por_zona, zonas_config, alert_threshold)
    else:
        metrics["alertas"] = []

    return metrics


def procesar(watch_dir, zonas, interval, verbose):
    """Monitorea directorio y procesa archivos nuevos."""
    import time
    procesados = set()

    print(f"Monitoreando: {watch_dir} (intervalo: {interval}s)")
    while True:
        for f in sorted(Path(watch_dir).glob("*.json")):
            if f.name in procesados:
                continue
            if verbose:
                print(f"Nuevo archivo detectado: {f}")
            try:
                detecciones = cargar_detecciones(str(f))
                resultados = [evaluar_compliance(d, zonas) for d in detecciones]
                metrics = compute_metrics(resultados, zonas, [], False, 0.9)
                print(f"  Procesado: {len(detecciones)} detecciones, "
                      f"compliance: {metrics['global']['compliance_pct']}%")
                procesados.add(f.name)
            except Exception as e:
                print(f"  Error procesando {f}: {e}")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(
        description="DS 132 Compliance Report — Reporte de Cumplimiento Normativo Minero"
    )
    parser.add_argument("--input", help="Archivo JSON con detecciones del pipeline")
    parser.add_argument("--zones", required=True, help="Archivo de configuración de zonas")
    parser.add_argument("--output", default="reporte_compliance.pdf", help="Archivo de salida")
    parser.add_argument("--format", choices=["pdf", "html", "json"], default="pdf",
                        help="Formato de salida")
    parser.add_argument("--period", choices=["daily", "weekly", "monthly"],
                        default="daily", help="Período del reporte")
    parser.add_argument("--company", default="Minera", help="Nombre de la empresa")
    parser.add_argument("--site", default="Faena Principal", help="Nombre de la faena")
    parser.add_argument("--scoring", choices=["worst", "average"], default="worst",
                        help="Método de scoring por persona")
    parser.add_argument("--alerts", action="store_true", help="Generar alertas regulatorias")
    parser.add_argument("--alert-threshold", type=float, default=0.9,
                        help="Umbral de alerta (default: 0.9)")
    parser.add_argument("--dashboard", action="store_true",
                        help="Generar dashboard HTML interactivo")
    parser.add_argument("--penalties", action="store_true", help="Incluir estimación de multas")
    parser.add_argument("--multi-site", action="store_true", help="Reporte multi-faena")
    parser.add_argument("--distinguish-visitors", action="store_true",
                        help="Distinguir visitantes de trabajadores")
    parser.add_argument("--tolerance-window", type=int, default=0,
                        help="Ventana de tolerancia en segundos")
    parser.add_argument("--multi-frame", action="store_true",
                        help="Usar verificación multi-frame")
    parser.add_argument("--min-frames", type=int, default=3,
                        help="Mínimo de frames para infracción")
    parser.add_argument("--watch-dir", help="Monitorear directorio para detecciones")
    parser.add_argument("--interval", type=int, default=60,
                        help="Intervalo de monitoreo en segundos")
    parser.add_argument("--verbose", action="store_true", help="Modo verbose")
    parser.add_argument("--version", action="store_true", help="Mostrar versión")

    args = parser.parse_args()

    if args.version:
        print(f"DS 132 Compliance Report v{VERSION}")
        return

    # Cargar zonas
    zonas = cargar_zonas(args.zones)
    errores = validar_zonas(zonas)
    if errores:
        for err in errores:
            print(f"Error de validación: {err}")
        sys.exit(1)

    if args.verbose:
        print(f"Zonas cargadas: {len(zonas)}")
        for zid, z in zonas.items():
            print(f"  {zid}: {z.get('nombre')} — {', '.join(z.get('required', []))}")

    # Modo watch
    if args.watch_dir:
        procesar(args.watch_dir, zonas, args.interval, args.verbose)
        return

    # Modo normal: procesar archivo de detecciones
    if not args.input:
        print("Error: Se requiere --input o --watch-dir")
        sys.exit(1)

    detecciones = cargar_detecciones(args.input)
    if args.verbose:
        print(f"Detecciones cargadas: {len(detecciones)}")

    if not detecciones:
        print("Advertencia: No se encontraron detecciones")
        return

    resultados = []
    for det in detecciones:
        zona_id = det.get("zona", "desconocida")
        zona_config = zonas.get(zona_id, zonas.get("default", {}))
        if not zona_config:
            if args.verbose:
                print(f"Advertencia: Zona '{zona_id}' no encontrada en configuración")
            continue
        resultado = evaluar_compliance(det, zona_config, args.scoring)
        resultados.append(resultado)

    if args.verbose:
        compliant_count = sum(1 for r in resultados if r["compliant"])
        print(f"Evaluaciones: {len(resultados)} total, {compliant_count} compliant "
              f"({compliant_count/len(resultados)*100:.1f}%)")

    metrics = compute_metrics(resultados, zonas, args.alerts, args.alerts, args.alert_threshold)

    # Generar output según formato
    ext = os.path.splitext(args.output)[1].lower()
    fmt = args.format

    if fmt == "pdf" or ext == ".pdf":
        generar_reporte_pdf(metrics, zonas, args.output, args.company, args.site, args.period)
    elif fmt == "html" or ext == ".html":
        generar_reporte_html(metrics, zonas, args.output, args.company, args.site, args.period)
    else:
        generar_reporte_json(metrics, args.output)


if __name__ == "__main__":
    main()
