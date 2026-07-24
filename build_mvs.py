import os
import time
import psycopg2

ADMIN_URI = os.environ.get('DW_ADMIN_URI')
if not ADMIN_URI:
    raise SystemExit("Falta la variable de entorno DW_ADMIN_URI con la credencial de administrador.")

APP_ROLE = 'app_user'
SCHEMA = 'dssge'

AREA_EXPR = """
    CASE l.area
        WHEN 'CEXT' THEN 'CONSULTA EXTERNA'
        WHEN 'CQUI' THEN 'CENTRO QUIRURGICO'
        WHEN 'EMER' THEN 'EMERGENCIA'
        WHEN 'HOSP' THEN 'HOSPITALIZACION'
        ELSE 'CONSULTA EXTERNA'          -- NMED pertenece a Consulta Externa
    END
"""

EDAD_EXPR = r"""
    CASE
        WHEN l.anio_edad ~ '^[0-9]+$' THEN
            CASE
                WHEN l.anio_edad::int < 12  THEN '0-11'
                WHEN l.anio_edad::int < 18  THEN '12-17'
                WHEN l.anio_edad::int < 30  THEN '18-29'
                WHEN l.anio_edad::int < 45  THEN '30-44'
                WHEN l.anio_edad::int < 60  THEN '45-59'
                WHEN l.anio_edad::int < 150 THEN '60+'
                ELSE 'SIN DATO'
            END
        ELSE 'SIN DATO'
    END
"""

BASE_SQL = f"""
CREATE MATERIALIZED VIEW {SCHEMA}.mv_ejec_base AS
-- INNER JOIN con mt_patologia: excluye desde la base a los registros sin
-- patologia catalogada (antes quedaban como 'SIN PATOLOGIA'). Ya no hace
-- falta el COALESCE porque el JOIN garantiza que patologia/patron nunca son
-- NULL.
SELECT
    l.cod_tipdoc_paciente,
    l.doc_paciente,
    l.anio_busqueda                              AS anio,
    l.tipo_busqueda,
    p.patologia                                  AS patologia,
    p.patron                                     AS patron,
    {AREA_EXPR}                                  AS area,
    l.cod_oricentro,
    l.cod_centro,
    c.cenasides,
    c.redasiscod,
    r.redasisdes,
    l.cod_servicio,
    s.servhosdes,
    l.cod_tipodiag,
    td.tipodiagnom,
    l.cod_diagnostico,
    d.diagdes,
    l.sexo,
    l.anio_edad,
    {EDAD_EXPR}                                  AS grupo_edad
FROM dssge.mtd_lista_unica_pacientes l
JOIN dwsge.mt_patologia p ON p.tipo_busqueda = l.tipo_busqueda
LEFT JOIN dwsge.sgss_cmcas10 c ON c.cenasicod = l.cod_centro AND c.oricenasicod = l.cod_oricentro
LEFT JOIN dwsge.sgss_cmras10 r ON r.redasiscod = c.redasiscod
LEFT JOIN dwsge.sgss_cmsho10 s ON s.servhoscod = l.cod_servicio
LEFT JOIN dwsge.sgss_cbtid10 td ON td.tipodiagcod = l.cod_tipodiag
LEFT JOIN dwsge.sgss_cmdia10 d ON d.diagcod = l.cod_diagnostico
"""

