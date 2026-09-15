"""
Precalienta la cache de PostgreSQL (shared_buffers) para las tablas
particionadas por anio/periodo que usa el Dashboard de Procedimientos
(dashboard_proc.py), para que la primera busqueda de un centro/mes no
pague el costo de leer todo desde disco.

Por que existe: dw_proc_2026_01, dw_lab_2026_01, etc. son particiones que
casi no se consultan hasta que alguien busca ese mes puntual. La primera
consulta sobre una particion "fria" hace miles de lecturas de disco
(shared_buffers read) y puede tardar 50-70s; una vez que los bloques
quedan en cache, la misma consulta baja a <1s (ver EXPLAIN ANALYZE:
Buffers shared hit vs read).

IMPORTANTE sobre --centro all: precalentar TODOS los centros con datos
reales significa leer casi toda la tabla igual (en enero 2026, 395 de 677
centros "activos" tienen filas en dw_proc). Eso es costo de I/O real que
no se puede evitar con una query mas lista - dw_lab_2026_01 solo tiene
24.3M de filas y puede tardar minutos la primera vez. Lo que SI evitamos:
1) perder tiempo en centros sin ningun dato (se descubren los centros
   reales contra dw_proc, no se recorren los 677/715 codigos a ciegas), y
2) el problema de count(*) sin filtro que dejo parallel workers huerfanos
   corriendo 28+ min server-side la vez que se corto el cliente a mitad
   de camino (ver dw-count-sin-filtro-cuelga.md) - por eso este script NO
   se debe interrumpir a la mitad; dejarlo terminar o subir --timeout.

No necesita CREATE ni la extension pg_prewarm, por eso corre bien con
app_user (ver dw-app-user-sin-create.md). Corre como app_user, igual que
refresh_mvs.py. Programar:
  - Despues de cada carga/ETL que agrega un mes nuevo al DW (usar --centro
    all para cubrir todos los centros con datos ese mes).
  - Y/o diario contra el mes en curso (por si la cache se vacia por
    memory pressure de otras consultas).

Uso:
    python prewarm_dw.py                              # centro 001, mes actual
    python prewarm_dw.py --centro 003
    python prewarm_dw.py --centro 001 003 --periodo 2026 09
    python prewarm_dw.py --centro all --periodo 2026 09       # todos los centros con datos ese mes
    python prewarm_dw.py --centro all --periodo all --anio 2025 2026 --timeout 1800
        # todos los centros, los 12 meses de cada anio listado (tablas que no
        # existen todavia se saltan solas). Con 12-24 periodos esto puede
        # tardar 30-60 min (dw_lab domina el tiempo) - correrlo de fondo/de
        # noche, nunca mientras alguien espera una busqueda.
    python prewarm_dw.py --tabla lab --centro all --periodo all --timeout 1800
        # solo dw_lab (la mas pesada), todos los centros, todos los meses del anio actual
    python prewarm_dw.py --tabla lab --centro all --periodo 2026 02 --parallel 6 --timeout 1800
        # igual, pero dividiendo los centros en 6 conexiones simultaneas -
        # dw_lab_2026_02 no alcanzaba a terminar en 900s con una sola
        # conexion; en paralelo el disco puede atender varias lecturas a la
        # vez en vez de una detras de otra. Empezar con 4-8 y subir si el
        # disco/CPU del servidor lo aguanta (mirar carga con otros usuarios).
"""
import argparse
import concurrent.futures
import os
import sys
import time
from datetime import date

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2 import errors as pg_errors

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extensions import validate_anio_periodo

SCHEMA = "dssge"
DEFAULT_CENTROS = ["001"]
DEFAULT_TIMEOUT_S = 300  # corte de seguridad; subir con --timeout para --centro all en tablas grandes
DEFAULT_PARALLEL = 1  # conexiones simultaneas para --tabla; 1 = comportamiento serial original

TABLAS = {
    "cq": "dwe_centro_quirurgico_{anio}_{periodo}",
    "proc": "dw_proc_{anio}_{periodo}",
    "proc_eme": "dw_proc_eme_{anio}_{periodo}",
    "proc_hos": "dw_proc_hos_{anio}_{periodo}",
    "lab": "dw_lab_{anio}_{periodo}",
}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--centro", nargs="+", default=DEFAULT_CENTROS,
                         help=f"Codigos de centro, o 'all' para descubrir todos los que "
                              f"tienen datos ese periodo (default: {DEFAULT_CENTROS})")
    parser.add_argument("--periodo", nargs="+", default=None,
                         help="Pares anio periodo (ej: 2026 08 2026 09), o 'all' para "
                              "recorrer los 12 meses de cada --anio (default: mes actual)")
    parser.add_argument("--anio", nargs="+", default=None,
                         help="Anios a usar junto con --periodo all (default: anio actual)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S,
                         help=f"Limite de seguridad por consulta, en segundos (default: {DEFAULT_TIMEOUT_S})")
    parser.add_argument("--tabla", nargs="+", choices=list(TABLAS.keys()), default=None,
                         help=f"Tablas a precalentar: {list(TABLAS.keys())} (default: todas)")
    parser.add_argument("--parallel", type=int, default=DEFAULT_PARALLEL,
                         help=f"Conexiones simultaneas al dividir los centros de cada tabla "
                              f"(default: {DEFAULT_PARALLEL}, sin paralelismo)")
    args = parser.parse_args()

    if args.periodo is None:
        hoy = date.today()
        periodos = [(str(hoy.year), f"{hoy.month:02d}")]
    elif args.periodo == ["all"]:
        anios = args.anio or [str(date.today().year)]
        periodos = [
            (validate_anio_periodo(anio, f"{mes:02d}"))
            for anio in anios
            for mes in range(1, 13)
        ]
    else:
        if len(args.periodo) % 2 != 0:
            parser.error("--periodo espera pares anio periodo, ej: 2026 08 2026 09, o 'all'")
        periodos = [
            validate_anio_periodo(args.periodo[i], args.periodo[i + 1])
            for i in range(0, len(args.periodo), 2)
        ]
    tablas = [TABLAS[k] for k in (args.tabla or TABLAS.keys())]
    return args.centro, periodos, args.timeout, tablas, args.parallel


