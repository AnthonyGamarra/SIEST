import io
import os
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
import oracledb
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table, no_update
from flask import has_request_context
from flask_login import current_user
from sqlalchemy import text

TIPDOC_OPTIONS = [
    {"label": "D.N.I.", "value": "1"},
    {"label": "CARNE DE EXTRANJERIA/PASAPORTE", "value": "2"},
    {"label": "NEONATO", "value": "8"},
    {"label": "CARNET DE IDENTIDAD - RR.EE.", "value": "6"},
    {"label": "CARNET PERMISO TEMP PERM CPP", "value": "7"},
    {"label": "DOCUMENTO IDENTIDAD EXTRANJERO", "value": "4"},
    {"label": "PERMISO TEMPORAL DE PERMANENCIA", "value": "5"},
    {"label": "CARNET DE REFUGIADOS", "value": "T"},
]

COLUMNS = [
    {"name": "Red", "id": "RED"},
    {"name": "Centro", "id": "CENTRO"},
    {"name": "Acto medico", "id": "ACTO_MED"},
    {"name": "Area", "id": "AREA"},
    {"name": "Servicio", "id": "SERVICIO"},
    {"name": "Diagnostico (hipertension)", "id": "DIAGNOSTICO"},
    {"name": "Tipo de atencion", "id": "TIPO_ATENCION"},
    {"name": "Edad en atencion", "id": "EDAD_EN_ATENCION"},
    {"name": "Fecha de atencion", "id": "FECHA_ATENCION"},
    {"name": "Atencion", "id": "ACTMEDATE"},
    {"name": "Procedimiento", "id": "ACTMEDPRO"},
    {"name": "Receta", "id": "ACTMEDREC"},
    {"name": "Examen imagen", "id": "ACTMEDEXAIMA"},
    {"name": "Examen laboratorio", "id": "ACTMEDEXALAB"},
    {"name": "Examen patologia", "id": "ACTMEDEXAPAT"},
    {"name": "Hospitalizacion", "id": "ACTMEDHOS"},
    {"name": "Operacion", "id": "ACTMEDOPE"},
    {"name": "Cita topico", "id": "ACTMEDCITT"},
]

SQL_ATENCIONES = """
    SELECT
        c.cenasicod as cod_centro,
        r.redasismeddes  AS RED,
        c.cenasidescor   AS CENTRO,
        a.actmednum      AS ACTO_MED,
        are.arehosdes    AS AREA,
        ser.servhosdes   AS SERVICIO,
        tp.tipoparenom   AS TIPO_ATENCION,
        a.actmededadaten AS EDAD_EN_ATENCION,
        a.actmedfecaten  AS FECHA_ATENCION,
        a.actmedate      AS ACTMEDATE,
        a.actmedpro      AS ACTMEDPRO,
        a.actmedrec      AS ACTMEDREC,
        a.actmedexaima   AS ACTMEDEXAIMA,
        a.actmedexalab   AS ACTMEDEXALAB,
        a.actmedexapat   AS ACTMEDEXAPAT,
        a.actmedhos      AS ACTMEDHOS,
        a.actmedope      AS ACTMEDOPE,
        a.actmedcitt     AS ACTMEDCITT
    FROM sgss.cmame10 a
    LEFT OUTER JOIN sgss.cmcas10 c ON c.oricenasicod = a.oricenasicod
                                  AND c.cenasicod    = a.cenasicod
    LEFT OUTER JOIN sgss.cmras10 r   ON r.redasiscod   = c.redasiscod
    LEFT OUTER JOIN sgss.cmaho10 are ON are.arehoscod  = a.actmedarehoscod
    LEFT OUTER JOIN sgss.cmsho10 ser ON ser.servhoscod = a.actmedservhoscod
    LEFT OUTER JOIN sgss.cbtpa10 tp  ON tp.tipoparecod  = a.tipoparecod
    INNER JOIN sgss.cmper10 p ON p.persecnum = a.actmedpacsecnum
    WHERE p.pertipdocidencod = :tipdoc
      AND p.perdocidennum    = :docnum
    ORDER BY a.actmedfecaten DESC
"""

SQL_DIAG = """
    SELECT ce.cod_centro, ce.acto_med, ce.cod_diagnostico, d.diagdes
    FROM dssge.mtd_paciente_atencion_diagnostico ce
    LEFT JOIN dwsge.sgss_cmdia10 d ON d.diagcod = ce.cod_diagnostico
    WHERE ce.doc_paciente = :docnum AND ce.cod_tipdoc_paciente = :tipdoc
"""


