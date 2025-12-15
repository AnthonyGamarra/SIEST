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

def style_horizontal_bar(fig: go.Figure, x_title: str, y_title: str) -> go.Figure:
    title_text = getattr(getattr(fig.layout, "title", None), "text", "") or ""
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>Número de citas: %{x:,.0f}<br>%{customdata[0]:.1%}<extra></extra>",
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
    )
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_coloraxes(showscale=False)
    return fig

# Helpers reutilizables
def get_codcas_periodo(pathname: str, search: str, periodo_dropdown: str):
    if not pathname:
        return None, None
    codcas = pathname.rstrip("/").split("/")[-1]
    periodo = _parse_periodo(search) or periodo_dropdown
    return codcas, periodo

# Layout sin verificador de query
layout = html.Div([
    dcc.Location(id="page-url", refresh=False),
    html.Div([
        # Header con icono
        html.Div([
            html.Div([
                html.I(className="bi bi-journal-medical", style={'fontSize': '26px', 'color': BRAND, 'marginRight': '12px'}),
                html.Div([
                    html.H4("Citas por consulta externa",
                            style={"margin": 0, "color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700, "letterSpacing": "-0.3px"}),
                    html.P("📅 Distribución y top de citas del periodo seleccionado",
                           style={"color": MUTED, "fontSize": "13px", "marginTop": "6px", "fontFamily": FONT_FAMILY})
                ])
            ], style={'display': 'flex', 'alignItems': 'center', 'flex': 1})
        ], style={'flex': 1}),
        # Lado derecho: botón descargar
        html.Div([
            html.Button(
                [html.I(className="bi bi-download me-2"), "Descargar CSV"],
                id="tc-download-btn",
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
            dcc.Download(id="tc-download")
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
        id="main-tabs",
        value="tab-graficos",
        style={"border": "none"},
        parent_style={"marginTop": "12px"},
        className="custom-tabs",
        children=[
            dcc.Tab(
                label="Número de citas",
                value="tab-graficos",
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=html.Div([
                    html.Div([
                        dcc.Loading(
                            html.Div([
                                # NUEVO: contenedor flex para 2 gráficos
                                html.Div([
                                    dcc.Graph(id="graph-top-subactividad", config=GRAPH_CONFIG, style={"height": "340px", "width": "100%"}),
                                ], style={"flex": 1, "minWidth": "320px"}),
                                html.Div([
                                    dcc.Graph(id="graph-top-servicio", config=GRAPH_CONFIG, style={"height": "340px", "width": "100%"}),
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
                                html.Div(
                                    dcc.Graph(id="graph-total-servicio", config=GRAPH_CONFIG, style={"height": "340px", "width": "100%"}),
                                    style={"flex": 1, "minWidth": "320px"}
                                ),
                                html.Div(
                                    dcc.Graph(id="graph-total-subactividad", config=GRAPH_CONFIG, style={"height": "340px", "width": "100%"}),
                                    style={"flex": 1, "minWidth": "320px"}
                                ),
                            ], style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
                            type="dot"
                        ),
                        html.Div(
                            id="total-citados-msg",
                            style={"marginTop": "6px", "color": MUTED, "fontFamily": FONT_FAMILY, "fontSize": "12px", "fontWeight": "bold"}
                        )
                    ], style={**CARD_STYLE, "marginTop": "12px"}),
                    # Tercer bloque: Tornado (movido dentro del primer tab)
                    html.Div([
                        html.H5("Número de citas por estado",
                                style={"color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700, "marginBottom": "12px", "letterSpacing": "-0.2px"}),
                        dcc.Loading(
                            html.Div([
                                html.Div(
                                    # Aumentar altura para agrandar el círculo
                                    dcc.Graph(id="pie-estado-cita", config=GRAPH_CONFIG, style={"height": "420px", "width": "100%"}),
                                    style={"flex": 1, "minWidth": "320px"}
                                ),
                            ]),
                            type="dot"
                        ),
                        html.Div(id="tornado-citados-msg",
                                 style={"marginTop": "6px", "color": MUTED, "fontFamily": FONT_FAMILY,
                                        "fontSize": "12px", "fontWeight": "bold"})
                    ], style={**CARD_STYLE, "marginTop": "12px"})
                ], style={"padding": "8px"})
            ),
            # NUEVA TAB Número de citas x servicio
            dcc.Tab(
                label="Número de citas x servicio",
                value="tab-vacia",
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=html.Div([
                    html.Div([
                        html.H5(
                            "Citas por servicio",
                            style={"color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 600, "marginBottom": "8px"}
                        ),
                        # Filtro + gráfico de tendencia (NUEVO, va antes de la tabla)
                        html.Div([
                            html.Div([

                            ], style={"display": "flex", "flexDirection": "column", "gap": "4px"}),
                            html.Div(style={"flex": 1})
                        ], style={"display": "flex", "alignItems": "end", "gap": "12px", "marginBottom": "10px"}),
                        dcc.Loading(
                        ),
                        # Tabla (ya existente) debajo del gráfico
                        html.Div(id="tabla-prod-servicio-wrapper")
                    ], style={**CARD_STYLE}),
                ], style={"padding": "4px"})
            )
        ],
        content_style=TABS_CONTAINER_STYLE
    ),
    # Stores
    dcc.Store(id="store-detalle-data")
], style={
    "width": "100%",
    "maxWidth": "1600px",
    "margin": "0 auto",
    "padding": "8px 16px 24px 16px",
    "fontFamily": FONT_FAMILY
})


# Registrar página
register_page(
    __name__,
    path_template="/dash/total_citados/<codcas>",
    name="total_citados",
    layout=layout
)

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

# REEMPLAZO: función para construir query dinámicamente
def build_query(periodo: str, codcas: str) -> str:
    return f"""
    SELECT
        ce.cod_servicio,
        ce.cod_especialidad,
        ca.cenasides,
        am.actdes AS actividad,
        ag.agrupador AS agrupador,
        a.actespnom AS detalle_subactividad,
        c.servhosdes AS descripcion_servicio,
        e.especialidad AS descripcion_especialidad,
        cb.estcitnom AS estado_cita,
        ct.tipopacinom AS tipo_paciente,
        ce.cod_paciente,
        ce.acto_med
    FROM dwsge.dwe_consulta_externa_citados_homologacion_2025_{periodo} AS ce
    LEFT JOIN dwsge.sgss_cmsho10 AS c ON ce.cod_servicio = c.servhoscod
    LEFT JOIN dwsge.dim_especialidad AS e ON ce.cod_especialidad = e.cod_especialidad
    LEFT JOIN dwsge.sgss_cmace10 AS a ON ce.cod_actividad = a.actcod AND ce.cod_subactividad = a.actespcod
    LEFT JOIN dwsge.sgss_cmact10 AS am ON ce.cod_actividad = am.actcod
    LEFT JOIN dwsge.sgss_cmcas10 AS ca ON ce.cod_oricentro = ca.oricenasicod AND ce.cod_centro = ca.cenasicod
    LEFT JOIN dwsge.sgss_cbeci10 AS cb ON cb.estcitcod = ce.cod_estado
    LEFT JOIN dwsge.dim_agrupador AS ag ON ce.cod_agrupador = ag.cod_agrupador
    LEFT JOIN dwsge.sgss_cbtpc10 AS ct ON ct.tipopacicod = ce.cod_paciente
    WHERE ce.cod_centro = '{codcas}'
      AND ce.cod_actividad = '91'
      AND ce.cod_variable = '001'
      AND ce.cod_estado <>'0'
    """

# Callback nuevo para los dos gráficos top10
@callback(
    Output("graph-top-servicio", "figure"),
    Output("graph-top-subactividad", "figure"),
    # NUEVO: salida para pie
    Output("pie-estado-cita", "figure"),
    # NUEVO: salidas para totales (segundo bloque)
    Output("graph-total-servicio", "figure"),
    Output("graph-total-subactividad", "figure"),
    Input("page-url", "pathname"),
    Input("page-url", "search"),
)
def update_top_bars(pathname, search):
    # Resolver periodo (default '01' si no viene) y codcas
    periodo = _parse_periodo(search) or "01"
    if not pathname:
        return (
            empty_fig("Top 10 servicios"),
            empty_fig("Top 10 subactividades"),
            empty_fig("Tipo de paciente"),
            empty_fig("Total citas por servicio"),
            empty_fig("Total citas por subactividad"),
        )
    codcas = pathname.rstrip("/").split("/")[-1]

    engine = create_connection()
    if engine is None:
        return (
            empty_fig("Top 10 servicios (sin conexión)"),
            empty_fig("Top 10 subactividades (sin conexión)"),
            empty_fig("Tipo de paciente"),
            empty_fig("Total citas por servicio"),
            empty_fig("Total citas por subactividad"),
        )
    query = build_query(periodo, codcas)
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        print(f"Query error: {e}")
        return (
            empty_fig("Top 10 servicios (error)"),
            empty_fig("Top 10 subactividades (error)"),
            empty_fig("Tipo de paciente"),
            empty_fig("Total citas por servicio"),
            empty_fig("Total citas por subactividad"),
        )
    if df.empty:
        return (
            empty_fig("Top 10 servicios (sin datos)"),
            empty_fig("Top 10 subactividades (sin datos)"),
            empty_fig("Tipo de paciente (sin datos)"),
            empty_fig("Total citas por servicio (sin datos)"),
            empty_fig("Total citas por subactividad (sin datos)"),
        )

    # Top por servicio (cod_servicio)
    top_act_esp = (
        df.assign(cod_servicio=df["detalle_subactividad"].fillna("Sin subactividad"))
          .groupby("detalle_subactividad", dropna=False)
          .size()
          .reset_index(name="citas")
          .sort_values("citas", ascending=False)
          .head(10)
          .sort_values("citas")  # Para que horizontal muestre mayor arriba
    )
    # Top por descripción de servicio
    top_desc_servicio = (
        df.assign(descripcion_servicio=df["descripcion_servicio"].fillna("Sin servicio"))
          .groupby("descripcion_servicio", dropna=False)
          .size()
          .reset_index(name="citas")
          .sort_values("citas", ascending=False)
          .head(10)
          .sort_values("citas")
    )

    # Totales por agrupador
    total_agrupador = (
        df.assign(agrupador=df["agrupador"].fillna("Sin agrupador"))
          .groupby("agrupador", dropna=False)
          .size()
          .reset_index(name="citas")
          .sort_values("citas", ascending=False)
          .head(20)
    )
    total_ag_sum = int(total_agrupador["citas"].sum())
    total_agrupador["pct"] = (total_agrupador["citas"] / total_ag_sum) if total_ag_sum else 0
    total_agrupador["pct"] = total_agrupador["pct"].fillna(0)
    total_agrupador["text_label"] = total_agrupador.apply(
        lambda r: f"{r['citas']:,} ({r['pct']:.1%})", axis=1
    )

    total_especialidad = (
        df.assign(descripcion_especialidad=df["descripcion_especialidad"].fillna("Sin especialidad"))
          .groupby("descripcion_especialidad", dropna=False)
          .size()
          .reset_index(name="citas")
          .sort_values("citas", ascending=False)
          .head(10)
    )
    total_esp_sum = int(total_especialidad["citas"].sum())
    total_especialidad["pct"] = (total_especialidad["citas"] / total_esp_sum) if total_esp_sum else 0
    total_especialidad["pct"] = total_especialidad["pct"].fillna(0)
    total_especialidad["text_label"] = total_especialidad.apply(
        lambda r: f"{r['citas']:,} ({r['pct']:.1%})", axis=1
    )

    # Figuras Totales (agrupador, especialidad)
    fig_total_agrupador = px.bar(
        total_agrupador,
        x="citas",
        y="agrupador",
        orientation="h",
        title="Total citas por agrupador",
        custom_data=["pct"],
        color="citas",
        color_continuous_scale=BAR_COLOR_SCALE,
        text="text_label",
    )
    fig_total_agrupador = style_horizontal_bar(fig_total_agrupador, "Número de citas", "Agrupador")

    fig_total_especialidad = px.bar(
        total_especialidad,
        x="citas",
        y="descripcion_especialidad",
        orientation="h",
        title="Total citas por especialidad",
        custom_data=["pct"],
        color="citas",
        color_continuous_scale=BAR_COLOR_SCALE,
        text="text_label",
    )
    fig_total_especialidad = style_horizontal_bar(fig_total_especialidad, "Número de citas", "Especialidad")

    # Porcentajes para Top 10
    total_top_serv = int(top_act_esp["citas"].sum())
    total_top_desc = int(top_desc_servicio["citas"].sum())
    top_act_esp["pct"] = (top_act_esp["citas"] / total_top_serv) if total_top_serv else 0
    top_act_esp["pct"] = top_act_esp["pct"].fillna(0)
    top_act_esp["text_label"] = top_act_esp.apply(
        lambda r: f"{r['citas']:,} ({r['pct']:.1%})", axis=1
    )
    top_desc_servicio["pct"] = (top_desc_servicio["citas"] / total_top_desc) if total_top_desc else 0
    top_desc_servicio["pct"] = top_desc_servicio["pct"].fillna(0)
    top_desc_servicio["text_label"] = top_desc_servicio.apply(
        lambda r: f"{r['citas']:,} ({r['pct']:.1%})", axis=1
    )

    fig_serv = px.bar(
        top_act_esp,
        x="citas",
        y="detalle_subactividad",
        orientation="h",
        title="Top 10 por subactividad",
        custom_data=["pct"],
        color="citas",
        color_continuous_scale=BAR_COLOR_SCALE,
        text="text_label",
    )
    fig_serv = style_horizontal_bar(fig_serv, "Número de citas", "Subactividad")

    fig_desc_serv = px.bar(
        top_desc_servicio,
        x="citas",
        y="descripcion_servicio",
        orientation="h",
        title="Top 10 por descripción de servicio",
        custom_data=["pct"],
        color="citas",
        color_continuous_scale=BAR_COLOR_SCALE,
        text="text_label",
    )
    fig_desc_serv = style_horizontal_bar(fig_desc_serv, "Número de citas", "Servicio")

    # Pie por estado de cita
    tipo_df = (
        df.groupby("estado_cita", dropna=False)
          .size()
          .reset_index(name="citas")
          .sort_values("citas", ascending=False)
    )
    tipo_df["estado_cita"] = tipo_df["estado_cita"].fillna("Sin estado")

    fig_pie = px.pie(
        tipo_df,
        names="estado_cita",
        values="citas",
    )
    fig_pie.update_traces(
        textposition="outside",
        texttemplate="%{label}<br>%{percent} (%{value:,})",
        pull=0.04,
        marker=dict(line=dict(color="#FFFFFF", width=2)),
        textfont_size=14,
    )
    fig_pie.update_layout(
        template="simple_white",
        showlegend=False,
        margin=dict(l=40, r=40, t=60, b=40),
        font=dict(family=FONT_FAMILY, size=13, color="#1F2937"),
        plot_bgcolor="#F9FBFD",
        paper_bgcolor="#F9FBFD",
        uniformtext_minsize=12,
        uniformtext_mode="hide",
    )

    # Orden de retorno: servicio(código), descripcion_servicio, pie, agrupador, descripcion_especialidad
    return fig_serv, fig_desc_serv, fig_pie, fig_total_agrupador, fig_total_especialidad

@callback(
    Output("tabla-prod-servicio-wrapper", "children"),
    Input("page-url", "pathname"),
    Input("page-url", "search"),
)
def render_tabla_prod_servicio(pathname, search):
    # Resolver periodo (default '01') y codcas
    periodo = _parse_periodo(search) or "01"
    if not pathname:
        return html.Div("Sin ruta.", style={"color": "#b00"})
    codcas = pathname.rstrip("/").split("/")[-1]

    engine = create_connection()
    if engine is None:
        return html.Div("Error de conexión a la base de datos.", style={"color": "#b00"})

    try:
        df = pd.read_sql(build_query(periodo, codcas), engine)
    except Exception as e:
        return html.Div(f"Error ejecutando consulta: {e}", style={"color": "#b00"})

    if df.empty:
        return html.Div(f"Sin datos para periodo {periodo}.", style={"color": "#b00"})

    # Seleccionar columnas solicitadas y normalizar nulos (usar 'agrupador' en lugar de 'subactividad')
    cols = ["descripcion_servicio", "agrupador", "acto_med", "estado_cita", "tipo_paciente"]
    df_table = (
        df.assign(
            descripcion_servicio=df["descripcion_servicio"].fillna("Sin servicio"),
            agrupador=df["agrupador"].fillna("Sin agrupador"),
            estado_cita=df["estado_cita"].fillna("Sin estado"),
            tipo_paciente=df["tipo_paciente"].fillna("Sin tipo"),
        )[cols]
        .sort_values(["descripcion_servicio", "agrupador"])
    )

    col_defs = [
        {"headerName": "Servicio", "field": "descripcion_servicio", "minWidth": 320},
        {"headerName": "Agrupador", "field": "agrupador", "minWidth": 280},
        {"headerName": "Acto Med", "field": "acto_med", "filter": "agNumberColumnFilter"},
        {"headerName": "Estado cita", "field": "estado_cita", "minWidth": 220},
        {"headerName": "Tipo paciente", "field": "tipo_paciente", "minWidth": 280},
    ]

    grid = dag.AgGrid(
        id="tabla-prod-servicio",
        columnDefs=col_defs,
        rowData=df_table.to_dict("records"),
        defaultColDef={
            "sortable": True,
            "resizable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
        },
        dashGridOptions={
            "pinnedBottomRowData": [{"descripcion_servicio": f"Total filas: {len(df_table):,}"}],
            "onFirstDataRendered": {"function": "params.api.autoSizeAllColumns();"},
            "statusBar": {
                "statusPanels": [{"statusPanel": "agAggregationComponent", "align": "right"}]
            },
        },
        className="ag-theme-alpine",
        style={"height": "520px", "width": "100%"},
    )
    return grid





@callback(
    Output("tc-download", "data"),
    Input("tc-download-btn", "n_clicks"),
    State("page-url", "pathname"),   # corrected id
    State("page-url", "search"),     # corrected id
    State("filter-periodo", "value"),
    prevent_initial_call=True
)
def tc_descargar_csv(n_clicks, pathname, search, periodo_dropdown):
    if not n_clicks:
        return None
    codcas, periodo = get_codcas_periodo(pathname, search, periodo_dropdown)
    if not codcas or not periodo:
        return None
    engine = create_connection()
    if engine is None:
        return None
    query = build_query(periodo, codcas)
    try:
        df = pd.read_sql(query, engine)
    except Exception:
        return None
    if df.empty:
        return None
    filename = f"citas_{codcas}_{periodo}.csv"
    return dcc.send_data_frame(df.to_csv, filename, index=False, encoding="utf-8-sig", sep="|")