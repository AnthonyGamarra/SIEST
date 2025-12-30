from dash import html, dcc, register_page, Input, Output, State, callback
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import dash_ag_grid as dag

# Paleta similar a dashboard.py
BRAND = "#0064AF"
BRAND_SOFT = "#D7E9FF"
CARD_BG = "#FFFFFF"
TEXT = "#1C1F26"
MUTED = "#6B7280"
BORDER = "#E5E7EB"
FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"
BAR_COLOR_SCALE = ["#D7E9FF", "#92C4F9", "#2E78C7"]
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

def style_horizontal_bar(fig: go.Figure, x_title: str, y_title: str, height: int = 340) -> go.Figure:
    title_text = getattr(getattr(fig.layout, "title", None), "text", "") or ""
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>Horas efectivas: %{x:,.0f}<br>%{customdata[0]:.1%}<extra></extra>",
        texttemplate="%{text}",
        textposition="outside",
        cliponaxis=False,
        marker=dict(line=dict(color="rgba(0,0,0,0.08)", width=1.2), opacity=0.92),
        selector=dict(type="bar"),
    )
    fig.update_layout(
        title=dict(text=title_text, font=dict(size=18, color=BRAND, family=FONT_FAMILY), x=0, xanchor="left"),
        plot_bgcolor="#F9FBFD",
        paper_bgcolor="#F9FBFD",
        margin=dict(l=90, r=32, t=70, b=40),
        font=dict(family=FONT_FAMILY, size=12, color="#1F2937"),
        xaxis=dict(
            title=x_title,
            showgrid=True,
            gridcolor="rgba(10,76,140,0.08)",
            zeroline=False,
            ticks="outside",
            tickformat=",.0f",
            tickfont=dict(color="#475569"),
        ),
        yaxis=dict(
            title=y_title,
            showgrid=False,
            ticks="outside",
            tickfont=dict(color="#1F2937"),
        ),
        bargap=0.18,
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(family=FONT_FAMILY, color="#0F172A")),
        showlegend=False,
        height=height,
    )
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_coloraxes(showscale=False)
    return fig

# Helpers reutilizables
def _parse_periodo(search: str) -> str | None:
    if not search:
        return None
    # search llega como "?periodo=03&otra=x"
    params = dict(
        part.split("=", 1) for part in search.lstrip("?").split("&") if "=" in part
    )
    return params.get("periodo")

def get_codcas_periodo(pathname: str, search: str, periodo_dropdown: str):
    if not pathname:
        return None, None
    import secure_code as sc
    codcas = pathname.rstrip("/").split("/")[-1]
    codcas = sc.decode_code(codcas)
    periodo = _parse_periodo(search) or periodo_dropdown
    return codcas, periodo

