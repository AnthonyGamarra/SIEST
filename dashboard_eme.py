from dash import Dash, html, dcc, Input, Output, State
from flask import has_request_context
from flask_login import current_user
from sqlalchemy import create_engine
import pandas as pd
import dash_bootstrap_components as dbc
import plotly.express as px
from datetime import date
import dash_ag_grid as dag
import os  # agregado
import dash
from urllib.parse import quote_plus

# Importar páginas de detalle
from Indicadores import ate_topicos_1
from Indicadores import ate_topicos_2
from Indicadores import ate_topicos_3
from Indicadores import ate_topicos_4
from Indicadores import ate_topicos_5


def create_dash_app(flask_app, url_base_pathname='/dashboard_alt/'):
    external_stylesheets = [
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
    ]

    # Paleta y estilos consistentes con dashboard.py
    BRAND = "#0064AF"
    BRAND_SOFT = "#D7E9FF"
    ACCENT = "#00AEEF"
    CARD_BG = "#FFFFFF"
    TEXT = "#1C1F26"
    MUTED = "#6B7280"
    BORDER = "#E5E7EB"
    FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"

    # Colores por prioridad
    PRIORIDAD_COLORS = {
        '1': '#dc3545',
        '2': '#fd7e14',
        '3': '#ffc107',
        '4': '#28a745',
        '5': '#17a2b8'
    }

    CARD_STYLE = {
        "cursor": "pointer",
        "border": f"1px solid {BORDER}",
        "borderRadius": "14px",
        "backgroundColor": CARD_BG,
        "boxShadow": "0 10px 24px rgba(0,0,0,0.08)",
        "padding": "6px",
        "transition": "transform .12s ease, box-shadow .12s ease",
    }
    CARD_BODY_STYLE = {
        "padding": "18px",
        "background": "linear-gradient(180deg, #ffffff 0%, #f9fbff 100%)",
        "borderRadius": "12px",
    }

    # Use a unique name for the Dash instance to avoid conflicts when mounting multiple apps on the same Flask server
    app_name = f"dash_{url_base_pathname.strip('/').replace('/', '_') or 'alt'}"

    # asegurar carpeta de assets correcta (assets junto a este archivo) y assets_url_path consistente
    assets_path = os.path.join(os.path.dirname(__file__), "assets")
    # construir assets_url_path sin duplicar barras
    assets_url_path = f"{url_base_pathname.rstrip('/')}/assets"

    dash_app = Dash(
        name=app_name,
        server=flask_app,
        url_base_pathname=url_base_pathname,  # <-- use provided pathname
        assets_folder=assets_path,            # <- ruta física a assets
        assets_url_path=assets_url_path,      # <- ruta pública para assets (única por app)
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
    )

    dash_app.title = "SIEST"

    # Registrar callbacks de páginas de detalle
    from Indicadores import ate_topicos_1, ate_topicos_2, ate_topicos_3, ate_topicos_4, ate_topicos_5
    ate_topicos_1.register_callbacks(dash_app)
    ate_topicos_2.register_callbacks(dash_app)
    ate_topicos_3.register_callbacks(dash_app)
    ate_topicos_4.register_callbacks(dash_app)
    ate_topicos_5.register_callbacks(dash_app)

    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    anio = ['2025', '2026']
    tipo_asegurado = ['Asegurado', 'No Asegurado', 'Todos']
    anio_options = [{'label': year, 'value': year} for year in anio]
    valores = [f"{i:02d}" for i in range(1, 13)]
    df_period = pd.DataFrame({'mes': meses, 'periodo': valores})
    tipo_asegurado_options = [{'label': tipo, 'value': tipo} for tipo in tipo_asegurado]

    DEFAULT_TIPO_ASEGURADO = 'Todos'
    TIPO_ASEGURADO_SQL = {
        'Asegurado': "('1')",
        'No Asegurado': "('2')",
        'Todos': "('1','2')"
    }

    def resolve_tipo_asegurado_clause(selection: str | None) -> str:
        normalized = selection if selection in TIPO_ASEGURADO_SQL else DEFAULT_TIPO_ASEGURADO
        return TIPO_ASEGURADO_SQL[normalized]

    def render_card(title, value, border_color, subtitle_text, href=None, extra_style=None):
        link_content = html.H5(
            title,
            className="card-title",
            style={
                'color': BRAND,
                'marginBottom': '6px',
                'fontFamily': FONT_FAMILY,
                'letterSpacing': '-0.1px'
            }
        )
        heading = dcc.Link(
            link_content,
            href=href,
            className=(
                "link-underline-primary link-underline-opacity-0 "
                "link-underline-opacity-100-hover link-offset-2-hover text-reset"
            )
        ) if href else link_content

        card_style = {**CARD_STYLE, "borderLeft": f"5px solid {border_color}", "height": "100%"}
        if extra_style:
            card_style.update(extra_style)

        return dbc.Card(
            dbc.CardBody([
                heading,
                html.H2(value, style={
                    'fontWeight': '800', 'color': TEXT, 'fontSize': '34px', 'margin': 0,
                    'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.2px'
                }),
                html.P(subtitle_text, style={
                    'fontSize': '12px', 'color': MUTED, 'margin': '6px 0 0 0', 'fontFamily': FONT_FAMILY
                })
            ], style=CARD_BODY_STYLE),
            style=card_style
        )

    def render_priority_table(dataframe):
        if dataframe is None or dataframe.empty:
            body_children = [
                html.P(
                    "Sin registros",
                    className="text-muted mb-0",
                    style={'fontFamily': FONT_FAMILY, 'fontSize': '12px'}
                )
            ]
        else:
            table_body = html.Tbody([
                html.Tr([
                    html.Td(
                        row.get('des_estandar') or "Sin tópico",
                        style={'padding': '4px 8px', 'lineHeight': '1.1'}
                    ),
                    html.Td(
                        f"{row.get('Atenciones', 0):,.0f}",
                        style={'textAlign': 'right', 'padding': '4px 8px', 'lineHeight': '1.1'}
                    )
                ])
                for _, row in dataframe.iterrows()
            ])

            body_children = [
                dbc.Table(
                    [table_body],
                    bordered=False,
                    hover=False,
                    responsive=True,
                    striped=False,
                    className="mb-0",
                    style={'fontSize': '12px'}
                )
            ]

        return dbc.Card(
            dbc.CardBody(
                body_children,
                style={**CARD_BODY_STYLE, 'padding': '14px'}
            ),
            style={**CARD_STYLE, "borderLeft": f"5px solid {ACCENT}", "height": "100%"}
        )

    # ========== LAYOUT ==========
    def serve_layout():
        if not has_request_context():
            return html.Div()

        if getattr(current_user, "is_authenticated", False):
            return dbc.Container([
                dcc.Location(id='url', refresh=False),

                html.Div([
                # ENCABEZADO
                html.Div([
                    html.Div([
                        html.Img(
                            src=dash_app.get_asset_url('logo.png'),
                            style={
                                'width': '120px',
                                'height': '60px',
                                'objectFit': 'contain',
                                'marginRight': '20px'
                            }
                        ),
                        html.Div([
                            html.Div([
                                html.I(className="bi bi-hospital", style={
                                    'fontSize': '32px',
                                    'color': BRAND,
                                    'marginRight': '12px'
                                }),
                                html.H2(
                                    "Emergencias - Prioridad por tópico",
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
                                f"📅 Información actualizada al 31/01/2026 | Sistema de Gestión Estadístico",
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
                        })
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
                ]),

                # FILTROS + BOTONES
                html.Div([
                    html.I(className="bi bi-calendar-week dashboard-control-icon", style={
                        'fontSize': '20px',
                        'color': BRAND,
                        'marginRight': '10px'
                    }),
                    dcc.Dropdown(
                        id='filter-anio',
                        options=anio_options,
                        placeholder='Año',
                        clearable=True,
                        style={
                            'width': '160px',
                            'fontFamily': FONT_FAMILY
                        }
                    ),
                    dcc.Dropdown(
                        id='filter-periodo',
                        options=[{'label': row['mes'], 'value': row['periodo']} for _, row in df_period.iterrows()],
                        placeholder='Periodo',
                        clearable=True,
                        style={
                            'width': '240px',
                            'fontFamily': FONT_FAMILY
                        }
                    ),
                    dcc.Dropdown(
                        id='filter-tipo-asegurado',
                        options=tipo_asegurado_options,
                        value=DEFAULT_TIPO_ASEGURADO,
                        clearable=False,
                        style={
                            'width': '200px',
                            'fontFamily': FONT_FAMILY
                        }
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-search me-2"), "Buscar"],
                        id='search-button',
                        color='primary',
                        className='dashboard-control-btn',
                        style={
                            'backgroundColor': BRAND,
                            'borderColor': BRAND,
                            'fontFamily': FONT_FAMILY,
                            'fontWeight': '600',
                            'borderRadius': '8px',
                            'padding': '8px 20px'
                        }
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-download me-2"), "Exportar CSV"],
                        id='download-button',
                        color='success',
                        className='dashboard-control-btn',
                        style={
                            'backgroundColor': '#28a745',
                            'borderColor': '#28a745',
                            'fontFamily': FONT_FAMILY,
                            'fontWeight': '600',
                            'borderRadius': '8px',
                            'padding': '8px 20px'
                        }
                    ),
                    dcc.Download(id="download-dataframe-csv"),
                    dbc.Button(
                        [html.I(className="bi bi-arrow-left me-1"), "Volver"],
                        id="btn-volver-eme",
                        color='secondary',
                        outline=True,
                        className='dashboard-control-btn dashboard-control-btn-back',
                        href='javascript:history.back();',
                        external_link=True,
                        style={
                            'marginLeft': 'auto',
                            'padding': '8px 12px'
                        }
                    ),
                ], className='dashboard-control-bar', style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'gap': '16px',
                    'marginBottom': '30px',
                    'padding': '20px',
                    'backgroundColor': CARD_BG,
                    'borderRadius': '14px',
                    'boxShadow': '0 8px 20px rgba(0,0,0,0.08)'
                }),
                dbc.Tooltip("Volver a la página anterior", target='btn-volver-eme', placement='bottom'),

                # CONTENEDORES
                dbc.Row([
                    dbc.Col(
                        html.Div(
                            dcc.Loading(
                                className='dashboard-loading-inline',
                                parent_className='dashboard-loading-parent',
                                parent_style={'width': '100%'},
                                type='default',
                                style={'width': '100%'},
                                children=html.Div(id='summary-container')
                            ),
                            className='dashboard-loading-shell'
                        ),
                        width=12
                    )
                ]),
                html.Br(),
                dbc.Row([
                    dbc.Col(
                        html.Div(
                            dcc.Loading(
                                className='dashboard-loading-inline',
                                parent_className='dashboard-loading-parent',
                                parent_style={'width': '100%'},
                                type='default',
                                style={'width': '100%'},
                                children=html.Div(id='charts-container')
                            ),
                            className='dashboard-loading-shell'
                        ),
                        width=12
                    )
                ]),
                ], id='main-eme-content'),

                # Contenedor para páginas de detalle
                html.Div(id='page-eme-container', style={'display': 'none'})

            ], fluid=True, style={
                'backgroundImage': "url('/static/76824.jpg')",
                'backgroundSize': 'cover',
                'backgroundPosition': 'center center',
                'backgroundRepeat': 'no-repeat',
                'backgroundAttachment': 'fixed',
                'minHeight': '100vh',
                'paddingTop': '20px',
                'paddingBottom': '20px'
            })

        return html.Div([
            html.H3('No autenticado'),
            html.P('Debes iniciar sesión para ver el dashboard.'),
            dbc.Button(
                'Volver',
                id='unauth-back-button-eme',
                color='primary',
                href='javascript:history.back();',
                external_link=True,
                style={'marginTop': '12px'}
            )
        ])

    # ========== CONEXIÓN DB ==========
    _engine = None
    _engine_lock = None
    
    def create_connection():
        """Crea o retorna una instancia singleton del engine de base de datos con reintentos."""
        nonlocal _engine, _engine_lock
        
        if _engine_lock is None:
            import threading
            _engine_lock = threading.Lock()
        
        with _engine_lock:
            if _engine is not None:
                try:
                    # Verificar si la conexión sigue válida
                    with _engine.connect() as conn:
                        pass
                    return _engine
                except Exception:
                    # Si falla, recrear el engine
                    _engine = None
            
            # Intentar crear nueva conexión con reintentos
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    import time
                    engine = create_engine(
                        'postgresql+psycopg2://app_user:sge02@10.0.29.117:5433/DW_ESTADISTICA',
                        pool_size=3,
                        max_overflow=2,
                        pool_pre_ping=True,
                        pool_recycle=1800,
                        pool_timeout=30,
                        echo_pool=False
                    )
                    # Verificar la conexión
                    with engine.connect() as conn:
                        pass
                    _engine = engine
                    return _engine
                except Exception as e:
                    print(f"[Dashboard EME] Intento {attempt + 1}/{max_retries} - Failed to connect: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(1 * (attempt + 1))
                    else:
                        print("[Dashboard EME] No se pudo establecer conexión después de todos los reintentos")
                        return None

    # Callback de Enrutamiento Manual (Reemplaza a Dash Pages)
    @dash_app.callback(
        Output('main-eme-content', 'style'),
        Output('page-eme-container', 'children'),
        Output('page-eme-container', 'style'),
        Input('url', 'pathname')
    )
    def router(pathname):
        # Estilos por defecto
        show_dash = {'display': 'block'}
        hide_dash = {'display': 'none'}
        show_page = {'display': 'block'}
        hide_page = {'display': 'none'}

        if not pathname:
            return show_dash, html.Div(), hide_page

        # Limpiar la ruta base para obtener la ruta relativa
        # Ejemplo: /dashboard_alt/prioridad_1/001 -> prioridad_1/001
        prefix = url_base_pathname.rstrip('/')
        clean_path = pathname
        if clean_path.startswith(prefix):
            clean_path = clean_path[len(prefix):].strip('/')
        
        if not clean_path:
            return show_dash, html.Div(), hide_page

        # Lógica de enrutamiento
        if clean_path.startswith('prioridad_'):
            try:
                parts = clean_path.split('/')
                # parts[0] -> "prioridad_1", parts[1] -> "001" (codcas)
                prio_num = parts[0].split('_')[1]
                codcas = parts[1] if len(parts) > 1 else "000"
                
                content = None
                if prio_num == '1': content = ate_topicos_1.layout(codcas=codcas)
                elif prio_num == '2': content = ate_topicos_2.layout(codcas=codcas)
                elif prio_num == '3': content = ate_topicos_3.layout(codcas=codcas)
                elif prio_num == '4': content = ate_topicos_4.layout(codcas=codcas)
                elif prio_num == '5': content = ate_topicos_5.layout(codcas=codcas)
                
                if content:
                    return hide_dash, content, show_page
            except Exception:
                pass # Si falla el parsing, vuelve al dashboard
        
        # Si no coincide con ninguna ruta conocida, mostrar dashboard
        return show_dash, html.Div(), hide_page

    # ========== CALLBACK PRINCIPAL ==========
    @dash_app.callback(
        [Output('summary-container', 'children'),
         Output('charts-container', 'children')],
        Input('search-button', 'n_clicks'),
        State('filter-periodo', 'value'),
        State('filter-anio', 'value'),
        State('filter-tipo-asegurado', 'value'),
        State('url', 'pathname')
    )
    def on_search(n_clicks, periodo, anio, tipo_asegurado, pathname):
        if not n_clicks:
            return html.Div(), html.Div()
        
        import secure_code as sc
        codcas_url = pathname.rstrip('/').split('/')[-1] if pathname else None
        codcas = sc.decode_code(codcas_url)
        if not periodo or not anio or not codcas:
            return html.Div([
                html.I(className="bi bi-exclamation-circle", style={
                    'fontSize': '64px',
                    'color': '#ffc107',
                    'marginBottom': '20px'
                }),
                html.H4("Información requerida", style={
                    'color': TEXT,
                    'fontFamily': FONT_FAMILY,
                    'marginBottom': '10px'
                }),
                html.P("Por favor, seleccione un año y un periodo y asegúrese de tener un centro válido.", style={
                    'color': MUTED,
                    'fontFamily': FONT_FAMILY
                })
            ], style={
                'textAlign': 'center',
                'padding': '60px',
                'backgroundColor': CARD_BG,
                'borderRadius': '16px',
                'boxShadow': '0 10px 30px rgba(0,0,0,0.08)'
            }), html.Div()

        anio_str = str(anio)
        tipo_filter = tipo_asegurado or DEFAULT_TIPO_ASEGURADO
        codasegu_clause = resolve_tipo_asegurado_clause(tipo_filter)

        engine = create_connection()
        if engine is None:
            return html.Div("Error de conexión a la base de datos."), html.Div()

        query = f"""
            SELECT 
                ce.cod_centro,
                ce.anio,
                ce.periodo,
                ce.cod_topico,
                ce.fecha_aten,
                ce.cod_tipo_paciente,
                ce.cod_prioridad,
                ce.cod_diagnostico,
                ce.cod_emergencia,
                ca.cenasides AS cenasides,               -- agregado: nombre del centro
                ce.cod_estandar,
                es.des_estandar AS desc_estandar,         -- aliasado como desc_estandar para coincidir con el código
                t.tipopacinom AS desc_tipo_paciente,
                ce.acto_med
            FROM dwsge.dwe_emergencia_atenciones_homologacion_{anio_str}_{periodo} AS ce
            LEFT JOIN dwsge.sgss_cmcas10 AS ca
                ON ce.cod_oricentro = ca.oricenasicod
                AND ce.cod_centro = ca.cenasicod
            LEFT JOIN dwsge.dim_estandar AS es
                ON ce.cod_estandar = es.id_estandar
            LEFT JOIN dwsge.sgss_cbtpc10 AS t
                ON ce.cod_tipo_paciente = t.tipopacicod
            WHERE ce.cod_centro = '{codcas}'
            and ce.cod_estandar in ('04','05','06','07','08','09','10','11','12','13','14')
            and ce.cod_prioridad <> '0'
            and (
                    CASE 
                        WHEN ce.cod_tipo_paciente = '4' THEN '2'
                        ELSE '1'
                    END
                    ) IN {codasegu_clause}
        """

        query_defunciones= f"""
        SELECT * FROM dwsge.dwe_emergencia_defunciones_homologacion_{anio_str}_{periodo}
        WHERE cod_centro='{codcas}'
        and (
                    CASE 
                        WHEN cod_tipo_paciente = '4' THEN '2'
                        ELSE '1'
                    END
                    ) IN {codasegu_clause}
            """
        df_defunciones = pd.read_sql(query_defunciones, engine)
        defunciones_data = len(df_defunciones)

        df = pd.read_sql(query, engine)
        if not query.strip():
            return html.Div("No se definió la consulta SQL para este dashboard."), html.Div()

        df = pd.read_sql(query, engine)
        if df.empty:
            return html.Div([
                html.I(className="bi bi-inbox", style={
                    'fontSize': '64px',
                    'color': MUTED,
                    'marginBottom': '20px'
                }),
                html.H4("Sin registros", style={
                    'color': TEXT,
                    'fontFamily': FONT_FAMILY,
                    'marginBottom': '10px'
                }),
                html.P("No hay registros de atenciones para el año y periodo seleccionados.", style={
                    'color': MUTED,
                    'fontFamily': FONT_FAMILY
                }),
                html.P(f"Centro: {codcas} | Año: {anio_str} | Periodo: {periodo}", style={
                    'color': MUTED,
                    'fontFamily': FONT_FAMILY,
                    'fontSize': '12px'
                })
            ], style={
                'textAlign': 'center',
                'padding': '60px',
                'backgroundColor': CARD_BG,
                'borderRadius': '16px',
                'boxShadow': '0 10px 30px rgba(0,0,0,0.08)'
            }), html.Div()

        # === NOMBRE DEL CENTRO ===
        nombre_centro = df['cenasides'].dropna().unique()
        nombre_centro = nombre_centro[0] if len(nombre_centro) > 0 else codcas
        detail_query = f"?periodo={periodo}&anio={anio_str}&codasegu={quote_plus(tipo_filter)}"

        # === TARJETAS RESUMEN POR PRIORIDAD ===
        # Query base para obtener datos con cod_prioridad_n
        query_base = f"""
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
                            dwsge.dwe_emergencia_atenciones_homologacion_{anio_str}_{periodo} a
                LEFT OUTER JOIN dwsge.sgss_cmdia10 dg ON dg.diagcod=a.cod_diagnostico
                LEFT OUTER JOIN dwsge.sgss_cbtpc10 tp ON tp.tipopacicod= a.cod_tipo_paciente
                LEFT OUTER JOIN dwsge.sgss_mbtoe10 top ON top.topemecod=a.cod_topico
                LEFT OUTER JOIN dwsge.dim_estandar es ON es.id_estandar = a.cod_estandar
                where (a.cod_diagnostico IS not NULL )
                and a.cod_estandar in ('04','05','06','07','08','09','10','11','12','13','14')
                and (
                        CASE 
                            WHEN a.cod_tipo_paciente = '4' THEN '2'
                            ELSE '1'
                        END
                        ) IN {codasegu_clause}
                ) c	
            ) d
            WHERE
                d.SECUENCIA = '1'
            and cod_centro = '{codcas}'
        """
        
        # Obtener datos para cada prioridad (1-5)
        prioridades_data = {}
        priority_tables = {}
        prioridad_labels = {
            '1': 'Prioridad I',
            '2': 'Prioridad II',
            '3': 'Prioridad III',
            '4': 'Prioridad IV',
            '5': 'Prioridad V'
        }
        
        for prioridad in ['1', '2', '3', '4', '5']:
            query_prioridad = query_base + f" and cod_prioridad_n = '{prioridad}'"
            try:
                df_prioridad = pd.read_sql(query_prioridad, engine)
                topic_col = 'topico_ses' if 'topico_ses' in df_prioridad.columns else 'des_estandar'
                df_prioridad_tabla = (
                    df_prioridad
                    .groupby(df_prioridad[topic_col])
                    .size()
                    .reset_index(name='Atenciones')
                    .sort_values(by='Atenciones', ascending=False)
                )
                df_prioridad_tabla = df_prioridad_tabla.rename(columns={topic_col: 'des_estandar'})
                priority_tables[prioridad] = df_prioridad_tabla
                prioridades_data[prioridad] = len(df_prioridad)
            except Exception as e:
                print(f"Error en query de prioridad {prioridad}: {e}")
                prioridades_data[prioridad] = 0
                priority_tables[prioridad] = pd.DataFrame(columns=['des_estandar', 'Atenciones'])

        query_mayor_24h = f"""
            SELECT des_estancia, COUNT(*) AS total
            FROM dwsge.dwe_emergencia_estancia_homologacion_{anio_str}_{periodo} estancias
            LEFT JOIN dwsge.dim_estancia est ON est.id_estancia = estancias.rango_estancia
            WHERE estancias.cod_centro = '{codcas}'
              AND des_estancia = 'Mayor 24h'
              AND estancia_horas IS NOT NULL
              AND (
                        CASE 
                            WHEN estancias.cod_tipo_paciente = '4' THEN '2'
                            ELSE '1'
                        END
                        ) IN {codasegu_clause}
            GROUP BY des_estancia
        """
        
        query_menor_24h = f"""
            SELECT des_estancia, COUNT(*) AS total
            FROM dwsge.dwe_emergencia_estancia_homologacion_{anio_str}_{periodo} estancias
            LEFT JOIN dwsge.dim_estancia est ON est.id_estancia = estancias.rango_estancia
            WHERE estancias.cod_centro = '{codcas}'
              AND des_estancia = 'Menor 24h'
              AND estancia_horas IS NOT NULL
              AND (
                        CASE 
                            WHEN estancias.cod_tipo_paciente = '4' THEN '2'
                            ELSE '1'
                        END
                        ) IN {codasegu_clause}
            GROUP BY des_estancia
        """

        def obtener_total_estancia(query, etiqueta):
            try:
                df_estancia = pd.read_sql(query, engine)
                if df_estancia.empty or 'total' not in df_estancia.columns:
                    return 0
                return int(df_estancia['total'].sum())
            except Exception as e:
                print(f"Error en query de estancia {etiqueta}: {e}")
                return 0

        mayor_24h_total = obtener_total_estancia(query_mayor_24h, 'mayor_24h')
        menor_24h_total = obtener_total_estancia(query_menor_24h, 'menor_24h')
        
        total_atenciones = sum(prioridades_data.values())
        subtitle = f"Año {anio_str} | Periodo {periodo} | {nombre_centro}"

        ROMAN_PRIORIDADES = {
                        1: "I",
                        2: "II",
                        3: "III",
                        4: "IV",
                        5: "V",
                    }

        cards = []

        for prioridad, label in prioridad_labels.items():
            prioridad_table = priority_tables.get(prioridad)

            roman = ROMAN_PRIORIDADES.get(prioridad, str(prioridad))

            cards.append({
                "title": label,
                "value": f"{prioridades_data.get(prioridad, 0):,.0f}",
                "border_color": PRIORIDAD_COLORS.get(prioridad, BRAND),
                "href": f"{url_base_pathname}prioridad_{prioridad}/{codcas_url}{detail_query}",
                "subtitle": f"Año {anio_str} | Periodo {periodo} | {nombre_centro}",
                "side_component": render_priority_table(
                    prioridad_table
                )           
            })

        cards.extend([
            {
                "title": "Defunciones",
                "value": f"{defunciones_data:,.0f}",
                "border_color": "#6c757d",
                "subtitle": subtitle,
            },
            {
                "title": "Egreso Pac.Sala Obs.<= 24 Horas",
                "value": f"{menor_24h_total:,.0f}",
                "border_color": BRAND_SOFT,
                "subtitle": "Observación corta",
            },
            {
                "title": "Egreso Pac.Sala Obs.> 24 Horas",
                "value": f"{mayor_24h_total:,.0f}",
                "border_color": ACCENT,
                "subtitle": "Observación prolongada",
            },
        ])

        summary_sections = []
        for card in cards:
            card_component = html.Div(
                render_card(
                    title=card["title"],
                    value=card["value"],
                    border_color=card["border_color"],
                    subtitle_text=card.get("subtitle", subtitle),
                    href=card.get("href"),
                    extra_style=card.get("extra_style")
                ),
                style={'width': '100%'}
            )

            if card.get("side_component") and card.get("stacked_side_component"):
                summary_sections.append(
                    dbc.Row(
                        dbc.Col(
                            card_component,
                            width=12,
                            lg=8,
                            style={'display': 'flex'}
                        ),
                        justify="center",
                        style={'marginBottom': '10px'}
                    )
                )
                summary_sections.append(
                    dbc.Row(
                        dbc.Col(
                            html.Div(card["side_component"], style={'width': '100%'}),
                            width=12,
                            lg=8,
                            style={'display': 'flex'}
                        ),
                        justify="center",
                        style={'marginBottom': '20px'}
                    )
                )
            elif card.get("side_component"):
                summary_sections.append(
                    dbc.Row(
                        [
                            dbc.Col(
                                card_component,
                                width=12,
                                lg=4,
                                style={'display': 'flex'}
                            ),
                            dbc.Col(
                                html.Div(card["side_component"], style={'width': '100%'}),
                                width=12,
                                lg=4,
                                style={'display': 'flex'}
                            )
                        ],
                        justify="center",
                        style={'marginBottom': '10px'}
                    )
                )
            else:
                summary_sections.append(
                    dbc.Row(
                        dbc.Col(
                            card_component,
                            width=12,
                            lg=8,
                            style={'display': 'flex'}
                        ),
                        justify="center",
                        style={'marginBottom': '10px'}
                    )
                )

        summary_row = dbc.Container(summary_sections, fluid=True)

        return summary_row, html.Div()
       # ========== CALLBACK DESCARGA CSV ==========
    @dash_app.callback(
        Output("download-dataframe-csv", "data"),
        Input("download-button", "n_clicks"),
        State('filter-periodo', 'value'),
        State('filter-anio', 'value'),
        State('filter-tipo-asegurado', 'value'),
        State('url', 'pathname'),
        prevent_initial_call=True
    )
    def download_csv(n_clicks, periodo, anio, tipo_asegurado, pathname):
        if not n_clicks or not periodo or not anio or not pathname:
            return None

        import secure_code as sc
        codcas_encoded = pathname.rstrip('/').split('/')[-1] if pathname else None
        codcas = sc.decode_code(codcas_encoded) if codcas_encoded else None
        if not codcas:
            return None

        anio_str = str(anio)

        tipo_filter = tipo_asegurado or DEFAULT_TIPO_ASEGURADO
        codasegu_clause = resolve_tipo_asegurado_clause(tipo_filter)

        engine = create_connection()
        if engine is None:
            return None

        query =  f"""
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
                            dwsge.dwe_emergencia_atenciones_homologacion_{anio_str}_{periodo} a
                LEFT OUTER JOIN dwsge.sgss_cmdia10 dg ON dg.diagcod=a.cod_diagnostico
                LEFT OUTER JOIN dwsge.sgss_cbtpc10 tp ON tp.tipopacicod= a.cod_tipo_paciente
                LEFT OUTER JOIN dwsge.sgss_mbtoe10 top ON top.topemecod=a.cod_topico
                LEFT OUTER JOIN dwsge.dim_estandar es ON es.id_estandar = a.cod_estandar
                where (a.cod_diagnostico IS not NULL )
                and a.cod_estandar in ('04','05','06','07','08','09','10','11','12','13','14')
                and (
                        CASE 
                            WHEN a.cod_tipo_paciente = '4' THEN '2'
                            ELSE '1'
                        END
                        ) IN {codasegu_clause}
                ) c	
            ) d

            WHERE
                d.SECUENCIA = '1'
            and cod_centro = '{codcas}'
            and cod_prioridad_n != '0'
        """
        df = pd.read_sql(query, engine)
        if df.empty:
            return None
        df = df.astype(str)
        filename = f"atenciones_por_prioridad_{codcas}_{anio_str}_{periodo}.csv"
        return dcc.send_data_frame(df.to_csv, filename, index=False)

    dash_app.layout = serve_layout
    return dash_app
  
