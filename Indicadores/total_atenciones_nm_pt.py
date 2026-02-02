from dash import html, dcc, register_page, Input, Output, State, callback
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
from urllib.parse import parse_qs
from flask import request, has_request_context

BRAND = "#0064AF"
BRAND_SOFT = "#D7E9FF"
CARD_BG = "#FFFFFF"
TEXT = "#1C1F26"
MUTED = "#6B7280"
BORDER = "#E5E7EB"
FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"
BAR_COLOR_SCALE = ["#D7E9FF", "#92C4F9", "#2E78C7"]
# COLORES DE GR??FICOS (NO MODIFICAR)
GRID = "#e9ecef"
MALE = "#4C78A8"
FEMALE = "#B82753"
CARD_STYLE = {
    "border": f"1px solid {BORDER}",
    "borderRadius": "16px",
    "backgroundColor": CARD_BG,
    "boxShadow": "0 10px 24px rgba(0,0,0,0.08)",
    "padding": "16px",
    "transition": "transform .12s ease, box-shadow .12s ease",
}
GRAPH_CONFIG = {"responsive": True, "displaylogo": False}
# NUEVOS ESTILOS TABS
TABS_CONTAINER_STYLE = {
    "backgroundColor": CARD_BG,
    "border": f"1px solid {BORDER}",
    "borderRadius": "16px",
    "padding": "8px 12px 4px 12px",
    "boxShadow": "0 4px 12px rgba(0,0,0,0.06)"
}
TAB_STYLE = {
    "padding": "12px 20px",
    "fontFamily": FONT_FAMILY,
    "fontSize": "14px",
    "fontWeight": "600",
    "color": MUTED,
    "borderRadius": "12px",
    "margin": "4px 6px",
    "cursor": "pointer",
    "transition": "all .2s ease",
    "border": "1px solid transparent",
    "letterSpacing": "-0.1px"
}
TAB_SELECTED_STYLE = {
    **TAB_STYLE,
    "color": BRAND,
    "background": "linear-gradient(145deg, #ffffff 0%, #F3F8FC 100%)",
    "boxShadow": "0 3px 8px rgba(0,100,175,0.12)",
    "border": f"1px solid {BRAND}",
    "fontWeight": "700"
}

DEFAULT_TIPO_ASEGURADO = "Todos"
TIPO_ASEGURADO_CLAUSES = {
    "asegurado": "('1')",
    "1": "('1')",
    "no asegurado": "('2')",
    "2": "('2')",
    "todos": "('1','2')"
}

def resolve_tipo_asegurado_clause(value: str | None) -> str:
    key = str(value).strip().lower() if value else ""
    return TIPO_ASEGURADO_CLAUSES.get(key, TIPO_ASEGURADO_CLAUSES["todos"])

def _parse_query_param(search: str, key: str) -> str | None:
    if not search and has_request_context():
        qs_bytes = request.query_string
        if qs_bytes:
            search = f"?{qs_bytes.decode('utf-8')}"
    if not search:
        return None
    params = parse_qs(search.lstrip("?"))
    values = params.get(key)
    return values[0] if values else None

def _parse_periodo(search: str) -> str | None:
    return _parse_query_param(search, "periodo")

def _parse_anio(search: str) -> str | None:
    return _parse_query_param(search, "anio")


def _parse_codasegu(search: str) -> str | None:
    return _parse_query_param(search, "codasegu")

# Helpers reutilizables
def empty_fig(title: str | None = None) -> go.Figure:
    fig = go.Figure()
    layout_kwargs = dict(
        template="simple_white",
        plot_bgcolor="#F9FBFD",
        paper_bgcolor="#F9FBFD",
        font=dict(family=FONT_FAMILY, color="#1F2937"),
        margin=dict(l=60, r=32, t=70, b=40),
    )
    if title:
        layout_kwargs["title"] = dict(
            text=title,
            font=dict(size=18, color=BRAND, family=FONT_FAMILY),
            x=0,
            xanchor="left",
        )
    fig.update_layout(**layout_kwargs)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.add_annotation(
        text="Sin datos disponibles",
        font=dict(color=MUTED, size=12),
        showarrow=False,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
    )
    return fig