# Layout sin verificador de query
layout = html.Div([
    dcc.Location(id="he-page-url", refresh=False),
    html.Div([
        # Header con icono
        html.Div([
            html.Div([
                html.I(className="bi bi-clock-history", style={'fontSize': '26px', 'color': BRAND, 'marginRight': '12px'}),
                html.Div([
                    html.H4("Horas efectivas por consulta externa",
                            style={"margin": 0, "color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700, "letterSpacing": "-0.3px"}),
                    html.P("⏱️ Distribución y resumen de horas efectivas del periodo seleccionado",
                           style={"color": MUTED, "fontSize": "13px", "marginTop": "6px", "fontFamily": FONT_FAMILY})
                ])
            ], style={'display': 'flex', 'alignItems': 'center', 'flex': 1})
        ], style={'flex': 1}),
        # Lado derecho: botón descargar
        html.Div([
            html.Button(
                [html.I(className="bi bi-download me-2"), "Descargar CSV"],
                id="he-download-btn",
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
            dcc.Download(id="he-download")
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
    # PESTAÑAS
    dcc.Tabs(
        id="he-main-tabs",
        value="tab-graficos",
        style={"border": "none"},
        parent_style={"marginTop": "12px"},
        className="custom-tabs",
        children=[
            dcc.Tab(
                label="Horas efectivas",
                value="tab-graficos",
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=html.Div([
                    html.Div([
                        dcc.Loading(
                            html.Div([
                                # NUEVO: contenedor flex para 2 gráficos
                                html.Div([
                                    dcc.Graph(
                                        id="he-servicio-graph",
                                        config=GRAPH_CONFIG,
                                        style={"height": "340px", "width": "100%"}
                                    )
                                ], style={"flex": 1, "minWidth": "320px"}),
                                html.Div([
                                    dcc.Graph(
                                        id="he-subactividad-graph",
                                        config=GRAPH_CONFIG,
                                        style={"height": "340px", "width": "100%"}
                                    )
                                ], style={"flex": 1, "minWidth": "320px"}),
                            ], style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
                            type="dot"
                        )
                    ], style={**CARD_STYLE}),
                    # Segundo bloque
                    html.Div([
                        dcc.Loading(
                            html.Div([
                                # NUEVO: gráficos de barras de totales
                                html.Div([
                                    dcc.Graph(
                                        id="he-agrupador-graph",
                                        config=GRAPH_CONFIG,
                                        style={"height": "340px", "width": "100%"}
                                    )
                                ], style={"flex": 1, "minWidth": "320px"}),
                                html.Div([
                                    dcc.Graph(
                                        id="he-especialidad-graph",
                                        config=GRAPH_CONFIG,
                                        style={"height": "340px", "width": "100%"}
                                    )
                                ], style={"flex": 1, "minWidth": "320px"}),
                            ], style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
                            type="dot"
                        ),
                        html.Div(
                            id="he-total-msg",
                            style={"marginTop": "10px", "color": MUTED, "fontFamily": FONT_FAMILY, "fontSize": "12px", "fontWeight": "600"}
                        )
                    ], style={**CARD_STYLE}),
                    # Tercer bloque: reemplazado por tabla resumen horas
                    html.Div([
                        html.H5("Resumen horas programadas",
                                style={"color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700,
                                       "marginBottom": "12px", "letterSpacing": "-0.2px"}),
                        dag.AgGrid(
                            id="he-grid",
                            columnDefs=[],
                            rowData=[],
                            defaultColDef={
                                "resizable": True,
                                "sortable": True,
                                "filter": True,
                                "wrapText": True,
                                "autoHeight": True,
                                "floatingFilter": True
                            },
                            style={"height": "420px", "width": "100%"},
                            dashGridOptions={
                                "animateRows": True
                            }
                        ),
                        html.Div(id="he-tornado-msg",
                                 style={"marginTop": "6px", "color": MUTED, "fontFamily": FONT_FAMILY,
                                        "fontSize": "12px", "fontWeight": "bold"})
                    ], style={**CARD_STYLE, "marginTop": "12px"})
                ], style={"padding": "8px"})
            ),
        ],
        content_style=TABS_CONTAINER_STYLE
    ),
    # Stores
    dcc.Store(id="he-store-data")
], style={
    "width": "100%",
    "maxWidth": "1600px",
    "margin": "0 auto",
    "padding": "8px 16px 24px 16px",
    "fontFamily": FONT_FAMILY
})


# Conexión DB
def create_connection():
    try:
        engine = create_engine('postgresql+psycopg2://postgres:admin@10.0.29.117:5433/DW_ESTADISTICA')
        with engine.connect():
            pass
        return engine
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        return None

def _parse_periodo(search: str) -> str | None:
    if not search:
        return None
    # search llega como "?periodo=03&otra=x"
    params = dict(
        part.split("=", 1) for part in search.lstrip("?").split("&") if "=" in part
    )
    return params.get("periodo")

def get_codcas_periodo(pathname: str, search: str, periodo_dropdown: str):
    if not pathname:
        return None, None
    codcas = pathname.rstrip("/").split("/")[-1]
    periodo = _parse_periodo(search) or periodo_dropdown
    return codcas, periodo

def build_query(periodo: str, codcas: str) -> str:
    return f"""
        SELECT 
            c.servhosdes as servicio,
            ag.agrupador,
            e.especialidad,
            a.actespnom as subactividad,
            ce.hras_prog
        FROM dwsge.dwe_consulta_externa_horas_efectivas_2025_{periodo} AS ce
        LEFT JOIN dwsge.sgss_cmsho10 AS c 
            ON ce.cod_servicio = c.servhoscod
        LEFT JOIN dwsge.dim_especialidad AS e
            ON ce.cod_especialidad = e.cod_especialidad
        LEFT JOIN dwsge.sgss_cmace10 AS a
            ON ce.cod_actividad = a.actcod
            AND ce.cod_subactividad = a.actespcod
        LEFT JOIN dwsge.sgss_cmact10 AS am
            ON ce.cod_actividad = am.actcod
        LEFT JOIN dwsge.sgss_cmcas10 AS ca
            ON ce.cod_oricentro = ca.oricenasicod
            AND ce.cod_centro = ca.cenasicod
        LEFT JOIN dwsge.dim_agrupador AS ag ON ce.cod_agrupador = ag.cod_agrupador
        WHERE ce.cod_centro = '{codcas}'
        AND ce.cod_actividad = '91'
        AND ce.cod_variable = '001';
"""

# Registrar la página con el layout explícito para evitar NoLayoutException
register_page(
    __name__,
    path_template="/dash/horas_efectivas/<codcas>",
    name="horas_efectivas",
    layout=layout
)

# NUEVO: carga de datos al Store
@callback(
    Output("he-store-data", "data"),
    Input("he-page-url", "pathname"),
    Input("he-page-url", "search"),
    prevent_initial_call=True
)
def load_data(pathname, search):
    if not pathname:
        return None
    codcas = pathname.rstrip("/").split("/")[-1]
    periodo = _parse_periodo(search) or "01"
    engine = create_connection()
    if engine is None:
        return None
    query = build_query(periodo, codcas)
    try:
        df = pd.read_sql(query, engine)
        if df.empty:
            return None
        return df.to_dict("records")
    except Exception as e:
        print(f"Query error: {e}")
        return None

# NUEVO: generación de figuras
@callback(
    Output("he-servicio-graph", "figure"),
    Output("he-subactividad-graph", "figure"),
    Input("he-store-data", "data")
)
def update_figs(data):
    if not data:
        return empty_fig("Horas Efectivas por Servicio"), empty_fig("Horas Efectivas por Subactividad")
    df = pd.DataFrame(data)
    df["hras_prog"] = pd.to_numeric(df["hras_prog"], errors="coerce").fillna(0)
    total_global = float(df["hras_prog"].sum()) or 0.0

    svc = (
        df.groupby("servicio", dropna=False)["hras_prog"]
          .sum()
          .sort_values(ascending=False)
          .head(10)
          .reset_index()
    )
    svc["pct"] = svc["hras_prog"] / total_global if total_global else 0
    svc["pct"] = svc["pct"].fillna(0)
    svc["text_label"] = svc.apply(lambda r: f"{r['hras_prog']:,} ({r['pct']:.1%})", axis=1)

    fig_serv = px.bar(
        svc,
        x="hras_prog",
        y="servicio",
        orientation="h",
        title="Horas Efectivas por Servicio",
        custom_data=["pct"],
        color="hras_prog",
        color_continuous_scale=BAR_COLOR_SCALE,
        text="text_label",
    )
    fig_serv = style_horizontal_bar(fig_serv, "Horas efectivas", "Servicio")

    sub = (
        df.groupby("subactividad", dropna=False)["hras_prog"]
          .sum()
          .sort_values(ascending=False)
          .head(10)
          .reset_index()
    )
    sub["pct"] = sub["hras_prog"] / total_global if total_global else 0
    sub["pct"] = sub["pct"].fillna(0)
    sub["text_label"] = sub.apply(lambda r: f"{r['hras_prog']:,} ({r['pct']:.1%})", axis=1)

    fig_sub = px.bar(
        sub,
        x="hras_prog",
        y="subactividad",
        orientation="h",
        title="Horas Efectivas por Subactividad",
        custom_data=["pct"],
        color="hras_prog",
        color_continuous_scale=BAR_COLOR_SCALE,
        text="text_label",
    )
    fig_sub = style_horizontal_bar(fig_sub, "Horas efectivas", "Subactividad")
    return fig_serv, fig_sub

@callback(
    Output("he-agrupador-graph", "figure"),
    Output("he-especialidad-graph", "figure"),
    Input("he-store-data", "data")
)
def update_second_figs(data):
    if not data:
        return empty_fig("Horas Efectivas por Agrupador"), empty_fig("Horas Efectivas por Especialidad")
    df = pd.DataFrame(data)
    df["hras_prog"] = pd.to_numeric(df["hras_prog"], errors="coerce").fillna(0)
    total_global = float(df["hras_prog"].sum()) or 0.0

    agr = (
        df.groupby("agrupador", dropna=False)["hras_prog"]
          .sum()
          .sort_values(ascending=False)
          .head(10)
          .reset_index()
    )
    agr["pct"] = agr["hras_prog"] / total_global if total_global else 0
    agr["pct"] = agr["pct"].fillna(0)
    agr["text_label"] = agr.apply(lambda r: f"{r['hras_prog']:,} ({r['pct']:.1%})", axis=1)

    fig_agr = px.bar(
        agr,
        x="hras_prog",
        y="agrupador",
        orientation="h",
        title="Horas Efectivas por Agrupador",
        custom_data=["pct"],
        color="hras_prog",
        color_continuous_scale=BAR_COLOR_SCALE,
        text="text_label",
    )
    fig_agr = style_horizontal_bar(fig_agr, "Horas efectivas", "Agrupador")

    esp = (
        df.groupby("especialidad", dropna=False)["hras_prog"]
          .sum()
          .sort_values(ascending=False)
          .head(10)
          .reset_index()
    )
    esp["pct"] = esp["hras_prog"] / total_global if total_global else 0
    esp["pct"] = esp["pct"].fillna(0)
    esp["text_label"] = esp.apply(lambda r: f"{r['hras_prog']:,} ({r['pct']:.1%})", axis=1)

    fig_esp = px.bar(
        esp,
        x="hras_prog",
        y="especialidad",
        orientation="h",
        title="Horas Efectivas por Especialidad",
        custom_data=["pct"],
        color="hras_prog",
        color_continuous_scale=BAR_COLOR_SCALE,
        text="text_label",
    )
    fig_esp = style_horizontal_bar(fig_esp, "Horas efectivas", "Especialidad")
    return fig_agr, fig_esp

@callback(
    Output("he-grid", "rowData"),
    Output("he-grid", "columnDefs"),
    Output("he-grid", "pinnedBottomRowData"),
    Input("he-store-data", "data")
)
def update_grid(data):
    if not data:
        return [], [
            {"headerName": "Servicio", "field": "servicio"},
            {"headerName": "Subactividad", "field": "subactividad"},
            {"headerName": "Agrupador", "field": "agrupador"},
            {"headerName": "Especialidad", "field": "especialidad"},
            {"headerName": "Horas Efectivas", "field": "horas_efectivas"}
        ], []
    df = pd.DataFrame(data)
    df = df[["servicio", "subactividad", "agrupador", "especialidad", "hras_prog"]].copy()
    df.rename(columns={"hras_prog": "horas_efectivas"}, inplace=True)
    total = df["horas_efectivas"].sum()
    df["total_variable"] = total
    # Formatear horas como int
    df["horas_efectivas"] = df["horas_efectivas"].round(0).astype(int)
    df["total_variable"] = df["total_variable"].round(0).astype(int)

    column_defs = [
        {"headerName": "Servicio", "field": "servicio", "width": 500},
        {"headerName": "Subactividad", "field": "subactividad"},
        {"headerName": "Agrupador", "field": "agrupador"},
        {"headerName": "Especialidad", "field": "especialidad"},
        {"headerName": "Horas Efectivas", "field": "horas_efectivas", "type": "numericColumn", "valueFormatter": "d3.format(',')(value)"},
    ]

    pinned = [{
        "servicio": "TOTAL",
        "subactividad": "",
        "agrupador": "",
        "especialidad": "",
        "horas_efectivas": int(total)
    }]

    return df.to_dict("records"), column_defs, pinned