def _connect():
    """Conexion a la base ESSI (Oracle), credenciales via variables de
    entorno (.env), nunca hardcodeadas en el codigo."""
    host = os.environ["ORACLE_HOST"]
    port = os.environ["ORACLE_PORT"]
    service = os.environ["ORACLE_SERVICE"]
    dsn = f"{host}:{port}/{service}"
    return oracledb.connect(user=os.environ["ORACLE_USER"], password=os.environ["ORACLE_PASS"], dsn=dsn)


def _query_atenciones(tipdoc, docnum):
    """Devuelve (df, error_str). error_str no nulo si la consulta fallo."""
    conn = None
    try:
        conn = _connect()
        df = pd.read_sql(SQL_ATENCIONES, conn, params={"tipdoc": tipdoc, "docnum": docnum})
        return df, None
    except Exception as exc:  # pragma: no cover
        print(f"[busqueda_paciente] Error de conexion/consulta ESSI: {exc}")
        return None, "Ocurrio un error al consultar la base ESSI."
    finally:
        if conn:
            conn.close()


def _check_hipertension(tipdoc, docnum):
    """True si el documento esta en dssge.mtd_lista_unica_pacientes_2 (lista
    de pacientes hipertensos). Usa la misma credencial de solo lectura del
    DW que el resto de la app (import perezoso, mismo patron que
    dashboard_ejec.py, para evitar imports circulares al cargar el modulo)."""
    from extensions import get_dw_engine

    try:
        engine = get_dw_engine()
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text(
                    "SELECT 1 FROM dssge.mtd_lista_unica_pacientes_2 "
                    "WHERE cod_tipdoc_paciente = :tipdoc AND doc_paciente = :docnum LIMIT 1"
                ),
                conn,
                params={"tipdoc": tipdoc, "docnum": docnum},
            )
        return not df.empty
    except Exception as exc:  # pragma: no cover
        print(f"[busqueda_paciente] Error verificando hipertension: {exc}")
        return False


def _query_diagnosticos(tipdoc, docnum):
    """Diagnosticos de hipertension (dssge.mtd_paciente_atencion_diagnostico)
    para el paciente, uno por (cod_centro, acto_med). Devuelve DataFrame
    vacio si no hay datos o si la consulta falla (no debe romper la
    busqueda principal de atenciones)."""
    from extensions import get_dw_engine

    try:
        engine = get_dw_engine()
        with engine.connect() as conn:
            return pd.read_sql_query(text(SQL_DIAG), conn, params={"tipdoc": tipdoc, "docnum": docnum})
    except Exception as exc:  # pragma: no cover
        print(f"[busqueda_paciente] Error consultando diagnosticos: {exc}")
        return pd.DataFrame(columns=["cod_centro", "acto_med", "cod_diagnostico", "diagdes"])


def _merge_diagnosticos(df, tipdoc, docnum):
    """Cruza el df de atenciones (ESSI/Oracle) con los diagnosticos de
    hipertension (DW/Postgres). Llave: cod_centro + acto_med (dentro de una
    misma busqueda, cod_tipdoc_paciente/doc_paciente ya son constantes,
    todas las filas son del mismo paciente). Agrega 'DIAGNOSTICO' (texto) y
    '_matched' (para resaltar las filas que cruzaron)."""
    df = df.copy()
    df["_matched"] = ""
    df["DIAGNOSTICO"] = ""

    diag = _query_diagnosticos(tipdoc, docnum)
    if diag.empty:
        return df

    diag = diag.copy()
    diag["cod_centro"] = diag["cod_centro"].astype(str).str.strip()
    diag["acto_med"] = pd.to_numeric(diag["acto_med"], errors="coerce").astype("Int64").astype(str)
    diag["etiqueta"] = diag["cod_diagnostico"].fillna("") + " - " + diag["diagdes"].fillna("")
    diag = diag.groupby(["cod_centro", "acto_med"])["etiqueta"].agg(lambda s: "; ".join(sorted(set(s)))).reset_index()

    df["_cod_centro_key"] = df["COD_CENTRO"].astype(str).str.strip()
    df["_acto_med_key"] = pd.to_numeric(df["ACTO_MED"], errors="coerce").astype("Int64").astype(str)

    merged = df.merge(
        diag, left_on=["_cod_centro_key", "_acto_med_key"], right_on=["cod_centro", "acto_med"], how="left"
    )
    merged["DIAGNOSTICO"] = merged["etiqueta"].fillna("")
    merged["_matched"] = merged["etiqueta"].notna().map({True: "1", False: ""})
    return merged.drop(columns=["_cod_centro_key", "_acto_med_key", "cod_centro", "acto_med", "etiqueta"])


