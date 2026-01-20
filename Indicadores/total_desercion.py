from dash import html, dcc, register_page, Input, Output, State, callback
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import dash_ag_grid as dag
from urllib.parse import parse_qs

# Paleta y estilos compartidos
BRAND = "#0064AF"
TEXT = "#0F172A"
BORDER = "#E5E7EB"
CARD_BG = "#FFFFFF"
MUTED = "#6B7280"
FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"
BAR_COLOR_SCALE = ["#D7E9FF", "#92C4F9", "#2E78C7"]
GRAPH_CONFIG = {"displaylogo": False, "responsive": True}
CARD_STYLE = {
    "border": f"1px solid {BORDER}",
    "borderRadius": "16px",
    "backgroundColor": CARD_BG,
    "boxShadow": "0 6px 18px rgba(0,0,0,0.06)",
    "padding": "14px",
}
TABS_CONTAINER_STYLE = {
    "backgroundColor": "#fff",
    "border": f"1px solid {BORDER}",
    "borderRadius": "16px",
    "padding": "6px 10px 2px 10px",
    "boxShadow": "0 4px 12px rgba(0,0,0,0.05)",
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
    "border": "1px solid transparent",
}
TAB_SELECTED_STYLE = {
    **TAB_STYLE,
    "color": BRAND,
    "background": "linear-gradient(145deg,#ffffff,#F3F8FC)",
    "boxShadow": "0 2px 6px rgba(0,0,0,0.08)",
    "border": f"1px solid {BRAND}",
}


def empty_fig(title: str | None = None) -> go.Figure:
    fig = go.Figure()
    layout_kwargs = dict(
        template="simple_white",
        plot_bgcolor="#F9FBFD",
        paper_bgcolor="#F9FBFD",
        font=dict(family=FONT_FAMILY, color=TEXT),
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


def style_horizontal_bar(fig: go.Figure, x_title: str, y_title: str = "", height: int = 380) -> go.Figure:
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
            tickfont=dict(color=TEXT),
        ),
        margin=dict(l=90, r=32, t=70, b=40),
        font=dict(family=FONT_FAMILY, size=12, color=TEXT),
        height=height,
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(family=FONT_FAMILY, color=TEXT)),
        bargap=0.18,
        uniformtext=dict(minsize=11, mode="show"),
        showlegend=False,
    )
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_coloraxes(showscale=False)
    return fig


