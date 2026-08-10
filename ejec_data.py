"""
Capa de datos del Modulo Ejecutivo de Patologias (Tab 1 - Analitica), sin
dependencias de Dash. La usa api_ejec.py (endpoints JSON para el frontend
React/Nivo) y puede seguir siendo usada por dashboard_ejec.py sin duplicar SQL.

Replica exactamente los criterios ya validados en dashboard_ejec.py:
- SIN PATOLOGIA excluida en todo el modulo.
- Patologias de alto costo = Raras / Oncologico / Renal.
- Todas las consultas leen de las materialized views dssge.mv_ejec_*.
"""
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from extensions import get_dw_engine

SCHEMA = "dssge"
ANIO_ORDER = ["2019", "2020", "2021", "2022", "2023", "2024"]

GLOBAL_PATOLOGIAS = ["Raras", "Oncologico", "Renal"]
EXCLUDE_COMPARATIVA_SQL = "patologia <> 'SIN PATOLOGIA'"


class EjecDataError(Exception):
    """Error de datos con mensaje ya listo para mostrar al usuario."""


def _pat_label(value):
    return str(value).replace("_", " ").title()


def run_df(sql, params=None):
    """Devuelve un DataFrame o lanza EjecDataError con un mensaje presentable."""
    try:
        engine = get_dw_engine()
        with engine.connect() as conn:
            return pd.read_sql_query(text(sql), conn, params=params or {})
    except SQLAlchemyError as exc:
        msg = str(getattr(exc, "orig", exc))
        if "mv_ejec" in msg and ("no existe" in msg.lower() or "does not exist" in msg.lower()):
            raise EjecDataError(
                "Las vistas materializadas aun no existen. Ejecute una vez "
                "build_mvs.py con credenciales de administrador para crearlas."
            ) from exc
        print(f"[Ejec][API] Error SQL: {exc}")
        raise EjecDataError("Ocurrio un error al consultar la base de datos.") from exc
    except Exception as exc:  # pragma: no cover
        print(f"[Ejec][API] Error: {exc}")
        raise EjecDataError("Ocurrio un error inesperado.") from exc


def get_anio_options():
    try:
        df = run_df(f"SELECT DISTINCT anio FROM {SCHEMA}.mv_ejec_pat_resumen ORDER BY anio")
    except EjecDataError:
        return [{"label": a, "value": a} for a in ANIO_ORDER] + [{"label": "Todos los anios", "value": "TODOS"}]
    if df.empty:
        return [{"label": a, "value": a} for a in ANIO_ORDER] + [{"label": "Todos los anios", "value": "TODOS"}]
    return [{"label": "Todos los anios" if a == "TODOS" else a, "value": a} for a in df["anio"]]


def get_pacientes_totales():
    """Pacientes totales por patologia de alto costo, historico completo."""
    df = run_df(
        f"SELECT patologia, pacientes FROM {SCHEMA}.mv_ejec_pat_resumen "
        f"WHERE anio = 'TODOS' AND patologia = ANY(:pats)",
        {"pats": GLOBAL_PATOLOGIAS},
    )
    if df.empty:
        return []
    d = df.sort_values("pacientes", ascending=False)
    return [
        {"patologia": row["patologia"], "label": _pat_label(row["patologia"]), "pacientes": int(row["pacientes"])}
        for _, row in d.iterrows()
    ]


def get_evolucion_anual():
    """Serie anual de pacientes por patologia de alto costo (para line chart)."""
    df = run_df(
        f"SELECT patologia, anio, pacientes FROM {SCHEMA}.mv_ejec_pat_resumen "
        f"WHERE anio <> 'TODOS' AND patologia = ANY(:pats) ORDER BY anio",
        {"pats": GLOBAL_PATOLOGIAS},
    )
    if df.empty:
        return []
    return [
        {"patologia": row["patologia"], "label": _pat_label(row["patologia"]), "anio": row["anio"], "pacientes": int(row["pacientes"])}
        for _, row in df.iterrows()
    ]


def get_comorbilidad_grupo(patologia_global, patron_comorbilidad):
    """% de pacientes de la patologia global que TAMBIEN tienen cada
    comorbilidad curada de su grupo (patron de dwsge.mt_patologia)."""
    df = run_df(
        f"""SELECT c.patologia_b, c.pacientes
            FROM {SCHEMA}.mv_ejec_comorbilidad c
            JOIN dwsge.mt_patologia p ON p.patologia = c.patologia_b
            WHERE c.patologia_a = :pat AND p.patron = :patron
            ORDER BY c.pacientes DESC""",
        {"pat": patologia_global, "patron": patron_comorbilidad},
    )
    if df.empty:
        return []

    total_df = run_df(
        f"SELECT pacientes FROM {SCHEMA}.mv_ejec_comorbilidad WHERE patologia_a = :pat AND patologia_b = :pat",
        {"pat": patologia_global},
    )
    total = int(total_df["pacientes"].iloc[0]) if not total_df.empty else 0
    if not total:
        return []

    out = []
    for _, row in df.iterrows():
        pacientes = int(row["pacientes"])
        out.append({
            "patologia_b": row["patologia_b"],
            "label": _pat_label(row["patologia_b"]),
            "pacientes": pacientes,
            "pct": round(pacientes / total * 100, 2),
        })
    return sorted(out, key=lambda r: r["pct"], reverse=True)


