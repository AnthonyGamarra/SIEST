import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
from sqlalchemy import create_engine
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# ==========================================================
# CONFIG
# ==========================================================
BRAND = "#0064AF"
CARD_BG = "#FFFFFF"
MUTED = "#6c757d"
FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"
BAR_COLOR_SCALE = ["#D7E9FF", "#92C4F9", "#2E78C7"]
PRIORIDAD = 2
COLOR_CONF = {
    'gradient': 'linear-gradient(135deg, #fd7e14 0%, #e8590c 100%)',
    'icon': 'bi-exclamation-circle-fill',
    'bg': '#fd7e14'
}
DB_URI = "postgresql+psycopg2://postgres:admin@10.0.29.117:5433/DW_ESTADISTICA"

# ==========================================================
# ESTILOS DE FIGURA / PLACEHOLDER
# ==========================================================
def empty_fig(title_text):
    fig = go.Figure()
    fig.update_layout(
        template="simple_white",
        paper_bgcolor="#F9FBFD",
        plot_bgcolor="#F9FBFD",
        title=dict(text=title_text, font=dict(size=18, color=BRAND)),
        margin=dict(l=40, r=20, t=50, b=40)
    )
    fig.add_annotation(
        text="Sin datos disponibles",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(color=MUTED)
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig

def style_horizontal(fig):
    fig.update_traces(
        orientation="h",
        hovertemplate="<b>%{y}</b><br>Atenciones: %{x}<extra></extra>",
        texttemplate="%{x}",
        textposition="outside"
    )
    fig.update_layout(
        plot_bgcolor="#F9FBFD",
        paper_bgcolor="#F9FBFD",
        font=dict(family=FONT_FAMILY, color="#1F2937"),
        margin=dict(l=80, r=20, t=50, b=40),
        xaxis=dict(title="Atenciones", showgrid=True, gridcolor="rgba(80,80,80,0.1)"),
        yaxis=dict(title="Diagnóstico", showgrid=False)
    )
    return fig

# ==========================================================
# HEADER
# ==========================================================
header = html.Div(
    [
        html.Img(src="/dashboard_alt/assets/logo.png", style={"width": "120px", "marginRight": "15px"}),
        html.Div(
            [
                html.H2(
                    f"Detalle de Atenciones - Prioridad {PRIORIDAD}",
                    style={"color": BRAND, "fontFamily": FONT_FAMILY}
                ),
                html.P(
                    f"📅 Actualizado al {date.today().strftime('%d/%m/%Y')}",
                    style={"color": MUTED, "fontSize": "13px"}
                )
            ]
        ),
      
    ],
    style={
        "padding": "14px 18px",
        "backgroundColor": CARD_BG,
        "borderRadius": "12px",
        "display": "flex",
        "alignItems": "center",
        "gap": "16px"
    }
)

# ==========================================================
# LAYOUT
# ==========================================================
def layout(codcas=None, **_):
    return html.Div(
        [
            dcc.Store(id="ate-topicos-codcas-store-2", data=codcas),
            dcc.Location(id="ate-topicos-url-2", refresh=False),
            header,
            dcc.Loading(dcc.Graph(id="diag-bar-chart-2")),
            html.Div(id="ate-topicos-msg-2", style={"marginTop": "8px", "color": "#0064AF", "fontSize": "16px"}),
            html.Div([
                html.H5("Atenciones por Fecha", style={"color": BRAND, "marginTop": "24px"}),
                dcc.Loading(dcc.Graph(id="timeline-atenciones-2")),
            ], style={
                "backgroundColor": CARD_BG,
                "borderRadius": "14px",
                "boxShadow": "0 8px 20px rgba(0,0,0,0.08)",
                "padding": "18px 18px 18px 18px",
                "marginTop": "18px"
            }),
            # Nuevo Card para el gráfico circular por tipo de paciente
            html.Div([
                html.H5("Distribución por Tipo de Paciente", style={"color": BRAND, "marginTop": "24px"}),
                dcc.Loading(dcc.Graph(id="pie-tipo-paciente-2"))
            ], style={
                "backgroundColor": CARD_BG,
                "borderRadius": "14px",
                "boxShadow": "0 8px 20px rgba(0,0,0,0.08)",
                "padding": "18px 18px 18px 18px",
                "marginTop": "18px"
            }),
        ]
    )

# ==========================================================
# DB
# ==========================================================
def get_engine():
    try:
        engine = create_engine(DB_URI, pool_pre_ping=True)
        return engine
    except Exception as e:
        return None

def build_query(periodo, codcas):
    return f"""
        SELECT d.diagdes
        FROM dwsge.dwe_emergencia_atenciones_homologacion_2025_{periodo} a
        LEFT JOIN dwsge.sgss_cmdia10 d ON d.diagcod=a.cod_diagnostico
        WHERE a.cod_diagnostico IS NOT NULL
          AND a.cod_estandar='05'
          AND a.cod_centro='{codcas}'
        """

# ==========================================================
# CALLBACK
# ==========================================================
def register_callbacks(app):
    @app.callback(
        [
            Output("diag-bar-chart-2", "figure"),
            Output("ate-topicos-msg-2", "children")
        ],
        [
            Input("ate-topicos-codcas-store-2", "data"),
            Input("ate-topicos-url-2", "search")
        ]
    )
    def update(codcas, search):
        if not codcas:
            return empty_fig("Top 10 Diagnósticos"), "Seleccione un centro."

        # Periodo desde URL
        periodo = None
        if search:
            params = dict(x.split("=") for x in search.lstrip("?").split("&") if "=" in x)
            periodo = params.get("periodo")

        if not periodo or not periodo.isdigit() or len(periodo) != 2:
            return empty_fig("Top 10 Diagnósticos"), "Periodo inválido."

        engine = get_engine()
        if not engine:
            return empty_fig("Top 10 Diagnósticos"), "No hay conexión a la BD."

        sql = build_query(periodo, codcas)

        try:
            df = pd.read_sql(sql, engine)
        except Exception as e:
            return empty_fig("Top 10 Diagnósticos"), "Error durante la consulta."

        if df.empty:
            return empty_fig("Top 10 Diagnósticos"), "No hay registros."

        diag_df = (
            df.assign(diagdes=df["diagdes"].fillna("SIN DIAGNÓSTICO"))
            .groupby("diagdes")
            .size()
            .reset_index(name="Atenciones")
            .sort_values("Atenciones", ascending=False)
            .head(10)
        )

        fig = px.bar(
            diag_df,
            y="diagdes",
            x="Atenciones",
            color="Atenciones",
            color_continuous_scale=BAR_COLOR_SCALE,
            title=f"Top 10 Diagnósticos P2 — Centro {codcas} ({periodo})"
        )
        fig = style_horizontal(fig)

        return fig, f"Mostrando {len(diag_df)} diagnósticos."
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
from sqlalchemy import create_engine
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date


# Estilos y colores consistentes con dashboard_eme.py
BRAND = "#0064AF"
CARD_BG = "#FFFFFF"
TEXT = "#212529"
MUTED = "#6c757d"
FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"
PRIORIDAD_COLORS = {
    '1': {'gradient': 'linear-gradient(135deg, #dc3545 0%, #c82333 100%)', 'icon': 'bi-exclamation-triangle-fill', 'bg': '#dc3545'},
    '2': {'gradient': 'linear-gradient(135deg, #fd7e14 0%, #e8590c 100%)', 'icon': 'bi-exclamation-circle-fill', 'bg': '#fd7e14'},
    '3': {'gradient': 'linear-gradient(135deg, #ffc107 0%, #e0a800 100%)', 'icon': 'bi-exclamation-diamond-fill', 'bg': '#ffc107'},
    '4': {'gradient': 'linear-gradient(135deg, #28a745 0%, #218838 100%)', 'icon': 'bi-check-circle-fill', 'bg': '#28a745'},
    '5': {'gradient': 'linear-gradient(135deg, #17a2b8 0%, #138496 100%)', 'icon': 'bi-info-circle-fill', 'bg': '#17a2b8'}
}

prioridad = 2
color_config = PRIORIDAD_COLORS[str(prioridad)]
BAR_COLOR_SCALE = ["#D7E9FF", "#92C4F9", "#2E78C7"]
GRID = "#e9ecef"

# Helpers de gráficos
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

def style_horizontal_bar(fig: go.Figure, x_title: str, y_title: str, height: int = 400) -> go.Figure:
    title_text = getattr(getattr(fig.layout, "title", None), "text", "") or ""
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>Atenciones: %{x:,.0f}<extra></extra>",
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

header = html.Div([
    html.Div([
        html.Img(
            src='/dashboard_alt/assets/logo.png',
            style={
                'width': '120px',
                'height': '60px',
                'objectFit': 'contain',
                'marginRight': '20px',
            }
        ),
        html.Div([
            html.Div([
                html.I(className=f"bi {color_config['icon']}", style={
                    'fontSize': '32px',
                    'color': color_config['bg'],
                    'marginRight': '12px'
                }),
                html.H2(
                    f"Detalle de Atenciones - Prioridad {prioridad}",
                    style={
                        'color': BRAND,
                        'fontFamily': FONT_FAMILY,
                        'fontSize': '26px',
                        'margin': '0',
                        'fontWeight': '700'
                    }
                )
            ], style={'display': 'flex', 'alignItems': 'center'}),
            html.P(
                f"📅 Información actualizada al {date.today().strftime('%d/%m/%Y')} | Sistema de Gestión Hospitalaria",
                style={
                    'color': MUTED,
                    'fontFamily': FONT_FAMILY,
                    'fontSize': '13px',
                    'margin': '8px 0 0 0'
                }
            )
        ], style={
            'display': 'flex',
            'flexDirection': 'column',
            'justifyContent': 'center',
            'flex': '1'
        }),
       
    ], style={
        'display': 'flex',
        'alignItems': 'center',
        'padding': '16px 20px',
        'backgroundColor': CARD_BG,
        'borderRadius': '14px',
        'boxShadow': '0 8px 20px rgba(0,0,0,0.08)',
        'gap': '20px'
    }),
    html.Br(),
])

def layout(codcas=None, **kwargs):
    return html.Div([
        dcc.Store(id='ate-topicos-codcas-store-2', data=codcas),
        dcc.Location(id="ate-topicos-url-2", refresh=False),
        header,
        dcc.Loading(
            dcc.Graph(id="diag-bar-chart-2")
        ),
        html.Div(id="ate-topicos-msg-2", style={"marginTop": "8px", "color": "#0064AF", "fontSize": "16px"}),
        html.Div([
            html.H5("Atenciones por Fecha", style={"color": BRAND, "marginTop": "24px"}),
            dcc.Loading(dcc.Graph(id="timeline-atenciones-2")),
        ], style={
            "backgroundColor": CARD_BG,
            "borderRadius": "14px",
            "boxShadow": "0 8px 20px rgba(0,0,0,0.08)",
            "padding": "18px 18px 18px 18px",
            "marginTop": "18px"
        }),
        # Nuevo Card para el gráfico circular por tipo de paciente
        html.Div([
            html.H5("Distribución por Tipo de Paciente", style={"color": BRAND, "marginTop": "24px"}),
            dcc.Loading(dcc.Graph(id="pie-tipo-paciente-2"))
        ], style={
            "backgroundColor": CARD_BG,
            "borderRadius": "14px",
            "boxShadow": "0 8px 20px rgba(0,0,0,0.08)",
            "padding": "18px 18px 18px 18px",
            "marginTop": "18px"
        }),
    ])


# Conexión DB
def create_connection():
    try:
        engine = create_engine('postgresql+psycopg2://postgres:admin@10.0.29.117:5433/DW_ESTADISTICA')
        print("Database engine created successfully.")
        with engine.connect():
            pass
        return engine
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        return None


def update_page_content(codcas, search):
    periodo = None
    if search:
        parts = dict(p.split("=", 1) for p in search.lstrip("?").split("&") if "=" in p)
        periodo = parts.get("periodo")

    if not periodo:
        return empty_fig("Top 10 Diagnósticos (Prioridad 2)"), "Seleccione un periodo en el dashboard principal."
    if not codcas:
        return empty_fig("Top 10 Diagnósticos (Prioridad 2)"), "No se ha especificado un centro (codcas)."

    engine = create_connection()
    if engine is None:
        return empty_fig("Top 10 Diagnósticos (Prioridad 2)"), "Error de conexión a la base de datos."

    query = f"""
            SELECT
            d.cod_centro,d.periodo,d.cod_topico,d.topemedes as topico_essi,d.acto_med,d.fecha_aten,d.hora_aten,d.cod_tipo_paciente, d.tipopacinom,
            d.cod_prioridad,d.cod_emergencia,
            d.secuen_aten,d.cod_estandar,d.des_estandar as topico_ses,d.cod_diagnostico,d.diagdes,d.cod_prioridad_n
            FROM (
                SELECT 
                    ROW_NUMBER() OVER (PARTITION BY cod_centro, cod_estandar, 
            acto_med,cod_emergencia ORDER BY cast(secuen_aten as integer) asc) AS SECUENCIA, c.*
                FROM (SELECT
                        a.cod_centro, 
                        a.periodo, 
                        a.cod_topico,
                        top.topemedes,
                        acto_med, 
                        fecha_aten, 
                        hora_aten, 
                        cod_tipo_paciente,
                        tp.tipopacinom,
                        cod_prioridad, 
                        a.cod_emergencia, 
                        secuen_aten, 
                        a.cod_estandar,
                        es.des_estandar,
                        a.cod_diagnostico,
                        dg.diagdes,
                (case when a.cod_estandar = '04' then '1'
                else (case when a.cod_prioridad='1' then '2'
                            else (a.cod_prioridad) 
                            end) 
                end )as cod_prioridad_n
                        FROM 
                            dwsge.dwe_emergencia_atenciones_homologacion_2025_{periodo} a
                LEFT OUTER JOIN dwsge.sgss_cmdia10 dg ON dg.diagcod=a.cod_diagnostico
                LEFT OUTER JOIN dwsge.sgss_cbtpc10 tp ON tp.tipopacicod= a.cod_tipo_paciente
                LEFT OUTER JOIN dwsge.sgss_mbtoe10 top ON top.topemecod=a.cod_topico
                LEFT OUTER JOIN dwsge.dim_estandar es ON es.id_estandar = a.cod_estandar
                where (a.cod_diagnostico IS not NULL )
                and a.cod_estandar in ('04','05','06','07','08','09','10','11','12','13','14')
                ) c	
            ) d

            WHERE
                d.SECUENCIA = '1'
            and cod_centro = '{codcas}'
            and cod_prioridad_n = '2'
        """
    try:
        df = pd.read_sql(query, engine)
        print("Query executed successfully")

    except Exception as e:
        return empty_fig("Top 10 Diagnósticos (Prioridad 3)"), f"Error al ejecutar la consulta: {e}"

    if df.empty:
        return empty_fig(f"Top 10 Diagnósticos - Sin datos para {codcas} en periodo {periodo}"), "No se encontraron registros."

    total_atenciones = df.shape[0]
    diag_df = (
        df.groupby(['cod_diagnostico', 'diagdes'], dropna=False)
        .size()
        .reset_index(name='Atenciones')
        .sort_values('Atenciones', ascending=False)
        .head(10)
    )
    diag_df['diagdes'] = diag_df['diagdes'].fillna('SIN DIAGNÓSTICO')
    diag_df['label'] = diag_df['Atenciones'].apply(
        lambda v: f"{v:,.0f} ({(v/total_atenciones):.1%})" if total_atenciones else f"{v:,.0f}"
    )

    fig = px.bar(
        diag_df,
        y='diagdes',
        x='Atenciones',
        orientation='h',
        title=f"Top 10 Diagnósticos - Prioridad 2 (Centro: {codcas} | Periodo: {periodo})",
        text='label',
        color='Atenciones',
        color_continuous_scale=BAR_COLOR_SCALE,
    )
    fig = style_horizontal_bar(fig, x_title="Atenciones", y_title="Diagnóstico")

    # Gráfico de línea de tiempo por fecha_aten
    try:
        df_fecha = df.copy()
        df_fecha['fecha_aten'] = pd.to_datetime(df_fecha['fecha_aten'], errors='coerce')
        timeline_df = (
            df_fecha.groupby('fecha_aten', dropna=True)
            .size()
            .reset_index(name='Atenciones')
            .sort_values('fecha_aten')
        )
        timeline_fig = px.line(
            timeline_df,
            x='fecha_aten',
            y='Atenciones',
            markers=True,
            title="Atenciones por Fecha",
            line_shape="linear",
        )
        timeline_fig.update_traces(line_color=BRAND, marker_color=BRAND)
        timeline_fig.update_layout(
            xaxis_title="Fecha de Atención",
            yaxis_title="Atenciones",
            plot_bgcolor="#F9FBFD",
            paper_bgcolor="#F9FBFD",
            font=dict(family=FONT_FAMILY, color="#1F2937"),
            margin=dict(l=60, r=32, t=70, b=40),
        )
    except Exception as e:
        timeline_fig = empty_fig("Atenciones por Fecha")

    # Gráfico circular por tipo de paciente
    try:
        pie_df = (
            df.groupby('cod_tipo_paciente', dropna=False)
            .size()
            .reset_index(name='Atenciones')
        )
        pie_df['cod_tipo_paciente'] = pie_df['cod_tipo_paciente'].fillna('SIN TIPO')
        pie_fig = px.pie(
            pie_df,
            names='cod_tipo_paciente',
            values='Atenciones',
            title="Distribución por Tipo de Paciente",
            color_discrete_sequence=BAR_COLOR_SCALE
        )
        pie_fig.update_traces(textinfo='label+percent', pull=[0.05]*len(pie_df))
        pie_fig.update_layout(
            font=dict(family=FONT_FAMILY, color="#1F2937"),
            margin=dict(l=40, r=40, t=60, b=40),
            legend_title_text="Tipo de Paciente",
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
    except Exception as e:
        pie_fig = empty_fig("Distribución por Tipo de Paciente")

    return fig, "", timeline_fig, pie_fig

def register_callbacks(app):
    app.callback(
        [Output("diag-bar-chart-2", "figure"),
         Output("ate-topicos-msg-2", "children"),
         Output("timeline-atenciones-2", "figure"),
         Output("pie-tipo-paciente-2", "figure")],
        [Input("ate-topicos-codcas-store-2", "data"),
         Input("ate-topicos-url-2", "search")],
    )(update_page_content)