def style_horizontal_bar(fig: go.Figure, height: int = 320) -> go.Figure:
    title_component = getattr(getattr(fig.layout, "title", None), "text", "") or ""
    fig.update_traces(
        marker=dict(line=dict(color="rgba(0,0,0,0.08)", width=1.2), opacity=0.92),
        hovertemplate="<b>%{y}</b><br>Atenciones: %{x:,.0f}<extra></extra>",
        texttemplate="%{text}",
        textposition="outside",
        cliponaxis=False,
        selector=dict(type="bar"),
    )
    fig.update_layout(
        title=dict(text=title_component, font=dict(size=18, color=BRAND, family=FONT_FAMILY), x=0, xanchor="left"),
        plot_bgcolor="#F9FBFD",
        paper_bgcolor="#F9FBFD",
        xaxis=dict(
            title="Atenciones",
            showgrid=True,
            gridcolor="rgba(10,76,140,0.08)",
            zeroline=False,
            ticks="outside",
            tickformat=",.0f",
            tickfont=dict(color="#475569"),
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            ticks="outside",
            tickfont=dict(color="#1F2937"),
        ),
        margin=dict(l=90, r=32, t=70, b=40),
        font=dict(family=FONT_FAMILY, size=12, color="#1F2937"),
        height=height,
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(family=FONT_FAMILY, color="#0F172A")),
        bargap=0.18,
        uniformtext=dict(minsize=11, mode="show"),
        showlegend=False,
    )
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_coloraxes(showscale=False)
    return fig

# Helpers espec??ficos para esta p??gina
def get_codcas_periodo(pathname: str, search: str, periodo_dropdown: str, anio_dropdown: str, tipo_asegurado_dropdown: str | None = None):
    if not pathname:
        return None, None, None, DEFAULT_TIPO_ASEGURADO
    import secure_code as sc
    codcas = pathname.rstrip("/").split("/")[-1]
    codcas = sc.decode_code(codcas)
    periodo = _parse_periodo(search) or periodo_dropdown
    anio = _parse_anio(search) or anio_dropdown
    codasegu = _parse_codasegu(search) or tipo_asegurado_dropdown or DEFAULT_TIPO_ASEGURADO
    return codcas, periodo, anio, codasegu

