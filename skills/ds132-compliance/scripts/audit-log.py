#!/usr/bin/env python3
"""
audit-log.py — Log de Auditoría Inmutable DS 132

Registro inviolable de evaluaciones de cumplimiento de EPP para normativa
DS 132. Usa SHA256 encadenado (hash chain) para garantizar inmutabilidad.
Almacena en SQLite con exportación a CSV y JSON.

Uso:
  python3 audit-log.py --input compliance.json --db auditoria.db
  python3 audit-log.py --db auditoria.db --export csv --output auditoria.csv
  python3 audit-log.py --db auditoria.db --verify-chain

Argumentos:
  --input               Archivo JSON con evaluaciones de compliance
  --db                  Ruta a base de datos SQLite
  --export              Formato de exportación: csv | json
  --output              Archivo de salida para exportación
  --delimiter           Delimitador CSV (default: ",")
  --encoding            Encoding CSV (default: "utf-8")
  --no-images           Excluir imágenes de evidencia en exportación
  --multi-site          Soportar múltiples faenas
  --site                Identificador de faena

  Consultas:
  --query-persona       Historial de infracciones por persona
  --query-zona          Historial de compliance por zona
  --query-epp-faltante  Frecuencia de EPP faltante
  --query-reincidencia  Patrones de reincidencia
  --query-horas-criticas Horas del día con más infracciones
  --query-false-positives  Casos dudosos para revisión humana
  --group-by            Agrupar por: turno | zona | persona
  --period              Período en días (ej: 30d, 7d)
  --limit               Límite de resultados

  Mantenimiento:
  --verify-chain        Verificar integridad de la cadena de hash
  --apply-blur          Aplicar blur facial a imágenes almacenadas
  --blur-strength       Intensidad del blur (default: 15)
  --update-db           Actualizar base de datos con cambios

  --verbose             Modo verbose
  --version             Mostrar versión
"""

import argparse
import csv
import hashlib
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta

VERSION = "1.0.0"

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS auditoria_epp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    zona TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    tipo_persona TEXT DEFAULT 'trabajador',
    epp_detectado TEXT NOT NULL,
    epp_requerido TEXT NOT NULL,
    epp_faltante TEXT NOT NULL,
    compliant INTEGER NOT NULL,
    score REAL NOT NULL,
    confianza_promedio REAL DEFAULT 0.0,
    imagen_evidencia TEXT,
    hash_anterior TEXT,
    hash_registro TEXT UNIQUE NOT NULL,
    faena TEXT DEFAULT '',
    turno TEXT DEFAULT '',
    frame_id TEXT DEFAULT '',
    fuente TEXT DEFAULT 'ppe-pipeline',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_auditoria_persona ON auditoria_epp(persona_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_zona ON auditoria_epp(zona);
CREATE INDEX IF NOT EXISTS idx_auditoria_timestamp ON auditoria_epp(timestamp);
CREATE INDEX IF NOT EXISTS idx_auditoria_compliant ON auditoria_epp(compliant);

CREATE TABLE IF NOT EXISTS metadata_auditoria (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO metadata_auditoria (key, value)
VALUES ('version', '{version}');
INSERT OR IGNORE INTO metadata_auditoria (key, value)
VALUES ('created', '{fecha}');
INSERT OR IGNORE INTO metadata_auditoria (key, value)
VALUES ('description', 'Log de auditoría DS 132 — EPP Compliance');
""".format(version=VERSION, fecha=datetime.now().isoformat())


def conectar_db(db_path):
    """Conecta a la base de datos SQLite y crea schema si es necesario."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQLITE)
    conn.commit()
    return conn


def calcular_hash(registro, hash_anterior):
    """Calcula SHA256 de un registro incluyendo el hash anterior."""
    contenido = json.dumps({
        "timestamp": registro.get("timestamp", ""),
        "zona": registro.get("zona", ""),
        "persona_id": registro.get("persona_id", ""),
        "epp_requerido": sorted(registro.get("epp_requerido", [])),
        "epp_faltante": sorted(registro.get("epp_faltante", [])),
        "compliant": registro.get("compliant", False),
        "score": registro.get("score", 0.0),
        "hash_anterior": hash_anterior or "",
    }, sort_keys=True)
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def obtener_ultimo_hash(conn):
    """Obtiene el hash del último registro."""
    cursor = conn.execute(
        "SELECT hash_registro FROM auditoria_epp ORDER BY id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    return row["hash_registro"] if row else None


def insertar_evaluacion(conn, evaluacion):
    """Inserta una evaluación en el log de auditoría con hash chain."""
    hash_anterior = obtener_ultimo_hash(conn)
    hash_registro = calcular_hash(evaluacion, hash_anterior)

    conn.execute(
        """INSERT INTO auditoria_epp
           (timestamp, zona, persona_id, tipo_persona,
            epp_detectado, epp_requerido, epp_faltante,
            compliant, score, confianza_promedio,
            imagen_evidencia, hash_anterior, hash_registro,
            faena, turno, frame_id, fuente)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            evaluacion.get("timestamp", ""),
            evaluacion.get("zona", ""),
            evaluacion.get("persona_id", ""),
            evaluacion.get("tipo_persona", "trabajador"),
            json.dumps(evaluacion.get("epp_presente", []), ensure_ascii=False),
            json.dumps(evaluacion.get("epp_requerido", []), ensure_ascii=False),
            json.dumps(evaluacion.get("epp_faltante", []), ensure_ascii=False),
            1 if evaluacion.get("compliant") else 0,
            evaluacion.get("score", 0.0),
            evaluacion.get("confianza_promedio", 0.0),
            evaluacion.get("imagen_evidencia", ""),
            hash_anterior or "",
            hash_registro,
            evaluacion.get("faena", ""),
            evaluacion.get("turno", ""),
            evaluacion.get("frame_id", ""),
            "ppe-pipeline",
        )
    )
    conn.commit()
    return hash_registro


def procesar_archivo(input_path, db_path, multi_site, site, verbose):
    """Procesa archivo JSON de evaluaciones y las inserta en la DB."""
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalizar: puede ser lista o dict con clave "evaluaciones"
    if isinstance(data, dict):
        evaluaciones = data.get("evaluaciones", data.get("results", data.get("resultados", [])))
        if not evaluaciones and "por_persona" in data:
            # Es un reporte completo, extraer evaluaciones individuales
            print("Advertencia: El archivo parece ser un reporte consolidado, no evaluaciones individuales")
            return 0
    else:
        evaluaciones = data

    if not evaluaciones:
        print("No se encontraron evaluaciones en el archivo")
        return 0

    conn = conectar_db(db_path)
    count = 0

    for ev in evaluaciones:
        if multi_site and site:
            ev["faena"] = site
        hash_reg = insertar_evaluacion(conn, ev)
        count += 1
        if verbose and count % 100 == 0:
            print(f"  Insertadas: {count}")

    conn.close()
    print(f"✅ {count} evaluaciones registradas en {db_path}")
    return count


def exportar_csv(conn, output_path, delimiter, encoding, no_images, verbose):
    """Exporta el log de auditoría a CSV."""
    cursor = conn.execute("SELECT * FROM auditoria_epp ORDER BY id")
    rows = cursor.fetchall()

    if not rows:
        print("No hay registros para exportar")
        return

    columnas = [desc[0] for desc in cursor.description]
    if no_images and "imagen_evidencia" in columnas:
        columnas.remove("imagen_evidencia")

    with open(output_path, "w", newline="", encoding=encoding) as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(columnas)
        for row in rows:
            row_dict = dict(row)
            if no_images:
                row_dict.pop("imagen_evidencia", None)
            writer.writerow([row_dict.get(col, "") for col in columnas])

    print(f"✅ Exportados {len(rows)} registros a {output_path}")


def exportar_json(conn, output_path, no_images, verbose):
    """Exporta el log de auditoría a JSON."""
    cursor = conn.execute("SELECT * FROM auditoria_epp ORDER BY id")
    rows = cursor.fetchall()

    if not rows:
        print("No hay registros para exportar")
        return

    registros = []
    for row in rows:
        d = dict(row)
        if no_images:
            d.pop("imagen_evidencia", None)
        # Parsear JSON strings
        for campo in ["epp_detectado", "epp_requerido", "epp_faltante"]:
            try:
                d[campo] = json.loads(d[campo])
            except (json.JSONDecodeError, TypeError):
                pass
        registros.append(d)

    output = {
        "metadata": {
            "skill": "ds132-compliance",
            "version": VERSION,
            "exportado": datetime.now().isoformat(),
            "total_registros": len(registros),
        },
        "registros": registros,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"✅ Exportados {len(registros)} registros a {output_path}")


def verificar_cadena(conn, verbose):
    """Verifica la integridad de la cadena de hash."""
    cursor = conn.execute(
        "SELECT id, hash_anterior, hash_registro, persona_id, timestamp "
        "FROM auditoria_epp ORDER BY id"
    )
    rows = cursor.fetchall()

    if not rows:
        print("No hay registros en la base de datos")
        return True

    errores = []
    hash_esperado = None

    for row in rows:
        # Verificar que el hash_anterior coincide
        if hash_esperado is not None and row["hash_anterior"] != hash_esperado:
            errores.append(
                f"  Registro #{row['id']}: hash_anterior no coincide. "
                f"Esperado: {hash_esperado[:16]}..., "
                f"Obtenido: {row['hash_anterior'][:16]}..."
            )

        # Reconstruir el dict original usado para calcular el hash
        cursor2 = conn.execute(
            "SELECT * FROM auditoria_epp WHERE id = ?", (row["id"],)
        )
        full_row = dict(cursor2.fetchone())

        # Reconstruir la estructura de datos original que se usó en insertar_evaluacion
        data_original = {
            "timestamp": full_row["timestamp"],
            "zona": full_row["zona"],
            "persona_id": full_row["persona_id"],
            "epp_requerido": json.loads(full_row["epp_requerido"]) if isinstance(full_row["epp_requerido"], str) else full_row["epp_requerido"],
            "epp_faltante": json.loads(full_row["epp_faltante"]) if isinstance(full_row["epp_faltante"], str) else full_row["epp_faltante"],
            "compliant": bool(full_row["compliant"]),
            "score": full_row["score"],
        }

        hash_recalculado = calcular_hash(
            data_original,
            row["hash_anterior"] if row["id"] == 1 else hash_esperado
        )

        if hash_recalculado != row["hash_registro"]:
            errores.append(
                f"  Registro #{row['id']}: hash_registro no coincide. "
                f"Hash almacenado: {row['hash_registro'][:16]}..., "
                f"Recalculado: {hash_recalculado[:16]}..."
            )

        hash_esperado = row["hash_registro"]

    if not errores:
        print(f"✅ Cadena de auditoría íntegra: {len(rows)} registros verificados")
        return True
    else:
        print(f"⚠️  Errores encontrados en la cadena de auditoría:")
        for err in errores:
            print(err)
        return False


def query_persona(conn, persona_id, limit=50):
    """Consulta historial de infracciones por persona."""
    cursor = conn.execute(
        """SELECT id, timestamp, zona, epp_faltante, compliant, score, turno
           FROM auditoria_epp
           WHERE persona_id = ?
           ORDER BY timestamp DESC
           LIMIT ?""",
        (persona_id, limit),
    )
    rows = cursor.fetchall()

    if not rows:
        print(f"No se encontraron registros para persona: {persona_id}")
        return

    total = len(rows)
    no_compliant = sum(1 for r in rows if not r["compliant"])
    compliance = (total - no_compliant) / total * 100 if total else 0

    print(f"Historial de: {persona_id}")
    print(f"  Total registros: {total}")
    print(f"  Infracciones: {no_compliant}")
    print(f"  Compliance: {compliance:.1f}%")
    print()
    print(f"{'ID':>4} {'Fecha':<22} {'Zona':<20} {'EPP Faltante':<30} {'Compliant':<10}")
    print("-" * 90)
    for r in rows:
        faltante = ", ".join(json.loads(r["epp_faltante"])) if r["epp_faltante"] else "—"
        print(f"{r['id']:>4} {r['timestamp']:<22} {r['zona']:<20} {faltante:<30} "
              f"{'✅' if r['compliant'] else '❌'} (score: {r['score']:.2f})")


def query_zona(conn, zona_id, period_days=30, limit=100):
    """Consulta historial de compliance por zona."""
    fecha_limite = (datetime.now() - timedelta(days=period_days)).isoformat()
    cursor = conn.execute(
        """SELECT id, timestamp, persona_id, epp_faltante, compliant, score, turno
           FROM auditoria_epp
           WHERE zona = ? AND timestamp >= ?
           ORDER BY timestamp DESC
           LIMIT ?""",
        (zona_id, fecha_limite, limit),
    )
    rows = cursor.fetchall()

    if not rows:
        print(f"No se encontraron registros para zona: {zona_id}")
        return

    total = len(rows)
    no_compliant = sum(1 for r in rows if not r["compliant"])
    compliance = (total - no_compliant) / total * 100 if total else 0

    print(f"Historial de zona: {zona_id} (últimos {period_days} días)")
    print(f"  Total registros: {total}")
    print(f"  Infracciones: {no_compliant}")
    print(f"  Compliance: {compliance:.1f}%")
    print()
    print(f"{'ID':>4} {'Fecha':<22} {'Persona':<15} {'EPP Faltante':<30} {'Compliant':<10}")
    print("-" * 85)
    for r in rows:
        faltante = ", ".join(json.loads(r["epp_faltante"])) if r["epp_faltante"] else "—"
        print(f"{r['id']:>4} {r['timestamp']:<22} {r['persona_id']:<15} {faltante:<30} "
              f"{'✅' if r['compliant'] else '❌'}")


def query_epp_faltante(conn, group_by=None, limit=20):
    """Consulta frecuencia de EPP faltante, opcionalmente agrupado."""
    if group_by == "turno":
        cursor = conn.execute(
            """SELECT turno, epp_faltante FROM auditoria_epp
               WHERE compliant = 0 AND epp_faltante != '[]'"""
        )
    elif group_by == "zona":
        cursor = conn.execute(
            """SELECT zona, epp_faltante FROM auditoria_epp
               WHERE compliant = 0 AND epp_faltante != '[]'"""
        )
    else:
        cursor = conn.execute(
            """SELECT epp_faltante FROM auditoria_epp
               WHERE compliant = 0 AND epp_faltante != '[]'"""
        )

    rows = cursor.fetchall()
    if not rows:
        print("No hay infracciones registradas")
        return

    conteo = defaultdict(lambda: defaultdict(int))

    for row in rows:
        try:
            faltante = json.loads(row["epp_faltante"])
        except (json.JSONDecodeError, TypeError):
            faltante = []

        if group_by:
            clave = row[group_by] or "sin_turno" if group_by == "turno" else row[group_by] or "sin_zona"
        else:
            clave = "total"

        for epp in faltante:
            if isinstance(epp, dict):
                epp = epp.get("epp", str(epp))
            conteo[clave][epp] += 1

    if group_by:
        print(f"EPP faltante agrupado por {group_by}:")
        print()
        for grupo, epps in sorted(conteo.items()):
            total_epp = sum(epps.values())
            print(f"  {grupo}: ({total_epp} faltas)")
            for epp, count in sorted(epps.items(), key=lambda x: -x[1])[:5]:
                pct = count / total_epp * 100
                print(f"    - {epp:20s}: {count:4d} ({pct:5.1f}%)")
            print()
    else:
        print("EPP faltante — ranking global:")
        print()
        for epp, count in sorted(conteo["total"].items(), key=lambda x: -x[1])[:limit]:
            total = sum(conteo["total"].values())
            pct = count / total * 100 if total else 0
            print(f"  {epp:20s}: {count:4d} ({pct:5.1f}%)")


def query_reincidencia(conn, min_infracciones=3, limit=20):
    """Identifica personas reincidentes en infracciones."""
    cursor = conn.execute(
        """SELECT persona_id, COUNT(*) as total_infracciones,
                  GROUP_CONCAT(DISTINCT epp_faltante) as epps_faltantes,
                  GROUP_CONCAT(DISTINCT zona) as zonas
           FROM auditoria_epp
           WHERE compliant = 0
           GROUP BY persona_id
           HAVING total_infracciones >= ?
           ORDER BY total_infracciones DESC
           LIMIT ?""",
        (min_infracciones, limit),
    )
    rows = cursor.fetchall()

    if not rows:
        print(f"No se encontraron personas con {min_infracciones}+ infracciones")
        return

    print(f"Personas reincidentes ({min_infracciones}+ infracciones):")
    print()
    print(f"{'Persona':<20} {'Infracciones':<14} {'Zonas':<30} {'EPP Faltante Común'}")
    print("-" * 90)
    for r in rows:
        # Obtener EPP más frecuente
        epps = []
        try:
            for epp_str in r["epps_faltantes"].split(","):
                faltante = json.loads(epp_str)
                for f in faltante:
                    if isinstance(f, dict):
                        epps.append(f.get("epp", str(f)))
                    else:
                        epps.append(f)
        except (json.JSONDecodeError, AttributeError):
            pass
        from collections import Counter
        epp_comun = Counter(epps).most_common(1)
        epp_comun_str = epp_comun[0][0] if epp_comun else "—"

        zonas = r["zonas"].replace(",", ", ") if r["zonas"] else "—"
        print(f"{r['persona_id']:<20} {r['total_infracciones']:<14} {zonas:<30} {epp_comun_str}")


def query_horas_criticas(conn, limit=10):
    """Identifica las horas del día con más infracciones."""
    cursor = conn.execute(
        """SELECT SUBSTR(timestamp, 12, 2) as hora, COUNT(*) as infracciones
           FROM auditoria_epp
           WHERE compliant = 0
           GROUP BY hora
           ORDER BY infracciones DESC
           LIMIT ?""",
        (limit,),
    )
    rows = cursor.fetchall()

    if not rows:
        print("No hay infracciones registradas")
        return

    print("Horas críticas del día (más infracciones):")
    print()
    for r in rows:
        barras = "█" * (r["infracciones"] // 5 + 1)
        print(f"  {r['hora']:>2}:00  {barras} {r['infracciones']}")


def query_false_positives(conn, limit=50):
    """Identifica casos dudosos para revisión humana (score entre 0.5 y 0.8)."""
    cursor = conn.execute(
        """SELECT id, timestamp, zona, persona_id, epp_detectado, epp_requerido,
                  epp_faltante, score, imagen_evidencia
           FROM auditoria_epp
           WHERE score BETWEEN 0.5 AND 0.8
           ORDER BY score ASC
           LIMIT ?""",
        (limit,),
    )
    rows = cursor.fetchall()

    if not rows:
        print("No se encontraron casos dudosos")
        return

    print(f"Casos dudosos para revisión humana ({len(rows)} registros, score 0.5–0.8):")
    print()
    print(f"{'ID':>4} {'Fecha':<22} {'Zona':<20} {'Persona':<15} {'Score':<8} {'EPP'}")
    print("-" * 85)
    for r in rows:
        faltante = json.loads(r["epp_faltante"]) if r["epp_faltante"] else []
        faltante_str = ", ".join(f["epp"] if isinstance(f, dict) else str(f) for f in faltante)
        print(f"{r['id']:>4} {r['timestamp']:<22} {r['zona']:<20} {r['persona_id']:<15} "
              f"{r['score']:<8.2f} {faltante_str}")


def main():
    parser = argparse.ArgumentParser(
        description="DS 132 Audit Log — Log de Auditoría Inmutable"
    )
    parser.add_argument("--input", help="Archivo JSON con evaluaciones de compliance")
    parser.add_argument("--db", default="auditoria_ds132.db",
                        help="Base de datos SQLite")
    parser.add_argument("--export", choices=["csv", "json"],
                        help="Formato de exportación")
    parser.add_argument("--output", help="Archivo de salida para exportación")
    parser.add_argument("--delimiter", default=",", help="Delimitador CSV")
    parser.add_argument("--encoding", default="utf-8", help="Encoding CSV")
    parser.add_argument("--no-images", action="store_true",
                        help="Excluir imágenes de evidencia")
    parser.add_argument("--multi-site", action="store_true",
                        help="Soportar múltiples faenas")
    parser.add_argument("--site", help="Identificador de faena")

    # Consultas
    parser.add_argument("--query-persona", help="Historial por persona")
    parser.add_argument("--query-zona", help="Historial por zona")
    parser.add_argument("--query-epp-faltante", action="store_true",
                        help="Frecuencia de EPP faltante")
    parser.add_argument("--query-reincidencia", action="store_true",
                        help="Patrones de reincidencia")
    parser.add_argument("--query-horas-criticas", action="store_true",
                        help="Horas con más infracciones")
    parser.add_argument("--query-false-positives", action="store_true",
                        help="Casos dudosos para revisión")
    parser.add_argument("--group-by", choices=["turno", "zona", "persona"],
                        help="Agrupar resultados")
    parser.add_argument("--period", default="30d", help="Período en días (ej: 30d)")
    parser.add_argument("--limit", type=int, default=50,
                        help="Límite de resultados")

    # Mantenimiento
    parser.add_argument("--verify-chain", action="store_true",
                        help="Verificar cadena de hash")
    parser.add_argument("--apply-blur", action="store_true",
                        help="Aplicar blur facial a imágenes")
    parser.add_argument("--blur-strength", type=int, default=15,
                        help="Intensidad del blur")
    parser.add_argument("--update-db", action="store_true",
                        help="Actualizar DB con cambios")

    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--version", action="store_true")

    args = parser.parse_args()

    if args.version:
        print(f"DS 132 Audit Log v{VERSION}")
        return

    # Modo importación: procesar archivo
    if args.input:
        procesar_archivo(args.input, args.db, args.multi_site, args.site, args.verbose)
        return

    # Conectar a DB existente
    if not os.path.exists(args.db):
        print(f"Error: Base de datos no encontrada: {args.db}")
        print("Use --input para crear la base de datos con evaluaciones.")
        sys.exit(1)

    conn = conectar_db(args.db)

    # Exportación
    if args.export:
        if not args.output:
            args.output = f"auditoria_export.{args.export}"
        if args.export == "csv":
            exportar_csv(conn, args.output, args.delimiter, args.encoding, args.no_images, args.verbose)
        elif args.export == "json":
            exportar_json(conn, args.output, args.no_images, args.verbose)
        conn.close()
        return

    # Verificación de cadena
    if args.verify_chain:
        verificar_cadena(conn, args.verbose)
        conn.close()
        return

    # Consultas
    if args.query_persona:
        query_persona(conn, args.query_persona, args.limit)
    elif args.query_zona:
        dias = int(args.period.rstrip("d")) if args.period.endswith("d") else 30
        query_zona(conn, args.query_zona, dias, args.limit)
    elif args.query_epp_faltante:
        query_epp_faltante(conn, args.group_by, args.limit)
    elif args.query_reincidencia:
        query_reincidencia(conn, 3, args.limit)
    elif args.query_horas_criticas:
        query_horas_criticas(conn, args.limit)
    elif args.query_false_positives:
        query_false_positives(conn, args.limit)
    else:
        # Mostrar resumen si no hay consulta específica
        cursor = conn.execute("SELECT COUNT(*) as total FROM auditoria_epp")
        total = cursor.fetchone()["total"]
        cursor = conn.execute("SELECT COUNT(*) as no_comp FROM auditoria_epp WHERE compliant = 0")
        no_comp = cursor.fetchone()["no_comp"]
        cursor = conn.execute("SELECT COUNT(DISTINCT persona_id) as personas FROM auditoria_epp")
        personas = cursor.fetchone()["personas"]
        cursor = conn.execute("SELECT COUNT(DISTINCT zona) as zonas FROM auditoria_epp")
        zonas = cursor.fetchone()["zonas"]

        print(f"📊 Resumen de Auditoría DS 132")
        print(f"   Base de datos: {args.db}")
        print(f"   Total registros: {total}")
        print(f"   Infracciones: {no_comp} ({(no_comp/total*100) if total else 0:.1f}%)")
        print(f"   Personas: {personas}")
        print(f"   Zonas: {zonas}")
        print()
        print("Consultas disponibles:")
        print("  --query-persona ID        Historial por persona")
        print("  --query-zona ID           Historial por zona")
        print("  --query-epp-faltante      Ranking EPP faltante")
        print("  --query-reincidencia      Personas reincidentes")
        print("  --query-horas-criticas    Horas con más infracciones")
        print("  --query-false-positives   Casos dudosos para revisión")
        print("  --verify-chain            Verificar integridad")
        print("  --export csv|json         Exportar registros")

    conn.close()


if __name__ == "__main__":
    main()