def get_comorbilidad_burbujas():
    """Todas las intersecciones entre patologias (diagonal excluida),
    historico completo. Un registro por par (patologia_a, patologia_b)."""
    df = run_df(
        f"SELECT patologia_a, patologia_b, pacientes FROM {SCHEMA}.mv_ejec_comorbilidad "
        f"WHERE patologia_a <> patologia_b AND pacientes > 0"
    )
    if df.empty:
        return {"order": [], "puntos": []}

    total_df = run_df(
        f"SELECT patologia_a, pacientes FROM {SCHEMA}.mv_ejec_comorbilidad WHERE patologia_a = patologia_b"
    )
    totals = total_df.set_index("patologia_a")["pacientes"] if not total_df.empty else pd.Series(dtype=float)

    order = sorted(set(df["patologia_a"]), key=lambda p: -totals.get(p, 0))
    order_labels = [_pat_label(p) for p in order]

    puntos = [
        {
            "patologia_a": row["patologia_a"],
            "patologia_a_label": _pat_label(row["patologia_a"]),
            "patologia_b": row["patologia_b"],
            "patologia_b_label": _pat_label(row["patologia_b"]),
            "pacientes": int(row["pacientes"]),
        }
        for _, row in df.iterrows()
    ]
    return {"order": order_labels, "puntos": puntos}


def get_comparativa(anio_list):
    """KPIs + ranking por red, dependientes del filtro de anio."""
    rank_df = run_df(
        f"SELECT patologia, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_resumen "
        f"WHERE anio = ANY(:anio) AND patologia NOT IN ('TOTAL GENERAL', 'TOTAL CATALOGADO', 'SIN PATOLOGIA') "
        f"GROUP BY patologia ORDER BY pacientes DESC",
        {"anio": anio_list},
    )
    if rank_df.empty:
        return {"kpis": None, "ranking_red": []}

    total_df = run_df(
        f"SELECT COALESCE(SUM(pacientes),0) AS pacientes FROM {SCHEMA}.mv_ejec_pat_resumen "
        f"WHERE anio = ANY(:anio) AND patologia = ANY(:pats)",
        {"anio": anio_list, "pats": GLOBAL_PATOLOGIAS},
    )
    pac_total = int(total_df["pacientes"].iloc[0]) if not total_df.empty else 0

    kpis = {
        "pacientes_alto_costo": pac_total,
        "patologias_activas": len(rank_df),
    }

    top_red_df = run_df(
        f"SELECT patologia, redasisdes, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_red "
        f"WHERE anio = ANY(:anio) AND {EXCLUDE_COMPARATIVA_SQL} AND redasisdes IS NOT NULL "
        f"GROUP BY patologia, redasisdes ORDER BY pacientes DESC LIMIT 1",
        {"anio": anio_list},
    )
    if not top_red_df.empty:
        row = top_red_df.iloc[0]
        kpis["top_red"] = {
            "patologia_label": _pat_label(row["patologia"]),
            "nombre": row["redasisdes"],
            "pacientes": int(row["pacientes"]),
        }

    top_centro_df = run_df(
        f"SELECT patologia, cenasides, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_centro "
        f"WHERE anio = ANY(:anio) AND {EXCLUDE_COMPARATIVA_SQL} AND cenasides IS NOT NULL "
        f"GROUP BY patologia, cenasides ORDER BY pacientes DESC LIMIT 1",
        {"anio": anio_list},
    )
    if not top_centro_df.empty:
        row = top_centro_df.iloc[0]
        kpis["top_centro"] = {
            "patologia_label": _pat_label(row["patologia"]),
            "nombre": row["cenasides"],
            "pacientes": int(row["pacientes"]),
        }

    red_df = run_df(
        f"SELECT redasisdes, patologia, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_red "
        f"WHERE anio = ANY(:anio) AND patologia = ANY(:pats) AND redasisdes IS NOT NULL "
        f"GROUP BY redasisdes, patologia",
        {"anio": anio_list, "pats": GLOBAL_PATOLOGIAS},
    )
    ranking_red = []
    if not red_df.empty:
        rdf = red_df.copy()
        totales_red = rdf.groupby("redasisdes")["pacientes"].sum().sort_values(ascending=False)
        top_redes = totales_red.head(15).index.tolist()
        rdf = rdf[rdf["redasisdes"].isin(top_redes)]
        for redasisdes in top_redes:
            sub = rdf[rdf["redasisdes"] == redasisdes]
            entry = {"redasisdes": redasisdes, "total": int(sub["pacientes"].sum())}
            for _, row in sub.iterrows():
                entry[_pat_label(row["patologia"])] = int(row["pacientes"])
            ranking_red.append(entry)
        ranking_red.sort(key=lambda r: r["total"])

    return {"kpis": kpis, "ranking_red": ranking_red}


