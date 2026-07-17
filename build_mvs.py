"""
Construccion de vistas materializadas para el Modulo Ejecutivo de Patologias.
Se ejecuta UNA vez con credenciales de administrador (superusuario) del DW.
Las MV quedan con OWNER = app_user para que la app pueda refrescarlas en runtime.

Uso (PowerShell):
    $env:DW_ADMIN_URI="postgresql://postgres:PASSWORD@10.0.29.117:5433/DW_ESTADISTICA"
    python build_mvs.py

Refresco posterior: refresh_mvs.py (corre como app_user).
"""
import os
import time
import psycopg2

ADMIN_URI = os.environ.get('DW_ADMIN_URI')
if not ADMIN_URI:
    raise SystemExit("Falta la variable de entorno DW_ADMIN_URI con la credencial de administrador.")

APP_ROLE = 'app_user'
SCHEMA = 'dssge'

# --- Expresiones reutilizables (se calculan una vez en mv_ejec_base) ---
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
SELECT
    l.doc_paciente,
    l.anio_busqueda                              AS anio,
    l.tipo_busqueda,
    COALESCE(p.patologia, 'SIN PATOLOGIA')       AS patologia,
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
LEFT JOIN dwsge.sgss_cmcas10 c ON c.cenasicod = l.cod_centro AND c.oricenasicod = l.cod_oricentro
LEFT JOIN dwsge.sgss_cmras10 r ON r.redasiscod = c.redasiscod
LEFT JOIN dwsge.sgss_cmsho10 s ON s.servhoscod = l.cod_servicio
LEFT JOIN dwsge.sgss_cbtid10 td ON td.tipodiagcod = l.cod_tipodiag
LEFT JOIN dwsge.sgss_cmdia10 d ON d.diagcod = l.cod_diagnostico
LEFT JOIN dwsge.mt_patologia p ON p.tipo_busqueda = l.tipo_busqueda
"""

# Rollups para la Tab 1 (analitica por patologia). GROUPING SETS agrega la fila
# 'TODOS' los anios con COUNT(DISTINCT) EXACTO (no es la suma de los anios).
ROLLUPS = {
    "mv_ejec_pat_resumen": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_resumen AS
        SELECT COALESCE(patologia, 'TOTAL GENERAL') AS patologia,
               COALESCE(anio, 'TODOS')              AS anio,
               COUNT(DISTINCT doc_paciente)         AS pacientes,
               COUNT(*)                             AS registros
        FROM dssge.mv_ejec_base
        -- (pat,anio)=celda; (pat)=todos los anios; (anio)=TOTAL GENERAL por anio; ()=total absoluto
        -- Cada COUNT(DISTINCT) es exacto para su nivel (no es la suma de los inferiores).
        -- TOTAL GENERAL incluye a los pacientes con SIN PATOLOGIA (universo completo de la tabla base).
        GROUP BY GROUPING SETS ((patologia, anio), (patologia), (anio), ())
        UNION ALL
        -- TOTAL CATALOGADO: mismo total pero excluyendo SIN PATOLOGIA, para el KPI
        -- "pacientes con patologia catalogada" (no es TOTAL GENERAL menos SIN_PATOLOGIA,
        -- porque un paciente puede tener filas en ambos grupos; se calcula aparte y exacto).
        SELECT 'TOTAL CATALOGADO' AS patologia,
               COALESCE(anio, 'TODOS') AS anio,
               COUNT(DISTINCT doc_paciente) AS pacientes,
               COUNT(*) AS registros
        FROM dssge.mv_ejec_base
        WHERE patologia <> 'SIN PATOLOGIA'
        GROUP BY GROUPING SETS ((anio), ())
    """,
    "mv_ejec_pat_area": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_area AS
        SELECT patologia,
               COALESCE(anio, 'TODOS')            AS anio,
               area,
               COUNT(DISTINCT doc_paciente)       AS pacientes
        FROM dssge.mv_ejec_base
        GROUP BY GROUPING SETS ((patologia, anio, area), (patologia, area))
    """,
    # Filtrable por anio/red/centro (ademas de patologia) para la seccion
    # "Detalle por patologia". CUBE(anio,red,centro) genera las 8 combinaciones
    # (especifico/TODOS en cada una de las 3 dimensiones) por patologia+servicio,
    # asi cualquier combinacion de filtros que arme la UI ya esta precalculada.
    "mv_ejec_pat_servicio": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_servicio AS
        SELECT patologia,
               cod_servicio,
               servhosdes,
               COALESCE(anio, 'TODOS')              AS anio,
               COALESCE(redasiscod, 'TODAS')        AS redasiscod,
               COALESCE(cod_centro, 'TODOS')         AS cod_centro,
               COUNT(DISTINCT doc_paciente)         AS pacientes
        FROM dssge.mv_ejec_base
        WHERE servhosdes IS NOT NULL
        GROUP BY patologia, cod_servicio, servhosdes, CUBE(anio, redasiscod, cod_centro)
    """,
    "mv_ejec_pat_sexo_edad": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_sexo_edad AS
        SELECT patologia,
               sexo,
               grupo_edad,
               COALESCE(anio, 'TODOS')              AS anio,
               COALESCE(redasiscod, 'TODAS')        AS redasiscod,
               COALESCE(cod_centro, 'TODOS')         AS cod_centro,
               COUNT(DISTINCT doc_paciente)         AS pacientes
        FROM dssge.mv_ejec_base
        GROUP BY patologia, sexo, grupo_edad, CUBE(anio, redasiscod, cod_centro)
    """,
    # KPIs (pacientes/registros) de la seccion "Detalle por patologia", filtrable
    # por anio/red/centro. Distinto de mv_ejec_pat_resumen (que sirve la Vista
    # comparativa y NO se debe filtrar por red/centro).
    "mv_ejec_pat_detalle": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_detalle AS
        SELECT patologia,
               COALESCE(anio, 'TODOS')              AS anio,
               COALESCE(redasiscod, 'TODAS')        AS redasiscod,
               COALESCE(cod_centro, 'TODOS')         AS cod_centro,
               COUNT(DISTINCT doc_paciente)         AS pacientes,
               COUNT(*)                             AS registros
        FROM dssge.mv_ejec_base
        GROUP BY patologia, CUBE(anio, redasiscod, cod_centro)
    """,
    "mv_ejec_pat_red": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_red AS
        SELECT patologia,
               COALESCE(anio, 'TODOS')            AS anio,
               redasiscod,
               redasisdes,
               COUNT(DISTINCT doc_paciente)       AS pacientes
        FROM dssge.mv_ejec_base
        GROUP BY GROUPING SETS ((patologia, anio, redasiscod, redasisdes),
                                (patologia, redasiscod, redasisdes))
    """,
    # Jerarquia Red -> Centro. Misma forma que mv_ejec_pat_red pero un nivel
    # mas fino (cod_centro), usada para el drill-down del tablero comparativo.
    "mv_ejec_pat_centro": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_pat_centro AS
        SELECT patologia,
               COALESCE(anio, 'TODOS')            AS anio,
               redasiscod,
               redasisdes,
               cod_centro,
               cenasides,
               COUNT(DISTINCT doc_paciente)       AS pacientes
        FROM dssge.mv_ejec_base
        GROUP BY GROUPING SETS ((patologia, anio, redasiscod, redasisdes, cod_centro, cenasides),
                                (patologia, redasiscod, redasisdes, cod_centro, cenasides))
    """,
    # Matriz de comorbilidad: cuantos pacientes con patologia_a tambien tienen
    # patologia_b (todo el historico, sin filtro de anio). Diagonal = total de
    # la patologia (sirve de chequeo cruzado contra mv_ejec_pat_resumen).
    "mv_ejec_comorbilidad": """
        CREATE MATERIALIZED VIEW dssge.mv_ejec_comorbilidad AS
        WITH pac_pat AS (
            SELECT DISTINCT doc_paciente, patologia
            FROM dssge.mv_ejec_base
            WHERE patologia <> 'SIN PATOLOGIA'
        )
        SELECT a.patologia AS patologia_a,
               b.patologia AS patologia_b,
               COUNT(DISTINCT a.doc_paciente) AS pacientes
        FROM pac_pat a
        JOIN pac_pat b ON a.doc_paciente = b.doc_paciente
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
               COUNT(DISTINCT doc_paciente)         AS pacientes,
               COUNT(*)                             AS registros
        FROM dssge.mv_ejec_base
        GROUP BY patologia, cod_diagnostico, diagdes, cod_tipodiag, tipodiagnom,
                 CUBE(anio, redasiscod, cod_centro)
    """,
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

    print(f"4) Transfiriendo OWNER a {APP_ROLE} (para REFRESH en runtime)...")
    for mv in ALL_MVS:
        cur.execute(f"ALTER MATERIALIZED VIEW {SCHEMA}.{mv} OWNER TO {APP_ROLE}")

    print("\n5) Conteos:")
    for mv in ALL_MVS:
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{mv}")
        print(f"  {mv:26s} {cur.fetchone()[0]:>12,} filas")

    conn.close()
    print("\nListo. MVs creadas en el esquema dssge y propiedad de app_user.")


if __name__ == "__main__":
    main()
