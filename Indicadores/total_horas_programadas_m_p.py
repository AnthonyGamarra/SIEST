from dash import html, dcc, register_page, Input, Output, State, callback
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import dash_ag_grid as dag
from urllib.parse import parse_qs
import secure_code as sc

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

def style_horizontal_bar(fig: go.Figure, height: int = 360, color: str | None = None) -> go.Figure:
    title_component = getattr(getattr(fig.layout, "title", None), "text", "") or ""
    marker_kwargs = dict(line=dict(color="rgba(0,0,0,0.08)", width=1.2), opacity=0.92)
    if color:
        marker_kwargs["color"] = color
    fig.update_traces(
        marker=marker_kwargs,
        hovertemplate="<b>%{y}</b><br>Total horas: %{x:,.0f}<extra></extra>",
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
            title="Total horas",
            showgrid=True,
            gridcolor="rgba(10,76,140,0.08)",
            zeroline=False,
            tickformat=",.0f",
            tickfont=dict(color="#475569"),
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            tickfont=dict(color="#1F2937"),
        ),
        margin=dict(l=90, r=32, t=70, b=40),
        font=dict(family=FONT_FAMILY, size=12, color="#1F2937"),
        height=height,
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(family=FONT_FAMILY, color="#0F172A")),
        bargap=0.18,
        uniformtext=dict(minsize=11, mode="show"),
    )
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_coloraxes(showscale=False)
    return fig

# Helpers reutilizables
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


def get_codcas_periodo(pathname: str, search: str, periodo_dropdown: str | None, anio_dropdown: str | None):
    if not pathname:
        return None, None, None
    codcas = pathname.rstrip("/").split("/")[-1]
    codcas = sc.decode_code(codcas)
    periodo = _parse_periodo(search) or periodo_dropdown
    anio = _parse_anio(search) or anio_dropdown
    return codcas, periodo, anio

