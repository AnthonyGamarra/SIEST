"""
Construye las vistas materializadas del Reporteador self-service (pivot),
solo para el anio en curso (2026).

Por que solo 2026: dwsge.dwe_consulta_externa_homologacion es una tabla
particionada por LIST (anio); filtrar WHERE anio = '2026' poda a la
particion de ese anio (no escanea el historico completo). El anio en curso
cambia seguido (se recarga con cada ETL), asi que conviene tenerlo en MVs
separadas del historico 2019-2025 (a construir despues, una sola vez, sin
necesidad de refrescarlo tan seguido). Ver conversacion de diseno: cada
REFRESH MATERIALIZED VIEW recalcula todo desde cero, no es incremental, asi
que separar "anio en curso" de "historico cerrado" es lo que mantiene el
refresh mensual barato.

Requiere superusuario (app_user no tiene CREATE, ver [[dw-app-user-sin-create]]).
Se corre 1 vez (o cada vez que se agregue/cambie un rollup) con
$env:DW_ADMIN_URI = uri de postgres. Deja las MV con OWNER=app_user para que
refresh_mvs_diag.py pueda refrescarlas en runtime sin credenciales de admin.
"""
import os
import time
import psycopg2

ADMIN_URI = os.environ.get('DW_ADMIN_URI')
if not ADMIN_URI:
    raise SystemExit("Falta la variable de entorno DW_ADMIN_URI con la credencial de administrador.")

APP_ROLE = 'app_user'
SCHEMA = 'dssge'
ANIO_ACTUAL = '2026'

# anio_edad es varchar en dwe_consulta_externa_homologacion, igual que en
# mtd_lista_unica_pacientes: mismo patron de bucketing que EDAD_EXPR en
# build_mvs.py (modulo ejecutivo de patologias).
EDAD_EXPR = r"""
    CASE
        WHEN ce.anio_edad ~ '^[0-9]+$' THEN
            CASE
                WHEN ce.anio_edad::int < 12  THEN '0-11'
                WHEN ce.anio_edad::int < 18  THEN '12-17'
                WHEN ce.anio_edad::int < 30  THEN '18-29'
                WHEN ce.anio_edad::int < 45  THEN '30-44'
                WHEN ce.anio_edad::int < 60  THEN '45-59'
                WHEN ce.anio_edad::int < 150 THEN '60+'
                ELSE 'SIN DATO'
            END
        ELSE 'SIN DATO'
    END
"""

BASE_SQL = f"""
CREATE MATERIALIZED VIEW {SCHEMA}.mv_diag_{ANIO_ACTUAL}_base AS
-- Mismos joins que report_union_query_template en dashboard_diag.py, pero
-- apuntando al padre particionado (no a la tabla de un mes especifico) y
-- acotado a anio = '{ANIO_ACTUAL}' via partition pruning.
SELECT
    ce.cod_oricentro,
    ce.cod_centro,
    ca.cenasides,
    ca.redasiscod,
    r.redasisdes,
    ce.periodo,
    ce.anio,
    v.cod_variable,
    v.variable,
    ce.cod_servicio,
    c.servhosdes                                 AS servicio,
    ce.cod_actividad,
    am.actdes                                     AS actividad,
    ce.cod_subactividad,
    a.actespnom                                   AS subactividad,
    ce.dni_medico,
    ce.acto_med,
    ce.cod_tipdoc_paciente,
    ce.doc_paciente,
    ce.anio_edad,
    {EDAD_EXPR}                                   AS grupo_edad,
    ce.sexo,
    ce.fecha_atencion,
    ce.cod_diag,
    d.diagdes,
    d.edxcapdes                                   AS capitulo
FROM dwsge.dwe_consulta_externa_homologacion ce
LEFT JOIN dwsge.sgss_cmdia10_chapter d ON ce.cod_diag = d.diagcod
LEFT JOIN dwsge.sgss_cmsho10 AS c ON ce.cod_servicio = c.servhoscod
LEFT JOIN dwsge.sgss_cmcas10 AS ca ON ce.cod_oricentro = ca.oricenasicod AND ce.cod_centro = ca.cenasicod
LEFT JOIN dwsge.sgss_cmace10 AS a ON ce.cod_actividad = a.actcod AND ce.cod_subactividad = a.actespcod
LEFT JOIN dwsge.sgss_cmact10 AS am ON ce.cod_actividad = am.actcod
LEFT JOIN dwsge.sgss_cmras10 r ON ca.redasiscod = r.redasiscod
LEFT JOIN dwsge.dim_variable v ON v.cod_variable = ce.cod_variable
WHERE ce.anio = '{ANIO_ACTUAL}' AND ce.clasificacion IN (2,4,6)
"""

METRICS = """
       COUNT(*)                                             AS registros,
       COUNT(DISTINCT (cod_tipdoc_paciente, doc_paciente))   AS pacientes
"""

# --- Rollups de 1 dimension: (dim[, desc], periodo), (dim[, desc]), (periodo), () ---
# Cubre "total del anio por dimension" y "evolucion mensual por dimension"
# con un solo objeto, sin pagar el costo de un CUBE completo.