# Layout sin verificador de query
layout = html.Div([
    dcc.Location(id="page-url_nm_pt", refresh=False),
    html.Div([
        # Header con icono
        html.Div([
            html.Div([
                html.I(className="bi bi-clipboard2-pulse", style={'fontSize': '28px', 'color': BRAND, 'marginRight': '12px'}),
                html.Div([
                    html.H4("Detalle de Atenciones Procedimiento terapéutico",
                            style={"margin": 0, "color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700, "letterSpacing": "-0.3px"}),
                    html.P("Análisis completo de la producción del periodo seleccionado",
                           style={"color": MUTED, "fontSize": "13px", "marginTop": "6px", "fontFamily": FONT_FAMILY})
                ])
            ], style={'display': 'flex', 'alignItems': 'center', 'flex': 1})
        ], style={'flex': 1}),
        # Lado derecho: bot??n descargar
        html.Div([
            html.Button(
                [html.I(className="bi bi-download me-2"), "Descargar CSV"],
                id="btn-download-query1_nm_pt",
                n_clicks=0,
                style={
                    "backgroundColor": BRAND,
                    "color": "#fff",
                    "border": "none",
                    "borderRadius": "10px",
                    "padding": "10px 16px",
                    "fontFamily": FONT_FAMILY,
                    "fontSize": "14px",
                    "fontWeight": "600",
                    "cursor": "pointer",
                    "boxShadow": "0 4px 12px rgba(0,100,175,0.2)",
                    "transition": "all .2s ease",
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "6px"
                }
            ),
            dcc.Download(id="download-query1-csv_nm_pt")
        ])
    ], style={
        "padding": "16px 20px",
        "background": "linear-gradient(120deg, #ffffff 0%, #EEF5FF 70%, #E4F0FF 100%)",
        "border": f"1px solid {BORDER}",
        "borderRadius": "16px",
        "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
        "marginBottom": "16px",
        "display": "flex",
        "justifyContent": "space-between",
        "alignItems": "center",
        "gap": "16px"
    }),
    # PESTA??AS
    dcc.Tabs(
        id="main-tabs_nm_pt",
        value="tab-graficos",
        style={"border": "none"},
        parent_style={"marginTop": "12px"},
        className="custom-tabs",
        children=[
            dcc.Tab(
                label="Producción",
                value="tab-graficos",
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=html.Div([
                    # Primer bloque: barras servicio / especialidad
                    html.Div([
                        dcc.Loading(
                            html.Div([
                                html.Div(dcc.Graph(id="bar-servicio-graph_nm_pt", config=GRAPH_CONFIG, style={"height": "320px", "width": "100%"}),
                                         style={"flex": "1", "minWidth": "320px"}),
                                html.Div(dcc.Graph(id="bar-especialidad-graph_nm_pt", config=GRAPH_CONFIG, style={"height": "320px", "width": "100%"}),
                                         style={"flex": "1", "minWidth": "320px"}),
                            ], style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
                            type="dot"
                        )
                    ], style={**CARD_STYLE}),
                    html.Br(),
                    html.Br(),
                    # Segundo bloque: gr??fico diagnóstico
                    html.Div([
                        dcc.Loading(
                            html.Div(
                                dcc.Graph(id="total-atenciones-graph_nm_pt", config=GRAPH_CONFIG, style={"height": "320px", "width": "100%"}),
                                style={"minWidth": "320px"}
                            ),
                            type="dot"
                        ),
                        html.Div(
                            id="total-atenciones-msg_nm_pt",
                            style={"marginTop": "10px", "color": MUTED, "fontFamily": FONT_FAMILY, "fontSize": "12px", "fontWeight": "600"}
                        )
                    ], style={**CARD_STYLE}),
                    html.Br()
                ], style={"padding": "8px"})
            ),
        ],
        content_style=TABS_CONTAINER_STYLE
    ),
], style={
    "width": "100%",
    "maxWidth": "1700px",
    "margin": "0 auto",
    "padding": "8px 16px 24px 16px",
    "fontFamily": FONT_FAMILY
})


# Registrar página
register_page(
    __name__,
    path_template="/dash/total_atenciones_nm_pt/<codcas>",
    name="total_atenciones_nm_pt",
    layout=layout
)

# Conexión DB
def create_connection():
    try:
        engine = create_engine('postgresql+psycopg2://app_user:sge02@10.0.29.117:5433/DW_ESTADISTICA')
        with engine.connect():
            pass
        return engine
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        return None

# Callback nuevas barras (inicio)
@callback(
    Output("bar-servicio-graph_nm_pt", "figure"),
    Output("bar-especialidad-graph_nm_pt", "figure"),
    Input("page-url_nm_pt", "pathname"),
    Input("page-url_nm_pt", "search"),
)
def update_barras_inicio(pathname, search):
    codcas, periodo, anio, tipo_asegurado = get_codcas_periodo(pathname, search, None, None)
    codasegu_clause = resolve_tipo_asegurado_clause(tipo_asegurado)
    if not codcas or not periodo or not anio:
        return empty_fig("Atenciones por servicio"), empty_fig("Atenciones por subactividad")
    engine = create_connection()
    if engine is None:
        return empty_fig("Atenciones por servicio"), empty_fig("Atenciones por subactividad")

    query = f"""
        SELECT 
            c.servhosdes AS descripcion_servicio,
            a.actespnom AS descripcion_subactividad
        FROM dwsge.dwe_consulta_externa_no_medicas_{anio}_{periodo} ce
        LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
            ON dg.diagcod=ce.diagcod
        LEFT JOIN dwsge.sgss_cmsho10 AS c 
            ON ce.cod_servicio = c.servhoscod
        LEFT JOIN dwsge.sgss_cmace10 AS a
            ON ce.cod_actividad = a.actcod
            AND ce.cod_subactividad = a.actespcod
        LEFT JOIN dwsge.sgss_cmact10 AS am
            ON ce.cod_actividad = am.actcod
        LEFT JOIN dwsge.sgss_cmcas10 AS ca
            ON ce.cod_oricentro = ca.oricenasicod
            AND ce.cod_centro = ca.cenasicod
            WHERE cod_centro = '{codcas}'
            AND cod_servicio ='E21'
            AND cod_actividad ='B1'
            AND ce.cod_subactividad in ('752','760','763','006')
            AND (
                    CASE 
                        WHEN ce.cod_tipo_paciente = '4' THEN '2'
                        ELSE '1'
                    END
                    ) IN {codasegu_clause}
    """
    try:
        df = pd.read_sql(query, engine)
    except Exception:
        return empty_fig("Atenciones por servicio"), empty_fig("Atenciones por subactividad")
    if df.empty:
        return (
            empty_fig(f"Atenciones por servicio - Periodo {periodo}"),
            empty_fig(f"Atenciones por subactividad - Periodo {periodo}"),
        )

    # Servicio
    serv_df = (
        df.assign(descripcion_servicio=df["descripcion_servicio"].fillna("Sin servicio"))
          .groupby("descripcion_servicio")
          .size()
          .reset_index(name="Atenciones")
          .sort_values("Atenciones", ascending=False)
          .head(10)
    )
    if serv_df.empty:
        fig_serv = empty_fig(f"Atenciones por servicio - Periodo {periodo}")
    else:
        total_serv = serv_df["Atenciones"].sum()
        serv_df["label"] = serv_df["Atenciones"].apply(
            lambda v: f"{v:,.0f} ({(v/total_serv):.1%})" if total_serv else f"{v:,.0f} (0.0%)"
        )
        fig_serv = px.bar(
            serv_df,
            y="descripcion_servicio",
            x="Atenciones",
            orientation="h",
            title=f"Atenciones por servicio - Periodo {periodo}",
            text="label",
            color="Atenciones",
            color_continuous_scale=BAR_COLOR_SCALE,
        )
        fig_serv = style_horizontal_bar(fig_serv, height=320)
    fig_serv.update_layout(
        template="simple_white",
        paper_bgcolor="#F9FBFD",
        plot_bgcolor="#F9FBFD",
        margin=dict(l=24, r=16, t=52, b=24),
        title_font=dict(size=18, color=BRAND),
        font=dict(family=FONT_FAMILY, size=12),
        xaxis=dict(title="Atenciones", showgrid=True, gridcolor=GRID, zeroline=False, ticks="outside"),
        yaxis=dict(title="Servicio", showgrid=False, ticks="outside"),
        hovermode="y",
        showlegend=False,
        bargap=0.24, bargroupgap=0.12
    )

    # Especialidad
    esp_df = (
        df.assign(descripcion_subactividad=df["descripcion_subactividad"].fillna("Sin subactividad"))
          .groupby("descripcion_subactividad")
          .size()
          .reset_index(name="Atenciones")
          .sort_values("Atenciones", ascending=False)
          .head(10)
    )
    if esp_df.empty:
        fig_esp = empty_fig(f"Atenciones por subactividad - Periodo {periodo}")
    else:
        total_esp = esp_df["Atenciones"].sum()
        esp_df["label"] = esp_df["Atenciones"].apply(
            lambda v: f"{v:,.0f} ({(v/total_esp):.1%})" if total_esp else f"{v:,.0f} (0.0%)"
        )
        fig_esp = px.bar(
            esp_df,
            y="descripcion_subactividad",
            x="Atenciones",
            orientation="h",
            title=f"Atenciones por subactividad - Periodo {periodo}",
            text="label",
            color="Atenciones",
            color_continuous_scale=BAR_COLOR_SCALE,
        )
        fig_esp = style_horizontal_bar(fig_esp, height=320)
    fig_esp.update_layout(
        template="simple_white",
        paper_bgcolor="#F9FBFD",
        plot_bgcolor="#F9FBFD",
        margin=dict(l=24, r=16, t=52, b=24),
        title_font=dict(size=18, color=BRAND),
        font=dict(family=FONT_FAMILY, size=12),
        xaxis=dict(title="Atenciones", showgrid=True, gridcolor=GRID, zeroline=False, ticks="outside"),
        yaxis=dict(title="Servicio", showgrid=False, ticks="outside"),
        hovermode="y",
        showlegend=False,
        bargap=0.24, bargroupgap=0.12
    )
    return fig_serv, fig_esp

# Callback para construir los gráficos principales
@callback(
    Output("total-atenciones-graph_nm_pt", "figure"),
    Output("total-atenciones-msg_nm_pt", "children"),
    Input("page-url_nm_pt", "pathname"),
    Input("page-url_nm_pt", "search"),
)
def update_total_atenciones_nm_pt(pathname, search):
    codcas, periodo, anio, tipo_asegurado = get_codcas_periodo(pathname, search, None, None)
    codasegu_clause = resolve_tipo_asegurado_clause(tipo_asegurado)
    if not codcas:
        return (
            empty_fig("Atenciones por diagnóstico"),
            "Sin ruta."
        )
    if not periodo or not anio:
        return (
            empty_fig("Atenciones por diagnóstico"),
            "Faltan filtros requeridos (asegúrate de tener ?periodo=MM&anio=YYYY o dropdowns con datos)."
        )
    engine = create_connection()
    if engine is None:
        return (
            empty_fig("Atenciones por diagnóstico"),
            "Error de conexión a la base de datos."
        )

    query = f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio}_{periodo} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = '{codcas}'
                        AND cod_servicio ='E21'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad in ('752','760','763','006')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu_clause}
    """
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        return (
            empty_fig("Atenciones por diagnóstico"),
            f"Error ejecutando consulta: {e}"
        )
    if df.empty:
        return (
            empty_fig(f"Atenciones por diagnóstico - Periodo {periodo}"),
            f"Sin datos para periodo {periodo}."
        )

    # Gráfico agrupador
    bar_df = (
        df.assign(diagdes=df["diagdes"].fillna("Sin diagnóstico"))
          .groupby("diagdes").size().reset_index(name="Atenciones")
          .sort_values("Atenciones", ascending=False).head(10)
    )
    if bar_df.empty:
        fig = empty_fig(f"Atenciones por diagnóstico - Periodo {periodo}")
        msg_fig = "Sin datos de diagnósticos."
    else:
        total_agr = bar_df["Atenciones"].sum()
        bar_df["label"] = bar_df["Atenciones"].apply(
            lambda v: f"{v:,.0f} ({(v/total_agr):.1%})" if total_agr else f"{v:,.0f} (0.0%)"
        )
        fig = px.bar(
            bar_df,
            y="diagdes",
            x="Atenciones",
            orientation="h",
            title=f"Atenciones por diagnóstico - Periodo {periodo}",
            text="label",
            color="Atenciones",
            color_continuous_scale=BAR_COLOR_SCALE,
        )
        fig = style_horizontal_bar(fig, height=320)
        msg_fig = f"{bar_df['Atenciones'].sum():,} atenciones en {bar_df.shape[0]} diagnósticos."
    fig.update_layout(
        xaxis_title="Atenciones",
        yaxis_title="Diagnóstico",
        template="simple_white",
        paper_bgcolor="#F9FBFD",
        plot_bgcolor="#F9FBFD",
        margin=dict(l=90, r=32, t=70, b=40),
        title_font=dict(size=18, color=BRAND),
        font=dict(family=FONT_FAMILY, size=12, color="#1F2937"),
        xaxis=dict(showgrid=True, gridcolor="rgba(10,76,140,0.08)", zeroline=False, ticks="outside"),
        yaxis=dict(showgrid=False, ticks="outside"),
        hovermode="y",
        showlegend=False,
        bargap=0.24, bargroupgap=0.12
    )
    msg = f"{len(df):,} registros procesados | {msg_fig}"
    return fig, msg

@callback(
    Output("download-query1-csv_nm_pt", "data"),
    Input("btn-download-query1_nm_pt", "n_clicks"),
    State("page-url_nm_pt", "pathname"),
    State("page-url_nm_pt", "search"),
    prevent_initial_call=True
)
def descargar_query1_csv(n_clicks, pathname, search):
    codcas, periodo, anio, tipo_asegurado = get_codcas_periodo(pathname, search, None, None)
    if not codcas or not periodo or not anio:
        return None
    engine = create_connection()
    if engine is None:
        return None
    codasegu_clause = resolve_tipo_asegurado_clause(tipo_asegurado)

    query = f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio}_{periodo} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = '{codcas}'
                        AND cod_servicio ='E21'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad in ('752','760','763','006')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu_clause}
    """
    try:
        df = pd.read_sql(query, engine)
    except Exception:
        return None

    filename = f"total_atenciones_nm_pt_{codcas}_{anio}_{periodo}.csv"
    return dcc.send_data_frame(df.to_csv, filename, index=False, encoding="utf-8-sig", sep="|")

