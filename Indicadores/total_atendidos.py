from dash import html, dcc, register_page, Input, Output, State, callback
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import dash_ag_grid as dag

BRAND = "#0064AF"
CARD_BG = "#FFFFFF"
MUTED = "#6c757d"
FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"
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
    fig.update_layout(template="simple_white")
    if title:
        fig.update_layout(title=title)
    return fig

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
        # Lado izquierdo: título + subtítulo
        html.Div([
            html.H4("Detalle de PERSONAS ATENDIDAS",
                    style={"margin": 0, "color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700}),
            html.P("Visualización del periodo seleccionado.",
                   style={"color": MUTED, "fontSize": "13px", "marginTop": "4px", "fontFamily": FONT_FAMILY})
        ]),
        # Lado derecho: botón descargar
        html.Div([
            html.Button(
                "Descargar CSV",
                id="btn-download-query1",
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
            dcc.Download(id="download-query1-csv")
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
        id="main-tabs",
        value="tab-graficos",
        style={"border": "none"},
        parent_style={"marginTop": "12px"},
        className="custom-tabs",
        children=[
            dcc.Tab(
                label="Personas atendidas",
                value="tab-graficos",
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=html.Div([
                    # Primer bloque: barras servicio / especialidad
                    html.Div([
                        dcc.Loading(
                            html.Div([
                                dcc.Graph(
                                    id="fig-atendidos-servicio",
                                    figure=empty_fig("Atendidos por servicio"),
                                    style={"flex": "1", "minWidth": "300px"}
                                ),
                                html.Div(
                                         style={"flex": "1", "minWidth": "300px"}),
                            ], style={"display": "flex", "gap": "8px", "flexWrap": "wrap"}),
                            type="dot"
                        )
                    ], style={**CARD_STYLE}),
                    # Segundo bloque: gráfico agrupador + especialidad (lado a lado)
                    html.Div([
                        dcc.Loading(
                            html.Div([
                                html.Div(
                                    
                                    style={"flex": "1", "minWidth": "300px"}
                                ),
                                html.Div(
                                    
                                    style={"flex": "1", "minWidth": "300px"}
                                ),
                            ], style={"display": "flex", "gap": "8px", "flexWrap": "wrap"}),
                            type="dot"
                        ),
                        html.Div(
                            id="total-atendidos-msg",
                            style={"marginTop": "6px", "color": MUTED, "fontFamily": FONT_FAMILY, "fontSize": "12px", "fontWeight": "bold"}
                        )
                    ], style={**CARD_STYLE, "marginTop": "12px"}),
                    # Tercer bloque: Tornado (movido dentro del primer tab)
                    html.Div([
                        html.H5("Sexo y grupo etario vs atendidos",
                                style={"color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 600, "marginBottom": "8px"}),
                        dcc.Loading(
                            html.Div([
                                
                            ]),
                            type="dot"
                        ),
                        html.Div(id="tornado-atendidos-msg",
                                 style={"marginTop": "6px", "color": MUTED, "fontFamily": FONT_FAMILY,
                                        "fontSize": "12px", "fontWeight": "bold"})
                    ], style={**CARD_STYLE, "marginTop": "12px"})
                ], style={"padding": "4px"})
            ),
            dcc.Tab(
                label="Diagnósticos por atendidos",
                value="tab-resumen",
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=html.Div([
                    html.Div([
                        html.H5("Resumen servicio / subactividad / diagnóstico",
                                style={"color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 600,
                                       "marginBottom": "8px"}),
                        # NUEVO: gráfico Top10 coddiag x sexo (antes de la tabla)
                        dcc.Loading(
                        ),
                        html.Div(id="tabla-resumen-atendidos-wrapper")
                    ], style={**CARD_STYLE})
                ], style={"padding": "4px"})
            )
        ],
        content_style=TABS_CONTAINER_STYLE
    ),
    # Stores
    dcc.Store(id="store-detalle-data")
], style={
    "maxWidth": "1400px",
    "margin": "0 auto",
    "padding": "4px 4px 20px 4px",  
    "fontFamily": FONT_FAMILY
})


# Registrar la página con el layout explícito para evitar NoLayoutException
register_page(
    __name__,
    path_template="/dash/total_atendidos/<codcas>",
    name="total_atendidos",
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
    import secure_code as sc
    codcas = pathname.rstrip("/").split("/")[-1]
    codcas = sc.decode_code(codcas)
    periodo = _parse_periodo(search) or periodo_dropdown
    return codcas, periodo

def update_total_atenciones(pathname, search, periodo_dropdown):
    empty_div = html.Div()
    codcas, periodo = get_codcas_periodo(pathname, search, periodo_dropdown)
    if not codcas:
        return empty_fig(), empty_fig(), "Sin ruta.", empty_div, None, empty_div, empty_fig()
    if not periodo:
        return empty_fig(), empty_fig(), "Falta periodo (URL sin ?periodo=MM y dropdown vacío).", empty_div, None, empty_div, empty_fig()
    engine = create_connection()
    if engine is None:
        return empty_fig(), empty_fig(), "Error de conexión a la base de datos.", empty_div, None, empty_div, empty_fig()
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
            c.servhosdes AS descripcion_servicio,
            e.especialidad AS descripcion_especialidad,
            t.tipcondes AS descripcion_tipo_consulta,
            d.diagdes AS descripcion_diagnostico,
            dni_medico,
            doc_paciente,
            cod_tipdoc_paciente,
            sexo,
            fecha_atencion,
            acto_med
        FROM dwsge.dw_consulta_externa_homologacion_2025_{periodo} AS ce
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
    """
    try:
        df = pd.read_sql(query, engine)
        # corregido (no usado aquí, solo se deja consistente)
        # atendidos = df[['cod_tipdoc_paciente','doc_paciente']].drop_duplicates().shape[0]
    except Exception as e:
        return empty_fig(), empty_fig(), f"Error ejecutando consulta: {e}", empty_div, None, empty_div, empty_fig()
    if df.empty:
        return (
            empty_fig(),
            empty_fig(),
            f"Sin datos para periodo {periodo}.",
            empty_div,                # tabla-detalle-wrapper
            None,                     # store-detalle-data
            html.Div("Sin datos resumen.", style={"color": "#b00"}),
            empty_fig(f"Top 10 diagnósticos por atenciones - Periodo {periodo}")
        )

# NUEVO: callback para gráfico "número de atendidos por servicio"
@callback(
    Output("fig-atendidos-servicio", "figure"),
    Input("page-url", "pathname"),
    Input("page-url", "search"),
)
def render_atendidos_por_servicio(pathname, search):
    codcas, periodo = get_codcas_periodo(pathname, search, None)
    title_base = "Atendidos por servicio"
    if not codcas or not periodo:
        return empty_fig(f"{title_base}")

    engine = create_connection()
    if engine is None:
        return empty_fig(f"{title_base} - Error de conexión")

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
            c.servhosdes AS descripcion_servicio,
            e.especialidad AS descripcion_especialidad,
            t.tipcondes AS descripcion_tipo_consulta,
            d.diagdes AS descripcion_diagnostico,
            dni_medico,
            doc_paciente,
            cod_tipdoc_paciente,
            sexo,
            fecha_atencion,
            acto_med
        FROM dwsge.dw_consulta_externa_homologacion_2025_{periodo} AS ce
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
    """
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        return empty_fig(f"{title_base} - Error: {e}")

    if df.empty:
        return empty_fig(f"{title_base} - Sin datos periodo {periodo}")

    # Construir ID único de paciente y contar únicos por servicio
    df["paciente_id"] = df["cod_tipdoc_paciente"].astype(str) + "-" + df["doc_paciente"].astype(str)
    svc = (
        df.dropna(subset=["descripcion_servicio", "paciente_id"])
          .drop_duplicates(subset=["descripcion_servicio", "paciente_id"])
          .groupby("descripcion_servicio", as_index=False)["paciente_id"]
          .count()
          .rename(columns={"paciente_id": "atendidos"})
          .sort_values("atendidos", ascending=True)
    )

    order = svc["descripcion_servicio"].tolist()
    fig = px.bar(
        svc,
        y="descripcion_servicio",
        x="atendidos",
        orientation="h",
        title=f"{title_base} - Periodo {periodo}",
        labels={"descripcion_servicio": "Servicio", "atendidos": "Personas atendidas"},
        template="simple_white",
    )
    fig.update_traces(marker_color=BRAND, hovertemplate="%{y}<br>Atendidos: %{x}<extra></extra>")
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="Personas atendidas",
        yaxis_title="Servicio",
        yaxis=dict(automargin=True, categoryorder="array", categoryarray=order),
        showlegend=False,
    )
    return fig