def descubrir_centros(conn, cur, anio, periodo):
    """Centros con datos reales ese periodo (evita perder tiempo en codigos sin datos)."""
    tabla = f"dw_proc_{anio}_{periodo}"
    t0 = time.time()
    try:
        cur.execute(f"SELECT DISTINCT cod_centro FROM {SCHEMA}.{tabla}")
        centros = [r[0] for r in cur.fetchall()]
        print(f"  (descubiertos {len(centros)} centros con datos en {tabla}, {time.time()-t0:.2f}s)")
        return centros
    except (pg_errors.UndefinedTable, pg_errors.UndefinedColumn):
        conn.rollback()
        print(f"  {tabla} no existe todavia, no se puede descubrir centros para este periodo.")
        return []
    except pg_errors.QueryCanceled:
        conn.rollback()
        print(f"  [--timeout {time.time()-t0:.0f}s--] {tabla}: se supero el limite, se salta este periodo")
        return []


def _contar_chunk(uri, timeout_s, tabla, chunk):
    conn = psycopg2.connect(uri)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"SET statement_timeout = {timeout_s * 1000}")
    t0 = time.time()
    try:
        cur.execute(
            f"SELECT count(*) FROM {SCHEMA}.{tabla} WHERE cod_centro = ANY(%s)",
            (chunk,),
        )
        return (cur.fetchone()[0], time.time() - t0, None)
    except (pg_errors.UndefinedTable, pg_errors.UndefinedColumn) as exc:
        return (0, time.time() - t0, "undefined")
    except pg_errors.QueryCanceled:
        return (0, time.time() - t0, "timeout")
    finally:
        conn.close()


def prewarm_tabla(conn, cur, uri, timeout_s, tabla, centros, parallel):
    t0 = time.time()

    if parallel <= 1 or len(centros) <= 1:
        try:
            cur.execute(
                f"SELECT count(*) FROM {SCHEMA}.{tabla} WHERE cod_centro = ANY(%s)",
                (centros,),
            )
            total = cur.fetchone()[0]
            print(f"  [{time.time()-t0:6.2f}s] {tabla}: {total} filas ({len(centros)} centros)")
        except (pg_errors.UndefinedTable, pg_errors.UndefinedColumn) as exc:
            conn.rollback()
            print(f"  [--skip--] {tabla}: {exc.pgerror.strip() if exc.pgerror else exc}")
        except pg_errors.QueryCanceled:
            conn.rollback()
            print(f"  [--timeout tras {time.time()-t0:.0f}s--] {tabla}: se salta este mes")
        return

    n = min(parallel, len(centros))
    chunks = [centros[i::n] for i in range(n)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as ex:
        resultados = list(ex.map(lambda c: _contar_chunk(uri, timeout_s, tabla, c), chunks))

    total = sum(r[0] for r in resultados)
    errores = {r[2] for r in resultados if r[2]}
    elapsed = time.time() - t0
    if errores == {"undefined"} and total == 0:
        print(f"  [--skip--] {tabla}: no existe")
    else:
        extra = f" (con errores parciales: {sorted(errores)})" if errores else ""
        print(f"  [{elapsed:6.2f}s] {tabla}: {total} filas ({len(centros)} centros, "
              f"{n} conexiones paralelas){extra}")


def main():
    centros_arg, periodos, timeout_s, tablas, parallel = parse_args()
    uri = os.environ["DW_DATABASE_URI"].replace("postgresql+psycopg2://", "postgresql://")
    conn = psycopg2.connect(uri)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"SET statement_timeout = {timeout_s * 1000}")

    t_inicio = time.time()
    for i, (anio, periodo) in enumerate(periodos, 1):
        print(f"\n== Periodo {anio}-{periodo} ({i}/{len(periodos)}) ==")
        if centros_arg == ["all"]:
            centros = descubrir_centros(conn, cur, anio, periodo)
            if not centros:
                continue
        else:
            centros = centros_arg

        for plantilla in tablas:
            tabla = plantilla.format(anio=anio, periodo=periodo)
            prewarm_tabla(conn, cur, uri, timeout_s, tabla, centros, parallel)

    conn.close()
    print(f"\nPrecalentamiento completo. Total: {time.time()-t_inicio:.1f}s para {len(periodos)} periodo(s).")


if __name__ == "__main__":
    main()