# Layout sin verificador de query
layout = html.Div([
    dcc.Location(id="hp-page-url_m_p", refresh=False),
    html.Div([
        # Header con icono
        html.Div([
            html.Div([
                html.I(className="bi bi-calendar-check", style={'fontSize': '26px', 'color': BRAND, 'marginRight': '12px'}),
                html.Div([
                    html.H4("Horas programadas por consulta externa",
                            style={"margin": 0, "color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700, "letterSpacing": "-0.3px"}),
                    html.P("📅 Distribución y resumen de horas programadas del periodo seleccionado",
                           style={"color": MUTED, "fontSize": "13px", "marginTop": "6px", "fontFamily": FONT_FAMILY})
                ])
            ], style={'display': 'flex', 'alignItems': 'center', 'flex': 1})
        ], style={'flex': 1}),
        # Lado derecho: botón descargar
        html.Div([
            html.Button(
                [html.I(className="bi bi-download me-2"), "Descargar CSV"],
                id="hp-download-btn_m_p",
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
            dcc.Download(id="hp-download_m_p")
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
        id="hp-main-tabs_m_p",
        value="tab-graficos",
        style={"border": "none"},
        parent_style={"marginTop": "12px"},
        className="custom-tabs",
        children=[
            dcc.Tab(
                label="Horas programadas",
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
                                        id="hp-graph-servicio_m_p",
                                        figure=empty_fig("Horas programadas por servicio"),
                                        config=GRAPH_CONFIG,
                                        style={"height": "380px", "width": "100%"}
                                    )
                                ], style={"flex": 1, "minWidth": "320px"}),
                                html.Div([
                                    dcc.Graph(
                                        id="hp-graph-subactividad_m_p",
                                        figure=empty_fig("Horas programadas por subactividad"),
                                        config=GRAPH_CONFIG,
                                        style={"height": "380px", "width": "100%"}
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
                                html.Div(
                                    dcc.Graph(id="hp-graph-agrupador_m_p", config=GRAPH_CONFIG, style={"height": "320px", "width": "100%"}),
                                    style={"flex": 1, "minWidth": "320px"}
                                ),
                                html.Div(
                                    dcc.Graph(id="hp-graph-especialidad_m_p", config=GRAPH_CONFIG, style={"height": "320px", "width": "100%"}),
                                    style={"flex": 1, "minWidth": "320px"}
                                ),
                            ], style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
                            type="dot"
                        ),
                    ], style={**CARD_STYLE, "marginTop": "12px"}),
                    # Tercer bloque: matriz antes de la tabla
                    html.Div([
                        html.Div([
                            html.I(
                                className="bi bi-grid-3x3-gap",
                                style={'fontSize': '20px', 'color': BRAND, 'marginRight': '10px'}
                            ),
                            html.H5(
                                "Matriz de horas programadas por día",
                                style={"margin": 0, "color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700}
                            )
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
                        dcc.Loading(
                            html.Div(id="hp-matriz-wrapper_m_p", style={"marginTop": "12px"}),
                            type="dot"
                        )
                    ], style={**CARD_STYLE, "marginTop": "12px"}),
                    # Tercer bloque: reemplazado por tabla resumen horas
                    html.Div([
                        html.H5("Resumen horas programadas",
                                style={"color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700,
                                       "marginBottom": "12px", "letterSpacing": "-0.2px"}),
                        dag.AgGrid(
                            id="hp-tabla-horas-programadas_m_p",
                            className="ag-theme-alpine",
                            style={"height": "430px", "width": "100%"},
                            columnDefs=[
                                {"headerName": "Fecha programada", "field": "fecha_prog", "width": 140},
                                {"headerName": "DNI Médico", "field": "dni_medico"},
                                {"headerName": "Servicio", "field": "descripcion_servicio", "width": 360},
                                {"headerName": "Subactividad", "field": "detalle_subactividad","width": 360},
                                {"headerName": "Agrupador", "field": "agrupador"},
                                {"headerName": "Especialidad", "field": "descripcion_especialidad"},
                                {"headerName": "Total horas programadas", "field": "total_horas", "filter": "agNumberColumnFilter"}
                            ],
                            defaultColDef={"sortable": True, "resizable": True,
                                           "filter": "agTextColumnFilter", "floatingFilter": True},
                            rowData=[],
                            dashGridOptions={"onFirstDataRendered": {"function": "params.api.autoSizeAllColumns();"}}
                        ),
                    ], style={**CARD_STYLE, "marginTop": "12px"})
                ], style={"padding": "8px"})
            ),
        ],
        content_style=TABS_CONTAINER_STYLE
    ),
    # Stores
    dcc.Store(id="hp-store-data_m_p")
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
        engine = create_engine('postgresql+psycopg2://app_user:sge02@10.0.29.117:5433/DW_ESTADISTICA')
        with engine.connect():
            pass
        return engine
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        return None

# REEMPLAZO: función para construir query dinámicamente
def build_query(periodo: str, anio: str, codcas: str) -> str:
    return f"""
    SELECT 
	    ce.cod_servicio,
        ce.cod_especialidad,
        ca.cenasides,
        ce.cod_tipdoc_medico,
        ce.dni_medico,
        am.actdes AS actividad,
        ag.agrupador AS agrupador,
        a.actespnom AS detalle_subactividad,
        c.servhosdes AS descripcion_servicio,
        e.especialidad AS descripcion_especialidad,
		ce.total_horas,
        ce.fecha_prog
    FROM dwsge.dwe_consulta_externa_programacion_{anio}_{periodo} ce
    LEFT JOIN dwsge.sgss_cmsho10 AS c ON ce.cod_servicio = c.servhoscod
    LEFT JOIN dwsge.dim_especialidad AS e ON ce.cod_especialidad = e.cod_especialidad
    LEFT JOIN dwsge.sgss_cmace10 AS a ON ce.cod_actividad = a.actcod AND ce.cod_subactividad = a.actespcod
    LEFT JOIN dwsge.sgss_cmact10 AS am ON ce.cod_actividad = am.actcod
    LEFT JOIN dwsge.sgss_cmcas10 AS ca ON ce.cod_oricentro = ca.oricenasicod AND ce.cod_centro = ca.cenasicod
    LEFT JOIN dwsge.dim_agrupador AS ag ON ce.cod_agrupador = ag.cod_agrupador
    WHERE ce.cod_centro = '{codcas}'
        AND (
            ce.cod_motivo_suspension IS NULL 
            OR ce.cod_motivo_suspension NOT IN ('04','09','10','99','13','16','11')
        )
                        AND ce.cod_actividad = '91'
                        AND ce.cod_subactividad = '682'
                        AND ce.cod_servicio = 'L16'
    """

# Registrar la página con el layout explícito para evitar NoLayoutException
register_page(
    __name__,
    path_template="/dash/horas_programadas_m_p/<codcas>",
    name="horas_programadas_m_p",
    layout=layout
)

# ====== NUEVOS CALLBACKS (ids actualizados) ======
@callback(
    Output("hp-store-data_m_p", "data"),
    Input("hp-page-url_m_p", "pathname"),
    Input("hp-page-url_m_p", "search"),
    State("filter-periodo", "value"),
    State("filter-anio", "value"),
    prevent_initial_call=False,
)
def load_data_to_store(pathname, search, periodo_dropdown, anio_dropdown):
    # Obtener codcas y periodo desde URL
    codcas, periodo, anio = get_codcas_periodo(pathname or "", search or "", periodo_dropdown, anio_dropdown)
    if not codcas or not periodo or not anio:
        return None

    engine = create_connection()
    if engine is None:
        return None

    query = build_query(periodo, anio, codcas)
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(query, con=conn)
    except Exception as e:
        print(f"Error ejecutando consulta horas programadas: {e}")
        return None

    if df.empty:
        return None

    # Asegurar tipo numérico
    df["total_horas"] = pd.to_numeric(df.get("total_horas", 0), errors="coerce").fillna(0)
    return df.to_dict("records")


@callback(
    Output("hp-graph-servicio_m_p", "figure"),
    Output("hp-graph-subactividad_m_p", "figure"),
    Input("hp-store-data_m_p", "data"),
)
def update_graficos_primer_bloque(data):
    if not data:
        return (
            empty_fig("Horas programadas por servicio"),
            empty_fig("Horas programadas por subactividad"),
        )

    df = pd.DataFrame(data)
    total_all = float(pd.to_numeric(df.get("total_horas", 0), errors="coerce").fillna(0).sum())

    # Agrupar por servicio (ordenar y luego top 10)
    service_col = "descripcion_servicio" if "descripcion_servicio" in df.columns else "cod_servicio"
    df_serv = (
        df.groupby(service_col, as_index=False)["total_horas"]
          .sum()
          .sort_values("total_horas", ascending=False)
          .head(10)
    )
    df_serv["label"] = df_serv["total_horas"].apply(
        lambda v: f"{v:,.0f} ({(v/total_all):.1%})" if total_all else f"{v:,.0f} (0.0%)"
    )
    fig_serv = px.bar(
        df_serv,
        y=service_col,
        x="total_horas",
        orientation="h",
        title="Horas programadas por servicio",
        text="label",
        color="total_horas",
        color_continuous_scale=BAR_COLOR_SCALE,
    )
    fig_serv = style_horizontal_bar(fig_serv, height=380)

    # Agrupar por detalle_subactividad (ordenar y luego top 10)
    sub_col = "detalle_subactividad" if "detalle_subactividad" in df.columns else "cod_subactividad"
    df_sub = (
        df.groupby(sub_col, as_index=False)["total_horas"]
          .sum()
          .sort_values("total_horas", ascending=False)
          .head(10)
    )
    df_sub["label"] = df_sub["total_horas"].apply(
        lambda v: f"{v:,.0f} ({(v/total_all):.1%})" if total_all else f"{v:,.0f} (0.0%)"
    )
    fig_sub = px.bar(
        df_sub,
        y=sub_col,
        x="total_horas",
        orientation="h",
        title="Horas programadas por subactividad",
        text="label",
        color="total_horas",
        color_continuous_scale=BAR_COLOR_SCALE,
    )
    fig_sub = style_horizontal_bar(fig_sub, height=380)
    return fig_serv, fig_sub

# ====== NUEVO: segundo bloque (agrupador y especialidad) ======
@callback(
    Output("hp-graph-agrupador_m_p", "figure"),
    Output("hp-graph-especialidad_m_p", "figure"),
    Input("hp-store-data_m_p", "data"),
)
def update_graficos_segundo_bloque(data):
    if not data:
        return empty_fig("Horas programadas por agrupador"), empty_fig("Horas programadas por especialidad")

    df = pd.DataFrame(data)
    df["total_horas"] = pd.to_numeric(df.get("total_horas", 0), errors="coerce").fillna(0)
    total_all = float(df["total_horas"].sum()) or 0.0

    # Agrupador vs total_horas (Top 10)
    grp_col = "agrupador" if "agrupador" in df.columns else None
    if grp_col:
        df_grp = (
            df.assign(agrupador=df[grp_col].fillna("Sin agrupador"))
              .groupby("agrupador", as_index=False)["total_horas"].sum()
              .sort_values("total_horas", ascending=False)
              .head(10)
        )
        df_grp["label"] = df_grp["total_horas"].apply(
            lambda v: f"{v:,.0f} ({(v/total_all):.1%})" if total_all else f"{v:,.0f} (0.0%)"
        )
        fig_grp = px.bar(
            df_grp,
            y="agrupador",
            x="total_horas",
            orientation="h",
            title="Horas programadas por agrupador",
            text="label",
            color="total_horas",
            color_continuous_scale=BAR_COLOR_SCALE,
        )
        fig_grp = style_horizontal_bar(fig_grp, height=320)
    else:
        fig_grp = empty_fig("Horas programadas por agrupador")

    # Especialidad vs total_horas (Top 10)
    esp_col = "descripcion_especialidad" if "descripcion_especialidad" in df.columns else None
    if esp_col:
        df_esp = (
            df.assign(descripcion_especialidad=df[esp_col].fillna("Sin especialidad"))
              .groupby("descripcion_especialidad", as_index=False)["total_horas"].sum()
              .sort_values("total_horas", ascending=False)
              .head(10)
        )
        df_esp["label"] = df_esp["total_horas"].apply(
            lambda v: f"{v:,.0f} ({(v/total_all):.1%})" if total_all else f"{v:,.0f} (0.0%)"
        )
        fig_esp = px.bar(
            df_esp,
            y="descripcion_especialidad",
            x="total_horas",
            orientation="h",
            title="Horas programadas por especialidad",
            text="label",
            color="total_horas",
            color_continuous_scale=BAR_COLOR_SCALE,
        )
        fig_esp = style_horizontal_bar(fig_esp, height=320)
    else:
        fig_esp = empty_fig("Horas programadas por especialidad")

    return fig_grp, fig_esp


@callback(
    Output("hp-matriz-wrapper_m_p", "children"),
    Input("hp-store-data_m_p", "data"),
)
def build_matriz_horas(data):
    error_style = {"color": "#b00", "fontFamily": FONT_FAMILY}
    if not data:
        return html.Div("Sin datos de horas programadas.", style=error_style)

    df = pd.DataFrame(data)
    if df.empty:
        return html.Div("Sin datos de horas programadas.", style=error_style)

    df["total_horas"] = pd.to_numeric(df.get("total_horas", 0), errors="coerce").fillna(0).astype(float)
    df["dni_medico"] = df.get("dni_medico", "").fillna("Sin DNI").replace("", "Sin DNI")
    df["fecha_prog"] = pd.to_datetime(df.get("fecha_prog"), errors="coerce").dt.strftime("%Y-%m-%d").fillna("Sin fecha")

    df_valid = df[df["fecha_prog"] != "Sin fecha"].copy()
    if df_valid.empty:
        return html.Div("No hay fechas válidas en los datos.", style=error_style)

    pivot_df = (
        df_valid.groupby(["dni_medico", "fecha_prog"])  # horas por médico y fecha
        ["total_horas"].sum()
        .unstack(fill_value=0)
    )
    pivot_df = pivot_df.reindex(sorted(pivot_df.columns), axis=1)
    pivot_df["Total"] = pivot_df.sum(axis=1)
    pivot_df = pivot_df.sort_values("Total", ascending=False).reset_index()

    date_columns = [col for col in pivot_df.columns if col not in ["dni_medico", "Total"]]

    col_defs = [
        {
            "headerName": "DNI Médico",
            "field": "dni_medico",
            "pinned": "left",
            "minWidth": 140,
            "cellStyle": {"fontWeight": "bold", "backgroundColor": "#f8f9fa"}
        }
    ]

    for fecha in date_columns:
        col_defs.append({
            "headerName": fecha,
            "field": fecha,
            "filter": "agNumberColumnFilter",
            "minWidth": 110,
            "cellStyle": {
                "function": "Number(params.value || 0) > 0 ? {backgroundColor: '#ECF5FB', fontWeight: '600'} : {}"
            }
        })

    col_defs.append({
        "headerName": "Total",
        "field": "Total",
        "pinned": "right",
        "filter": "agNumberColumnFilter",
        "minWidth": 120,
        "cellStyle": {"fontWeight": "bold", "backgroundColor": "#7FB9DE"}
    })

    total_row = {"dni_medico": "TOTAL"}
    for col in date_columns + ["Total"]:
        total_row[col] = float(pivot_df[col].sum())

    return dag.AgGrid(
        id="hp-matriz-grid_m_p",
        columnDefs=col_defs,
        rowData=pivot_df.to_dict("records"),
        defaultColDef={
            "sortable": True,
            "resizable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": False,
            "flex": 0
        },
        dashGridOptions={
            "pinnedBottomRowData": [total_row],
            "onFirstDataRendered": {"function": "params.api.autoSizeAllColumns();"}
        },
        className="ag-theme-alpine",
        style={"height": "650px", "width": "100%"}
    )

# ===== NUEVO: construir rowData tabla horas programadas =====
@callback(
    Output("hp-tabla-horas-programadas_m_p", "rowData"),
    Input("hp-store-data_m_p", "data"),
)
def build_tabla_horas(data):
    if not data:
        return []
    df = pd.DataFrame(data)
    df["total_horas"] = pd.to_numeric(df.get("total_horas", 0), errors="coerce").fillna(0).astype(float)
    df["fecha_prog"] = pd.to_datetime(df.get("fecha_prog"), errors="coerce").dt.strftime("%Y-%m-%d").fillna("Sin fecha")
    df = df.assign(
        descripcion_servicio=df.get("descripcion_servicio", "").fillna("Sin servicio").replace("", "Sin servicio"),
        detalle_subactividad=df.get("detalle_subactividad", "").fillna("Sin subactividad").replace("", "Sin subactividad"),
        agrupador=df.get("agrupador", "").fillna("Sin agrupador").replace("", "Sin agrupador"),
        descripcion_especialidad=df.get("descripcion_especialidad", "").fillna("Sin especialidad").replace("", "Sin especialidad"),
        cod_tipdoc_medico=df.get("cod_tipdoc_medico", "").fillna("Sin tipo doc").replace("", "Sin tipo doc"),
        dni_medico=df.get("dni_medico", "").fillna("Sin DNI").replace("", "Sin DNI"),
    )
    grouped = (df.groupby(
        ["fecha_prog", "descripcion_servicio", "detalle_subactividad", "agrupador", "descripcion_especialidad", "cod_tipdoc_medico", "dni_medico"],
        as_index=False)["total_horas"].sum()
               .sort_values("total_horas", ascending=False))
    # CASTEO EXPLÍCITO TRAS EL GROUPBY
    grouped["total_horas"] = pd.to_numeric(grouped["total_horas"], errors="coerce").fillna(0).astype(float)
    return grouped.to_dict("records")

# ===== Helper para aplicar filtro local (similar al otro archivo) =====
def _apply_filter(records, filter_model):
    if not records or not filter_model:
        return records
    df_local = pd.DataFrame(records)
    for col, f in filter_model.items():
        if col not in df_local.columns:
            continue
        ft = f.get("filterType")
        t = f.get("type")
        val = f.get("filter")
        if ft == "text":
            serie = df_local[col].astype(str)
            pattern = str(val or "").lower()
            if t == "contains":
                mask = serie.str.lower().str.contains(pattern)
            elif t == "notContains":
                mask = ~serie.str.lower().str.contains(pattern)
            elif t == "equals":
                mask = serie.str.lower() == pattern
            elif t == "startsWith":
                mask = serie.str.lower().str.startswith(pattern)
            elif t == "endsWith":
                mask = serie.str.lower().str.endswith(pattern)
            else:
                mask = True
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
                    mask = True
            else:
                mask = True
            df_local = df_local[mask]
    return df_local.to_dict("records")

# ===== NUEVO: total dinámico en fila inferior =====
@callback(
    Output("hp-tabla-horas-programadas_m_p", "dashGridOptions"),
    Input("hp-tabla-horas-programadas_m_p", "filterModel"),
    Input("hp-tabla-horas-programadas_m_p", "rowData"),  # agregado para recalcular al cargar datos
)
def actualizar_total_horas(filter_model, row_data):
    if not row_data:
        return {
            "pinnedBottomRowData": [{
                "fecha_prog": "",
                "descripcion_servicio": "Total horas: 0.00",
                "total_horas": 0
            }]
        }
    filtrados = _apply_filter(row_data, filter_model)
    df_f = pd.DataFrame(filtrados) if filtrados else pd.DataFrame(columns=["total_horas"])
    df_f["total_horas"] = pd.to_numeric(df_f.get("total_horas", 0), errors="coerce").fillna(0).astype(float)
    total = float(df_f["total_horas"].sum())
    is_filtered = bool(filter_model) and len(filter_model.keys()) > 0
    label = "Total horas filtradas" if is_filtered else "Total horas"
    return {
        "pinnedBottomRowData": [{
            "fecha_prog": "",
            "descripcion_servicio": f"{label}: {total:,.2f}",
            "total_horas": total
        }],
        "statusBar": {
            "statusPanels": [
                {"statusPanel": "agAggregationComponent", "align": "right"}
            ]
        }
    }


@callback(
    Output("hp-download_m_p", "data"),
    Input("hp-download-btn_m_p", "n_clicks"),
    State("hp-page-url_m_p", "pathname"),   # <-- corregido id
    State("hp-page-url_m_p", "search"),     # <-- corregido id
    State("filter-periodo", "value"),
    State("filter-anio", "value"),
    prevent_initial_call=True
)
def hp_descargar_csv(n_clicks, pathname, search, periodo_dropdown, anio_dropdown):
    if not n_clicks:
        return None
    codcas, periodo, anio = get_codcas_periodo(pathname, search, periodo_dropdown, anio_dropdown)
    if not codcas or not periodo or not anio:
        return None
    engine = create_connection()
    if engine is None:
        return None
    query = build_query(periodo, anio, codcas)  # <-- reutiliza build_query
    try:
        df = pd.read_sql(query, engine)
    except Exception:
        return None
    if df.empty:
        return None
    filename = f"horas_programadas_{codcas}_{anio}_{periodo}.csv"  # <-- nombre ajustado
    return dcc.send_data_frame(df.to_csv, filename, index=False, encoding="utf-8-sig", sep="|")