def get_flujo_area(anio_list, top_n_servicio=6):
    """Flujo Patologia -> Area -> Servicio (datos crudos para armar el
    Sankey en el frontend). Pliega servicios de cola larga por area."""
    df = run_df(
        f"SELECT patologia, area, servhosdes, SUM(pacientes) AS pacientes "
        f"FROM {SCHEMA}.mv_ejec_pat_area_servicio "
        f"WHERE anio = ANY(:anio) AND patologia = ANY(:pats) AND area IS NOT NULL "
        f"GROUP BY patologia, area, servhosdes",
        {"anio": anio_list, "pats": GLOBAL_PATOLOGIAS},
    )
    if df.empty:
        return {"pat_area": [], "area_servicio": []}

    d = df.copy()
    d["patologia_label"] = d["patologia"].map(_pat_label)

    pat_area = d.groupby(["patologia_label", "area"])["pacientes"].sum().reset_index()
    pat_area_out = [
        {"patologia_label": row["patologia_label"], "area": row["area"], "pacientes": int(row["pacientes"])}
        for _, row in pat_area.iterrows()
    ]

    area_serv = d.groupby(["area", "servhosdes"])["pacientes"].sum().reset_index()
    rows = []
    for area, grupo in area_serv.groupby("area"):
        grupo = grupo.sort_values("pacientes", ascending=False)
        for _, row in grupo.head(top_n_servicio).iterrows():
            rows.append({"area": area, "servicio": row["servhosdes"], "pacientes": int(row["pacientes"])})
        resto = grupo.iloc[top_n_servicio:]
        if not resto.empty:
            rows.append({
                "area": area,
                "servicio": f"Otros servicios ({len(resto)})",
                "pacientes": int(resto["pacientes"].sum()),
            })

    return {"pat_area": pat_area_out, "area_servicio": rows}


def get_diag_treemap(anio_list, top_n=10, top_n_servicio=5):
    """Jerarquia Patologia -> Diagnostico -> Servicio (datos crudos para
    armar el Treemap en el frontend). Pliega diagnosticos/servicios de cola
    larga, igual criterio que la version Dash."""
    df = run_df(
        f"SELECT patologia, diagdes, servhosdes, SUM(pacientes) AS pacientes "
        f"FROM {SCHEMA}.mv_ejec_pat_diag_servicio "
        f"WHERE anio = ANY(:anio) AND patologia = ANY(:pats) "
        f"GROUP BY patologia, diagdes, servhosdes",
        {"anio": anio_list, "pats": GLOBAL_PATOLOGIAS},
    )
    if df.empty:
        return []

    d = df.copy()
    d["patologia_label"] = d["patologia"].map(_pat_label)

    totales_diag = d.groupby(["patologia_label", "diagdes"])["pacientes"].sum().reset_index()
    rows = []
    for pat_label, grupo_pat in totales_diag.groupby("patologia_label"):
        grupo_pat = grupo_pat.sort_values("pacientes", ascending=False)
        top_diags = grupo_pat.head(top_n)["diagdes"].tolist()
        resto_diags = grupo_pat.iloc[top_n:]

        for diag in top_diags:
            sub = d[(d["patologia_label"] == pat_label) & (d["diagdes"] == diag)]
            sub = sub.sort_values("pacientes", ascending=False)
            for _, row in sub.head(top_n_servicio).iterrows():
                rows.append({
                    "patologia_label": pat_label, "diagnostico": diag,
                    "servicio": row["servhosdes"], "pacientes": int(row["pacientes"]),
                })
            resto_serv = sub.iloc[top_n_servicio:]
            if not resto_serv.empty:
                rows.append({
                    "patologia_label": pat_label, "diagnostico": diag,
                    "servicio": f"Otros servicios ({len(resto_serv)})",
                    "pacientes": int(resto_serv["pacientes"].sum()),
                })

        if not resto_diags.empty:
            rows.append({
                "patologia_label": pat_label,
                "diagnostico": f"Otros diagnosticos ({len(resto_diags)})",
                "servicio": "Varios servicios",
                "pacientes": int(resto_diags["pacientes"].sum()),
            })

    return rows