SINGLE_DIM_ROLLUPS = {
    "mv_diag_2026_servicio": {
        "cols": "cod_servicio, servicio",
        "sets": "(cod_servicio, servicio, periodo), (cod_servicio, servicio), (periodo), ()",
    },
    "mv_diag_2026_red": {
        "cols": "redasiscod, redasisdes",
        "sets": "(redasiscod, redasisdes, periodo), (redasiscod, redasisdes), (periodo), ()",
    },
    "mv_diag_2026_centro": {
        "cols": "cod_centro, cenasides",
        "sets": "(cod_centro, cenasides, periodo), (cod_centro, cenasides), (periodo), ()",
    },
    "mv_diag_2026_actividad": {
        "cols": "cod_actividad, actividad",
        "sets": "(cod_actividad, actividad, periodo), (cod_actividad, actividad), (periodo), ()",
    },
    "mv_diag_2026_subactividad": {
        "cols": "cod_subactividad, subactividad",
        "sets": "(cod_subactividad, subactividad, periodo), (cod_subactividad, subactividad), (periodo), ()",
    },
    "mv_diag_2026_variable": {
        "cols": "cod_variable, variable",
        "sets": "(cod_variable, variable, periodo), (cod_variable, variable), (periodo), ()",
    },
    "mv_diag_2026_capitulo": {
        "cols": "capitulo",
        "sets": "(capitulo, periodo), (capitulo), (periodo), ()",
    },
    "mv_diag_2026_sexo": {
        "cols": "sexo",
        "sets": "(sexo, periodo), (sexo), (periodo), ()",
    },
    "mv_diag_2026_edad": {
        "cols": "grupo_edad",
        "sets": "(grupo_edad, periodo), (grupo_edad), (periodo), ()",
    },
}

ROLLUPS = {
    name: f"""
        CREATE MATERIALIZED VIEW {SCHEMA}.{name} AS
        SELECT {spec['cols']},
               COALESCE(periodo, 'TODOS') AS periodo,
               {METRICS}
        FROM {SCHEMA}.mv_diag_{ANIO_ACTUAL}_base
        GROUP BY GROUPING SETS ({spec['sets']})
    """
    for name, spec in SINGLE_DIM_ROLLUPS.items()
}

# --- Cruces de 2 dimensiones: (dim1, dim2, periodo), (dim1, dim2), () ---
# Sin desglose por periodo NI por dimension individual (eso ya lo cubren los
# rollups de 1 dimension de arriba): solo el cruce en si, con y sin mes.

TWO_DIM_ROLLUPS = {
    "mv_diag_2026_servicio_sexo": {
        "cols": "cod_servicio, servicio, sexo",
        "sets": "(cod_servicio, servicio, sexo, periodo), (cod_servicio, servicio, sexo), ()",
    },
    "mv_diag_2026_capitulo_edad": {
        "cols": "capitulo, grupo_edad",
        "sets": "(capitulo, grupo_edad, periodo), (capitulo, grupo_edad), ()",
    },
    "mv_diag_2026_red_servicio": {
        "cols": "redasiscod, redasisdes, cod_servicio, servicio",
        "sets": "(redasiscod, redasisdes, cod_servicio, servicio, periodo), (redasiscod, redasisdes, cod_servicio, servicio), ()",
    },
}

ROLLUPS.update({
    name: f"""
        CREATE MATERIALIZED VIEW {SCHEMA}.{name} AS
        SELECT {spec['cols']},
               COALESCE(periodo, 'TODOS') AS periodo,
               {METRICS}
        FROM {SCHEMA}.mv_diag_{ANIO_ACTUAL}_base
        GROUP BY GROUPING SETS ({spec['sets']})
    """
    for name, spec in TWO_DIM_ROLLUPS.items()
})

# Indice de filtro por periodo en cada rollup (todas lo tienen como columna).
FILTER_INDEXES = {name: "periodo" for name in ROLLUPS}

ALL_MVS = [f"mv_diag_{ANIO_ACTUAL}_base"] + list(ROLLUPS.keys())


def run(cur, label, sql):
    t = time.time()
    cur.execute(sql)
    print(f"  [{time.time()-t:6.1f}s] {label}")


def main():
    conn = psycopg2.connect(ADMIN_URI)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT current_user")
    print("Conectado como:", cur.fetchone()[0])

    print("\n1) Limpieza (DROP IF EXISTS)...")
    for mv in reversed(ALL_MVS):
        cur.execute(f"DROP MATERIALIZED VIEW IF EXISTS {SCHEMA}.{mv} CASCADE")

    print(f"2) Construyendo mv_diag_{ANIO_ACTUAL}_base (particion {ANIO_ACTUAL}, ~20M filas, 7 joins)...")
    run(cur, f"mv_diag_{ANIO_ACTUAL}_base", BASE_SQL)
    run(cur, "index periodo", f"CREATE INDEX ix_diag_{ANIO_ACTUAL}_base_periodo ON {SCHEMA}.mv_diag_{ANIO_ACTUAL}_base (periodo)")
    run(cur, "index doc_paciente", f"CREATE INDEX ix_diag_{ANIO_ACTUAL}_base_doc ON {SCHEMA}.mv_diag_{ANIO_ACTUAL}_base (doc_paciente)")

    print("3) Construyendo rollups (1 dimension + cruces de 2)...")
    for name, sql in ROLLUPS.items():
        run(cur, name, sql)

    print("4) Creando indices de filtro (periodo) en cada rollup...")
    for mv, cols in FILTER_INDEXES.items():
        run(cur, f"index filtro {mv}", f"CREATE INDEX ix_{mv}_filtro ON {SCHEMA}.{mv} ({cols})")

    print(f"5) Transfiriendo OWNER a {APP_ROLE} (para REFRESH en runtime)...")
    for mv in ALL_MVS:
        cur.execute(f"ALTER MATERIALIZED VIEW {SCHEMA}.{mv} OWNER TO {APP_ROLE}")

    print("\n6) Conteos:")
    for mv in ALL_MVS:
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{mv}")
        print(f"  {mv:32s} {cur.fetchone()[0]:>12,} filas")

    conn.close()
    print(f"\nListo. MVs de {ANIO_ACTUAL} creadas en el esquema dssge y propiedad de app_user.")


if __name__ == "__main__":
    main()
