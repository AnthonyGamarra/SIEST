import io
from datetime import datetime
from functools import lru_cache

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table, no_update
from flask import has_request_context
from flask_login import current_user
from sqlalchemy import create_engine, text


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
        "borderBottomLeftRadius": "14px",
        "borderBottomRightRadius": "14px",
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
    anios = ["2025", "2026"]
    anio_options = [{"label": year, "value": year} for year in anios]

    dim_queries = {
        "red": {
            "sql": """SELECT redasiscod, redasisdes, redasismeddes FROM dwsge.sgss_cmras10 ORDER BY redasisdes""",
            "label": "redasismeddes",
            "value": "redasiscod",
        },
        "centro": {
            "sql": """SELECT cenasicod, cenasides FROM dwsge.sgss_cmcas10 ORDER BY cenasides""",
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
        ("cod_actividad", "Actividad"),
        ("actividad", "Desc. actividad"),
        ("cod_subactividad", "Subactividad"),
        ("subactividad", "Desc. subactividad"),
        ("sexo", "Sexo"),
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
               cod_diag,
               d.diagdes,
               d.edxcapdes AS capitulo
        FROM dwsge.dw_consulta_externa_homologacion_{table_suffix} ce
        LEFT JOIN dwsge.sgss_cmdia10_chapter d ON ce.cod_diag = d.diagcod
        LEFT JOIN dwsge.sgss_cmsho10 AS c ON ce.cod_servicio = c.servhoscod
        LEFT JOIN dwsge.sgss_cmcas10 AS ca ON ce.cod_oricentro = ca.oricenasicod AND ce.cod_centro = ca.cenasicod
        LEFT JOIN dwsge.sgss_cmace10 AS a ON ce.cod_actividad = a.actcod AND ce.cod_subactividad = a.actespcod
        LEFT JOIN dwsge.sgss_cmact10 AS am ON ce.cod_actividad = am.actcod
        LEFT JOIN dwsge.sgss_cmras10 r ON ca.redasiscod = r.redasiscod
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

    def build_table_suffix(anio_value, periodo_value):
        year = ''.join(ch for ch in str(anio_value) if ch.isdigit())[:4]
        month_raw = ''.join(ch for ch in str(periodo_value) if ch.isdigit())
        month = month_raw[-2:].zfill(2) if month_raw else '01'
        if not year:
            return None
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

    @lru_cache(maxsize=1)
    def create_connection():
        try:
            engine = create_engine(
                "postgresql+psycopg2://app_user:sge02@10.0.29.117:5433/DW_ESTADISTICA",
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            with engine.connect():
                pass
            return engine
        except Exception as exc:  # pragma: no cover - connection issues logged
            print(f"[Diag Report] Error creando conexión: {exc}")
            return None

    def field_wrapper(label_text, component):
        return html.Div(
            [
                html.Small(label_text, style={"fontWeight": "600", "color": muted, "fontFamily": font_family}),
                component,
            ],
            style={"display": "flex", "flexDirection": "column", "gap": "4px", "flex": "1 1 200px", "minWidth": "180px"},
        )

    @lru_cache(maxsize=None)
    def get_dimension_records(name):
        cfg = dim_queries.get(name)
        if cfg is None:
            return tuple()

        engine = create_connection()
        if engine is None:
            return tuple()

        try:
            with engine.connect() as conn:
                df = pd.read_sql_query(cfg["sql"], conn)
        except Exception as exc:  # pragma: no cover - SQL errors logged
            print(f"[Diag Report] Error cargando dimensión {name}: {exc}")
            return tuple()

        if df.empty:
            return tuple()

        df = df.fillna("").astype(str)
        dedupe_subset = [cfg["value"], cfg["label"]]
        if name == "capitulo":
            dedupe_subset = [cfg["label"]]
        df = df.drop_duplicates(subset=dedupe_subset)
        df = df.sort_values(cfg["label"])

        records = []
        for _, row in df.iterrows():
            label = row[cfg["label"]]
            if name == "subactividad":
                label = f"{row.get('actcod', '')} - {label}".strip(" -")
            records.append((row[cfg["value"]], label))
        return tuple(records)

    def build_dimension_options(name):
        return [{"label": label, "value": value} for value, label in get_dimension_records(name)]

    def build_filter_controls():
        periodo_options = [
            {"label": row["mes"], "value": row["periodo"]}
            for _, row in df_period.iterrows()
        ]

        dropdown_style = {"width": "100%", "fontFamily": font_family}

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
                    placeholder="Mes",
                    clearable=False,
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
            field_wrapper(
                "Actividad",
                dcc.Dropdown(
                    id="diag-filter-actividad",
                    options=build_dimension_options("actividad"),
                    placeholder="Todas",
                    clearable=True,
                    style=dropdown_style,
                ),
            ),
            field_wrapper(
                "Subactividad",
                dcc.Dropdown(
                    id="diag-filter-subactividad",
                    options=build_dimension_options("subactividad"),
                    placeholder="Todas",
                    clearable=True,
                    style=dropdown_style,
                ),
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
            field_wrapper(
                "Capítulo CIE",
                dcc.Dropdown(
                    id="diag-filter-capitulo",
                    options=build_dimension_options("capitulo"),
                    placeholder="Todos",
                    clearable=True,
                    style=dropdown_style,
                ),
            ),
            html.Div(
                [
                    dbc.Button(
                        [html.I(className="bi bi-search me-1"), "Buscar"],
                        id="diag-filter-search",
                        color="primary",
                        style={"backgroundColor": brand, "borderColor": brand, "fontWeight": 600},
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-download me-1"), "Descargar"],
                        id="diag-report-download-button",
                        color="secondary",
                        outline=True,
                        style={"borderColor": brand, "color": brand},
                    ),
                ],
                style={"display": "flex", "gap": "12px", "minWidth": "200px"},
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
                html.Img(
                    src=dash_app.get_asset_url("logo.png"),
                    style={"width": "120px", "height": "60px", "objectFit": "contain", "marginRight": "16px"},
                ),
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
                                dbc.Button(
                                    [html.I(className="bi bi-file-earmark-arrow-down me-2"), "Ficha técnica"],
                                    id="download-ficha-tecnica-button-nm",
                                    color="light",
                                    outline=True,
                                    size="sm",
                                    style={"borderColor": brand, "color": brand, "fontFamily": font_family, "fontWeight": "600", "borderRadius": "8px", "padding": "4px 12px"},
                                ),
                                dcc.Download(id="download-ficha-tecnica-nm"),
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
                            "Información actualizada al 31/01/2026 | Sistema de Gestión Estadística",
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
                build_report_section(),
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

        if not anio_value or not periodo_value:
            message = build_feedback_alert("Selecciona el año y el periodo para continuar.", "warning")
            return [], "Sin búsqueda realizada", message, None

        periodo_compuesto = f"{anio_value}{periodo_value}"
        table_suffix = build_table_suffix(anio_value, periodo_value)
        if not table_suffix:
            message = build_feedback_alert("El periodo seleccionado no es válido.", "danger")
            return [], "Sin búsqueda realizada", message, None

        filters = {
            "anio": str(anio_value),
            "periodo": periodo_compuesto,
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
        Input("diag-report-download-button", "n_clicks"),
        State("diag-report-store", "data"),
        prevent_initial_call=True,
    )
    def download_report(n_clicks, data_store):
        if not n_clicks or not data_store:
            return no_update
        filters = data_store.get("filters") if isinstance(data_store, dict) else None
        table_suffix = data_store.get("table_suffix") if isinstance(data_store, dict) else None
        if not filters or not table_suffix:
            return no_update

        df, error = run_report(filters, table_suffix)
        if error or df is None or df.empty:
            return no_update

        df = sanitize_dataframe(df)
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        filename = f"reporte_diag_{datetime.now():%Y%m%d_%H%M%S}.csv"
        return {"content": buffer.getvalue(), "filename": filename, "type": "text/csv"}

    return dash_app
