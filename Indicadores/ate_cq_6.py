from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from sqlalchemy import create_engine
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_ag_grid as dag
from urllib.parse import parse_qs
from datetime import date

# ===== Config de esta complejidad =====
N                   = 6
COMPLEJIDAD_LABEL   = "Sin código"
COMPLEJIDAD_COLOR   = "#6c757d"
COMPLEJIDAD_FILTER  = "AND (cq.cod_complejidad IS NULL OR TRIM(cq.cod_complejidad::text) = '')"
CSV_SUFFIX          = "sin_codigo"

# ===== Estilos compartidos =====
BRAND       = "#0064AF"
CARD_BG     = "#FFFFFF"
TEXT        = "#1C1F26"
MUTED       = "#6B7280"
FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"
BAR_SCALE   = ["#D7E9FF", "#92C4F9", "#2E78C7"]

DEFAULT_TIPO_ASEGURADO = "Todos"
TIPO_ASEGURADO_CLAUSES = {
    "asegurado": "('1')", "1": "('1')",
    "no asegurado": "('2')", "2": "('2')",
    "todos": "('1','2')"
}

def _resolve_codasegu(value):
    key = str(value).strip().lower() if value else ""
    return TIPO_ASEGURADO_CLAUSES.get(key, TIPO_ASEGURADO_CLAUSES["todos"])

def _qp(search, key):
    if not search:
        return None
    vals = parse_qs(search.lstrip("?")).get(key)
    return vals[0] if vals else None

def empty_fig(title=None):
    fig = go.Figure()
    kw = dict(template="simple_white", plot_bgcolor="#F9FBFD", paper_bgcolor="#F9FBFD",
              font=dict(family=FONT_FAMILY, color="#1F2937"), margin=dict(l=60, r=32, t=60, b=40))
    if title:
        kw["title"] = dict(text=title, font=dict(size=15, color=BRAND, family=FONT_FAMILY), x=0)
    fig.update_layout(**kw)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.add_annotation(text="Sin datos", font=dict(color=MUTED, size=12),
                       showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")
    return fig

def style_bar(fig, x_title, y_title, height=360):
    fig.update_traces(
        texttemplate="%{text}", textposition="outside", cliponaxis=False,
        marker=dict(line=dict(color="rgba(0,0,0,0.08)", width=1), opacity=0.92),
        selector=dict(type="bar"),
    )
    fig.update_layout(
        plot_bgcolor="#F9FBFD", paper_bgcolor="#F9FBFD",
        margin=dict(l=90, r=32, t=60, b=40), font=dict(family=FONT_FAMILY, size=12),
        xaxis=dict(title=x_title, showgrid=True, gridcolor="rgba(10,76,140,0.08)", tickformat=",.0f"),
        yaxis=dict(title=y_title, showgrid=False),
        bargap=0.18, showlegend=False, height=height,
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(family=FONT_FAMILY)),
    )
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_coloraxes(showscale=False)
    return fig

CARD_STYLE = {
    "backgroundColor": CARD_BG, "borderRadius": "14px",
    "boxShadow": "0 8px 20px rgba(0,0,0,0.08)", "padding": "18px", "marginBottom": "18px"
}

COLUMN_DEFS = [
    {"field": "cenasides",             "headerName": "Centro",             "minWidth": 180},
    {"field": "area",                  "headerName": "Area",               "minWidth": 160},
    {"field": "servicio",              "headerName": "Servicio",           "minWidth": 200},
    {"field": "cod_cpms",              "headerName": "Cod CPMS",           "minWidth": 80},
    {"field": "cpms",                  "headerName": "CPMS",               "minWidth": 160},
    {"field": "cod_complejidad",       "headerName": "Complejidad",        "minWidth": 110},
    {"field": "des_tipo_programacion", "headerName": "Tipo Programacion",  "minWidth": 180},
    {"field": "salopedes",             "headerName": "Sala Operaciones",   "minWidth": 160},
    {"field": "acto_med",              "headerName": "Acto Med.",          "minWidth": 110},
    {"field": "num_solicitud",         "headerName": "N° Solicitud",       "minWidth": 120},
    {"field": "fec_oper",              "headerName": "Fecha Operacion",    "minWidth": 150},
    {"field": "anio_edad",             "headerName": "Edad",               "minWidth": 80},
    {"field": "sexo",                  "headerName": "Sexo",               "minWidth": 80},
    {"field": "cod_anest",             "headerName": "Anestesia",          "minWidth": 110},
    {"field": "cod_tipdoc_paciente",   "headerName": "Tipo Doc.",          "minWidth": 100},
    {"field": "doc_paciente",          "headerName": "N° Documento",       "minWidth": 140},
]