ROLLUPS = {
    "mv_ejec_pat_resumen": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_resumen AS
        SELECT COALESCE(patologia, 'TOTAL CATALOGADO') AS patologia,
               COALESCE(anio, 'TODOS')                 AS anio,
               COUNT(DISTINCT (cod_tipdoc_paciente, doc_paciente))            AS pacientes,
               COUNT(*)                                AS registros
        FROM dssge.mv_ejec_base
        WHERE patologia <> 'SIN PATOLOGIA'
        -- (pat,anio)=celda; (pat)=todos los anios; (anio)=TOTAL CATALOGADO por anio; ()=total absoluto
        -- Cada COUNT(DISTINCT) es exacto para su nivel (no es la suma de los inferiores).
        -- Excluye SIN PATOLOGIA en todos los niveles (universo = solo patologias catalogadas).
        GROUP BY GROUPING SETS ((patologia, anio), (patologia), (anio), ())
    """,
    "mv_ejec_pat_area": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_area AS
        SELECT patologia,
               COALESCE(anio, 'TODOS')            AS anio,
               area,
               COUNT(DISTINCT (cod_tipdoc_paciente, doc_paciente))       AS pacientes
        FROM dssge.mv_ejec_base
        WHERE patologia <> 'SIN PATOLOGIA'
        GROUP BY GROUPING SETS ((patologia, anio, area), (patologia, area))
    """,

    "mv_ejec_pat_servicio": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_servicio AS
        SELECT patologia,
               cod_servicio,
               servhosdes,
               COALESCE(anio, 'TODOS')              AS anio,
               COALESCE(redasiscod, 'TODAS')        AS redasiscod,
               COALESCE(cod_centro, 'TODOS')         AS cod_centro,
               COALESCE(grupo_edad, 'TODOS')        AS grupo_edad,
               COUNT(DISTINCT (cod_tipdoc_paciente, doc_paciente))         AS pacientes
        FROM dssge.mv_ejec_base
        WHERE servhosdes IS NOT NULL AND patologia <> 'SIN PATOLOGIA'
        GROUP BY patologia, cod_servicio, servhosdes, CUBE(anio, redasiscod, cod_centro, grupo_edad)
    """,

    "mv_ejec_pat_sexo_edad": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_sexo_edad AS
        SELECT patologia,
               COALESCE(sexo, 'TODOS')              AS sexo,
               COALESCE(grupo_edad, 'TODOS')         AS grupo_edad,
               COALESCE(anio, 'TODOS')              AS anio,
               COALESCE(redasiscod, 'TODAS')        AS redasiscod,
               COALESCE(cod_centro, 'TODOS')         AS cod_centro,
               COUNT(DISTINCT (cod_tipdoc_paciente, doc_paciente))         AS pacientes
        FROM dssge.mv_ejec_base
        WHERE patologia <> 'SIN PATOLOGIA'
        GROUP BY patologia, GROUPING SETS ((sexo, grupo_edad), (sexo), (grupo_edad)),
                 CUBE(anio, redasiscod, cod_centro)
    """,

    "mv_ejec_pat_detalle": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_detalle AS
        SELECT patologia,
               COALESCE(anio, 'TODOS')              AS anio,
               COALESCE(redasiscod, 'TODAS')        AS redasiscod,
               COALESCE(cod_centro, 'TODOS')         AS cod_centro,
               COALESCE(grupo_edad, 'TODOS')        AS grupo_edad,
               COUNT(DISTINCT (cod_tipdoc_paciente, doc_paciente))         AS pacientes,
               COUNT(*)                             AS registros
        FROM dssge.mv_ejec_base
        WHERE patologia <> 'SIN PATOLOGIA'
        GROUP BY patologia, CUBE(anio, redasiscod, cod_centro, grupo_edad)
    """,
    "mv_ejec_pat_red": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_red AS
        SELECT patologia,
               COALESCE(anio, 'TODOS')            AS anio,
               redasiscod,
               redasisdes,
               COUNT(DISTINCT (cod_tipdoc_paciente, doc_paciente))       AS pacientes
        FROM dssge.mv_ejec_base
        WHERE patologia <> 'SIN PATOLOGIA'
        GROUP BY GROUPING SETS ((patologia, anio, redasiscod, redasisdes),
                                (patologia, redasiscod, redasisdes))
    """,

    "mv_ejec_pat_centro": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_centro AS
        SELECT patologia,
               COALESCE(anio, 'TODOS')            AS anio,
               redasiscod,
               redasisdes,
               cod_centro,
               cenasides,
               COUNT(DISTINCT (cod_tipdoc_paciente, doc_paciente))       AS pacientes
        FROM dssge.mv_ejec_base
        WHERE patologia <> 'SIN PATOLOGIA'
        GROUP BY GROUPING SETS ((patologia, anio, redasiscod, redasisdes, cod_centro, cenasides),
                                (patologia, redasiscod, redasisdes, cod_centro, cenasides))
    """,

    "mv_ejec_comorbilidad": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_comorbilidad AS
        WITH pac_pat AS (
            SELECT DISTINCT cod_tipdoc_paciente, doc_paciente, patologia
            FROM dssge.mv_ejec_base
            WHERE patologia <> 'SIN PATOLOGIA'
        )
        SELECT a.patologia AS patologia_a,
               b.patologia AS patologia_b,
               COUNT(DISTINCT (a.cod_tipdoc_paciente, a.doc_paciente)) AS pacientes
        FROM pac_pat a
        JOIN pac_pat b ON a.doc_paciente = b.doc_paciente AND a.cod_tipdoc_paciente = b.cod_tipdoc_paciente
        GROUP BY a.patologia, b.patologia
    """,
    "mv_ejec_pat_diag": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_diag AS
        SELECT patologia,
               cod_diagnostico,
               diagdes,
               cod_tipodiag,
               tipodiagnom,
               COALESCE(anio, 'TODOS')              AS anio,
               COALESCE(redasiscod, 'TODAS')        AS redasiscod,
               COALESCE(cod_centro, 'TODOS')         AS cod_centro,
               COALESCE(grupo_edad, 'TODOS')        AS grupo_edad,
               COUNT(DISTINCT (cod_tipdoc_paciente, doc_paciente))         AS pacientes,
               COUNT(*)                             AS registros
        FROM dssge.mv_ejec_base
        WHERE patologia <> 'SIN PATOLOGIA'
        GROUP BY patologia, cod_diagnostico, diagdes, cod_tipodiag, tipodiagnom,
                 CUBE(anio, redasiscod, cod_centro, grupo_edad)
    """,

    # --- Vistas para el treemap de diagnosticos y el Sankey de flujo por
    # area del modulo ejecutivo. Llevan 'anio' (via GROUPING SETS, no CUBE
    # completo: solo 2 conjuntos, no hace falta cruzarlo con nada mas) para
    # que ambos graficos respondan al filtro de Anio de la pestana, igual que
    # el Ranking por red.
    "mv_ejec_pat_diag_servicio": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_diag_servicio AS
        SELECT patologia,
               cod_diagnostico,
               diagdes,
               cod_servicio,
               servhosdes,
               COALESCE(anio, 'TODOS') AS anio,
               COUNT(DISTINCT (cod_tipdoc_paciente, doc_paciente)) AS pacientes
        FROM dssge.mv_ejec_base
        WHERE patologia <> 'SIN PATOLOGIA' AND servhosdes IS NOT NULL
        GROUP BY GROUPING SETS (
            (patologia, cod_diagnostico, diagdes, cod_servicio, servhosdes, anio),
            (patologia, cod_diagnostico, diagdes, cod_servicio, servhosdes)
        )
    """,
    "mv_ejec_pat_area_servicio": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_area_servicio AS
        SELECT patologia,
               area,
               cod_servicio,
               servhosdes,
               COALESCE(anio, 'TODOS') AS anio,
               COUNT(DISTINCT (cod_tipdoc_paciente, doc_paciente)) AS pacientes
        FROM dssge.mv_ejec_base
        WHERE patologia <> 'SIN PATOLOGIA' AND servhosdes IS NOT NULL
        GROUP BY GROUPING SETS (
            (patologia, area, cod_servicio, servhosdes, anio),
            (patologia, area, cod_servicio, servhosdes)
        )
    """,
}

# Subconjunto de ROLLUPS que se puede crear de forma quirurgica (sin DROP ni
# reconstruccion de las demas vistas) porque son nuevas y ninguna otra vista
# depende de ellas. Usado por build_mvs_extra.py.
EXTRA_ROLLUPS = ["mv_ejec_pat_diag_servicio", "mv_ejec_pat_area_servicio"]


FILTER_INDEXES = {
    "mv_ejec_pat_detalle": "patologia, anio, redasiscod, cod_centro, grupo_edad",
    "mv_ejec_pat_servicio": "patologia, anio, redasiscod, cod_centro, grupo_edad",
    "mv_ejec_pat_diag": "patologia, anio, redasiscod, cod_centro, grupo_edad",
}

ALL_MVS = ["mv_ejec_base"] + list(ROLLUPS.keys())


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

    print("2) Construyendo mv_ejec_base (~4.4M filas, 6 joins)...")
    run(cur, "mv_ejec_base", BASE_SQL)
    run(cur, "index doc_paciente", f"CREATE INDEX ix_ejec_base_doc ON {SCHEMA}.mv_ejec_base (doc_paciente)")
    run(cur, "index patologia/anio", f"CREATE INDEX ix_ejec_base_pat ON {SCHEMA}.mv_ejec_base (patologia, anio)")

    print("3) Construyendo rollups de la Tab 1...")
    for name, sql in ROLLUPS.items():
        run(cur, name, sql)

    print("4) Creando indices de filtro (anio/red/centro/grupo_edad)...")
    for mv, cols in FILTER_INDEXES.items():
        run(cur, f"index filtro {mv}", f"CREATE INDEX ix_{mv}_filtro ON {SCHEMA}.{mv} ({cols})")

    print(f"5) Transfiriendo OWNER a {APP_ROLE} (para REFRESH en runtime)...")
    for mv in ALL_MVS:
        cur.execute(f"ALTER MATERIALIZED VIEW {SCHEMA}.{mv} OWNER TO {APP_ROLE}")

    print("\n6) Conteos:")
    for mv in ALL_MVS:
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{mv}")
        print(f"  {mv:26s} {cur.fetchone()[0]:>12,} filas")

    conn.close()
    print("\nListo. MVs creadas en el esquema dssge y propiedad de app_user.")


if __name__ == "__main__":
    main()
