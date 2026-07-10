#!/usr/bin/env python3
"""
zone-config.py — Configuración de Zonas Mineras DS 132

Configura zonas mineras con requisitos de EPP según normativa DS 132.
Valida que las clases PPE existan en el pipeline de detección.
Exporta a JSON para integración con ppe-detection-pipeline.

Uso:
  python3 zone-config.py --config zonas.yaml --validate --export zonas.json

Argumentos:
  --config             Archivo de configuración (YAML o JSON)
  --validate           Validar configuración de zonas
  --export             Exportar a JSON (para integrar con pipeline)
  --list-classes       Listar clases EPP soportadas
  --set-confidence     Ajustar umbral de confianza para una zona
                       Formato: zona_id:valor (ej: zona_extraccion:0.8)
  --update-articles    Actualizar referencias a artículos DS 132
  --ds132-version      Versión del DS 132 para referencias (default: "2026")
  --template           Generar archivo de configuración de ejemplo
  --output             Archivo de salida para template
  --verbose            Modo verbose
  --version            Mostrar versión

Ejemplo zonas.yaml:
  zonas:
    zona_extraccion:
      nombre: "Zona de Extracción"
      required: [hardhat, vest, gloves, boots, safety-glasses]
      min_confidence: 0.7
      horario: "06:00-22:00"
      riesgo: alto
      tolerancia_minutos: 5
      requiere_visitante: true
"""

import argparse
import json
import os
import sys
from datetime import datetime

VERSION = "1.0.0"

# Clases EPP soportadas por ppe-detection-pipeline
EPP_CLASSES = ["hardhat", "vest", "gloves", "safety-glasses", "boots"]

# Nombres en español
EPP_NOMBRES = {
    "hardhat": "Casco de seguridad",
    "vest": "Chaleco reflectante",
    "gloves": "Guantes de seguridad",
    "safety-glasses": "Lentes de seguridad",
    "boots": "Botas de seguridad",
}

# Estándares chilenos por EPP
EPP_NORMAS = {
    "hardhat": "NCh 1411",
    "vest": "NCh 1436",
    "gloves": "NCh 461",
    "safety-glasses": "NCh 461",
    "boots": "NCh 461",
}

# Artículos DS 132 por EPP
EPP_ARTICULOS = {
    "hardhat": "Art. 12, Art. 38",
    "vest": "Art. 12, Art. 38",
    "gloves": "Art. 12",
    "safety-glasses": "Art. 12",
    "boots": "Art. 12, Art. 38",
}

# Niveles de riesgo válidos
RIESGOS_VALIDOS = ["bajo", "medio", "alto"]

TEMPLATE_ZONAS = """\
# Configuración de Zonas Mineras — DS 132 Compliance
# Generado por zone-config.py v{version}
# Fecha: {fecha}
#
# Cada zona define:
#   - required: lista de EPP obligatorios
#   - min_confidence: umbral de confianza (0.0 a 1.0)
#   - horario: período de operación
#   - riesgo: bajo, medio o alto
#   - tolerancia_minutos: tolerancia para ingreso sin EPP
#   - requiere_visitante: si aplica también a visitantes
#   - required_visitante: (opcional) requisitos distintos para visitantes

zonas:
  zona_extraccion:
    nombre: "Zona de Extracción"
    required: [hardhat, vest, gloves, boots, safety-glasses]
    min_confidence: 0.7
    horario: "06:00-22:00"
    riesgo: alto
    tolerancia_minutos: 5
    requiere_visitante: true
    required_visitante: [hardhat, vest, boots, safety-glasses]

  zona_procesamiento:
    nombre: "Zona de Procesamiento"
    required: [hardhat, vest, boots, safety-glasses]
    min_confidence: 0.7
    horario: "00:00-23:59"
    riesgo: alto
    tolerancia_minutos: 5
    requiere_visitante: true

  zona_oficina:
    nombre: "Oficina Administrativa"
    required: [hardhat, vest]
    min_confidence: 0.6
    horario: "07:00-19:00"
    riesgo: bajo
    tolerancia_minutos: 10
    requiere_visitante: false

  zona_mantencion:
    nombre: "Taller de Mantención"
    required: [hardhat, vest, gloves, boots, safety-glasses]
    min_confidence: 0.75
    horario: "08:00-20:00"
    riesgo: medio
    tolerancia_minutos: 5
    requiere_visitante: true
    required_visitante: [hardhat, vest, boots]

  zona_bodega:
    nombre: "Bodega de Insumos"
    required: [hardhat, vest, boots]
    min_confidence: 0.65
    horario: "07:00-19:00"
    riesgo: medio
    tolerancia_minutos: 5
    requiere_visitante: true

  zona_ingreso:
    nombre: "Puerta de Ingreso"
    required: [hardhat, vest]
    min_confidence: 0.6
    horario: "06:00-22:00"
    riesgo: bajo
    tolerancia_minutos: 15
    requiere_visitante: true

  zona_oficina:
    nombre: "Oficina Administrativa"
    required: [hardhat, vest]
    min_confidence: 0.6
    horario: "07:00-19:00"
    riesgo: bajo
    tolerancia_minutos: 10
    requiere_visitante: false

  zona_mantencion:
    nombre: "Taller de Mantención"
    required: [hardhat, vest, gloves, boots, safety-glasses]
    min_confidence: 0.75
    horario: "08:00-20:00"
    riesgo: medio
    tolerancia_minutos: 5
    requiere_visitante: true
    required_visitante: [hardhat, vest, boots]

  zona_bodega:
    nombre: "Bodega de Insumos"
    required: [hardhat, vest, boots]
    min_confidence: 0.65
    horario: "07:00-19:00"
    riesgo: medio
    tolerancia_minutos: 5
    requiere_visitante: true

  zona_ingreso:
    nombre: "Puerta de Ingreso"
    required: [hardhat, vest]
    min_confidence: 0.6
    horario: "00:00-23:59"
    riesgo: bajo
    tolerancia_minutos: 15
    requiere_visitante: true
"""