# Layout sin verificador de query
layout = html.Div([
    dcc.Location(id="hp-page-url", refresh=False),
    html.Div([
        html.Div([
            html.Div([
                html.H4(
                    "Detalle DESERCIONES CONSULTA EXTERNA",
                    style={
                        "margin": 0,
                        "color": BRAND,
                        "fontFamily": FONT_FAMILY,
                        "fontWeight": 750,
                        "letterSpacing": "-0.1px",
                    },
                ),
                html.P(
                    "Visualización del periodo seleccionado.",
                    style={
                        "color": MUTED,
                        "fontSize": "13px",
                        "margin": "2px 0 0 0",
                        "fontFamily": FONT_FAMILY,
                    },
                ),
            ], style={"display": "flex", "flexDirection": "column", "gap": "2px"}),
        ], style={"display": "flex", "alignItems": "center", "gap": "12px"}),
        html.Div([
            html.Button(
                "Descargar CSV",
                id="td-download-btn",
                n_clicks=0,
                style={
                    "backgroundColor": BRAND,
                    "color": "#fff",
                    "border": f"1px solid {BORDER}",
                    "borderRadius": "10px",
                    "padding": "9px 14px",
                    "fontFamily": FONT_FAMILY,
                    "fontSize": "13px",
                    "cursor": "pointer",
                    "boxShadow": "0 3px 10px rgba(0,0,0,0.10)",
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "8px",
                },
            ),
            dcc.Download(id="td-download"),
        ], style={"display": "flex", "alignItems": "center"}),
    ], style={
        "padding": "12px 16px",
        "background": "linear-gradient(90deg,#ffffff 0%,#F5F8FB 100%)",
        "border": f"1px solid {BORDER}",
        "borderRadius": "16px",
        "boxShadow": "0 6px 16px rgba(0,0,0,0.08)",
        "marginBottom": "12px",
        "display": "flex",
        "justifyContent": "space-between",
        "alignItems": "center",
        "gap": "12px",
        "flexWrap": "wrap",
    }),
    # PESTAÑAS
    dcc.Tabs(
        id="hp-main-tabs",
        value="tab-graficos",
        style={"border": "none"},
        parent_style={"marginTop": "12px"},
        className="custom-tabs",
        children=[
            dcc.Tab(
                label="Detalle deserciones",
                value="tab-graficos",
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=html.Div([
                    html.Div([
                        dcc.Loading(
                            html.Div([
                                html.Div([
                                    dcc.Graph(
                                        id="hp-deserciones-serv-subact",
                                        figure=empty_fig("Deserciones por servicio"),
                                        config=GRAPH_CONFIG,
                                        style={"height": "380px"},
                                    )
                                ], style={"flex": 1, "minWidth": "320px"}),
                                html.Div([
                                    dcc.Graph(
                                        id="hp-deserciones-subactividad",
                                        figure=empty_fig("Deserciones por subactividad"),
                                        config=GRAPH_CONFIG,
                                        style={"height": "380px"},
                                    )
                                ], style={"flex": 1, "minWidth": "320px"}),
                            ], style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
                            type="dot",
                        )
                    ], style={**CARD_STYLE}),
                    # Segundo bloque
                    html.Div([
                        dcc.Loading(
                            html.Div([
                                html.Div([
                                    dcc.Graph(
                                        id="hp-deserciones-agrupador",
                                        figure=empty_fig("Deserciones por agrupador"),
                                        config=GRAPH_CONFIG,
                                        style={"height": "380px"},
                                    )
                                ], style={"flex": 1, "minWidth": "320px"}),
                                html.Div([
                                    dcc.Graph(
                                        id="hp-deserciones-especialidad",
                                        figure=empty_fig("Deserciones por especialidad"),
                                        config=GRAPH_CONFIG,
                                        style={"height": "380px"},
                                    )
                                ], style={"flex": 1, "minWidth": "320px"}),
                            ], style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
                            type="dot",
                        ),
                        html.Div(
                            id="hp-total-msg",
                            style={
                                "marginTop": "6px",
                                "color": MUTED,
                                "fontFamily": FONT_FAMILY,
                                "fontSize": "12px",
                                "fontWeight": "bold",
                            },
                        ),
                    ], style={**CARD_STYLE, "marginTop": "12px"}),
                    html.Div([
                        html.H5(
                            "Resumen deserción por consulta externa",
                            style={
                                "color": TEXT,
                                "fontFamily": FONT_FAMILY,
                                "fontWeight": 650,
                                "marginBottom": "8px",
                            },
                        ),
                        dag.AgGrid(
                            id="hp-tabla-desercion",
                            className="ag-theme-alpine",
                            style={"height": "430px", "width": "100%"},
                            columnDefs=[
                                {"headerName": "Servicio", "field": "servicio", "sortable": True, "filter": "agTextColumnFilter"},
                                {"headerName": "Subactividad", "field": "subactividad", "sortable": True, "filter": "agTextColumnFilter"},
                                {"headerName": "Agrupador", "field": "agrupador", "sortable": True, "filter": "agTextColumnFilter"},
                                {"headerName": "Especialidad", "field": "especialidad", "sortable": True, "filter": "agTextColumnFilter"},
                                {"headerName": "Acto médico", "field": "acto_med", "sortable": True, "filter": "agTextColumnFilter"},
                            ],
                            defaultColDef={"resizable": True, "floatingFilter": True},
                            rowData=[],
                            dashGridOptions={"rowSelection": "multiple"},
                        ),
                        html.Div(
                            id="hp-tornado-msg",
                            style={
                                "marginTop": "6px",
                                "color": MUTED,
                                "fontFamily": FONT_FAMILY,
                                "fontSize": "12px",
                                "fontWeight": "bold",
                            },
                        ),
                    ], style={**CARD_STYLE, "marginTop": "12px"}),
                ], style={"padding": "6px"})
            ),
        ],
        content_style=TABS_CONTAINER_STYLE
    ),
    # Stores
    dcc.Store(id="hp-store-data")
], style={
    "maxWidth": "1600px",
    "width": "100%",
    "margin": "0 auto",
    "padding": "8px 10px 20px 10px",
    "fontFamily": FONT_FAMILY,
})

# Registrar la página con el layout explícito para evitar NoLayoutException
register_page(
    __name__,
    path_template="/dash/desercion_citas/<codcas>",
    name="desercion_citas",
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

@callback(
    Output("hp-deserciones-serv-subact", "figure"),
    Output("hp-deserciones-subactividad", "figure"),
    Output("hp-deserciones-agrupador", "figure"),
    Output("hp-deserciones-especialidad", "figure"),
    Input("hp-page-url", "pathname"),
    Input("hp-page-url", "search"),
    State("filter-periodo", "value"),
    State("filter-anio", "value"),
)
def actualizar_deserciones(pathname, search, periodo_dropdown, anio_dropdown):
    """Genera dos gráficos: servicio vs total y subactividad vs total deserciones."""
    codcas, periodo, anio = get_codcas_periodo(pathname, search, periodo_dropdown, anio_dropdown)
    if not codcas or not periodo or not anio:
        return (
            empty_fig("Deserciones por servicio"),
            empty_fig("Deserciones por subactividad"),
            empty_fig("Deserciones por agrupador"),
            empty_fig("Deserciones por especialidad"),
        )
    if not re.fullmatch(r"\d{2}", periodo):
        return (
            empty_fig("Periodo inválido"),
            empty_fig("Periodo inválido"),
            empty_fig("Periodo inválido"),
            empty_fig("Periodo inválido"),
        )
    if not re.fullmatch(r"[A-Za-z0-9]+", codcas):
        return (
            empty_fig("Centro inválido"),
            empty_fig("Centro inválido"),
            empty_fig("Centro inválido"),
            empty_fig("Centro inválido"),
        )
    engine = create_connection()
    if engine is None:
        return (
            empty_fig("Error conexión DB"),
            empty_fig("Error conexión DB"),
            empty_fig("Error conexión DB"),
            empty_fig("Error conexión DB"),
        )
    query = f"""
            SELECT            
                c.servhosdes as servicio,
                a.actespnom as subactividad,
                ag.agrupador AS agrupador,
                e.especialidad,
                am.actdes,
                ca.cenasides,
                ce.acto_med
            FROM dwsge.dw_consulta_externa_homologacion_{anio}_{periodo} ce
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
            LEFT JOIN dwsge.dim_agrupador as ag ON ce.cod_agrupador = ag.cod_agrupador
            WHERE ce.cod_centro = '{codcas}'
            AND ce.cod_actividad = '91'
            AND ce.clasificacion IN (1,3,5,0)
            AND ce.cod_variable = '001'

            UNION ALL

            SELECT
                c.servhosdes as servicio,
                a.actespnom as subactividad,
                ag.agrupador AS agrupador,
                e.especialidad,
                am.actdes,
                ca.cenasides,
                p.acto_med
            FROM dwsge.dwe_consulta_externa_citados_homologacion_{anio}_{periodo} p
            LEFT JOIN dwsge.sgss_cmsho10 AS c 
                ON p.cod_servicio = c.servhoscod
            LEFT JOIN dwsge.dim_especialidad AS e
                ON p.cod_especialidad = e.cod_especialidad
            LEFT JOIN dwsge.sgss_cmace10 AS a
                ON p.cod_actividad = a.actcod
                AND p.cod_subactividad = a.actespcod
            LEFT JOIN dwsge.sgss_cmact10 AS am
                ON p.cod_actividad = am.actcod
            LEFT JOIN dwsge.sgss_cmcas10 AS ca
                ON p.cod_oricentro = ca.oricenasicod
                AND p.cod_centro = ca.cenasicod
            LEFT JOIN dwsge.dim_agrupador as ag ON p.cod_agrupador = ag.cod_agrupador
            WHERE p.cod_centro = '{codcas}'
            AND p.cod_actividad = '91'
            AND p.cod_variable = '001'
            AND p.cod_estado IN ('1','2','5');
    """
    try:
        df = pd.read_sql(query, engine)
    except Exception:
        return (
            empty_fig("Error consultando deserciones"),
            empty_fig("Error consultando deserciones"),
            empty_fig("Error consultando deserciones"),
            empty_fig("Error consultando deserciones"),
        )
    if df.empty:
        return (
            empty_fig("Sin datos de deserciones"),
            empty_fig("Sin datos de deserciones"),
            empty_fig("Sin datos de deserciones"),
            empty_fig("Sin datos de deserciones"),
        )

    total_deserciones = len(df)

    # Agregación por servicio
    df_serv = (df.groupby("servicio", dropna=False)
                 .size()
                 .reset_index(name="deserciones")
                 .sort_values("deserciones", ascending=False))
    if df_serv.empty:
        fig_serv = empty_fig("Deserciones por servicio")
    else:
        df_serv["porcentaje"] = (df_serv["deserciones"] / total_deserciones * 100).round(2)
        df_serv = df_serv.head(10)
        fig_serv = px.bar(
            df_serv,
            x="deserciones",
            y="servicio",
            orientation="h",
            title="Deserciones por servicio",
            text=df_serv.apply(lambda r: f"{r.deserciones} ({r.porcentaje}%)", axis=1),
            color="deserciones",
            color_continuous_scale=BAR_COLOR_SCALE,
        )
        fig_serv.update_traces(
            customdata=df_serv["porcentaje"],
            hovertemplate="<b>%{y}</b><br>Deserciones: %{x:,}<br>Porcentaje: %{customdata:.2f}%<extra></extra>",
        )
        fig_serv = style_horizontal_bar(fig_serv, "Total deserciones", "Servicio")

    # Agregación por subactividad
    df_sub = (df.groupby("subactividad", dropna=False)
                .size()
                .reset_index(name="deserciones")
                .sort_values("deserciones", ascending=False))
    if df_sub.empty:
        fig_sub = empty_fig("Deserciones por subactividad")
    else:
        df_sub["porcentaje"] = (df_sub["deserciones"] / total_deserciones * 100).round(2)
        df_sub = df_sub.head(10)
        fig_sub = px.bar(
            df_sub,
            x="deserciones",
            y="subactividad",
            orientation="h",
            title="Deserciones por subactividad",
            text=df_sub.apply(lambda r: f"{r.deserciones} ({r.porcentaje}%)", axis=1),
            color="deserciones",
            color_continuous_scale=BAR_COLOR_SCALE,
        )
        fig_sub.update_traces(
            customdata=df_sub["porcentaje"],
            hovertemplate="<b>%{y}</b><br>Deserciones: %{x:,}<br>Porcentaje: %{customdata:.2f}%<extra></extra>",
        )
        fig_sub = style_horizontal_bar(fig_sub, "Total deserciones", "Subactividad")

    # Agregación por agrupador
    df_agr = (df.groupby("agrupador", dropna=False)
                .size()
                .reset_index(name="deserciones")
                .sort_values("deserciones", ascending=False))
    if df_agr.empty:
        fig_agr = empty_fig("Deserciones por agrupador")
    else:
        df_agr["porcentaje"] = (df_agr["deserciones"] / total_deserciones * 100).round(2)
        df_agr = df_agr.head(10)
        fig_agr = px.bar(
            df_agr,
            x="deserciones",
            y="agrupador",
            orientation="h",
            title="Deserciones por agrupador",
            text=df_agr.apply(lambda r: f"{r.deserciones} ({r.porcentaje}%)", axis=1),
            color="deserciones",
            color_continuous_scale=BAR_COLOR_SCALE,
        )
        fig_agr.update_traces(
            customdata=df_agr["porcentaje"],
            hovertemplate="<b>%{y}</b><br>Deserciones: %{x:,}<br>Porcentaje: %{customdata:.2f}%<extra></extra>",
        )
        fig_agr = style_horizontal_bar(fig_agr, "Total deserciones", "Agrupador")

    # Agregación por especialidad
    df_esp = (df.groupby("especialidad", dropna=False)
                .size()
                .reset_index(name="deserciones")
                .sort_values("deserciones", ascending=False))
    if df_esp.empty:
        fig_esp = empty_fig("Deserciones por especialidad")
    else:
        df_esp["porcentaje"] = (df_esp["deserciones"] / total_deserciones * 100).round(2)
        df_esp = df_esp.head(10)
        fig_esp = px.bar(
            df_esp,
            x="deserciones",
            y="especialidad",
            orientation="h",
            title="Deserciones por especialidad",
            text=df_esp.apply(lambda r: f"{r.deserciones} ({r.porcentaje}%)", axis=1),
            color="deserciones",
            color_continuous_scale=BAR_COLOR_SCALE,
        )
        fig_esp.update_traces(
            customdata=df_esp["porcentaje"],
            hovertemplate="<b>%{y}</b><br>Deserciones: %{x:,}<br>Porcentaje: %{customdata:.2f}%<extra></extra>",
        )
        fig_esp = style_horizontal_bar(fig_esp, "Total deserciones", "Especialidad")

    return fig_serv, fig_sub, fig_agr, fig_esp

@callback(
    Output("hp-tabla-desercion", "rowData"),
    Output("hp-tabla-desercion", "pinnedBottomRowData"),
    Input("hp-page-url", "pathname"),
    Input("hp-page-url", "search"),
    State("filter-periodo", "value"),
    State("filter-anio", "value"),
)
def cargar_tabla_deserciones(pathname, search, periodo_dropdown, anio_dropdown):
    codcas, periodo, anio = get_codcas_periodo(pathname, search, periodo_dropdown, anio_dropdown)
    if not codcas or not periodo or not anio:
        return [], []
    if not re.fullmatch(r"\d{2}", periodo):
        return [], []
    if not re.fullmatch(r"[A-Za-z0-9]+", codcas):
        return [], []
    engine = create_connection()
    if engine is None:
        return [], []
    query = f"""
            SELECT
                c.servhosdes as servicio,
                a.actespnom as subactividad,
                ag.agrupador AS agrupador,
                e.especialidad,
                am.actdes,
                ca.cenasides,
                ce.acto_med
            FROM dwsge.dw_consulta_externa_homologacion_{anio}_{periodo} ce
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
            LEFT JOIN dwsge.dim_agrupador as ag ON ce.cod_agrupador = ag.cod_agrupador
            WHERE ce.cod_centro = '{codcas}'
            AND ce.cod_actividad = '91'
            AND ce.clasificacion IN (1,3,0)
            AND ce.cod_variable = '001'
            UNION ALL
            SELECT
                c.servhosdes as servicio,
                a.actespnom as subactividad,
                ag.agrupador AS agrupador,
                e.especialidad,
                am.actdes,
                ca.cenasides,
                p.acto_med
            FROM dwsge.dwe_consulta_externa_citados_homologacion_{anio}_{periodo} p
            LEFT JOIN dwsge.sgss_cmsho10 AS c 
                ON p.cod_servicio = c.servhoscod
            LEFT JOIN dwsge.dim_especialidad AS e
                ON p.cod_especialidad = e.cod_especialidad
            LEFT JOIN dwsge.sgss_cmace10 AS a
                ON p.cod_actividad = a.actcod
                AND p.cod_subactividad = a.actespcod
            LEFT JOIN dwsge.sgss_cmact10 AS am
                ON p.cod_actividad = am.actcod
            LEFT JOIN dwsge.sgss_cmcas10 AS ca
                ON p.cod_oricentro = ca.oricenasicod
                AND p.cod_centro = ca.cenasicod
            LEFT JOIN dwsge.dim_agrupador as ag ON p.cod_agrupador = ag.cod_agrupador
            WHERE p.cod_centro = '{codcas}'
            AND p.cod_actividad = '91'
            AND p.cod_variable = '001'
            AND p.cod_estado IN ('1','2','5');
    """
    try:
        df = pd.read_sql(query, engine)
    except Exception:
        return [], []
    if df.empty:
        return [], []
    rows = (df[["servicio", "subactividad", "agrupador", "especialidad", "acto_med"]]
              .fillna("")
              .to_dict("records"))
    # Conteo de filas, NO suma de acto_med
    count_rows = len(rows)
    pinned = [{
        "servicio": "TOTAL FILAS",
        "subactividad": "",
        "agrupador": "",
        "especialidad": "",
        "acto_med": count_rows  # mantener numérico
    }]
    return rows, pinned


@callback(
    Output("td-download", "data"),
    Input("td-download-btn", "n_clicks"),
    State("hp-page-url", "pathname"),
    State("hp-page-url", "search"),
    State("filter-periodo", "value"),
    State("filter-anio", "value"),
    prevent_initial_call=True
)
def tm_descargar_csv(n_clicks, pathname, search, periodo_dropdown, anio_dropdown):
    if not n_clicks:
        return None
    codcas, periodo, anio = get_codcas_periodo(pathname, search, periodo_dropdown, anio_dropdown)
    if not codcas or not periodo or not anio:
        return None
    engine = create_connection()
    if engine is None:
        return None
    query = f"""
            SELECT            
                c.servhosdes as servicio,
                a.actespnom as subactividad,
                ag.agrupador AS agrupador,
                e.especialidad,
                am.actdes,
                ca.cenasides,
                ce.acto_med
            FROM dwsge.dw_consulta_externa_homologacion_{anio}_{periodo} ce
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
            LEFT JOIN dwsge.dim_agrupador as ag ON ce.cod_agrupador = ag.cod_agrupador
            WHERE ce.cod_centro = '{codcas}'
            AND ce.cod_actividad = '91'
            AND ce.clasificacion IN (1,3,0)
            AND ce.cod_variable = '001'

            UNION ALL

            SELECT
                c.servhosdes as servicio,
                a.actespnom as subactividad,
                ag.agrupador AS agrupador,
                e.especialidad,
                am.actdes,
                ca.cenasides,
                p.acto_med
            FROM dwsge.dwe_consulta_externa_citados_homologacion_{anio}_{periodo} p
            LEFT JOIN dwsge.sgss_cmsho10 AS c 
                ON p.cod_servicio = c.servhoscod
            LEFT JOIN dwsge.dim_especialidad AS e
                ON p.cod_especialidad = e.cod_especialidad
            LEFT JOIN dwsge.sgss_cmace10 AS a
                ON p.cod_actividad = a.actcod
                AND p.cod_subactividad = a.actespcod
            LEFT JOIN dwsge.sgss_cmact10 AS am
                ON p.cod_actividad = am.actcod
            LEFT JOIN dwsge.sgss_cmcas10 AS ca
                ON p.cod_oricentro = ca.oricenasicod
                AND p.cod_centro = ca.cenasicod
            LEFT JOIN dwsge.dim_agrupador as ag ON p.cod_agrupador = ag.cod_agrupador
            WHERE p.cod_centro = '{codcas}'
            AND p.cod_actividad = '91'
            AND p.cod_variable = '001'
            AND p.cod_estado IN ('1','2','5');
    """
    try:
        df = pd.read_sql(query, engine)
    except Exception:
        return None
    filename = f"total_desercion_{codcas}_{anio}_{periodo}.csv"
    return dcc.send_data_frame(df.to_csv, filename, index=False, encoding="utf-8-sig", sep="|")

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
    import secure_code as sc
    codcas = pathname.rstrip("/").split("/")[-1]
    codcas = sc.decode_code(codcas)
    periodo = _parse_periodo(search) or periodo_dropdown
    anio = _parse_anio(search) or anio_dropdown
    return codcas, periodo, anio