def create_dash_app(flask_app, url_base_pathname="/busqueda_paciente_embed/"):
    brand = "#0064AF"
    brand_soft = "#D7E9FF"
    card_bg = "#FFFFFF"
    muted = "#6B7280"
    border = "#E5E7EB"
    font_family = "Inter, 'Segoe UI', Calibri, sans-serif"

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
    dash_app.title = "SIEST - Busqueda de Paciente"

    card_style = {
        "border": f"1px solid {border}",
        "borderRadius": "16px",
        "backgroundColor": card_bg,
        "boxShadow": "0 8px 20px rgba(0,0,0,0.08)",
        "padding": "18px",
    }

    def alert_box(msg, kind="info"):
        styles = {
            "warning": {"bg": "#FFF7E6", "border": "#F5C451", "ink": "#8A5B00", "icon": "bi-exclamation-triangle-fill"},
            "info": {"bg": "#EFF6FF", "border": "#93C5FD", "ink": "#1D4ED8", "icon": "bi-info-circle-fill"},
        }
        s = styles.get(kind, styles["info"])
        return html.Div(
            [
                html.I(className=f"bi {s['icon']}", style={"fontSize": "16px", "color": s["ink"], "flexShrink": "0", "marginTop": "1px"}),
                html.Span(msg, style={"color": s["ink"], "fontFamily": font_family, "fontSize": "13px", "fontWeight": 600, "lineHeight": "1.4"}),
            ],
            style={
                "display": "flex", "alignItems": "flex-start", "gap": "10px",
                "backgroundColor": s["bg"], "border": f"1px solid {s['border']}",
                "borderRadius": "12px", "padding": "12px 16px",
            },
        )

    def build_header():
        return html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            html.I(className="bi bi-person-vcard", style={"fontSize": "24px", "color": brand}),
                            style={
                                "width": "48px", "height": "48px", "borderRadius": "14px",
                                "backgroundColor": brand_soft, "display": "flex",
                                "alignItems": "center", "justifyContent": "center", "flexShrink": "0",
                            },
                        ),
                        html.H2(
                            "Seguimiento de Paciente",
                            style={"color": "#111827", "fontFamily": font_family, "fontSize": "23px", "fontWeight": 800, "margin": 0, "letterSpacing": "-0.01em"},
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "14px"},
                ),
                html.P(
                    "Busqueda de atenciones medicas por documento del paciente | Base ESSI",
                    style={"color": muted, "fontFamily": font_family, "fontSize": "13px", "margin": "8px 0 0 62px"},
                ),
            ],
            style={
                "padding": "18px 22px", "backgroundColor": card_bg, "borderRadius": "16px",
                "boxShadow": "0 8px 20px rgba(0,0,0,0.08)", "borderTop": f"3px solid {brand}",
            },
        )

    def hipertension_card():
        return html.Div(
            [
                html.I(className="bi bi-exclamation-octagon-fill", style={"fontSize": "28px", "color": "#B91C1C", "flexShrink": "0"}),
                html.Div(
                    [
                        html.Div("PACIENTE HIPERTENSO", style={"fontWeight": 800, "fontSize": "18px", "color": "#B91C1C", "letterSpacing": "0.02em"}),
                    ],
                ),
            ],
            className="ejec-card",
            style={
                **card_style, "display": "flex", "alignItems": "center", "gap": "14px",
                "backgroundColor": "#FEF2F2", "border": "2px solid #FCA5A5",
            },
        )

    def unauthorized_layout():
        return html.Div(
            [html.H3("Acceso restringido"), html.P("Este modulo esta disponible solo para administradores.")],
            style={"padding": "40px", "fontFamily": font_family},
        )

    def build_search_form():
        dropdown_style = {"width": "100%", "fontFamily": font_family, "fontSize": "13px"}
        return html.Div(
            [
                html.Div(
                    [
                        html.Small("Tipo de documento", style={"fontWeight": 600, "color": muted}),
                        dcc.Dropdown(
                            id="busq-tipdoc", options=TIPDOC_OPTIONS, value="1",
                            clearable=False, style=dropdown_style,
                        ),
                    ],
                    style={"flex": "2 1 280px", "display": "flex", "flexDirection": "column", "gap": "4px"},
                ),
                html.Div(
                    [
                        html.Small("Numero de documento", style={"fontWeight": 600, "color": muted}),
                        dbc.Input(id="busq-docnum", type="text", placeholder="Ej: 02448422", debounce=True, style={"fontFamily": font_family}),
                    ],
                    style={"flex": "2 1 220px", "display": "flex", "flexDirection": "column", "gap": "4px"},
                ),
                dbc.Button(
                    [html.I(className="bi bi-search me-1"), "Buscar"],
                    id="busq-buscar", color="primary",
                    style={"backgroundColor": brand, "borderColor": brand, "fontWeight": 600, "alignSelf": "flex-end", "height": "38px"},
                ),
            ],
            style={**card_style, "display": "flex", "gap": "14px", "flexWrap": "wrap", "alignItems": "flex-end", "padding": "14px 16px"},
        )

    def serve_layout():
        if not has_request_context():
            return html.Div()
        if not getattr(current_user, "is_authenticated", False) or getattr(current_user, "role", None) != "admin":
            return unauthorized_layout()
        return dbc.Container(
            [
                build_header(),
                html.Br(),
                build_search_form(),
                html.Div(id="busq-hipertension", style={"marginTop": "14px"}),
                html.Div(id="busq-feedback", style={"marginTop": "14px"}),
                html.Div(
                    [
                        html.Div("Atenciones del paciente", style={"fontWeight": 700, "color": brand, "marginBottom": "8px", "fontSize": "15px"}),
                        html.Small("Ordenadas de la mas antigua a la mas reciente.", style={"color": muted}),
                        dcc.Loading(html.Div(id="busq-tabla"), type="default"),
                        html.Div(
                            dbc.Button([html.I(className="bi bi-download me-1"), "Descargar"], id="busq-dl-btn", color="secondary", outline=True, style={"borderColor": brand, "color": brand, "marginTop": "10px"}),
                        ),
                        dcc.Download(id="busq-download"),
                        dcc.Store(id="busq-store"),
                    ],
                    className="ejec-card",
                    style={**card_style, "marginTop": "14px"},
                ),
            ],
            fluid=True,
            style={
                "backgroundColor": "#F3F6FB",
                "minHeight": "100vh",
                "padding": "18px 12px 26px 12px",
                "fontFamily": font_family,
            },
        )

    dash_app.layout = serve_layout

    def _build_tabla(df):
        d = df.copy()
        d["FECHA_ATENCION"] = pd.to_datetime(d["FECHA_ATENCION"], errors="coerce").dt.strftime("%d/%m/%Y")
        d = d.fillna("").astype(str)
        return dash_table.DataTable(
            columns=COLUMNS,
            data=d.to_dict("records"),
            page_size=20,
            filter_action="native",
            sort_action="native",
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "fontFamily": font_family, "fontSize": "12px", "padding": "7px", "maxWidth": "220px", "whiteSpace": "normal"},
            style_header={"backgroundColor": brand_soft, "fontWeight": 700, "border": f"1px solid {border}"},
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#F8FAFF"},
                {"if": {"filter_query": "{_matched} = '1'"}, "backgroundColor": "#FEF2F2", "color": "#B91C1C", "fontWeight": 600},
            ],
        )

    @dash_app.callback(
        Output("busq-feedback", "children"),
        Output("busq-hipertension", "children"),
        Output("busq-tabla", "children"),
        Output("busq-store", "data"),
        Input("busq-buscar", "n_clicks"),
        Input("busq-docnum", "n_submit"),
        State("busq-tipdoc", "value"),
        State("busq-docnum", "value"),
        prevent_initial_call=True,
    )
    def buscar(n_clicks, n_submit, tipdoc, docnum):
        docnum = (docnum or "").strip()
        if not tipdoc or not docnum:
            return alert_box("Seleccione el tipo e ingrese el numero de documento.", "warning"), None, None, None

        hipertension = hipertension_card() if _check_hipertension(tipdoc, docnum) else None

        df, err = _query_atenciones(tipdoc, docnum)
        if err:
            return alert_box(err, "warning"), hipertension, None, None
        if df is None or df.empty:
            return alert_box(f"No se encontraron atenciones para el documento {docnum}.", "info"), hipertension, None, None

        df = _merge_diagnosticos(df, tipdoc, docnum)
        tabla = _build_tabla(df)
        store = df.astype(str).to_dict("records")
        return None, hipertension, tabla, {"tipdoc": tipdoc, "docnum": docnum, "rows": store}

    @dash_app.callback(
        Output("busq-download", "data"),
        Input("busq-dl-btn", "n_clicks"),
        State("busq-store", "data"),
        prevent_initial_call=True,
    )
    def descargar(n_clicks, store):
        if not n_clicks or not store or not store.get("rows"):
            return no_update
        df = pd.DataFrame(store["rows"])
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        filename = f"atenciones_{store.get('docnum','paciente')}_{datetime.now():%Y%m%d_%H%M%S}.csv"
        return {"content": "﻿" + buffer.getvalue(), "filename": filename, "type": "text/csv"}

    return dash_app
