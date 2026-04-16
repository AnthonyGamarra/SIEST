from dash import Dash, html, dcc, Input, Output, State
from flask import has_request_context
from flask_login import current_user
from sqlalchemy import create_engine,text
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
from Indicadores import ate_cq_1
from Indicadores import ate_cq_2
from Indicadores import ate_cq_3
from Indicadores import ate_cq_4
from Indicadores import ate_cq_5
from Indicadores import ate_cq_6


def create_dash_app(flask_app, url_base_pathname='/dashboard_cq/'):
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
        'A': '#dc3545',
        'B': '#fd7e14',
        'C': '#ffc107',
        'D': '#28a745',
        'E': '#17a2b8',
        'SIN_CODIGO': '#6c757d',
        'EMERGENCIA': '#0d6efd',
        'HORAS_ELECTIVAS': '#198754',
        'HORAS_EMERGENCIA': '#0dcaf0'
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
    ate_cq_1.register_callbacks(dash_app)
    ate_cq_2.register_callbacks(dash_app)
    ate_cq_3.register_callbacks(dash_app)
    ate_cq_4.register_callbacks(dash_app)
    ate_cq_5.register_callbacks(dash_app)
    ate_cq_6.register_callbacks(dash_app)

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
    
    def fecha_act(engine):
        if engine is None:
            return None

        try:
            with engine.connect() as connection:
                row = connection.execute(
                    text("SELECT TO_CHAR(MIN(fecha_act), 'DD/MM/YYYY HH24:MI:SS') AS fecha_act FROM dwsge.fecha_act;"),
                ).mappings().first()
        except Exception as exc:
            print(f"Failed to fetch fecha_act: {exc}")
            return None

        # SQLAlchemy lowercases column aliases by default, so prefer the lowercase key
        fecha_col_value = row.get('fecha_act') or row.get('fecha_Act')
        if not row or not fecha_col_value:
            return None

        return fecha_col_value
    
    def render_priority_table(dataframe):
        table_title = html.H6(
            "Área",
            className="mb-2",
            style={
                'fontFamily': FONT_FAMILY,
                'fontSize': '12px',
                'fontWeight': '700',
                'color': BRAND,
                'margin': '0 0 6px 0'
            }
        )

        if dataframe is None or dataframe.empty:
            body_children = [
                table_title,
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
                table_title,
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
            engine = create_connection()
            fecha_act_value = fecha_act(engine)
            if not fecha_act_value:
                fecha_act_value = "Sin informacion disponible"
            return dbc.Container([
                dcc.Location(id='url-cq', refresh=False),

                html.Div([
                # ENCABEZADO
                html.Div([
                    html.Div([
                        # html.Img(
                        #     src=dash_app.get_asset_url('logo.png'),
                        #     style={
                        #         'width': '120px',
                        #         'height': '60px',
                        #         'objectFit': 'contain',
                        #         'marginRight': '20px'
                        #     }
                        # ),
                        html.Div([
                            html.Div([
                                html.I(className="bi bi-hospital", style={
                                    'fontSize': '32px',
                                    'color': BRAND,
                                    'marginRight': '12px'
                                }),
                                html.H2(
                                    [
                                        "Centro Quirúrgico - Intervenciones Quirúrgicas por grado de complejidad",
                                        html.Span(
                                            " (En proceso de validación)",
                                            style={
                                                'color': '#dc3545',
                                                'fontWeight': '700'
                                            }
                                        )
                                    ],
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
                                f"📅 Información actualizada al {fecha_act_value} | Sistema de Gestión Estadístico",
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
                        id='filter-anio-cq',
                        options=anio_options,
                        placeholder='Año',
                        clearable=True,
                        style={
                            'width': '160px',
                            'fontFamily': FONT_FAMILY,
                            'position': 'relative',
                            'zIndex': 4000
                        }
                    ),
                    dcc.Dropdown(
                        id='filter-periodo-cq',
                        options=[{'label': row['mes'], 'value': row['periodo']} for _, row in df_period.iterrows()],
                        placeholder='Periodo',
                        clearable=True,
                        style={
                            'width': '240px',
                            'fontFamily': FONT_FAMILY
                        }
                    ),
                    dcc.Dropdown(
                        id='filter-tipo-asegurado-cq',
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
                        id='search-button-cq',
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
                        id='download-button-cq',
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
                    dcc.Download(id="download-dataframe-csv-cq"),
                    dbc.Button(
                        [html.I(className="bi bi-arrow-left me-1"), "Volver"],
                        id="btn-volver-eme-cq",
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
                dbc.Tooltip("Volver a la página anterior", target='btn-volver-eme-cq', placement='bottom'),

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
                                children=html.Div(id='summary-container-cq')
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
                                children=html.Div(id='charts-container-cq')
                            ),
                            className='dashboard-loading-shell'
                        ),
                        width=12
                    )
                ]),
                ], id='main-eme-content-cq'),

                # Contenedor para páginas de detalle
                html.Div(id='page-eme-container-cq', style={'display': 'none'})

            ], fluid=True, style={
                'backgroundImage': "url('/static/76824.jpg')",
                'backgroundSize': 'cover',
                'backgroundPosition': 'center center',
                'backgroundRepeat': 'no-repeat',
                'backgroundAttachment': 'fixed',
                'minHeight': '100%',
                'paddingTop': '20px',
                'paddingBottom': '20px'
            })

        return html.Div([
            html.H3('No autenticado'),
            html.P('Debes iniciar sesión para ver el dashboard.'),
            dbc.Button(
                'Volver',
                id='unauth-back-button-eme-cq',
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
                        pool_size=5,
                        max_overflow=5,
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
        Output('main-eme-content-cq', 'style'),
        Output('page-eme-container-cq', 'children'),
        Output('page-eme-container-cq', 'style'),
        Input('url-cq', 'pathname')
    )
    def router(pathname):
        # Estilos por defecto
        show_dash = {'display': 'block'}
        hide_dash = {'display': 'none'}
        show_page = {'display': 'block'}
        hide_page = {'display': 'none'}

        if not pathname:
            return show_dash, html.Div(), hide_page

        # Limpiar la ruta para obtener la ruta relativa
        # Ejemplo: /dashboard_cq/complejidad_A/001 -> complejidad_A/001
        clean_path = pathname.strip('/')
        if clean_path.startswith('dashboard_cq_embed/'):
            clean_path = clean_path[len('dashboard_cq_embed/'):].strip('/')
        elif clean_path.startswith('dashboard_cq/'):
            clean_path = clean_path[len('dashboard_cq/'):].strip('/')
        
        if not clean_path:
            return show_dash, html.Div(), hide_page

        # Lógica de enrutamiento
        if clean_path.startswith('complejidad_'):
            try:
                parts = clean_path.split('/')
                ruta_comp = parts[0]
                codcas_enc = parts[1] if len(parts) > 1 else None

                route_map = {
                    'complejidad_A': ate_cq_1,
                    'complejidad_B': ate_cq_2,
                    'complejidad_C': ate_cq_3,
                    'complejidad_D': ate_cq_4,
                    'complejidad_E': ate_cq_5,
                    'complejidad_SC': ate_cq_6,
                }

                module = route_map.get(ruta_comp)
                if module:
                    content = module.layout(codcas=codcas_enc)
                    return hide_dash, content, show_page
            except Exception:
                pass  # Si falla el parsing, vuelve al dashboard
        
        # Si no coincide con ninguna ruta conocida, mostrar dashboard
        return show_dash, html.Div(), hide_page

    # ========== CALLBACK PRINCIPAL ==========
    @dash_app.callback(
        [Output('summary-container-cq', 'children'),
         Output('charts-container-cq', 'children')],
        Input('search-button-cq', 'n_clicks'),
        State('filter-periodo-cq', 'value'),
        State('filter-anio-cq', 'value'),
        State('filter-tipo-asegurado-cq', 'value'),
        State('url-cq', 'pathname')
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
            SELECT DISTINCT ON (cq.acto_med, cq.num_solicitud)
                cq.cod_oricentro,
                cq.cod_centro,
                ca.cenasides AS cenasides,
                cq.periodo,
                cq.anio,
                cq.cod_area,
                h.arehosdes AS area,
                cq.cod_servicio,
                c.servhosdes AS servicio,
                cq.cod_cpms,
                cp.cpsdes AS cpms,
                cq.cod_tipdoc_paciente,
                cq.doc_paciente,
                cq.anio_edad,
                cq.meses,
                cq.sexo,
                cq.cod_sala,
                cq.acto_med,
                cq.cod_complejidad,
                cq.cod_anest,
                cq.cod_tipo_programacion,
                cq.num_solicitud,
                cq.cod_quirof,
                ---q.salopedes,
                cq.fec_oper
            FROM dssge.dwe_centro_quirurgico_{anio_str}_{periodo} cq
            LEFT JOIN dwsge.sgss_cmsho10 AS c 
                ON cq.cod_servicio = c.servhoscod
            LEFT JOIN dwsge.sgss_cmcas10 AS ca 
                ON cq.cod_oricentro = ca.oricenasicod 
            AND cq.cod_centro = ca.cenasicod
            ---LEFT JOIN dwsge.sgss_qmcqs10 AS q 
            ---    ON q.cenasicod = cq.cod_centro 
            ---AND q.salopecod = cq.cod_sala_operacion 
            ---AND cq.cod_quirof = q.cenquicod
            LEFT JOIN dwsge.sgss_cmcpp10 as cp 
                ON cp.cpscod = cq.cod_cpms
            LEFT JOIN dwsge.sgss_cmaho10 as h
                ON h.arehoscod = cq.cod_area
            WHERE cq.cod_centro = '{codcas}'
                        AND (
                                CASE
                                    WHEN cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                            ) IN {codasegu_clause}
            ORDER BY cq.acto_med, cq.num_solicitud, cq.fec_oper DESC;
        """

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
            SELECT DISTINCT ON (cq.acto_med, cq.cod_cpms)
                cq.cod_oricentro,
                cq.cod_centro,
                ca.cenasides AS cenasides,
                cq.periodo,
                cq.anio,
                cq.cod_area,
                h.arehosdes AS area,
                cq.cod_servicio,
                c.servhosdes AS servicio,
                cq.cod_cpms,
                cp.cpsdes AS cpms,
                cq.cod_tipdoc_paciente,
                cq.doc_paciente,
                cq.anio_edad,
                cq.meses,
                cq.sexo,
                cq.cod_sala,
                cq.acto_med,
                cq.cod_complejidad,
                cq.cod_anest,
                cq.cod_tipo_programacion,
                b.conopedes as des_tipo_programacion,
                cq.num_solicitud,
                cq.cod_quirof,
                cq.fec_oper
            FROM dssge.dwe_centro_quirurgico_{anio_str}_{periodo} cq
            LEFT JOIN dwsge.sgss_cmsho10 AS c 
                ON cq.cod_servicio = c.servhoscod
            LEFT JOIN dwsge.sgss_cmcas10 AS ca 
                ON cq.cod_oricentro = ca.oricenasicod 
            AND cq.cod_centro = ca.cenasicod
            ---LEFT JOIN dwsge.sgss_qmcqs10 AS q 
            ---    ON q.cenasicod = cq.cod_centro 
            ---AND q.salopecod = cq.cod_sala_operacion 
            ---AND cq.cod_quirof = q.cenquicod
            LEFT JOIN dwsge.sgss_cmcpp10 as cp 
                ON cp.cpscod = cq.cod_cpms
            LEFT JOIN dwsge.sgss_cmaho10 as h
                ON h.arehoscod = cq.cod_area
            LEFT JOIN dwsge.sgss_qbcep10 as b ON b.conopecod = cq.cod_tipo_programacion
            WHERE cq.cod_centro = '{codcas}'
                        AND (
                                CASE
                                    WHEN cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                            ) IN {codasegu_clause}
            ORDER BY cq.acto_med, cq.cod_cpms, cq.fec_oper DESC;
        """
        query_de_emergencia = f"""
            SELECT DISTINCT ON (cq.acto_med, cq.cod_cpms)
                cq.cod_oricentro,
                cq.cod_centro,
                ca.cenasides AS cenasides,
                cq.periodo,
                cq.anio,
                cq.cod_area,
                h.arehosdes AS area,
                cq.cod_servicio,
                c.servhosdes AS servicio,
                cq.cod_cpms,
                cp.cpsdes AS cpms,
                cq.cod_tipdoc_paciente,
                cq.doc_paciente,
                cq.anio_edad,
                cq.meses,
                cq.sexo,
                cq.cod_sala,
                cq.acto_med,
                cq.cod_complejidad,
                cq.cod_anest,
                cq.cod_tipo_programacion,
                b.conopedes as des_tipo_programacion,
                cq.num_solicitud,
                cq.cod_quirof,
                ---q.salopedes,
                cq.fec_oper
            FROM dssge.dwe_centro_quirurgico_{anio_str}_{periodo} cq
            LEFT JOIN dwsge.sgss_cmsho10 AS c 
                ON cq.cod_servicio = c.servhoscod
            LEFT JOIN dwsge.sgss_cmcas10 AS ca 
                ON cq.cod_oricentro = ca.oricenasicod 
            AND cq.cod_centro = ca.cenasicod
            ---LEFT JOIN dwsge.sgss_qmcqs10 AS q 
            ---    ON q.cenasicod = cq.cod_centro 
            ---AND q.salopecod = cq.cod_sala_operacion 
            ---AND cq.cod_quirof = q.cenquicod
            LEFT JOIN dwsge.sgss_cmcpp10 as cp 
                ON cp.cpscod = cq.cod_cpms
            LEFT JOIN dwsge.sgss_cmaho10 as h
                ON h.arehoscod = cq.cod_area
            LEFT JOIN dwsge.sgss_qbcep10 as b ON b.conopecod = cq.cod_tipo_programacion
            WHERE cq.cod_centro = '{codcas}'
                        AND (
                                CASE
                                    WHEN cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                            ) IN {codasegu_clause}
            AND cq.cod_tipo_programacion = '2'
            ORDER BY cq.acto_med, cq.cod_cpms, cq.fec_oper DESC;
        """

        query_horas_quirurgicas_electivas = f"""
                SELECT 
                    SUM(
                        SPLIT_PART(t.duracion_sala, ':', 1)::numeric
                        + SPLIT_PART(t.duracion_sala, ':', 2)::numeric / 60
                    ) AS horas_quirurgicas_realizadas_iq_electivas
                FROM (
                    SELECT DISTINCT ON (cq.acto_med, cq.cod_cpms)
                        cq.cod_oricentro,
                        cq.cod_centro,
                        ca.cenasides AS cenasides,
                        cq.periodo,
                        cq.anio,
                        cq.cod_area,
                        h.arehosdes AS area,
                        cq.cod_servicio,
                        c.servhosdes AS servicio,
                        cq.cod_cpms,
                        cp.cpsdes AS cpms,
                        cq.cod_tipdoc_paciente,
                        cq.doc_paciente,
                        cq.anio_edad,
                        cq.meses,
                        cq.sexo,
                        cq.cod_sala,
                        cq.acto_med,
                        cq.cod_complejidad,
                        cq.cod_anest,
                        cq.cod_tipo_programacion,
                        b.conopedes AS des_tipo_programacion,
                        cq.num_solicitud,
                        cq.cod_quirof,
                        ---q.salopedes,
                        cq.fec_oper,
                        cq.duracion_sala
                    FROM dssge.dwe_centro_quirurgico_{anio_str}_{periodo} cq
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON cq.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca 
                        ON cq.cod_oricentro = ca.oricenasicod 
                    AND cq.cod_centro = ca.cenasicod
                    ---LEFT JOIN dwsge.sgss_qmcqs10 AS q 
                    ---    ON q.cenasicod = cq.cod_centro 
                    ---AND q.salopecod = cq.cod_sala_operacion 
                    ---AND cq.cod_quirof = q.cenquicod
                    LEFT JOIN dwsge.sgss_cmcpp10 AS cp 
                        ON cp.cpscod = cq.cod_cpms
                    LEFT JOIN dwsge.sgss_cmaho10 AS h 
                        ON h.arehoscod = cq.cod_area
                    LEFT JOIN dwsge.sgss_qbcep10 AS b 
                        ON b.conopecod = cq.cod_tipo_programacion
                    WHERE cq.cod_centro = '{codcas}'
                    AND (CASE WHEN cq.cod_tipo_paciente = '4' THEN '2' ELSE '1' END) IN {codasegu_clause}
                    AND cq.cod_tipo_programacion = '1'
                    ORDER BY cq.acto_med, cq.cod_cpms, cq.fec_oper DESC
                ) t;
        """

        query_horas_quirurgicas_emergencia = f"""
                    SELECT 
                        SUM(
                            SPLIT_PART(t.duracion_sala, ':', 1)::numeric
                            + SPLIT_PART(t.duracion_sala, ':', 2)::numeric / 60
                        ) AS horas_quirurgicas_realizadas_iq_emergencia
                    FROM (
                        SELECT DISTINCT ON (cq.acto_med, cq.cod_cpms)
                            cq.cod_oricentro,
                            cq.cod_centro,
                            ca.cenasides AS cenasides,
                            cq.periodo,
                            cq.anio,
                            cq.cod_area,
                            h.arehosdes AS area,
                            cq.cod_servicio,
                            c.servhosdes AS servicio,
                            cq.cod_cpms,
                            cp.cpsdes AS cpms,
                            cq.cod_tipdoc_paciente,
                            cq.doc_paciente,
                            cq.anio_edad,
                            cq.meses,
                            cq.sexo,
                            cq.cod_sala,
                            cq.acto_med,
                            cq.cod_complejidad,
                            cq.cod_anest,
                            cq.cod_tipo_programacion,
                            b.conopedes AS des_tipo_programacion,
                            cq.num_solicitud,
                            cq.cod_quirof,
                            ---q.salopedes,
                            cq.fec_oper,
                            cq.duracion_sala
                        FROM dssge.dwe_centro_quirurgico_{anio_str}_{periodo} cq
                        LEFT JOIN dwsge.sgss_cmsho10 AS c 
                            ON cq.cod_servicio = c.servhoscod
                        LEFT JOIN dwsge.sgss_cmcas10 AS ca 
                            ON cq.cod_oricentro = ca.oricenasicod 
                        AND cq.cod_centro = ca.cenasicod
                        ---LEFT JOIN dwsge.sgss_qmcqs10 AS q 
                        ---    ON q.cenasicod = cq.cod_centro 
                        ---AND q.salopecod = cq.cod_sala_operacion 
                        ---AND cq.cod_quirof = q.cenquicod
                        LEFT JOIN dwsge.sgss_cmcpp10 AS cp 
                            ON cp.cpscod = cq.cod_cpms
                        LEFT JOIN dwsge.sgss_cmaho10 AS h 
                            ON h.arehoscod = cq.cod_area
                        LEFT JOIN dwsge.sgss_qbcep10 AS b 
                            ON b.conopecod = cq.cod_tipo_programacion
                        WHERE cq.cod_centro = '{codcas}'
                        AND (CASE WHEN cq.cod_tipo_paciente = '4' THEN '2' ELSE '1' END) IN {codasegu_clause}
                        AND cq.cod_tipo_programacion = '2'
                        ORDER BY cq.acto_med, cq.cod_cpms, cq.fec_oper DESC
                    ) t;
        """
        # Ejecutar consultas
        df_base = pd.read_sql(query_base, engine)
        df_emergencia = pd.read_sql(query_de_emergencia, engine)
        df_horas_electivas = pd.read_sql(query_horas_quirurgicas_electivas, engine)
        df_horas_emergencia = pd.read_sql(query_horas_quirurgicas_emergencia, engine)


        # === Procesar por prioridad en Pandas ===

        prioridades_data = {}
        priority_tables = {}

        prioridad_labels = {
            'A': 'Complejidad A',
            'B': 'Complejidad B',
            'C': 'Complejidad C',
            'D': 'Complejidad D',
            'E': 'Complejidad E',
            'SIN_CODIGO': 'Sin código'
        }

        complejidad_series = df_base['cod_complejidad'].fillna('').astype(str).str.strip()

        for complejidad in ['A', 'B', 'C', 'D', 'E', 'SIN_CODIGO']:

            # Filtrar en memoria (no en SQL)
            if complejidad == 'SIN_CODIGO':
                df_complejidad = df_base[complejidad_series == '']
            else:
                df_complejidad = df_base[complejidad_series == complejidad]

            if df_complejidad.empty:
                prioridades_data[complejidad] = 0
                priority_tables[complejidad] = pd.DataFrame(
                    columns=['cod_complejidad', 'Atenciones']
                )
                continue

            df_prioridad_tabla = (
                df_complejidad
                .groupby('area')
                .size()
                .reset_index(name='Atenciones')
                .sort_values(by='Atenciones', ascending=False)
            )

            df_prioridad_tabla = df_prioridad_tabla.rename(
                columns={'area': 'des_estandar'}
            )

            priority_tables[complejidad] = df_prioridad_tabla
            prioridades_data[complejidad] = len(df_complejidad)

        if df_emergencia.empty:
            emergencia_table = pd.DataFrame(columns=['des_estandar', 'Atenciones'])
            total_emergencia = 0
        else:
            emergencia_table = (
                df_emergencia
                .groupby('area')
                .size()
                .reset_index(name='Atenciones')
                .sort_values(by='Atenciones', ascending=False)
                .rename(columns={'area': 'des_estandar'})
            )
            total_emergencia = len(df_emergencia)

        horas_electivas = 0.0
        if not df_horas_electivas.empty:
            horas_electivas = df_horas_electivas.iloc[0].get('horas_quirurgicas_realizadas_iq_electivas')
            horas_electivas = float(horas_electivas) if pd.notna(horas_electivas) else 0.0

        horas_emergencia = 0.0
        if not df_horas_emergencia.empty:
            horas_emergencia = df_horas_emergencia.iloc[0].get('horas_quirurgicas_realizadas_iq_emergencia')
            horas_emergencia = float(horas_emergencia) if pd.notna(horas_emergencia) else 0.0


        
        subtitle = f"Año {anio_str} | Periodo {periodo} | {nombre_centro}"

        cards = []

        PRIORIDAD_ROUTE = {
            'A': 'complejidad_A',
            'B': 'complejidad_B',
            'C': 'complejidad_C',
            'D': 'complejidad_D',
            'E': 'complejidad_E',
            'SIN_CODIGO': 'complejidad_SC',
        }

        for prioridad, label in prioridad_labels.items():
            prioridad_table = priority_tables.get(prioridad)
            ruta = PRIORIDAD_ROUTE.get(prioridad)
            href = f"/dashboard_cq/{ruta}/{codcas_url}{detail_query}" if ruta else None

            cards.append({
                "title": label,
                "value": f"{prioridades_data.get(prioridad, 0):,.0f}",
                "border_color": PRIORIDAD_COLORS.get(prioridad, BRAND),
                "href": href,
                "subtitle": f"Año {anio_str} | Periodo {periodo} | {nombre_centro}",
                "side_component": render_priority_table(prioridad_table),
            })

        cards.append({
            "title": "Intervenciones Quirúrgicas Ejecutadas Emergencia",
            "value": f"{total_emergencia:,.0f}",
            "border_color": PRIORIDAD_COLORS.get('EMERGENCIA', BRAND),
            "href": None,
            "subtitle": f"Año {anio_str} | Periodo {periodo} | {nombre_centro}",
            "side_component": render_priority_table(emergencia_table)
        })

        cards.append({
            "title": "Horas quirúrgicas realizadas IQ electivas",
            "value": f"{horas_electivas:,.2f}",
            "border_color": PRIORIDAD_COLORS.get('HORAS_ELECTIVAS', BRAND),
            "href": None,
            "subtitle": f"Año {anio_str} | Periodo {periodo} | {nombre_centro}",
            "side_component": None
        })

        cards.append({
            "title": "Horas quirúrgicas realizadas IQ emergencia",
            "value": f"{horas_emergencia:,.2f}",
            "border_color": PRIORIDAD_COLORS.get('HORAS_EMERGENCIA', BRAND),
            "href": None,
            "subtitle": f"Año {anio_str} | Periodo {periodo} | {nombre_centro}",
            "side_component": None
        })

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
        Output("download-dataframe-csv-cq", "data"),
        Input("download-button-cq", "n_clicks"),
        State('filter-periodo-cq', 'value'),
        State('filter-anio-cq', 'value'),
        State('filter-tipo-asegurado-cq', 'value'),
        State('url-cq', 'pathname'),
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
            SELECT DISTINCT ON (cq.acto_med, cq.num_solicitud)
                cq.cod_oricentro,
                cq.cod_centro,
                ca.cenasides AS cenasides,
                cq.periodo,
                cq.anio,
                cq.cod_area,
                h.arehosdes AS area,
                cq.cod_servicio,
                c.servhosdes AS servicio,
                cq.cod_cpms,
                cp.cpsdes AS cpms,
                cq.cod_tipdoc_paciente,
                cq.doc_paciente,
                cq.anio_edad,
                cq.meses,
                cq.sexo,
                cq.cod_sala,
                cq.acto_med,
                cq.cod_complejidad,
                cq.cod_anest,
                cq.cod_tipo_programacion,
                b.conopedes as des_tipo_programacion,
                cq.num_solicitud,
                cq.cod_quirof,
                q.salopedes,
                cq.fec_oper
            FROM dssge.dwe_centro_quirurgico_{anio_str}_{periodo} cq
            LEFT JOIN dwsge.sgss_cmsho10 AS c 
                ON cq.cod_servicio = c.servhoscod
            LEFT JOIN dwsge.sgss_cmcas10 AS ca 
                ON cq.cod_oricentro = ca.oricenasicod 
            AND cq.cod_centro = ca.cenasicod
            LEFT JOIN dwsge.sgss_qmcqs10 AS q 
                ON q.cenasicod = cq.cod_centro 
            AND q.salopecod = cq.cod_sala_operacion 
            AND cq.cod_quirof = q.cenquicod
            LEFT JOIN dwsge.sgss_cmcpp10 as cp 
                ON cp.cpscod = cq.cod_cpms
            LEFT JOIN dwsge.sgss_cmaho10 as h
                ON h.arehoscod = cq.cod_area
            LEFT JOIN dwsge.sgss_qbcep10 as b ON b.conopecod = cq.cod_tipo_programacion
            WHERE cq.cod_centro = '{codcas}'
                        AND (
                                CASE
                                    WHEN cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                            ) IN {codasegu_clause}
            ORDER BY cq.acto_med, cq.num_solicitud, cq.fec_oper DESC;
        """
        df = pd.read_sql(query, engine)
        if df.empty:
            return None
        df = df.astype(str)
        filename = f"atenciones_por_complejidad_{codcas}_{anio_str}_{periodo}.csv"
        return dcc.send_data_frame(df.to_csv, filename, index=False)

    dash_app.layout = serve_layout
    return dash_app
  
