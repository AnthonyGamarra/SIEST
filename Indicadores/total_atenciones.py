from dash import html, dcc, register_page, Input, Output, State, callback
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import dash_ag_grid as dag
from urllib.parse import parse_qs

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
def empty_table(title: str) -> html.Div:
    return html.Div(
        [
            html.Div(
                title,
                style={
                    "padding": "12px 16px",
                    "borderRadius": "8px",
                    "backgroundColor": "#F3F4F6",
                    "color": "#374151",
                    "fontFamily": FONT_FAMILY,
                    "fontSize": "14px",
                    "fontWeight": "500",
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                },
            ),
            html.Div(
                "Sin datos disponibles",
                style={
                    "padding": "24px 16px",
                    "borderRadius": "8px",
                    "backgroundColor": "#FFFFFF",
                    "color": "#6B7280",
                    "fontFamily": FONT_FAMILY,
                    "fontSize": "14px",
                    "fontWeight": "400",
                    "textAlign": "center",
                },
            ),
        ]
    )

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
    dcc.Location(id="page-url", refresh=False),
    html.Div([
        # Header con icono
        html.Div([
            html.Div([
                html.I(className="bi bi-clipboard2-pulse", style={'fontSize': '28px', 'color': BRAND, 'marginRight': '12px'}),
                html.Div([
                    html.H4("Detalle de Atenciones Médicas",
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
                id="btn-download-query1",
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
            dcc.Download(id="download-query1-csv")
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
        id="main-tabs",
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
                                html.Div(dcc.Graph(id="bar-servicio-graph", config=GRAPH_CONFIG, style={"height": "320px", "width": "100%"}),
                                         style={"flex": "1", "minWidth": "320px"}),
                                html.Div(dcc.Graph(id="bar-especialidad-graph", config=GRAPH_CONFIG, style={"height": "320px", "width": "100%"}),
                                         style={"flex": "1", "minWidth": "320px"}),
                            ], style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
                            type="dot"
                        )
                    ], style={**CARD_STYLE}),
                    html.Br(),
                    html.Br(),
                    # Segundo bloque: gr??fico agrupador + especialidad (lado a lado)
                    html.Div([
                        dcc.Loading(
                            html.Div([
                                html.Div(
                                    dcc.Graph(id="total-atenciones-graph", config=GRAPH_CONFIG, style={"height": "320px", "width": "100%"}),
                                    style={"flex": "1", "minWidth": "320px"}
                                ),
                                html.Div(
                                    dcc.Graph(id="total-atenciones-graph-esp", config=GRAPH_CONFIG, style={"height": "320px", "width": "100%"}),
                                    style={"flex": "1", "minWidth": "320px"}
                                ),
                            ], style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
                            type="dot"
                        ),
                        html.Div(
                            id="total-atenciones-msg",
                            style={"marginTop": "10px", "color": MUTED, "fontFamily": FONT_FAMILY, "fontSize": "12px", "fontWeight": "600"}
                        )
                    ], style={**CARD_STYLE}),
                    html.Br(),
                    # Tercer bloque: Tornado (movido dentro del primer tab)
                    html.Div([
                        html.Div([
                            html.I(className="bi bi-gender-ambiguous me-2", style={'color': BRAND, 'fontSize': '20px'}),
                            html.H5("Atenciones por grupo etario y sexo",
                                    style={"color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700, "marginBottom": 0, "letterSpacing": "-0.2px"}),
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '12px'}),
                        dcc.Loading(
                            html.Div([
                                dcc.Graph(id="tornado-atenciones-graph", config=GRAPH_CONFIG, style={"height": "360px", "width": "100%"})
                            ]),
                            type="dot"
                        ),
                        html.Div(id="tornado-atenciones-msg",
                                 style={"marginTop": "10px", "color": MUTED, "fontFamily": FONT_FAMILY,
                                        "fontSize": "12px", "fontWeight": "600"})
                    ], style={**CARD_STYLE})
                ], style={"padding": "8px"})
            ),
            # NUEVA TAB Producci??n x m??dico
            # dcc.Tab(
            #     label="Producci??n x m??dico",
            #     value="tab-vacia",
            #     style=TAB_STYLE,
            #     selected_style=TAB_SELECTED_STYLE,
            #     children=html.Div([
            #         html.Div([
            #             html.H5(
            #                 "Producci??n por m??dico",
            #                 style={"color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 600, "marginBottom": "8px"}
            #             ),
            #             # Filtro + gr??fico de tendencia (NUEVO, va antes de la tabla)
            #             html.Div([
            #                 html.Div([
            #                     html.Label("Filtrar por DNI del m??dico", style={"fontSize": "12px", "color": MUTED}),
            #                     dcc.Input(
            #                         id="dni-filter",
            #                         type="text",
            #                         placeholder="Ingrese DNI m??dico y presione Enter",
            #                         debounce=True,
            #                         style={
            #                             "width": "240px", "padding": "6px 10px", "borderRadius": "8px",
            #                             "border": "1px solid #d0d7de", "fontFamily": FONT_FAMILY, "fontSize": "13px"
            #                         }
            #                     )
            #                 ], style={"display": "flex", "flexDirection": "column", "gap": "4px"}),
            #                 html.Div(style={"flex": 1})
            #             ], style={"display": "flex", "alignItems": "end", "gap": "12px", "marginBottom": "10px"}),
            #             dcc.Loading(
            #                 dcc.Graph(id="line-atenciones-medico", style={"height": "320px", "width": "100%"}),
            #                 type="dot"
            #             ),
            #             # Tabla (ya existente) debajo del gr??fico
            #             html.Div(id="tabla-prod-medico-wrapper")
            #         ], style={**CARD_STYLE}),
            #     ], style={"padding": "4px"})
            # ),
            dcc.Tab(
                label="Diagnósticos",
                value="tab-resumen",
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=html.Div([
                    html.Div([
                        html.Div([
                            html.I(className="bi bi-clipboard-data me-2", style={'color': BRAND, 'fontSize': '20px'}),
                            html.H5("Resumen servicio / subactividad / diagnóstico",
                                    style={"color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700,
                                           "marginBottom": 0, "letterSpacing": "-0.2px"}),
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '12px'}),
                        # NUEVO: gráfico Top10 coddiag x sexo (antes de la tabla)
                        dcc.Loading(
                            dcc.Graph(id="bar-topdiag-graph", config=GRAPH_CONFIG, style={"height": "360px", "width": "100%"}),
                            type="dot"
                        ),
                        html.Div(id="tabla-resumen-atenciones-wrapper")
                    ], style={**CARD_STYLE})
                ], style={"padding": "8px"})
            ),
            dcc.Tab(
                label="Registros no considerados",
                value="tab-detalle",
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=html.Div([
                    html.Div([
                        html.Div([
                            html.I(className="bi bi-exclamation-triangle me-2", style={'color': BRAND, 'fontSize': '20px'}),
                            html.H5("Detalle de registros no considerados",
                                    style={"color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700,
                                           "marginBottom": 0, "letterSpacing": "-0.2px"}),
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '12px'}),
                        html.Div(id="tabla-detalle-wrapper")
                    ], style={**CARD_STYLE})
                ], style={"padding": "8px"})
            )
        ],
        content_style=TABS_CONTAINER_STYLE
    ),
    # Stores
    dcc.Store(id="store-detalle-data")
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
    path_template="/dash/total_atenciones/<codcas>",
    name="total_atenciones",
    layout=layout
)

# Conexión DB
def create_connection():
    try:
        engine = create_engine('postgresql+psycopg2://postgres:4dm1n@10.0.29.117:5433/DW_ESTADISTICA')
        with engine.connect():
            pass
        return engine
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        return None

def _parse_query_param(search: str, key: str) -> str | None:
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

# Callback nuevas barras (inicio)
@callback(
    Output("bar-servicio-graph", "figure"),
    Output("bar-especialidad-graph", "figure"),
    Input("page-url", "pathname"),
    Input("page-url", "search"),
    State("filter-periodo", "value"),
    State("filter-anio", "value"),
    State("filter-tipo-asegurado", "value")
)
def update_barras_inicio(pathname, search, periodo_dropdown, anio_dropdown, tipo_dropdown):
    codcas, periodo, anio, tipo_asegurado = get_codcas_periodo(pathname, search, periodo_dropdown, anio_dropdown, tipo_dropdown)
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
        FROM dwsge.dw_consulta_externa_homologacion_{anio}_{periodo} AS ce
        LEFT JOIN dwsge.sgss_cmsho10 AS c ON ce.cod_servicio = c.servhoscod
        LEFT JOIN dwsge.sgss_cmace10 AS a ON ce.cod_actividad = a.actcod AND ce.cod_subactividad = a.actespcod
        WHERE ce.cod_centro = '{codcas}'
          AND ce.cod_actividad = '91'
          AND ce.clasificacion in (2,4,6)
          AND ce.cod_variable = '001'
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

# Callback para construir el gráfico y las tablas
@callback(
    Output("total-atenciones-graph", "figure"),
    Output("total-atenciones-graph-esp", "figure"),
    Output("total-atenciones-msg", "children"),
    Output("tabla-detalle-wrapper", "children"),
    Output("store-detalle-data", "data"),
    Output("tabla-resumen-atenciones-wrapper", "children"),
    Output("bar-topdiag-graph", "figure"),
    Input("page-url", "pathname"),
    Input("page-url", "search"),
    State("filter-periodo", "value"),
    State("filter-anio", "value"),
    State("filter-tipo-asegurado", "value")
)
def update_total_atenciones(pathname, search, periodo_dropdown, anio_dropdown, tipo_dropdown):
    empty_div = html.Div()
    codcas, periodo, anio, tipo_asegurado = get_codcas_periodo(pathname, search, periodo_dropdown, anio_dropdown, tipo_dropdown)
    codasegu_clause = resolve_tipo_asegurado_clause(tipo_asegurado)
    if not codcas:
        return empty_fig("Atenciones por agrupador"), empty_fig("Atenciones por especialidad"), "Sin ruta.", empty_div, None, empty_div, empty_fig("Top 10 diagnósticos por atenciones")
    if not periodo or not anio:
        return (
            empty_fig("Atenciones por agrupador"),
            empty_fig("Atenciones por especialidad"),
            "Faltan filtros requeridos (aseg??rate de tener ?periodo=MM&anio=YYYY o dropdowns con datos).",
            empty_div,
            None,
            empty_div,
            empty_fig("Top 10 diagn??sticos por atenciones"),
        )
    engine = create_connection()
    if engine is None:
        return empty_fig("Atenciones por agrupador"), empty_fig("Atenciones por especialidad"), "Error de conexión a la base de datos.", empty_div, None, empty_div, empty_fig("Top 10 diagn??sticos por atenciones")

    query = f"""
        SELECT 
            ce.cod_servicio,
            ce.cod_especialidad,
            ca.cenasides,
            am.actdes AS actividad,
            ag.agrupador AS agrupador,
            a.actespnom AS subactividad,
            ce.cod_tipo_consulta,
            ce.cod_diag,
            d.diagdes AS descripcion_diagnostico,
            c.servhosdes AS descripcion_servicio,
            e.especialidad AS descripcion_especialidad,
            t.tipcondes AS descripcion_tipo_consulta,
            dni_medico,
            doc_paciente,
            cod_tipdoc_paciente,
            sexo,
            fecha_atencion,
            acto_med
        FROM dwsge.dw_consulta_externa_homologacion_{anio}_{periodo} AS ce
        LEFT JOIN dwsge.sgss_cmsho10 AS c ON ce.cod_servicio = c.servhoscod
        LEFT JOIN dwsge.dim_especialidad AS e ON ce.cod_especialidad = e.cod_especialidad
        LEFT JOIN dwsge.sgss_cmtco10 AS t ON ce.cod_tipo_consulta = t.tipconcod
        LEFT JOIN dwsge.sgss_cmdia10 AS d ON ce.cod_diag = d.diagcod
        LEFT JOIN dwsge.sgss_cmace10 AS a ON ce.cod_actividad = a.actcod AND ce.cod_subactividad = a.actespcod
        LEFT JOIN dwsge.sgss_cmact10 AS am ON ce.cod_actividad = am.actcod
        LEFT JOIN dwsge.sgss_cmcas10 AS ca ON ce.cod_oricentro = ca.oricenasicod AND ce.cod_centro = ca.cenasicod
        LEFT JOIN dwsge.dim_agrupador as ag ON ce.cod_agrupador = ag.cod_agrupador
        WHERE ce.cod_centro = '{codcas}'
          AND ce.cod_actividad = '91'
          AND ce.clasificacion in (2,4,6)
          AND ce.cod_variable = '001'
          AND (
                    CASE 
                        WHEN ce.cod_tipo_paciente = '4' THEN '2'
                        ELSE '1'
                    END
                    ) IN {codasegu_clause}
    """
    query2 = f"""
        SELECT 
            c.servhosdes AS Servicio2,
            am.actdes AS Actividad2,
            a.actespnom AS Subactividad2,
            t.tipcondes AS Tipo_consulta2,
            ce.cod_diag as CodDiag2,
            d.diagdes AS Diagnostico2,
            dni_medico as dni_medico2,
            acto_med as acto_med2,
            sexo as sexo2,
            fecha_atencion as fecha_atencion2,
            cl.desc_cl AS desc_cl2
        FROM dwsge.dw_consulta_externa_homologacion_{anio}_{periodo} AS ce
        LEFT JOIN dwsge.sgss_cmsho10 AS c ON ce.cod_servicio = c.servhoscod
        LEFT JOIN dwsge.dim_especialidad AS e ON ce.cod_especialidad = e.cod_especialidad
        LEFT JOIN dwsge.sgss_cmtco10 AS t ON ce.cod_tipo_consulta = t.tipconcod
        LEFT JOIN dwsge.sgss_cmdia10 AS d ON ce.cod_diag = d.diagcod
        LEFT JOIN dwsge.sgss_cmace10 AS a ON ce.cod_actividad = a.actcod AND ce.cod_subactividad = a.actespcod
        LEFT JOIN dwsge.sgss_cmact10 AS am ON ce.cod_actividad = am.actcod
        LEFT JOIN dwsge.sgss_cmcas10 AS ca ON ce.cod_oricentro = ca.oricenasicod AND ce.cod_centro = ca.cenasicod
        LEFT JOIN dwsge.dim_agrupador as ag ON ce.cod_agrupador = ag.cod_agrupador
        LEFT JOIN dwsge.dwe_cl10 as cl ON ce.clasificacion = cl.id_cl
        WHERE ce.cod_centro = '{codcas}'
          AND ce.cod_actividad = '91'
          AND ce.clasificacion in (1,3,5,0)
          AND ce.cod_variable = '001'
          AND (
                    CASE 
                        WHEN ce.cod_tipo_paciente = '4' THEN '2'
                        ELSE '1'
                    END
                    ) IN {codasegu_clause}
    """
    try:
        df = pd.read_sql(query, engine)
        df2 = pd.read_sql(query2, engine)
    except Exception as e:
        return empty_fig("Atenciones por agrupador"), empty_fig("Atenciones por especialidad"), f"Error ejecutando consulta: {e}", empty_div, None, empty_div, empty_fig("Top 10 diagn??sticos por atenciones")
    if df.empty:
        return (
            empty_fig(f"Atenciones por agrupador - Periodo {periodo}"),
            empty_fig(f"Atenciones por especialidad - Periodo {periodo}"),
            f"Sin datos para periodo {periodo}.",
            empty_div,
            None,
            html.Div("Sin datos resumen.", style={"color": "#b00"}),
            empty_fig(f"Top 10 diagn??sticos por atenciones - Periodo {periodo}"),
        )

    # Gr??fico agrupador
    bar_df = (
        df.assign(agrupador=df["agrupador"].fillna("Sin agrupador"))
          .groupby("agrupador").size().reset_index(name="Atenciones")
          .sort_values("Atenciones", ascending=False).head(10)
    )
    if bar_df.empty:
        fig = empty_fig(f"Atenciones por agrupador - Periodo {periodo}")
        msg_fig = "Sin datos de agrupador."
    else:
        total_agr = bar_df["Atenciones"].sum()
        bar_df["label"] = bar_df["Atenciones"].apply(
            lambda v: f"{v:,.0f} ({(v/total_agr):.1%})" if total_agr else f"{v:,.0f} (0.0%)"
        )
        fig = px.bar(
            bar_df,
            y="agrupador",
            x="Atenciones",
            orientation="h",
            title=f"Atenciones por agrupador - Periodo {periodo}",
            text="label",
            color="Atenciones",
            color_continuous_scale=BAR_COLOR_SCALE,
        )
        fig = style_horizontal_bar(fig, height=320)
        msg_fig = f"{bar_df['Atenciones'].sum():,} atenciones en {bar_df.shape[0]} agrupadores."
    fig.update_layout(
        xaxis_title="Atenciones",
        yaxis_title="Agrupador",
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

    # Gr??fico especialidad (nuevo fig2 junto al de agrupador)
    bar_df2 = (
        df.assign(descripcion_especialidad=df["descripcion_especialidad"].fillna("Sin especialidad"))
          .groupby("descripcion_especialidad").size().reset_index(name="Atenciones")
          .sort_values("Atenciones", ascending=False).head(10)
    )
    if bar_df2.empty:
        fig2 = empty_fig(f"Atenciones por especialidad - Periodo {periodo}")
    else:
        total_esp2 = bar_df2["Atenciones"].sum()
        bar_df2["label"] = bar_df2["Atenciones"].apply(
            lambda v: f"{v:,.0f} ({(v/total_esp2):.1%})" if total_esp2 else f"{v:,.0f} (0.0%)"
        )
        fig2 = px.bar(
            bar_df2,
            y="descripcion_especialidad",
            x="Atenciones",
            orientation="h",
            title=f"Atenciones por especialidad - Periodo {periodo}",
            text="label",
            color="Atenciones",
            color_continuous_scale=BAR_COLOR_SCALE,
        )
        fig2 = style_horizontal_bar(fig2, height=320)
    fig2.update_layout(
        xaxis_title="Atenciones",
        yaxis_title="Especialidad",
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

    # Tabla detalle (df2)
    if df2.empty:
        aggrid_detalle = html.Div("Sin datos detalle (query2).", style={"color": "#b00"})
    else:
        col_defs_detalle = [
            {"headerName": "Servicio", "field": "servicio2"},
            {"headerName": "Actividad", "field": "actividad2"},
            {"headerName": "Subactividad", "field": "subactividad2"},
            {"headerName": "Tipo consulta", "field": "tipo_consulta2"},
            {"headerName": "CodDiag", "field": "coddiag2"},
            {"headerName": "Diagnostico", "field": "diagnostico2"},
            {"headerName": "dni_medico", "field": "dni_medico2", "filter": "agNumberColumnFilter"},
            {"headerName": "acto_med", "field": "acto_med2", "filter": "agNumberColumnFilter"},
            {"headerName": "sexo", "field": "sexo2"},
            {"headerName": "fecha_atencion", "field": "fecha_atencion2"},
            {"headerName": "desc_cl", "field": "desc_cl2"}
        ]
        aggrid_detalle = dag.AgGrid(
            id="tabla-detalle-query2",
            defaultColDef={"sortable": True, "resizable": True, "filter": "agTextColumnFilter", "floatingFilter": True},
            columnDefs=col_defs_detalle,
            rowData=df2.to_dict("records"),
            enableEnterpriseModules=True,
            dashGridOptions={"onFirstDataRendered": {"function": "params.api.autoSizeAllColumns();"}},
            className="ag-theme-alpine",
            style={"height": "500px", "width": "100%"}
        )

    # Tabla resumen
    resumen_df = (
        df.assign(
            descripcion_servicio=df["descripcion_servicio"].fillna("Sin servicio"),
            subactividad=df["subactividad"].fillna("Sin subactividad"),
            sexo=df["sexo"].fillna("Sin sexo"),
            cod_diag=df["cod_diag"].fillna("Sin cod"),
            descripcion_diagnostico=df["descripcion_diagnostico"].fillna("Sin diagn??stico")
        ).groupby(["descripcion_servicio", "subactividad", "sexo", "cod_diag", "descripcion_diagnostico"])
         .size().reset_index(name="Atenciones").sort_values("Atenciones", ascending=False)
         # .head(300)  # eliminado: ahora se muestran todos los grupos
    )
    col_defs_resumen = [
        {"headerName": "Servicio", "field": "descripcion_servicio"},
        {"headerName": "Subactividad", "field": "subactividad"},
        {"headerName": "Sexo", "field": "sexo", "width": 100},
        {"headerName": "CodDiag", "field": "cod_diag", "width": 100},
        {"headerName": "Diagn??stico", "field": "descripcion_diagnostico", "width": 550},
        {"headerName": "Atenciones", "field": "Atenciones", "filter": "agNumberColumnFilter"}
    ]
    resumen_comp = dag.AgGrid(
        id="tabla-resumen-atenciones",
        columnDefs=col_defs_resumen,
        rowData=resumen_df.to_dict("records"),
        defaultColDef={"sortable": True, "resizable": True, "filter": "agTextColumnFilter", "floatingFilter": True},
        dashGridOptions={
            "pinnedBottomRowData": [{
                "descripcion_servicio": f"Total atenciones: {resumen_df['Atenciones'].sum():,}"
            }],
            "onFirstDataRendered": {"function": "params.api.autoSizeAllColumns();"}
        },
        className="ag-theme-alpine",
        style={"height": "400px", "width": "100%"}
    )

    diag_df = df.copy()
    def _sex_simple(s):
        s2 = str(s).strip().upper()
        if s2 in ("M", "MASCULINO", "VARON", "H"):
            return "M"
        if s2 in ("F", "FEMENINO", "MUJER"):
            return "F"
        return "Sin dato"
    diag_df["sexo_simple"] = diag_df["sexo"].apply(_sex_simple)
    diag_df["cod_diag"] = diag_df["cod_diag"].fillna("Sin cod")

    totals_diag = diag_df.groupby("cod_diag").size().reset_index(name="total")
    top_codes = totals_diag.sort_values("total", ascending=False).head(10)["cod_diag"].tolist()
    top_diag_df = diag_df[diag_df["cod_diag"].isin(top_codes)]

    if top_diag_df.empty:
        fig_topdiag = empty_fig(f"Top 10 diagn??sticos por atenciones - Periodo {periodo}")
    else:
        desc_map = (
            diag_df[["cod_diag", "descripcion_diagnostico"]]
            .dropna()
            .drop_duplicates()
            .set_index("cod_diag")["descripcion_diagnostico"]
            .to_dict()
        )
        bar_data = (
            top_diag_df.groupby(["cod_diag", "sexo_simple"])
            .size().reset_index(name="Atenciones")
        )
        order_y = (
            totals_diag[totals_diag["cod_diag"].isin(top_codes)]
            .sort_values("total", ascending=True)["cod_diag"].tolist()
        )
        bar_data["descripcion_diagnostico"] = bar_data["cod_diag"].map(desc_map)

        grand_total = bar_data["Atenciones"].sum()
        bar_data["label"] = bar_data["Atenciones"].apply(
            lambda v: f"{v:,.0f} ({(v/grand_total):.1%})" if grand_total else f"{v:,.0f} (0.0%)"
        )

        fig_topdiag = px.bar(
            bar_data,
            y="cod_diag",
            x="Atenciones",
            color="sexo_simple",
            orientation="h",
            title=f"Top 10 diagn??sticos por atenciones - Periodo {periodo}",
            hover_data={"descripcion_diagnostico": True, "cod_diag": False, "sexo_simple": False, "Atenciones": True},
            color_discrete_map={"M": "#4C78A8", "F": "#B82753", "Sin dato": "#9aa0a6"},
            text="label"
        )
        fig_topdiag.update_traces(
            textposition="outside",
            cliponaxis=False,
            texttemplate="%{text}",
            marker_line_color="rgba(0,0,0,0.06)",
            marker_line_width=1,
            textfont=dict(size=11)
        )
        fig_topdiag.update_layout(
            barmode="group",
            template="simple_white",
            paper_bgcolor="#F9FBFD",
            plot_bgcolor="#F9FBFD",
            margin=dict(l=90, r=32, t=70, b=40),
            title_font=dict(size=18, color=BRAND),
            font=dict(family=FONT_FAMILY, size=12, color="#1F2937"),
            xaxis_title="Atenciones",
            yaxis_title="CodDiag",
            yaxis=dict(categoryorder="array", categoryarray=order_y, ticks="outside", tickfont=dict(color="#1F2937")),
            legend_title_text="Sexo",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="rgba(0,0,0,0.05)",
                borderwidth=1,
            ),
            xaxis=dict(showgrid=True, gridcolor="rgba(10,76,140,0.08)", zeroline=False, ticks="outside"),
            hoverlabel=dict(bgcolor="#FFFFFF", font=dict(family=FONT_FAMILY, color="#0F172A")),
        )
    msg = f"{len(df):,} registros procesados | {msg_fig}"
    return fig, fig2, msg, aggrid_detalle, df2.to_dict("records"), resumen_comp, fig_topdiag

@callback(
    Output("tornado-atenciones-graph", "figure"),
    Output("tornado-atenciones-msg", "children"),
    Input("page-url", "pathname"),
    Input("page-url", "search"),
    State("filter-periodo", "value"),
    State("filter-anio", "value"),
    State("filter-tipo-asegurado", "value")
)
def update_tornado_atenciones(pathname, search, periodo_dropdown, anio_dropdown, tipo_dropdown):
    codcas, periodo, anio, tipo_asegurado = get_codcas_periodo(pathname, search, periodo_dropdown, anio_dropdown, tipo_dropdown)
    codasegu_clause = resolve_tipo_asegurado_clause(tipo_asegurado)
    if not codcas:
        return empty_fig("Sexo y grupo etario vs atenciones"), "Sin ruta."
    if not periodo or not anio:
        return empty_fig("Sexo y grupo etario vs atenciones"), "Faltan filtros requeridos (periodo/anio)."
    engine = create_connection()
    if engine is None:
        return empty_fig("Sexo y grupo etario vs atenciones"), "Error de conexión a la base de datos."

    query = f"""
        SELECT 
            ge.grupo_etario,
            ce.sexo,
            COUNT(*) AS atenciones
        FROM dwsge.dw_consulta_externa_homologacion_{anio}_{periodo} AS ce
        LEFT JOIN dwsge.dim_grupo_etario as ge ON ce.anio_edad = ge.edad
        WHERE ce.cod_centro = '{codcas}'
          AND ce.cod_actividad = '91'
          AND ce.clasificacion in (2,4,6)
          AND ce.cod_variable = '001'
          AND (
                    CASE 
                        WHEN ce.cod_tipo_paciente = '4' THEN '2'
                        ELSE '1'
                    END
                    ) IN {codasegu_clause}
        GROUP BY ge.grupo_etario, ce.sexo
    """
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        return empty_fig("Sexo y grupo etario vs atenciones"), f"Error ejecutando consulta: {e}"
    if df.empty:
        return empty_fig(f"Sexo y grupo etario vs atenciones - Periodo {periodo}"), f"Sin datos para periodo {periodo}."

    # Normalizar sexo
    def norm_sex(s):
        s2 = str(s).strip().upper()
        if s2 in ("M", "MASCULINO", "VARON", "H"):
            return "Masculino"
        if s2 in ("F", "FEMENINO", "MUJER"):
            return "Femenino"
        return s if pd.notna(s) else "Sin dato"

    df["sexo_norm"] = df["sexo"].apply(norm_sex)
    df["grupo_etario"] = df["grupo_etario"].fillna("Sin grupo")

    pv = df.pivot_table(index="grupo_etario", columns="sexo_norm", values="atenciones", aggfunc="sum", fill_value=0)

    def age_key(label):
        m = re.match(r"^\s*(\d+)", str(label))
        return int(m.group(1)) if m else 999

    preferred_groups = [
        ("adulto mayor", "Adulto mayor (60+ años)"),
        ("adulto", "Adulto (30-59 años)"),
        ("joven", "Joven (18-29 años)"),
        ("adolescente", "Adolescente (12-17 años)"),
        ("niño", "Niño (0-11 años)")
    ]

    def order_tuple(label):
        label_lower = str(label).lower()
        for idx, (keyword, _) in enumerate(preferred_groups):
            if keyword in label_lower:
                return (idx, 0)
        return (len(preferred_groups), age_key(label))

    age_order = sorted(list(pv.index), key=order_tuple)

    def prettify_label(label: str) -> str:
        label_lower = str(label).lower()
        for keyword, pretty in preferred_groups:
            if keyword in label_lower:
                return pretty
        return str(label)

    male_vals = pv["Masculino"].reindex(age_order, fill_value=0) if "Masculino" in pv.columns else pd.Series(0, index=age_order)
    fem_vals  = pv["Femenino"].reindex(age_order, fill_value=0) if "Femenino" in pv.columns else pd.Series(0, index=age_order)

    display_labels = [prettify_label(label) for label in age_order]

    grand_total = int(male_vals.sum() + fem_vals.sum())
    male_labels = [f"{v:,} ({(v/grand_total):.1%})" if grand_total else f"{v:,} (0.0%)" for v in male_vals.tolist()]
    fem_labels  = [f"{v:,} ({(v/grand_total):.1%})" if grand_total else f"{v:,} (0.0%)" for v in fem_vals.tolist()]

    fig = go.Figure()
    fig.add_bar(
        y=display_labels,
        x=(-male_vals).tolist(),
        name="Masculino",
        orientation="h",
        marker_color=BRAND,
        marker_line_color="rgba(0,0,0,0.06)",
        marker_line_width=1,
        hovertemplate="<b>%{y}</b><br>Masculino: %{customdata:,}<extra></extra>",
        customdata=male_vals.tolist(),
        text=male_labels,
        texttemplate="%{text}",
        textposition="outside",
        textfont=dict(size=13, color="#0F172A"),
    )
    fig.add_bar(
        y=display_labels,
        x=fem_vals.tolist(),
        name="Femenino",
        orientation="h",
        marker_color=FEMALE,
        marker_line_color="rgba(0,0,0,0.06)",
        marker_line_width=1,
        hovertemplate="<b>%{y}</b><br>Femenino: %{x:,}<extra></extra>",
        text=fem_labels,
        texttemplate="%{text}",
        textposition="outside",
        textfont=dict(size=13, color="#0F172A"),
    )
    fig.update_layout(
        barmode="relative",
        template="simple_white",
        paper_bgcolor="#F9FBFD",
        plot_bgcolor="#F9FBFD",
        margin=dict(l=80, r=32, t=60, b=40),
        title_font=dict(size=18, color=BRAND),
        font=dict(family=FONT_FAMILY, size=12, color="#1F2937"),
        xaxis=dict(
            title="Atenciones",
            showgrid=True,
            gridcolor="rgba(10,76,140,0.08)",
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor="#94a3b8",
            ticks="outside",
            tickformat=",.0f",
            tickfont=dict(color="#475569"),
        ),
        yaxis=dict(
            title="Grupo etario",
            categoryorder="array",
            categoryarray=display_labels,
            showgrid=False,
            ticks="outside",
            tickfont=dict(color="#1F2937"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="right",
            x=0,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="rgba(0,0,0,0.05)",
            borderwidth=1,
        ),
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(family=FONT_FAMILY, color="#0F172A")),
    )

    total_m = int(male_vals.sum())
    total_f = int(fem_vals.sum())
    total = total_m + total_f
    msg = f"Total atenciones: {total:,} | Masculino: {total_m:,} | Femenino: {total_f:,}"

    return fig, msg

# Funci??n auxiliar para aplicar filtro local
def _apply_filter(data_records, filter_model):
    if not filter_model:
        return data_records
    df_local = pd.DataFrame(data_records)
    for col, f in filter_model.items():
        if col not in df_local.columns:
            continue
        ft = f.get("filterType")
        t = f.get("type")
        val = f.get("filter")
        if ft == "text":
            serie = df_local[col].astype(str)
            if t == "contains":
                mask = serie.str.contains(val or "", case=False, na=False)
            elif t == "notContains":
                mask = ~serie.str.contains(val or "", case=False, na=False)
            elif t == "equals":
                mask = serie.str.lower() == str(val or "").lower()
            elif t == "startsWith":
                mask = serie.str.lower().str.startswith(str(val or "").lower())
            elif t == "endsWith":
                mask = serie.str.lower().str.endswith(str(val or "").lower())
            else:
                mask = pd.Series([True]*len(df_local))
            df_local = df_local[mask]
        elif ft == "number":
            serie = pd.to_numeric(df_local[col], errors="coerce")
            try:
                num = float(val) if val is not None else None
            except:
                num = None
            if t == "equals" and num is not None:
                mask = serie == num
            elif t == "greaterThan" and num is not None:
                mask = serie > num
            elif t == "lessThan" and num is not None:
                mask = serie < num
            elif t == "inRange":
                num_to = f.get("filterTo")
                try:
                    num_to = float(num_to) if num_to is not None else None
                except:
                    num_to = None
                if num is not None and num_to is not None:
                    mask = (serie >= num) & (serie <= num_to)
                elif num is not None:
                    mask = serie >= num
                elif num_to is not None:
                    mask = serie <= num_to
                else:
                    mask = pd.Series([True]*len(df_local))
            else:
                mask = pd.Series([True]*len(df_local))
            df_local = df_local[mask]
    return df_local.to_dict("records")

@callback(
    Output("tabla-detalle-query2", "dashGridOptions"),
    Input("tabla-detalle-query2", "filterModel"),
    State("store-detalle-data", "data")
)
def actualizar_total_detalle(filter_model, base_data):
    registros_filtrados = _apply_filter(base_data, filter_model)
    total = len(registros_filtrados)
    return {
        "pinnedBottomRowData": [{
            "servicio2": f"Total filas: {total}"
        }],
        "statusBar": {
            "statusPanels": [
                {"statusPanel": "agAggregationComponent", "align": "right"}
            ]
        }
    }

@callback(
    Output("tabla-resumen-atenciones", "dashGridOptions"),
    Input("tabla-resumen-atenciones", "filterModel"),
    State("tabla-resumen-atenciones", "rowData")
)
def actualizar_total_resumen(filter_model, row_data):
    if not row_data:
        return {"pinnedBottomRowData": [{"descripcion_servicio": "Total atenciones: 0", "Atenciones": 0}]}
    filtrados = _apply_filter(row_data, filter_model)
    df_f = pd.DataFrame(filtrados) if filtrados else pd.DataFrame(columns=["Atenciones"])
    total_att = int(pd.to_numeric(df_f.get("Atenciones", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    return {
        "pinnedBottomRowData": [{
            "descripcion_servicio": f"Total atenciones: {total_att:,}",
            "Atenciones": total_att
        }],
        "statusBar": {
            "statusPanels": [
                {"statusPanel": "agAggregationComponent", "align": "right"}
            ]
        }
    }

@callback(
    Output("download-query1-csv", "data"),
    Input("btn-download-query1", "n_clicks"),
    State("page-url", "pathname"),
    State("page-url", "search"),
    State("filter-periodo", "value"),
    State("filter-anio", "value"),
    State("filter-tipo-asegurado", "value"),
    prevent_initial_call=True
)
def descargar_query1_csv(n_clicks, pathname, search, periodo_dropdown, anio_dropdown, tipo_dropdown):
    codcas, periodo, anio, tipo_asegurado = get_codcas_periodo(pathname, search, periodo_dropdown, anio_dropdown, tipo_dropdown)
    if not codcas or not periodo or not anio:
        return None
    engine = create_connection()
    if engine is None:
        return None
    codasegu_clause = resolve_tipo_asegurado_clause(tipo_asegurado)

    query = f"""
        SELECT 
            ce.cod_servicio,
            ce.cod_especialidad,
            ca.cenasides,
            am.actdes AS actividad,
            ag.agrupador AS agrupador,
            a.actespnom AS subactividad,
            ce.cod_tipo_consulta,
            ce.cod_diag,
            d.diagdes AS descripcion_diagnostico,
            c.servhosdes AS descripcion_servicio,
            e.especialidad AS descripcion_especialidad,
            t.tipcondes AS descripcion_tipo_consulta,
            dni_medico,
            doc_paciente,
            anio_edad,
            cod_tipdoc_paciente,
            sexo,
            fecha_atencion,
            acto_med
        FROM dwsge.dw_consulta_externa_homologacion_{anio}_{periodo} AS ce
        LEFT JOIN dwsge.sgss_cmsho10 AS c ON ce.cod_servicio = c.servhoscod
        LEFT JOIN dwsge.dim_especialidad AS e ON ce.cod_especialidad = e.cod_especialidad
        LEFT JOIN dwsge.sgss_cmtco10 AS t ON ce.cod_tipo_consulta = t.tipconcod
        LEFT JOIN dwsge.sgss_cmdia10 AS d ON ce.cod_diag = d.diagcod
        LEFT JOIN dwsge.sgss_cmace10 AS a ON ce.cod_actividad = a.actcod AND ce.cod_subactividad = a.actespcod
        LEFT JOIN dwsge.sgss_cmact10 AS am ON ce.cod_actividad = am.actcod
        LEFT JOIN dwsge.sgss_cmcas10 AS ca ON ce.cod_oricentro = ca.oricenasicod AND ce.cod_centro = ca.cenasicod
        LEFT JOIN dwsge.dim_agrupador as ag ON ce.cod_agrupador = ag.cod_agrupador
        WHERE ce.cod_centro = '{codcas}'
          AND ce.cod_actividad = '91'
          AND ce.clasificacion in (2,4,6)
          AND ce.cod_variable = '001'
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

    filename = f"total_atenciones_{codcas}_{anio}_{periodo}.csv"
    return dcc.send_data_frame(df.to_csv, filename, index=False, encoding="utf-8-sig", sep="|")

