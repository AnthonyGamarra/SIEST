from dash import html, dcc, register_page, Input, Output, State, callback
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import dash_ag_grid as dag

# Paleta similar a dashboard.py
BRAND = "#0064AF"
CARD_BG = "#FFFFFF"
MUTED = "#6c757d"
FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"
BAR_COLOR_SCALE = ["#D7E9FF", "#92C4F9", "#2E78C7"]
CARD_STYLE = {
    "border": "none",
    "borderRadius": "14px",
    "backgroundColor": CARD_BG,
    "boxShadow": "0 8px 20px rgba(0,0,0,0.08)",
    "padding": "12px",  # antes 16px
}
# NUEVOS ESTILOS TABS
TABS_CONTAINER_STYLE = {
    "backgroundColor": "#fff",
    "border": "1px solid #e3e6eb",
    "borderRadius": "14px",
    "padding": "6px 10px 2px 10px",
    "boxShadow": "0 4px 12px rgba(0,0,0,0.05)"
}
TAB_STYLE = {
    "padding": "10px 18px",
    "fontFamily": FONT_FAMILY,
    "fontSize": "13px",
    "fontWeight": "600",
    "color": MUTED,
    "borderRadius": "10px",
    "margin": "4px 6px",
    "cursor": "pointer",
    "transition": "all .25s",
    "border": "1px solid transparent"
}
TAB_SELECTED_STYLE = {
    **TAB_STYLE,
    "color": BRAND,
    "background": "linear-gradient(145deg,#ffffff,#F3F8FC)",
    "boxShadow": "0 2px 6px rgba(0,0,0,0.08)",
    "border": f"1px solid {BRAND}",
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


def style_horizontal_bar(fig: go.Figure, x_title: str, y_title: str = "", height: int = 360) -> go.Figure:
    title_component = getattr(getattr(fig.layout, "title", None), "text", "") or ""
    fig.update_traces(
        marker=dict(line=dict(color="rgba(0,0,0,0.08)", width=1.2), opacity=0.92),
        textposition="outside",
        cliponaxis=False,
        selector=dict(type="bar"),
    )
    fig.update_layout(
        title=dict(text=title_component, font=dict(size=18, color=BRAND, family=FONT_FAMILY), x=0, xanchor="left"),
        plot_bgcolor="#F9FBFD",
        paper_bgcolor="#F9FBFD",
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

def _parse_periodo(search: str) -> str | None:
    if not search:
        return None
    # search llega como "?periodo=03&otra=x"
    params = dict(
        part.split("=", 1) for part in search.lstrip("?").split("&") if "=" in part
    )
    return params.get("periodo")


def _safe_periodo(raw: str | None) -> str | None:
    if not raw:
        return None
    m = re.fullmatch(r"\d+", str(raw).strip())
    return m.group(0) if m else None

def _safe_codcas(raw: str | None) -> str | None:
    if not raw:
        return None
    m = re.fullmatch(r"[A-Za-z0-9]+", str(raw).strip())
    return m.group(0) if m else None

def _build_query_promedio(periodo: str) -> str:
    table = f"dwsge.dwe_consulta_externa_citados_homologacion_2025_{periodo}"
    return f"""
    SELECT
        f.periodo,
        f.cod_oricentro,	
        f.cod_centro,
        f.cod_servicio,
        percentile_cont(0.50) WITHIN GROUP (ORDER BY f.diferimiento::int) AS p50_diferimiento,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY f.diferimiento::int) AS p75_diferimiento,
        percentile_cont(0.90) WITHIN GROUP (ORDER BY f.diferimiento::int) AS p90_diferimiento,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY f.diferimiento::int) AS p95_diferimiento,
        TRUNC(
            CASE 
                WHEN SUM(f.num_citas::int) = 0 THEN NULL
                ELSE SUM(f.diferimiento::int * f.num_citas::int)::numeric 
                    / SUM(f.num_citas::int)
            END
        , 2) AS promedio_ponderado_diferimiento,
        SUM(f.num_citas::int) AS num_atenciones,
        MAX(diferimiento::int) AS dif_max
    FROM {table} f
    WHERE f.flag_calidad IN ('1','2','3','6')
    AND f.cod_estado = '4'
    AND f.cod_actividad = '91'
    AND f.diferimiento IS NOT NULL
    AND f.diferimiento::int >= 0
    AND f.cod_variable = '001'
    AND f.cod_centro = :codcas
    GROUP BY 
        f.periodo,
        f.cod_oricentro,
        f.cod_centro,
        f.cod_servicio
    ORDER BY dif_max DESC
    """

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

def build_promedio_diferimiento_fig(codcas: str | None, periodo: str | None) -> go.Figure:
    codcas = _safe_codcas(codcas)
    periodo = _safe_periodo(periodo)
    if not codcas or not periodo:
        return empty_fig("Promedio ponderado de diferimiento por servicio")
    engine = create_connection()
    if engine is None:
        return empty_fig("Promedio ponderado de diferimiento por servicio")
    try:
        df = pd.read_sql(_build_query_promedio(periodo), con=engine, params={"codcas": codcas})
    except Exception:
        return empty_fig("Promedio ponderado de diferimiento por servicio")
    if df.empty or "promedio_ponderado_diferimiento" not in df.columns:
        return empty_fig("Promedio ponderado de diferimiento por servicio")
    df_plot = (
        df[["cod_servicio", "promedio_ponderado_diferimiento"]]
        .dropna().head(10)
        .sort_values("promedio_ponderado_diferimiento", ascending=False)
    )
    fig = px.bar(
        df_plot,
        x="promedio_ponderado_diferimiento",
        y="cod_servicio",
        orientation="h",
        text="promedio_ponderado_diferimiento",
        color="promedio_ponderado_diferimiento",
        color_continuous_scale=BAR_COLOR_SCALE,
        title="Promedio ponderado del diferimiento por servicio",
    )
    fig.update_traces(texttemplate="%{x:.2f}")
    return style_horizontal_bar(fig, x_title="Promedio ponderado del diferimiento (días)", y_title="Servicio", height=420)

def build_percentiles_diferimiento_fig(codcas: str | None, periodo: str | None) -> go.Figure:
    codcas = _safe_codcas(codcas)
    periodo = _safe_periodo(periodo)
    if not codcas or not periodo:
        return empty_fig("Percentiles de diferimiento por servicio")
    engine = create_connection()
    if engine is None:
        return empty_fig("Percentiles de diferimiento por servicio")
    try:
        df = pd.read_sql(_build_query_promedio(periodo), con=engine, params={"codcas": codcas})
    except Exception:
        return empty_fig("Percentiles de diferimiento por servicio")
    needed_cols = ["cod_servicio", "p50_diferimiento", "p75_diferimiento", "p90_diferimiento", "p95_diferimiento"]
    if df.empty or any(col not in df.columns for col in needed_cols):
        return empty_fig("Percentiles de diferimiento por servicio")

    df_box = df[needed_cols].dropna()
    df_box["cod_servicio"] = df_box["cod_servicio"].astype(str)
    order = (
        df_box.sort_values("p50_diferimiento", ascending=False)["cod_servicio"]
        .drop_duplicates()
        .head(12)
        .tolist()
    )
    df_box = df_box[df_box["cod_servicio"].isin(order)]

    fig = go.Figure()
    for _, row in df_box.iterrows():
        median = row["p50_diferimiento"]
        q3 = row["p75_diferimiento"]
        q1 = max(0, median - (q3 - median))
        iqr = q3 - q1
        lowerfence = max(0, q1 - 1.5 * iqr)
        upperfence = row["p95_diferimiento"]
        fig.add_trace(go.Box(
            name=row["cod_servicio"],
            q1=[q1],
            median=[median],
            q3=[q3],
            lowerfence=[lowerfence],
            upperfence=[upperfence],
            marker_color=BAR_COLOR_SCALE[2],
            line_color=BAR_COLOR_SCALE[1],
            fillcolor=BAR_COLOR_SCALE[0],
            opacity=0.75,
            boxpoints=False
        ))

    fig.update_layout(
        title=dict(text="Percentiles de diferimiento por servicio", font=dict(size=18, color=BRAND, family=FONT_FAMILY), x=0, xanchor="left"),
        plot_bgcolor="#F9FBFD",
        paper_bgcolor="#F9FBFD",
        font=dict(family=FONT_FAMILY, size=12, color="#1F2937"),
        margin=dict(l=60, r=32, t=70, b=120),  # más espacio para ticks
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(family=FONT_FAMILY, color="#0F172A")),
        xaxis=dict(
            title="Servicio",
            tickangle=-45,
            showgrid=False,
            type="category",
            categoryorder="array",
            categoryarray=order,
            tickmode="array",
            tickvals=order,
            ticktext=order,
            showticklabels=True,
            tickfont=dict(size=10, color="#1F2937"),
        ),
        yaxis=dict(title="Días de diferimiento", gridcolor="rgba(10,76,140,0.08)", zeroline=False),
        showlegend=False,
        boxmode="group",
    )
    fig.update_xaxes(showticklabels=True)
    return fig

# Placeholders for initial render
promedio_diferimiento_fig = empty_fig("Promedio ponderado de diferimiento por servicio")
percentiles_diferimiento_fig = empty_fig("Percentiles de diferimiento por servicio")

# Layout sin verificador de query
layout = html.Div([
    dcc.Location(id="hp-page-url", refresh=False),
    html.Div([
        # Lado izquierdo: título + subtítulo
        html.Div([
            html.H4("Detalle DESERCIONES CONSULTA EXTERNA",
                    style={"margin": 0, "color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700}),
            html.P("Visualización del periodo seleccionado.",
                   style={"color": MUTED, "fontSize": "13px", "marginTop": "4px", "fontFamily": FONT_FAMILY})
        ]),
        # Lado derecho: botón descargar
        html.Div([
            html.Button(
                "Descargar CSV",
                id="td-download-btn",
                n_clicks=0,
                style={
                    "backgroundColor": BRAND,
                    "color": "#fff",
                    "border": "none",
                    "borderRadius": "8px",
                    "padding": "8px 12px",
                    "fontFamily": FONT_FAMILY,
                    "fontSize": "13px",
                    "cursor": "pointer",
                    "boxShadow": "0 2px 6px rgba(0,0,0,0.12)"
                }
            ),
            dcc.Download(id="td-download")  # <-- cambiado id
        ])
    ], style={
        "padding": "10px 16px",
        "background": "linear-gradient(90deg,#ffffff 0%,#F0F6FC 100%)",
        "border": "1px solid #e9ecef",
        "borderRadius": "14px",
        "boxShadow": "0 4px 12px rgba(0,0,0,0.06)",
        "marginBottom": "12px",  # antes 18px
        "display": "flex",
        "justifyContent": "space-between",
        "alignItems": "center",
        "gap": "10px"  # antes 16px
    }),
    # PESTAÑAS
    dcc.Tabs(
        id="",
        value="",
        style={"border": "none"},
        parent_style={"marginTop": "12px"},
        className="custom-tabs",
        children=[
            dcc.Tab(
                label="",
                value="",
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=html.Div([
                    html.Div([
                        dcc.Loading(
                            html.Div([
                                # Gráfico 1: servicio vs total deserciones
                                html.Div([
                                    dcc.Graph(
                                        id="hp-fig-promedio-diferimiento-servicio",
                                        figure=promedio_diferimiento_fig,
                                        style={"height": "420px"}
                                    )
                                ], style={"flex": 1, "minWidth": "300px"}),
                                # Gráfico 2: percentiles por servicio
                                html.Div([
                                    dcc.Graph(
                                        id="hp-fig-percentiles-diferimiento-servicio",
                                        figure=percentiles_diferimiento_fig,
                                        style={"height": "420px"}
                                    )
                                ], style={"flex": 1, "minWidth": "300px"}),
                            ], style={"display": "flex", "gap": "8px", "flexWrap": "wrap"}),
                            type="dot"
                        )
                    ], style={**CARD_STYLE}),
                    # Segundo bloque
                    html.Div([
                        dcc.Loading(
                            html.Div([
                                # Gráfico 3: agrupador vs deserciones
                                html.Div([

                                ], style={"flex": 1, "minWidth": "300px"}),
                                # Gráfico 4: especialidad vs deserciones
                                html.Div([
                                    dcc.Graph(
                                        id="",
                                        figure=empty_fig("Deserciones por especialidad"),
                                        style={"height": "360px"}
                                    )
                                ], style={"flex": 1, "minWidth": "300px"}),
                            ], style={"display": "flex", "gap": "8px", "flexWrap": "wrap"}),
                            type="dot"
                        ),
                        html.Div(
                            id="hp-total-msg",
                            style={"marginTop": "6px", "color": MUTED, "fontFamily": FONT_FAMILY, "fontSize": "12px", "fontWeight": "bold"}
                        )
                    ], style={**CARD_STYLE, "marginTop": "12px"}),
                    # Tercer bloque: reemplazado por tabla resumen horas
                    html.Div([
                        html.H5("Resumen deserción por consulta externa",
                                style={"color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 600,
                                       "marginBottom": "8px"}),
                    ], style={**CARD_STYLE, "marginTop": "12px"})
                ], style={"padding": "4px"})
            ),
        ],
        content_style=TABS_CONTAINER_STYLE
    ),
    # Stores
    dcc.Store(id="hp-store-data")
], style={
    "maxWidth": "1400px",
    "margin": "0 auto",
    "padding": "4px 4px 20px 4px",  
    "fontFamily": FONT_FAMILY
})

# Registrar la página con el layout explícito para evitar NoLayoutException
register_page(
    __name__,
    path_template="/dash/diferimiento/<codcas>",
    name="diferimiento",
    layout=layout
)

@callback(
    Output("hp-fig-promedio-diferimiento-servicio", "figure"),
    Output("hp-fig-percentiles-diferimiento-servicio", "figure"),
    Input("hp-page-url", "pathname"),
    Input("hp-page-url", "search"),
)
def update_figures(pathname, search):
    codcas, periodo = get_codcas_periodo(pathname, search, None)
    return (
        build_promedio_diferimiento_fig(codcas, periodo),
        build_percentiles_diferimiento_fig(codcas, periodo),
    )