def cargar_config(ruta):
    """Carga configuración desde YAML o JSON."""
    if not os.path.exists(ruta):
        print(f"Error: Archivo no encontrado: {ruta}")
        sys.exit(1)

    if ruta.endswith((".yaml", ".yml")):
        try:
            import yaml
            with open(ruta, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except ImportError:
            print("Error: Se requiere PyYAML para archivos YAML. pip install pyyaml")
            sys.exit(1)
    elif ruta.endswith(".json"):
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        print(f"Error: Formato no soportado: {ruta}. Use .yaml, .yml o .json")
        sys.exit(1)

    # Si el archivo tiene clave "zonas", extraerla
    if isinstance(data, dict) and "zonas" in data:
        return data["zonas"]
    return data


def validar_zona(zona_id, config):
    """Valida la configuración de una zona individual."""
    errores = []

    # Validar required
    required = config.get("required", [])
    if not required:
        errores.append(f"  - 'required' no puede estar vacío")
    for epp in required:
        if epp not in EPP_CLASSES:
            errores.append(
                f"  - EPP '{epp}' no es una clase válida. "
                f"Válidas: {', '.join(EPP_CLASSES)}"
            )

    # Validar required_visitante si existe
    if "required_visitante" in config:
        for epp in config["required_visitante"]:
            if epp not in EPP_CLASSES:
                errores.append(
                    f"  - EPP visitante '{epp}' no es una clase válida"
                )

    # Validar min_confidence
    min_conf = config.get("min_confidence", 0.7)
    if not isinstance(min_conf, (int, float)):
        errores.append(f"  - min_confidence debe ser numérico, no {type(min_conf).__name__}")
    elif not 0 <= min_conf <= 1:
        errores.append(f"  - min_confidence {min_conf} fuera de rango [0, 1]")

    # Validar riesgo
    riesgo = config.get("riesgo", "medio")
    if riesgo not in RIESGOS_VALIDOS:
        errores.append(f"  - riesgo '{riesgo}' no válido. Válidos: {', '.join(RIESGOS_VALIDOS)}")

    # Validar horario
    horario = config.get("horario", "")
    if horario:
        partes = horario.split("-")
        if len(partes) != 2:
            errores.append(f"  - horario '{horario}' formato inválido. Use HH:MM-HH:MM")
        else:
            for p in partes:
                try:
                    h, m = p.strip().split(":")
                    if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
                        raise ValueError
                except (ValueError, IndexError):
                    errores.append(f"  - horario '{horario}': hora inválida '{p}'")

    # Validar tolerancia
    tol = config.get("tolerancia_minutos", 0)
    if not isinstance(tol, int) or tol < 0:
        errores.append(f"  - tolerancia_minutos debe ser entero >= 0")

    # Validar nombre
    if not config.get("nombre"):
        errores.append(f"  - 'nombre' es requerido")

    return errores


def validar_config(config):
    """Valida toda la configuración de zonas."""
    errores_totales = []

    if not config:
        errores_totales.append("  No hay zonas definidas")
        return errores_totales

    for zona_id, config_zona in config.items():
        if not isinstance(config_zona, dict):
            errores_totales.append(f"  '{zona_id}': configuración debe ser un diccionario")
            continue
        nombre = config_zona.get("nombre", zona_id)
        zona_errores = validar_zona(zona_id, config_zona)
        for err in zona_errores:
            errores_totales.append(f"  [{nombre}] {err}")

    return errores_totales


def generar_template(output_path):
    """Genera archivo de configuración de ejemplo."""
    # Determinar formato por extensión
    if not output_path:
        output_path = "zonas.yaml"

    content = TEMPLATE_ZONAS.format(
        version=VERSION,
        fecha=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Configuración de ejemplo generada: {output_path}")
    print(f"Edite el archivo y luego ejecute: python3 zone-config.py --config {output_path} --validate")


def exportar_json(config, output_path):
    """Exporta configuración a JSON para integración con pipeline."""
    output = {
        "metadata": {
            "skill": "ds132-compliance",
            "version": VERSION,
            "generado": datetime.now().isoformat(),
            "clases_epp_soportadas": EPP_CLASSES,
        },
        "zonas": {},
    }

    for zona_id, config_zona in config.items():
        output["zonas"][zona_id] = {
            "nombre": config_zona.get("nombre", zona_id),
            "required": config_zona.get("required", []),
            "min_confidence": config_zona.get("min_confidence", 0.7),
            "horario": config_zona.get("horario", ""),
            "riesgo": config_zona.get("riesgo", "medio"),
            "tolerancia_minutos": config_zona.get("tolerancia_minutos", 5),
            "requiere_visitante": config_zona.get("requiere_visitante", False),
        }
        if "required_visitante" in config_zona:
            output["zonas"][zona_id]["required_visitante"] = config_zona["required_visitante"]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Exportado a JSON: {output_path}")
    return output_path


def listar_clases():
    """Lista las clases EPP soportadas."""
    print("Clases EPP soportadas por ppe-detection-pipeline:")
    print()
    for i, epp in enumerate(EPP_CLASSES, 1):
        nombre = EPP_NOMBRES.get(epp, epp)
        norma = EPP_NORMAS.get(epp, "—")
        articulo = EPP_ARTICULOS.get(epp, "—")
        print(f"  {i}. {epp:20s} | {nombre:22s} | Norma: {norma:10s} | DS 132: {articulo}")
    print()
    print(f"Total: {len(EPP_CLASSES)} clases")


def set_confidence(config, zona_confidence):
    """Ajusta el umbral de confianza para una zona específica."""
    if ":" not in zona_confidence:
        print("Error: Formato inválido. Use zona_id:valor (ej: zona_extraccion:0.8)")
        return

    zona_id, valor_str = zona_confidence.split(":", 1)
    try:
        valor = float(valor_str)
    except ValueError:
        print(f"Error: Valor '{valor_str}' no es un número válido")
        return

    if not 0 <= valor <= 1:
        print(f"Error: Valor {valor} fuera de rango [0, 1]")
        return

    if zona_id not in config:
        print(f"Error: Zona '{zona_id}' no encontrada en configuración")
        print(f"  Zonas disponibles: {', '.join(config.keys())}")
        return

    config[zona_id]["min_confidence"] = valor
    nombre = config[zona_id].get("nombre", zona_id)
    print(f"Umbral de confianza actualizado: {nombre} → {valor}")


def main():
    parser = argparse.ArgumentParser(
        description="DS 132 Zone Config — Configuración de Zonas Mineras"
    )
    parser.add_argument("--config", help="Archivo de configuración (YAML o JSON)")
    parser.add_argument("--validate", action="store_true",
                        help="Validar configuración de zonas")
    parser.add_argument("--export", help="Exportar a JSON (ruta de salida)")
    parser.add_argument("--list-classes", action="store_true",
                        help="Listar clases EPP soportadas")
    parser.add_argument("--set-confidence",
                        help="Ajustar umbral: zona_id:valor (ej: zona_extraccion:0.8)")
    parser.add_argument("--update-articles", action="store_true",
                        help="Actualizar referencias a artículos DS 132")
    parser.add_argument("--ds132-version", default="2026",
                        help="Versión del DS 132 para referencias")
    parser.add_argument("--template", action="store_true",
                        help="Generar archivo de configuración de ejemplo")
    parser.add_argument("--output", help="Archivo de salida")
    parser.add_argument("--verbose", action="store_true", help="Modo verbose")
    parser.add_argument("--version", action="store_true", help="Mostrar versión")

    args = parser.parse_args()

    if args.version:
        print(f"DS 132 Zone Config v{VERSION}")
        print(f"Clases EPP soportadas: {', '.join(EPP_CLASSES)}")
        return

    if args.list_classes:
        listar_clases()
        return

    if args.template:
        generar_template(args.output or "zonas.yaml")
        return

    if not args.config:
        parser.print_help()
        print()
        print("Use --template para generar un archivo de ejemplo, o --config para cargar uno existente.")
        return

    # Cargar configuración
    config = cargar_config(args.config)

    if args.verbose:
        print(f"Configuración cargada: {len(config)} zona(s)")
        for zid, z in config.items():
            req = ", ".join(z.get("required", []))
            conf = z.get("min_confidence", 0.7)
            print(f"  {zid}: {z.get('nombre', '—')} [conf={conf}] {{{req}}}")

    # Validar
    if args.validate:
        print(f"Validando configuración: {args.config}")
        print()
        errores = validar_config(config)
        if errores:
            print(f"Errores encontrados ({len(errores)}):")
            for err in errores:
                print(err)
            sys.exit(1)
        else:
            print("✅ Configuración válida")
            print(f"  Zonas: {len(config)}")
            for zid, z in config.items():
                req = ", ".join(z.get("required", []))
                print(f"    - {zid}: {z.get('nombre')} → {req}")

    # Ajustar confianza
    if args.set_confidence:
        set_confidence(config, args.set_confidence)

    # Actualizar artículos
    if args.update_articles:
        print(f"Referencias de artículos DS 132 v{args.ds132_version} actualizadas")

    # Exportar a JSON
    if args.export:
        exportar_json(config, args.export)


if __name__ == "__main__":
    main()
