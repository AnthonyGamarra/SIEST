import io
from datetime import datetime
from functools import lru_cache

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table, no_update
from flask import has_request_context
from flask_login import current_user
from sqlalchemy import text


def create_dash_app(flask_app, url_base_pathname="/diag_cap/"):
    brand = "#0064AF"
    brand_soft = "#D7E9FF"
    card_bg = "#FFFFFF"
    muted = "#6B7280"
    border = "#E5E7EB"
    font_family = "Inter, 'Segoe UI', Calibri, sans-serif"

    control_bar_style = {
        "display": "flex",
        "alignItems": "flex-end",
        "flexWrap": "wrap",
        "gap": "12px",
        "marginBottom": "18px",
        "backgroundColor": card_bg,
        "border": f"1px solid {border}",
        "padding": "14px 16px",
        "borderRadius": "14px",
        "boxShadow": "0 4px 10px rgba(0,0,0,0.05)",
        "backdropFilter": "blur(3px)",
        "overflow": "visible",
        "position": "relative",
        "zIndex": 1100,
    }

    card_style = {
        "border": f"1px solid {border}",
        "borderRadius": "16px",
        "backgroundColor": card_bg,
        "boxShadow": "0 8px 20px rgba(0,0,0,0.08)",
        "padding": "18px",
    }

    TAB_STYLE = {
        "padding": "10px 18px",
        "fontFamily": font_family,
        "fontSize": "13px",
        "fontWeight": "600",
        "color": muted,
        "borderRadius": "10px",
        "margin": "4px 6px",
        "cursor": "pointer",
        "transition": "all .25s",
        "border": "1px solid transparent",
    }
    TAB_SELECTED_STYLE = {
        **TAB_STYLE,
        "color": brand,
        "background": "linear-gradient(145deg,#ffffff,#F3F8FC)",
        "boxShadow": "0 2px 6px rgba(0,0,0,0.08)",
        "border": f"1px solid {brand}",
    }

    external_stylesheets = [
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
    ]

    dash_app = Dash(
        __name__,
        server=flask_app,
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
        requests_pathname_prefix=url_base_pathname,
        routes_pathname_prefix=url_base_pathname,
    )
    dash_app.title = "SIEST - Diagnóstico"

    meses = [
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ]
    valores = [f"{i:02d}" for i in range(1, 13)]
    df_period = pd.DataFrame({"mes": meses, "periodo": valores})
    anios = ["2023","2024","2025", "2026"]
    anio_options = [{"label": year, "value": year} for year in anios]

    dim_queries = {
        "red": {
            "sql": """SELECT redasiscod, redasisdes, redasismeddes FROM dwsge.sgss_cmras10 ORDER BY redasisdes""",
            "label": "redasismeddes",
            "value": "redasiscod",
        },
        "centro": {
            "sql": """SELECT cenasicod, cenasides,redasiscod FROM dwsge.sgss_cmcas10 ORDER BY cenasides""",
            "label": "cenasides",
            "value": "cenasicod",
        },
        "servicio": {
            "sql": """SELECT servhoscod, servhosdes FROM dwsge.sgss_cmsho10 ORDER BY servhosdes""",
            "label": "servhosdes",
            "value": "servhoscod",
        },
        "actividad": {
            "sql": """SELECT actcod, actdes FROM dwsge.sgss_cmact10 ORDER BY actdes""",
            "label": "actdes",
            "value": "actcod",
        },
        "subactividad": {
            "sql": """
                SELECT actcod, actespcod, actespnom
                FROM dwsge.sgss_cmace10
                ORDER BY actcod, actespcod
            """,
            "label": "actespnom",
            "value": "actespcod",
        },
        "capitulo": {
            "sql": """SELECT diagcod, edxcapdes FROM dwsge.sgss_cmdia10_chapter ORDER BY edxcapdes""",
            "label": "edxcapdes",
            "value": "edxcapdes",
        },
        "variable": {
            "sql": """SELECT cod_variable, variable FROM dwsge.dim_variable ORDER BY variable""",
            "label": "variable",
            "value": "cod_variable",
        },
    }

    sexo_options = [
        {"label": "Masculino", "value": "M"},
        {"label": "Femenino", "value": "F"},
    ]

    report_columns = [
        ("cod_oricentro", "Centro origen"),
        ("redasiscod", "Cód. red"),
        ("redasisdes", "Red asistencial"),
        ("cod_centro", "Cód. centro"),
        ("cenasides", "Centro asistencial"),
        ("periodo", "Periodo"),
        ("anio", "Año"),
        ("cod_servicio", "Cód. servicio"),
        ("servicio", "Servicio"),
        ("cod_variable", "Cód. variable"),
        ("variable", "Variable"),
        ("cod_actividad", "Actividad"),
        ("actividad", "Desc. actividad"),
        ("cod_subactividad", "Subactividad"),
        ("subactividad", "Desc. subactividad"),
        ("sexo", "Sexo"),
        ("fecha_atencion", "Fecha atención"),
        ("anio_edad", "Edad (años)"),
        ("dni_medico", "DNI médico"),
        ("acto_med", "Acto médico"),
        ("doc_paciente", "Paciente"),
        ("cod_diag", "Cód. diagnóstico"),
        ("diagdes", "Diagnóstico"),
        ("capitulo", "Capítulo CIE"),
    ]

    report_union_query_template = """
        SELECT cod_oricentro,
               ca.redasiscod,
               r.redasisdes,
               cod_centro,
               cenasides,
               periodo,
               anio,
               v.cod_variable,
               v.variable,
               cod_servicio,
               c.servhosdes AS servicio,
               cod_actividad,
               am.actdes AS actividad,
               cod_subactividad,
               a.actespnom AS subactividad,
               dni_medico,
               acto_med,
               doc_paciente,
               anio_edad,
               sexo,
               fecha_atencion,
               cod_diag,
               d.diagdes,
               d.edxcapdes AS capitulo
        FROM dwsge.dwe_consulta_externa_homologacion_{table_suffix} ce
        LEFT JOIN dwsge.sgss_cmdia10_chapter d ON ce.cod_diag = d.diagcod
        LEFT JOIN dwsge.sgss_cmsho10 AS c ON ce.cod_servicio = c.servhoscod
        LEFT JOIN dwsge.sgss_cmcas10 AS ca ON ce.cod_oricentro = ca.oricenasicod AND ce.cod_centro = ca.cenasicod
        LEFT JOIN dwsge.sgss_cmace10 AS a ON ce.cod_actividad = a.actcod AND ce.cod_subactividad = a.actespcod
        LEFT JOIN dwsge.sgss_cmact10 AS am ON ce.cod_actividad = am.actcod
        LEFT JOIN dwsge.sgss_cmras10 r ON ca.redasiscod = r.redasiscod
        LEFT JOIN dwsge.dim_variable v ON v.cod_variable = ce.cod_variable
        WHERE ce.clasificacion IN (2,4,6)
    """

    report_filters = {
        "anio": "anio",
        "periodo": "periodo",
        "red": "redasiscod",
        "centro": "cod_centro",
        "servicio": "cod_servicio",
        "actividad": "cod_actividad",
        "subactividad": "cod_subactividad",
        "sexo": "sexo",
        "capitulo": "capitulo",
    }

    MAX_TABLE_ROWS = 100

    def build_table_suffix(anio_value, periodo_value=None):
        year = ''.join(ch for ch in str(anio_value) if ch.isdigit())[:4]
        if not year:
            return None
        if not periodo_value:
            return year
        month_raw = ''.join(ch for ch in str(periodo_value) if ch.isdigit())
        month = month_raw[-2:].zfill(2) if month_raw else '01'
        return f"{year}_{month}"

    def build_report_base_query(table_suffix):
        union_query = report_union_query_template.format(table_suffix=table_suffix)
        return f"""
        WITH report_data AS (
            {union_query}
        )
        SELECT *
        FROM report_data
        WHERE 1 = 1
        """

    def create_connection():
        from extensions import get_dw_engine
        return get_dw_engine()

    # =====================================================================
    # VISTA DINAMICA (pivot self-service) — solo anio 2026
    # =====================================================================
    # Lista blanca: el usuario nunca elige nombres de tabla/columna libres,
    # solo claves de estos diccionarios. Igual que report_filters mas abajo,
    # pero acá también fija a qué MV pre-agregada apunta cada combinación
    # (nunca se arma un GROUP BY dinámico contra la tabla particionada cruda).
    PIVOT_ANIO = "2026"
    PIVOT_DIMENSIONS = {
        "servicio": {"label": "Servicio", "mv": f"mv_diag_{PIVOT_ANIO}_servicio", "code_col": "cod_servicio", "desc_col": "servicio"},
        "red": {"label": "Red asistencial", "mv": f"mv_diag_{PIVOT_ANIO}_red", "code_col": "redasiscod", "desc_col": "redasisdes"},
        "centro": {"label": "Centro asistencial", "mv": f"mv_diag_{PIVOT_ANIO}_centro", "code_col": "cod_centro", "desc_col": "cenasides"},
        "actividad": {"label": "Actividad", "mv": f"mv_diag_{PIVOT_ANIO}_actividad", "code_col": "cod_actividad", "desc_col": "actividad"},
        "subactividad": {"label": "Subactividad", "mv": f"mv_diag_{PIVOT_ANIO}_subactividad", "code_col": "cod_subactividad", "desc_col": "subactividad"},
        "variable": {"label": "Variable", "mv": f"mv_diag_{PIVOT_ANIO}_variable", "code_col": "cod_variable", "desc_col": "variable"},
        "capitulo": {"label": "Capítulo CIE-10", "mv": f"mv_diag_{PIVOT_ANIO}_capitulo", "code_col": "capitulo", "desc_col": None},
        "sexo": {"label": "Sexo", "mv": f"mv_diag_{PIVOT_ANIO}_sexo", "code_col": "sexo", "desc_col": None},
        "grupo_edad": {"label": "Grupo etario", "mv": f"mv_diag_{PIVOT_ANIO}_edad", "code_col": "grupo_edad", "desc_col": None},
    }
    # (filas, columnas) -> MV de cruce. Solo se puede pivotear en estas
    # combinaciones porque son las únicas que build_mvs_diag.py construyó;
    # el resto queda disponible solo como "Filas" sin "Columnas".
    PIVOT_CROSSES = {
        ("servicio", "sexo"): f"mv_diag_{PIVOT_ANIO}_servicio_sexo",
        ("capitulo", "grupo_edad"): f"mv_diag_{PIVOT_ANIO}_capitulo_edad",
        ("red", "servicio"): f"mv_diag_{PIVOT_ANIO}_red_servicio",
    }
    PIVOT_METRICS = {
        "registros": "Atenciones (registros)",
        "pacientes": "Pacientes distintos",
    }
    PIVOT_NO_COLUMNAS = "__none__"

    def run_pivot_df(sql, params=None):
        try:
            engine = create_connection()
            with engine.connect() as conn:
                df = pd.read_sql_query(text(sql), conn, params=params or {})
            return df, None
        except Exception as exc:  # pragma: no cover
            print(f"[Diag Pivot] Error: {exc}")
            return None, "Ocurrió un error al ejecutar la consulta."

    def build_pivot_query(filas_key, columnas_key, desglose_mes):
        filas = PIVOT_DIMENSIONS.get(filas_key)
        if not filas:
            return None, None, "Elegí una dimensión válida para las filas."

        cross_mv = None
        columnas = None
        if columnas_key and columnas_key != PIVOT_NO_COLUMNAS:
            columnas = PIVOT_DIMENSIONS.get(columnas_key)
            cross_mv = PIVOT_CROSSES.get((filas_key, columnas_key))
            if not columnas or not cross_mv:
                return None, None, "Esa combinación de filas/columnas todavía no tiene una vista cruzada construida."

        mv = cross_mv or filas["mv"]
        select_cols = [filas["code_col"]]
        if filas["desc_col"]:
            select_cols.append(filas["desc_col"])
        if columnas:
            select_cols.append(columnas["code_col"])
            if columnas["desc_col"]:
                select_cols.append(columnas["desc_col"])

        # Con columnas (cruce 2D) el desglose mensual no es seguro: sumar los
        # meses en pandas duplicaría pacientes distintos presentes en mas de
        # un mes. El desglose por mes solo aplica sin columnas.
        usar_desglose = desglose_mes and not columnas
        sql = f"""
            SELECT {', '.join(select_cols)}, periodo, registros, pacientes
            FROM dssge.{mv}
            WHERE periodo {'<>' if usar_desglose else '='} 'TODOS'
        """
        return sql, {"filas": filas, "columnas": columnas, "desglose": usar_desglose}, None

    def build_pivot_table(df, meta, metric_key):
        metric_col = metric_key if metric_key in PIVOT_METRICS else "registros"
        filas_label = meta["filas"]["desc_col"] or meta["filas"]["code_col"]
        columnas_meta = meta.get("columnas")

        if columnas_meta:
            columnas_label = columnas_meta["desc_col"] or columnas_meta["code_col"]
            pivot_df = df.pivot_table(
                index=filas_label, columns=columnas_label, values=metric_col,
                aggfunc="sum", fill_value=0,
            ).reset_index()
            pivot_df.columns = [str(c) for c in pivot_df.columns]
            display_df = pivot_df
        else:
            keep = [filas_label, "periodo", metric_col] if meta.get("desglose") else [filas_label, metric_col]
            display_df = df[keep].rename(columns={metric_col: PIVOT_METRICS.get(metric_col, metric_col)})

        return dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in display_df.columns],
            data=display_df.to_dict("records"),
            page_size=20,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "fontFamily": font_family, "fontSize": "12px", "padding": "8px"},
            style_header={"backgroundColor": brand_soft, "fontWeight": "700", "border": f"1px solid {border}"},
            style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#F8FAFF"}],
            sort_action="native",
            filter_action="native",
        )

    def build_pivot_controls():
        dropdown_style = {"width": "100%", "fontFamily": font_family, "fontSize": "13px"}
        filas_options = [{"label": v["label"], "value": k} for k, v in PIVOT_DIMENSIONS.items()]
        metric_options = [{"label": v, "value": k} for k, v in PIVOT_METRICS.items()]
        return html.Div(
            [
                field_wrapper(
                    "Filas",
                    dcc.Dropdown(id="diag-pivot-filas", options=filas_options, value="servicio", clearable=False, style=dropdown_style),
                ),
                field_wrapper(
                    "Columnas (opcional)",
                    dcc.Dropdown(id="diag-pivot-columnas", options=[{"label": "(Sin columnas)", "value": PIVOT_NO_COLUMNAS}], value=PIVOT_NO_COLUMNAS, clearable=False, style=dropdown_style),
                ),
                field_wrapper(
                    "Métrica",
                    dcc.Dropdown(id="diag-pivot-metrica", options=metric_options, value="registros", clearable=False, style=dropdown_style),
                ),
                html.Div(
                    [
                        html.Small("", style={"fontFamily": font_family}),
                        dcc.Checklist(
                            id="diag-pivot-desglose",
                            options=[{"label": " Desglosar por mes", "value": "on"}],
                            value=[],
                            style={"fontFamily": font_family, "fontSize": "13px", "marginTop": "22px"},
                        ),
                    ],
                    style={"display": "flex", "flexDirection": "column", "flex": "1 1 200px", "minWidth": "180px"},
                ),
                html.Div(
                    dbc.Button(
                        [html.I(className="bi bi-table me-2"), "Generar"],
                        id="diag-pivot-generar", color="primary",
                        style={"backgroundColor": brand, "borderColor": brand, "fontFamily": font_family, "fontWeight": "600", "borderRadius": "8px"},
                    ),
                    style={"flex": "0 0 auto", "display": "flex", "alignItems": "flex-end"},
                ),
            ],
            className="dashboard-control-bar",
            style={**control_bar_style},
        )

    def build_pivot_section():
        return html.Div(
            [
                build_pivot_controls(),
                html.Div(id="diag-pivot-feedback"),
                html.Div(
                    dcc.Loading(html.Div(id="diag-pivot-table"), type="default"),
                    style=card_style,
                ),
            ],
            style={"display": "flex", "flexDirection": "column", "gap": "10px"},
        )

    def field_wrapper(label_text, component):
        return html.Div(
            [
                html.Small(label_text, style={"fontWeight": "600", "color": muted, "fontFamily": font_family}),
                component,
            ],
            style={"display": "flex", "flexDirection": "column", "gap": "4px", "flex": "1 1 200px", "minWidth": "180px"},
        )

    @lru_cache(maxsize=None)
    def load_dimension_df(name):
        cfg = dim_queries.get(name)
        if cfg is None:
            return None

        engine = create_connection()
        if engine is None:
            return None

        try:
            with engine.connect() as conn:
                df = pd.read_sql_query(cfg["sql"], conn)
        except Exception as exc:  # pragma: no cover - SQL errors logged
            print(f"[Diag Report] Error cargando dimensión {name}: {exc}")
            return None

        if df.empty:
            return pd.DataFrame()

        return df.fillna("").astype(str)

    def get_dimension_records(name, parent_value=None):
        cfg = dim_queries.get(name)
        if cfg is None:
            return tuple()

        df = load_dimension_df(name)
        if df is None or df.empty:
            return tuple()

        if name == "subactividad" and parent_value:
            parent_str = str(parent_value)
            if "actcod" in df.columns:
                df = df[df["actcod"] == parent_str]
        if name == "centro" and parent_value:
            parent_str = str(parent_value)
            if "redasiscod" in df.columns:
                df = df[df["redasiscod"] == parent_str]

        dedupe_subset = [cfg["value"], cfg["label"]]
        if name == "capitulo":
            dedupe_subset = [cfg["label"]]
        if name == "subactividad":
            dedupe_subset = [col for col in ["actcod", cfg["value"], cfg["label"]] if col in df.columns]
        if name == "centro":
            dedupe_subset = [col for col in ["redasiscod", cfg["value"], cfg["label"]] if col in df.columns]

        df = df.drop_duplicates(subset=dedupe_subset)
        if name == "subactividad" and "actcod" in df.columns:
            df = df.sort_values(["actcod", cfg["label"]])
        elif name == "centro" and "redasiscod" in df.columns:
            df = df.sort_values(["redasiscod", cfg["label"]])
        else:
            df = df.sort_values(cfg["label"])

        records = []
        for _, row in df.iterrows():
            label = row[cfg["label"]]
            if name == "subactividad":
                label = f"{row.get('actcod', '')} - {label}".strip(" -")
            records.append((row[cfg["value"]], label))
        return tuple(records)

    def build_dimension_options(name, parent_value=None):
        return [{"label": label, "value": value} for value, label in get_dimension_records(name, parent_value)]

    def build_filter_controls():
        periodo_options = [
            {"label": row["mes"], "value": row["periodo"]}
            for _, row in df_period.iterrows()
        ]

        dropdown_style = {"width": "100%", "fontFamily": font_family, "fontSize": "13px"}

        controls = [
            field_wrapper(
                "Año",
                dcc.Dropdown(
                    id="diag-filter-anio",
                    options=anio_options,
                    placeholder="Selecciona el año",
                    clearable=False,
                    style=dropdown_style,
                ),
            ),
            field_wrapper(
                "Periodo",
                dcc.Dropdown(
                    id="diag-filter-periodo",
                    options=periodo_options,
                    placeholder="Mes (opcional)",
                    clearable=True,
                    style=dropdown_style,
                ),
            ),
            field_wrapper(
                "Red asistencial",
                dcc.Dropdown(
                    id="diag-filter-red",
                    options=build_dimension_options("red"),
                    placeholder="Todas las redes",
                    clearable=True,
                    style=dropdown_style,
                ),
            ),
            field_wrapper(
                "Centro asistencial",
                dcc.Dropdown(
                    id="diag-filter-centro",
                    options=build_dimension_options("centro"),
                    placeholder="Todos los centros",
                    clearable=True,
                    style=dropdown_style,
                ),
            ),
            field_wrapper(
                "Servicio",
                dcc.Dropdown(
                    id="diag-filter-servicio",
                    options=build_dimension_options("servicio"),
                    placeholder="Todos los servicios",
                    clearable=True,
                    style=dropdown_style,
                ),
            ),

            html.Div(
                [
                    html.Small("Actividad", style={"fontWeight": "600", "color": muted, "fontFamily": font_family}),
                    dcc.Dropdown(
                        id="diag-filter-actividad",
                        options=build_dimension_options("actividad"),
                        placeholder="Todas",
                        clearable=True,
                        style=dropdown_style,
                    ),
                ],
                style={"display": "flex", "flexDirection": "column", "gap": "4px", "flex": "2 1 320px", "minWidth": "240px"},
            ),
            html.Div(
                [
                    html.Small("Subactividad", style={"fontWeight": "600", "color": muted, "fontFamily": font_family}),
                    dcc.Dropdown(
                        id="diag-filter-subactividad",
                        options=build_dimension_options("subactividad"),
                        placeholder="Todas",
                        clearable=True,
                        style=dropdown_style,
                    ),
                ],
                style={"display": "flex", "flexDirection": "column", "gap": "4px", "flex": "2 1 320px", "minWidth": "240px"},
            ),
            field_wrapper(
                "Sexo",
                dcc.Dropdown(
                    id="diag-filter-sexo",
                    options=sexo_options,
                    placeholder="Ambos",
                    clearable=True,
                    style=dropdown_style,
                ),
            ),
            html.Div(
                [
                    html.Small("Variable", style={"fontWeight": "600", "color": muted, "fontFamily": font_family}),
                    dcc.Dropdown(
                        id="diag-filter-variable",
                        options=build_dimension_options("variable"),
                        placeholder="Todas las variables",
                        clearable=True,
                        optionHeight=44,
                        style=dropdown_style,
                    ),
                ],
                style={"display": "flex", "flexDirection": "column", "gap": "4px", "flex": "1.5 1 260px", "minWidth": "220px"},
            ),
            html.Div(
                [
                    html.Small("Capítulo CIE", style={"fontWeight": "600", "color": muted, "fontFamily": font_family}),
                    dcc.Dropdown(
                        id="diag-filter-capitulo",
                        options=build_dimension_options("capitulo"),
                        placeholder="Todos",
                        clearable=True,
                        style=dropdown_style,
                    ),
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "4px",
                    "flex": "0 1 calc(40% - 12px)",
                    "minWidth": "200px",
                    "maxWidth": "40%",
                },
            ),
            html.Div(
                [
                    dbc.Button(
                        [html.I(className="bi bi-search me-1"), "Buscar"],
                        id="diag-filter-search",
                        color="primary",
                        style={"backgroundColor": brand, "borderColor": brand, "fontWeight": 600},
                    ),
                    html.Div(
                        [
                            dbc.Button(
                                [html.I(className="bi bi-download me-1"), "Descargar"],
                                id="diag-report-download-button",
                                color="secondary",
                                outline=True,
                                style={"borderColor": brand, "color": brand},
                            ),
                            dcc.Loading(
                                id="diag-report-download-spinner",
                                type="dot",
                                color=brand,
                                children=html.Div(id="diag-report-download-spinner-output", style={"width": "18px", "height": "18px"}),
                                style={"display": "flex", "alignItems": "center", "marginLeft": "14px"},
                            ),
                        ],
                        style={"display": "flex", "alignItems": "center", "gap": "12px"},
                    ),
                ],
                style={"display": "flex", "gap": "12px", "minWidth": "200px", "alignItems": "center"},
            ),
        ]

        return html.Div(controls, className="dashboard-control-bar", style=control_bar_style)

    def build_report_table():
        return dash_table.DataTable(
            id="diag-report-table",
            columns=[{"name": label, "id": column} for column, label in report_columns],
            data=[],
            page_size=20,
            style_table={"overflowX": "auto"},
            style_cell={
                "textAlign": "left",
                "fontFamily": font_family,
                "fontSize": "12px",
                "padding": "8px",
            },
            style_header={
                "backgroundColor": brand_soft,
                "fontWeight": "700",
                "border": f"1px solid {border}",
            },
            style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#F8FAFF"}],
            filter_action="native",
            sort_action="native",
            page_action="native",
        )

    def build_feedback_alert(message, color="warning"):
        if not message:
            return None
        return dbc.Alert(message, color=color, dismissable=True, style={"marginTop": "12px"})

    def sanitize_dataframe(df):
        if df is None or df.empty:
            return pd.DataFrame(columns=[column for column, _ in report_columns])
        sanitized = df.fillna("").astype(str)
        return sanitized

    def build_report_sql(filters, table_suffix):
        base_query = build_report_base_query(table_suffix)
        clauses = []
        params = {}
        for key, column in report_filters.items():
            value = filters.get(key)
            if value:
                clauses.append(f"AND {column} = :{key}")
                params[key] = value
        sql = base_query
        if clauses:
            sql = "\n".join([base_query, *clauses])
        sql = sql + "\nORDER BY anio DESC, periodo DESC, cod_centro, cod_servicio"
        return sql, params

    def run_report(filters, table_suffix, limit=None):
        sql, params = build_report_sql(filters, table_suffix)
        if limit is not None:
            try:
                limit_value = max(int(limit), 1)
                sql = f"{sql}\nLIMIT {limit_value}"
            except (TypeError, ValueError):
                pass
        engine = create_connection()
        if engine is None:
            return None, "No se pudo establecer conexión con la base de datos."
        try:
            with engine.connect() as conn:
                df = pd.read_sql_query(text(sql), conn, params={k: str(v) for k, v in params.items()})
            return df, None
        except Exception as exc:  # pragma: no cover - query issues logged
            print(f"[Diag Report] Error ejecutando consulta: {exc}")
            return None, "Ocurrió un error al ejecutar la consulta."

    def build_header():
        return html.Div(
            [
                # html.Img(
                #     src=dash_app.get_asset_url("logo.png"),
                #     style={"width": "120px", "height": "60px", "objectFit": "contain", "marginRight": "16px"},
                # ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.I(className="bi bi-hospital", style={"fontSize": "30px", "color": brand, "marginRight": "10px"}),
                                        html.H2(
                                            "Atenciones por capítulo CIE - Médicas",
                                            style={"color": brand, "fontFamily": font_family, "fontSize": "26px", "fontWeight": 800, "margin": "0"},
                                        ),
                                    ],
                                    style={"display": "flex", "alignItems": "center", "gap": "8px"},
                                ),
                            ],
                            style={"display": "flex", "alignItems": "center", "gap": "12px", "flexWrap": "wrap"},
                        ),
                        dbc.Tooltip(
                            "Descargar ficha técnica",
                            target="download-ficha-tecnica-button-nm",
                            placement="bottom",
                            style={"zIndex": 9999},
                        ),
                        html.P(
                            "Información actualizada al 01/04/2026 a las 00:00 horas  | Sistema de Gestión Estadística",
                            style={"color": muted, "fontFamily": font_family, "fontSize": "13px", "margin": "6px 0 0 0"},
                        ),
                    ],
                    style={"display": "flex", "flexDirection": "column", "justifyContent": "center"},
                ),
            ],
            style={"display": "flex", "alignItems": "center", "padding": "16px 20px", "backgroundColor": card_bg, "borderRadius": "16px", "boxShadow": "0 8px 20px rgba(0,0,0,0.08)", "gap": "14px"},
        )

    def build_report_section():
        return html.Div(
            [
                build_filter_controls(),
                dbc.Tooltip(
                    "Ejecutar búsqueda con los filtros seleccionados",
                    target="diag-filter-search",
                    placement="bottom",
                    style={"zIndex": 9999},
                ),
                dbc.Tooltip(
                    "Descargar el resultado actual",
                    target="diag-report-download-button",
                    placement="bottom",
                    style={"zIndex": 9999},
                ),
                html.Div(id="diag-report-feedback"),
                html.Div(
                    [
                        html.Div("Sin búsqueda realizada", id="diag-report-total", style={"fontFamily": font_family, "fontWeight": 600, "color": brand, "marginBottom": "12px"}),
                        dcc.Loading(build_report_table(), type="default"),
                    ],
                    style=card_style,
                ),
            ],
            style={"display": "flex", "flexDirection": "column", "gap": "16px"},
        )

    def unauthorized_layout():
        return html.Div(
            [
                html.H3("No autenticado"),
                html.P("Debes iniciar sesión para ver el dashboard."),
                dbc.Button(
                    "Volver",
                    id="unauth-back-button-nm",
                    color="primary",
                    href="javascript:history.back();",
                    external_link=True,
                    style={"marginTop": "12px"},
                ),
            ]
        )

    def serve_layout():
        if not has_request_context():
            return html.Div()
        if not getattr(current_user, "is_authenticated", False):
            return unauthorized_layout()
        return dbc.Container(
            [
                dcc.Location(id="url", refresh=True),
                build_header(),
                html.Br(),
                dcc.Tabs(
                    id="diag-main-tabs",
                    value="tab-detalle",
                    style={"border": "none"},
                    parent_style={"marginBottom": "16px", "overflow": "visible"},
                    className="custom-tabs",
                    children=[
                        dcc.Tab(label="Consulta detallada", value="tab-detalle", style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE, children=html.Div(build_report_section(), style={"paddingTop": "12px"})),
                        dcc.Tab(label="Vista dinámica (2026)", value="tab-pivot", style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE, children=html.Div(build_pivot_section(), style={"paddingTop": "12px"})),
                    ],
                ),
                dcc.Store(id="diag-report-store"),
                dcc.Download(id="diag-report-download"),
            ],
            fluid=True,
            style={
                "backgroundImage": "url('/static/76824.jpg')",
                "backgroundSize": "cover",
                "backgroundPosition": "center center",
                "backgroundRepeat": "no-repeat",
                "backgroundAttachment": "fixed",
                "minHeight": "100vh",
                "padding": "18px 12px 26px 12px",
                "fontFamily": font_family,
            },
        )

    dash_app.layout = serve_layout

    @dash_app.callback(
        Output("diag-filter-centro", "options"),
        Output("diag-filter-centro", "value"),
        Input("diag-filter-red", "value"),
    )
    def sync_centro_dropdown(red_value):
        return build_dimension_options("centro", red_value), None

    @dash_app.callback(
        Output("diag-filter-subactividad", "options"),
        Output("diag-filter-subactividad", "value"),
        Input("diag-filter-actividad", "value"),
    )
    def sync_subactividad_dropdown(actividad_value):
        return build_dimension_options("subactividad", actividad_value), None

    @dash_app.callback(
        Output("diag-report-table", "data"),
        Output("diag-report-total", "children"),
        Output("diag-report-feedback", "children"),
        Output("diag-report-store", "data"),
        Input("diag-filter-search", "n_clicks"),
        State("diag-filter-anio", "value"),
        State("diag-filter-periodo", "value"),
        State("diag-filter-red", "value"),
        State("diag-filter-centro", "value"),
        State("diag-filter-servicio", "value"),
        State("diag-filter-actividad", "value"),
        State("diag-filter-subactividad", "value"),
        State("diag-filter-capitulo", "value"),
        State("diag-filter-sexo", "value"),
        prevent_initial_call=True,
    )
    def handle_report_search(
        n_clicks,
        anio_value,
        periodo_value,
        red_value,
        centro_value,
        servicio_value,
        actividad_value,
        subactividad_value,
        capitulo_value,
        sexo_value,
    ):
        if not n_clicks:
            return no_update

        if not anio_value:
            message = build_feedback_alert("Selecciona el año para continuar.", "warning")
            return [], "Sin búsqueda realizada", message, None

        if not periodo_value and not centro_value:
            message = build_feedback_alert("Selecciona un periodo o filtra por centro asistencial para consultar el año completo.", "warning")
            return [], "Sin búsqueda realizada", message, None

        periodo_compuesto = f"{anio_value}{periodo_value}" if periodo_value else None
        table_suffix = build_table_suffix(anio_value, periodo_value)
        if not table_suffix:
            message = build_feedback_alert("El periodo seleccionado no es válido.", "danger")
            return [], "Sin búsqueda realizada", message, None

        filters = {
            "anio": str(anio_value),
            "periodo": periodo_compuesto if periodo_compuesto else None,
            "red": str(red_value) if red_value else None,
            "centro": str(centro_value) if centro_value else None,
            "servicio": str(servicio_value) if servicio_value else None,
            "actividad": str(actividad_value) if actividad_value else None,
            "subactividad": str(subactividad_value) if subactividad_value else None,
            "sexo": str(sexo_value) if sexo_value else None,
            "capitulo": str(capitulo_value) if capitulo_value else None,
        }

        df, error = run_report(filters, table_suffix, limit=MAX_TABLE_ROWS + 1)
        if error:
            return [], "Sin búsqueda realizada", build_feedback_alert(error, "danger"), None

        if df is None or df.empty:
            return [], "Sin resultados", build_feedback_alert("Sin datos para los filtros seleccionados.", "info"), None

        sanitized = sanitize_dataframe(df)
        records = sanitized.to_dict("records")
        has_more = len(records) > MAX_TABLE_ROWS
        display_records = records[:MAX_TABLE_ROWS] if has_more else records
        shown = len(display_records)
        total_label = f"Registros mostrados: {shown}" + (" | Hay más registros, usa Descargar para obtener todo" if has_more else "")
        store_payload = {"filters": filters, "table_suffix": table_suffix}
        return display_records, total_label, None, store_payload

    @dash_app.callback(
        Output("diag-report-download", "data"),
        Output("diag-report-download-spinner-output", "children"),
        Input("diag-report-download-button", "n_clicks"),
        State("diag-report-store", "data"),
        State("diag-filter-anio", "value"),
        State("diag-filter-periodo", "value"),
        State("diag-filter-red", "value"),
        State("diag-filter-centro", "value"),
        State("diag-filter-servicio", "value"),
        State("diag-filter-actividad", "value"),
        State("diag-filter-subactividad", "value"),
        State("diag-filter-capitulo", "value"),
        State("diag-filter-sexo", "value"),
        prevent_initial_call=True,
    )
    def download_report(
        n_clicks,
        data_store,
        anio_value,
        periodo_value,
        red_value,
        centro_value,
        servicio_value,
        actividad_value,
        subactividad_value,
        capitulo_value,
        sexo_value,
    ):
        from extensions import is_consulta_user
        if is_consulta_user():
            return no_update, ""
        if not n_clicks:
            return no_update, ""

        def build_filters_from_inputs():
            if not anio_value:
                return None, None
            if not periodo_value and not centro_value:
                return None, None
            suffix = build_table_suffix(anio_value, periodo_value)
            if not suffix:
                return None, None
            periodo_compuesto = f"{anio_value}{periodo_value}" if periodo_value else None
            filters_local = {
                "anio": str(anio_value),
                "periodo": periodo_compuesto if periodo_compuesto else None,
                "red": str(red_value) if red_value else None,
                "centro": str(centro_value) if centro_value else None,
                "servicio": str(servicio_value) if servicio_value else None,
                "actividad": str(actividad_value) if actividad_value else None,
                "subactividad": str(subactividad_value) if subactividad_value else None,
                "sexo": str(sexo_value) if sexo_value else None,
                "capitulo": str(capitulo_value) if capitulo_value else None,
            }
            return filters_local, suffix

        filters, table_suffix = build_filters_from_inputs()

        if filters is None or table_suffix is None:
            if isinstance(data_store, dict):
                filters = data_store.get("filters")
                table_suffix = data_store.get("table_suffix")
            else:
                filters = None
                table_suffix = None

        if not filters or not table_suffix:
            return no_update, ""

        df, error = run_report(filters, table_suffix)
        if error or df is None or df.empty:
            return no_update, ""

        df = sanitize_dataframe(df)
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        filename = f"reporte_diag_{datetime.now():%Y%m%d_%H%M%S}.csv"
        return {"content": buffer.getvalue(), "filename": filename, "type": "text/csv"}, ""

    @dash_app.callback(
        Output("diag-pivot-columnas", "options"),
        Output("diag-pivot-columnas", "value"),
        Input("diag-pivot-filas", "value"),
    )
    def sync_pivot_columnas(filas_key):
        opciones = [{"label": "(Sin columnas)", "value": PIVOT_NO_COLUMNAS}]
        for (f, c) in PIVOT_CROSSES:
            if f == filas_key:
                opciones.append({"label": PIVOT_DIMENSIONS[c]["label"], "value": c})
        return opciones, PIVOT_NO_COLUMNAS

    @dash_app.callback(
        Output("diag-pivot-table", "children"),
        Output("diag-pivot-feedback", "children"),
        Input("diag-pivot-generar", "n_clicks"),
        State("diag-pivot-filas", "value"),
        State("diag-pivot-columnas", "value"),
        State("diag-pivot-metrica", "value"),
        State("diag-pivot-desglose", "value"),
        prevent_initial_call=True,
    )
    def run_pivot(n_clicks, filas_key, columnas_key, metrica_key, desglose_value):
        if not n_clicks:
            return no_update, no_update

        desglose_mes = bool(desglose_value) and "on" in desglose_value
        sql, meta, error = build_pivot_query(filas_key, columnas_key, desglose_mes)
        if error:
            return html.Div(), dbc.Alert(error, color="warning", dismissable=True)

        df, db_error = run_pivot_df(sql)
        if db_error:
            return html.Div(), dbc.Alert(db_error, color="danger", dismissable=True)
        if df is None or df.empty:
            return html.Div(), dbc.Alert("Sin datos para esa combinación.", color="info", dismissable=True)

        table = build_pivot_table(df, meta, metrica_key)
        return table, None

    return dash_app