def layout(codcas=None, **kwargs):
    return html.Div([
        dcc.Store(id=f"cq-codcas-store-{N}", data=codcas),
        dcc.Location(id=f"cq-url-{N}", refresh=False),
        # Header
        html.Div([
            html.Div([
                html.Div([
                    html.I(className="bi bi-scissors",
                           style={"fontSize": "30px", "color": COMPLEJIDAD_COLOR, "marginRight": "12px"}),
                    html.H2(f"Detalle IQ - {COMPLEJIDAD_LABEL}", style={
                        "color": BRAND, "fontFamily": FONT_FAMILY,
                        "fontSize": "22px", "margin": "0", "fontWeight": "700"
                    }),
                ], style={"display": "flex", "alignItems": "center"}),
                  html.P(f"Fecha {date.today().strftime('%d/%m/%Y')} | Centro Quirurgico",
                       style={"color": MUTED, "fontFamily": FONT_FAMILY, "fontSize": "12px", "margin": "6px 0 0 0"}),
            ], style={"flex": "1", "display": "flex", "flexDirection": "column"}),
            html.Div([
                dbc.Button([html.I(className="bi bi-download me-2"), "CSV"],
                           id=f"cq-download-btn-{N}", color="success",
                           style={"fontFamily": FONT_FAMILY, "fontWeight": "600",
                                  "borderRadius": "8px", "padding": "7px 16px", "marginRight": "8px"}),
                dcc.Download(id=f"cq-download-{N}"),
                dbc.Button([html.I(className="bi bi-arrow-left me-1"), "Volver"],
                           id=f"cq-back-btn-{N}", color="secondary", outline=True,
                           href="javascript:history.back();", external_link=True,
                           style={"fontFamily": FONT_FAMILY, "fontWeight": "600",
                                  "borderRadius": "8px", "padding": "7px 16px"}),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style={"display": "flex", "alignItems": "center", "padding": "16px 20px",
                  "backgroundColor": CARD_BG, "borderRadius": "14px",
                  "boxShadow": "0 8px 20px rgba(0,0,0,0.08)", "marginBottom": "20px"}),
        # Contenido dinámico
        html.Div(id=f"cq-content-{N}"),
    ], style={"padding": "20px", "fontFamily": FONT_FAMILY})


def create_connection():
    from extensions import get_dw_engine
    return get_dw_engine()



def _build_query(anio_str, periodo, codcas, codasegu_clause):
    return f"""
        SELECT DISTINCT ON (cq.acto_med, cq.cod_cpms)
            cq.cod_oricentro, cq.cod_centro,
            ca.cenasides AS cenasides,
            cq.periodo, cq.anio,
            h.arehosdes   AS area,
            c.servhosdes  AS servicio,
            cq.cod_cpms      AS cod_cpms,
            cp.cpsdes     AS cpms,
            cq.cod_tipdoc_paciente, cq.doc_paciente,
            cq.anio_edad, cq.meses, cq.sexo,
            cq.acto_med, cq.cod_complejidad,
            cq.cod_anest, cq.cod_tipo_programacion,
            b.conopedes   AS des_tipo_programacion,
            cq.num_solicitud, cq.cod_quirof,
            q.salopedes, 
            cq.fec_oper
        FROM dssge.dwe_centro_quirurgico_{anio_str}_{periodo} cq
        LEFT JOIN dwsge.sgss_cmsho10  c  ON cq.cod_servicio = c.servhoscod
        LEFT JOIN dwsge.sgss_cmcas10  ca ON cq.cod_oricentro = ca.oricenasicod
                                         AND cq.cod_centro   = ca.cenasicod
        LEFT JOIN dwsge.sgss_qmcqs10  q  ON q.cenasicod  = cq.cod_centro
                                        AND q.salopecod  = cq.cod_sala_operacion
                                         AND cq.cod_quirof = q.cenquicod
        LEFT JOIN dwsge.sgss_cmcpp10  cp ON cp.cpscod      = cq.cod_cpms
        LEFT JOIN dwsge.sgss_cmaho10  h  ON h.arehoscod    = cq.cod_area
        LEFT JOIN dwsge.sgss_qbcep10  b  ON b.conopecod    = cq.cod_tipo_programacion
        WHERE cq.cod_centro = '{codcas}'
          AND (CASE WHEN cq.cod_tipo_paciente = '4' THEN '2' ELSE '1' END) IN {codasegu_clause}
          {COMPLEJIDAD_FILTER}
        ORDER BY cq.acto_med, cq.cod_cpms, cq.fec_oper DESC
    """


def register_callbacks(app):
    @app.callback(
        Output(f"cq-content-{N}", "children"),
        Input(f"cq-codcas-store-{N}", "data"),
        Input(f"cq-url-{N}", "search"),
        prevent_initial_call=True,
    )
    def update_content(codcas_enc, search):
        import secure_code as sc
        codcas = sc.decode_code(codcas_enc) if codcas_enc else None
        periodo    = _qp(search, "periodo")
        anio_str   = _qp(search, "anio")
        tipo_aseg  = _qp(search, "codasegu") or DEFAULT_TIPO_ASEGURADO
        codasegu   = _resolve_codasegu(tipo_aseg)

        if not codcas or not periodo or not anio_str:
            return html.P("Parámetros insuficientes.", style={"color": MUTED, "padding": "40px"})

        engine = create_connection()
        if engine is None:
            return html.P("Error de conexion.", style={"color": "#dc3545", "padding": "40px"})

        try:
            df = pd.read_sql(_build_query(anio_str, periodo, codcas, codasegu), engine)
        except Exception as e:
            return html.P(f"Error SQL: {e}", style={"color": "#dc3545", "padding": "40px"})

        if df.empty:
            return html.Div([
                html.I(className="bi bi-inbox",
                       style={"fontSize": "60px", "color": MUTED, "display": "block", "textAlign": "center"}),
                html.H4("Sin registros", style={"color": TEXT, "fontFamily": FONT_FAMILY, "textAlign": "center"}),
                  html.P(f"No hay IQ de {COMPLEJIDAD_LABEL} para {codcas} - {anio_str}/{periodo}",
                       style={"color": MUTED, "fontFamily": FONT_FAMILY, "textAlign": "center"}),
            ], style={"padding": "60px"})

        total = len(df)
        pacientes_operados = (
            df["doc_paciente"]
            .dropna()
            .astype(str)
            .str.strip()
            .replace("", pd.NA)
            .dropna()
            .nunique()
        )
        nombre_centro = (df["cenasides"].dropna().iloc[0]
                         if not df["cenasides"].dropna().empty else codcas)

        # ---- Gráfico Servicios ----
        svc = (df.groupby("servicio", dropna=False).size()
                 .reset_index(name="Cantidad")
                 .sort_values("Cantidad", ascending=False).head(10))
        svc["servicio"] = svc["servicio"].fillna("Sin servicio")
        svc["label"] = svc["Cantidad"].apply(lambda v: f"{v:,.0f} ({v/total:.1%})")
        fig_svc = px.bar(svc, y="servicio", x="Cantidad", orientation="h",
                         text="label", color="Cantidad", color_continuous_scale=BAR_SCALE)
        fig_svc = style_bar(fig_svc, "Cantidad", "Servicio")
        fig_svc.update_layout(title=dict(text="Top 10 Servicios",
                                         font=dict(size=14, color=BRAND), x=0))

        # ---- Grafico Areas ----
        area = (df.groupby("area", dropna=False).size()
                  .reset_index(name="Cantidad")
                  .sort_values("Cantidad", ascending=False).head(10))
        area["area"] = area["area"].fillna("Sin área")
        area["label"] = area["Cantidad"].apply(lambda v: f"{v:,.0f} ({v/total:.1%})")
        fig_area = px.bar(area, y="area", x="Cantidad", orientation="h",
                          text="label", color="Cantidad", color_continuous_scale=BAR_SCALE)
        fig_area = style_bar(fig_area, "Cantidad", "Area")
        fig_area.update_layout(title=dict(text="Top 10 Areas",
                                          font=dict(size=14, color=BRAND), x=0))

        # ---- Grafico Tipo Programacion ----
        prog = (df.groupby("des_tipo_programacion", dropna=False).size()
                  .reset_index(name="Cantidad"))
        prog["des_tipo_programacion"] = prog["des_tipo_programacion"].fillna("Sin tipo")
        prog["label"] = prog["Cantidad"].apply(lambda v: f"{v:,.0f}")
        fig_prog = px.bar(prog, y="des_tipo_programacion", x="Cantidad", orientation="h",
                          text="label", color="Cantidad", color_continuous_scale=BAR_SCALE)
        fig_prog = style_bar(fig_prog, "Cantidad", "Tipo Programacion", height=220)
        fig_prog.update_layout(title=dict(text="Por Tipo de Programacion",
                                          font=dict(size=14, color=BRAND), x=0))

        # ---- AG Grid ----
        cols_table = ["cenasides", "area", "servicio", "cod_cpms","cpms", "cod_complejidad",
                      "des_tipo_programacion", "salopedes", "acto_med", "num_solicitud",
                      "fec_oper", "anio_edad", "sexo", "cod_anest",
                      "cod_tipdoc_paciente", "doc_paciente"]
        rows = df[cols_table].astype(str).replace("nan", "").to_dict("records")

        return html.Div([
            # Tarjetas resumen
            dbc.Row([
                dbc.Col(html.Div([
                    html.H5(f"{COMPLEJIDAD_LABEL} - {nombre_centro}",
                            style={"color": BRAND, "fontFamily": FONT_FAMILY, "marginBottom": "6px"}),
                    html.H2(f"{total:,.0f}",
                            style={"fontWeight": "800", "fontSize": "34px", "color": TEXT,
                                   "fontFamily": FONT_FAMILY, "margin": "0"}),
                    html.P(f"Anio {anio_str} | Periodo {periodo}",
                           style={"color": MUTED, "fontSize": "12px", "fontFamily": FONT_FAMILY,
                                   "margin": "6px 0 0 0"}),
                ], style={**CARD_STYLE, "borderLeft": f"5px solid {COMPLEJIDAD_COLOR}"}), width=12, lg=6),
                dbc.Col(html.Div([
                    html.H5("Pacientes operados",
                            style={"color": BRAND, "fontFamily": FONT_FAMILY, "marginBottom": "6px"}),
                    html.H2(f"{pacientes_operados:,.0f}",
                            style={"fontWeight": "800", "fontSize": "34px", "color": TEXT,
                                   "fontFamily": FONT_FAMILY, "margin": "0"}),
                    html.P("Conteo distintivo por doc_paciente",
                           style={"color": MUTED, "fontSize": "12px", "fontFamily": FONT_FAMILY,
                                   "margin": "6px 0 0 0"}),
                ], style={**CARD_STYLE, "borderLeft": "5px solid #198754"}), width=12, lg=6),
            ]),

            dbc.Row([
                dbc.Col(html.Div([dcc.Graph(figure=fig_svc)],  style=CARD_STYLE), width=12, lg=6),
                dbc.Col(html.Div([dcc.Graph(figure=fig_area)], style=CARD_STYLE), width=12, lg=6),
            ]),
            html.Div([dcc.Graph(figure=fig_prog)], style=CARD_STYLE),

            # Tabla
            html.Div([
                html.H6("Detalle de registros",
                        style={"color": BRAND, "fontFamily": FONT_FAMILY, "marginBottom": "12px"}),
                dag.AgGrid(
                    id=f"cq-grid-{N}",
                    rowData=rows,
                    columnDefs=COLUMN_DEFS,
                    defaultColDef={"resizable": True, "sortable": True, "filter": True, "minWidth": 100},
                    dashGridOptions={"pagination": True, "paginationPageSize": 20},
                    style={"height": "440px"},
                    className="ag-theme-alpine",
                ),
            ], style=CARD_STYLE),
        ])

    @app.callback(
        Output(f"cq-download-{N}", "data"),
        Input(f"cq-download-btn-{N}", "n_clicks"),
        State(f"cq-codcas-store-{N}", "data"),
        State(f"cq-url-{N}", "search"),
        prevent_initial_call=True,
    )
    def download_csv(n_clicks, codcas_enc, search):
        if not n_clicks:
            return None
        from dash import dcc as _dcc
        import secure_code as sc
        codcas = sc.decode_code(codcas_enc) if codcas_enc else None
        periodo   = _qp(search, "periodo")
        anio_str  = _qp(search, "anio")
        tipo_aseg = _qp(search, "codasegu") or DEFAULT_TIPO_ASEGURADO
        codasegu  = _resolve_codasegu(tipo_aseg)
        if not codcas or not periodo or not anio_str:
            return None
        engine = create_connection()
        if engine is None:
            return None
        try:
            df = pd.read_sql(_build_query(anio_str, periodo, codcas, codasegu), engine)
        except Exception:
            return None
        if df.empty:
            return None
        return _dcc.send_data_frame(
            df.to_excel,
            f"cq_{CSV_SUFFIX}_{codcas}_{anio_str}_{periodo}.xlsx",
            index=False, sheet_name='Atenciones'
        )



