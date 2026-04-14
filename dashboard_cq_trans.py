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


def create_dash_app(flask_app, url_base_pathname='/dashboard_cq_trans/'):
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
        'E': '#17a2b8'
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
            "Código de sala",
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
                dcc.Location(id='url-cq-trans', refresh=False),

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
                                    [
                                        "Centro Quirúrgico - Transplantes",
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
                        id='filter-anio-cq-trans',
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
                        id='filter-periodo-cq-trans',
                        options=[{'label': row['mes'], 'value': row['periodo']} for _, row in df_period.iterrows()],
                        placeholder='Periodo',
                        clearable=True,
                        style={
                            'width': '240px',
                            'fontFamily': FONT_FAMILY
                        }
                    ),
                    dcc.Dropdown(
                        id='filter-tipo-asegurado-cq-trans',
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
                        id='search-button-cq-trans',
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
                        id='download-button-cq-trans',
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
                    dcc.Download(id="download-dataframe-csv-cq-trans"),
                    dbc.Button(
                        [html.I(className="bi bi-arrow-left me-1"), "Volver"],
                        id="btn-volver-eme-cq-trans",
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
                dbc.Tooltip("Volver a la página anterior", target='btn-volver-eme-cq-trans', placement='bottom'),

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
                                children=html.Div(id='summary-container-cq-trans')
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
                                children=html.Div(id='charts-container-cq-trans')
                            ),
                            className='dashboard-loading-shell'
                        ),
                        width=12
                    )
                ]),
                ], id='main-eme-content-cq-trans'),

                # Contenedor para páginas de detalle
                html.Div(id='page-eme-container-cq-trans', style={'display': 'none'})

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
                id='unauth-back-button-eme-cq-trans',
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
                        pool_size=20,
                        max_overflow=10,
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
        Output('main-eme-content-cq-trans', 'style'),
        Output('page-eme-container-cq-trans', 'children'),
        Output('page-eme-container-cq-trans', 'style'),
        Input('url-cq-trans', 'pathname')
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
        # Ejemplo: /dashboard_cq/complejidad_A/001 -> complejidad_A/001
        prefix = url_base_pathname.rstrip('/')
        clean_path = pathname
        if clean_path.startswith(prefix):
            clean_path = clean_path[len(prefix):].strip('/')
        
        if not clean_path:
            return show_dash, html.Div(), hide_page

        # Lógica de enrutamiento
        if clean_path.startswith('complejidad_'):
            try:
                parts = clean_path.split('/')
                # parts[0] -> "complejidad_A", parts[1] -> "001" (codcas)
                complejidad_num = parts[0].split('_')[1]
                codcas = parts[1] if len(parts) > 1 else "000"
                
                content = None
                if complejidad_num == 'A': content = ate_cq_1.layout(codcas=codcas)
                elif complejidad_num == 'B': content = ate_cq_2.layout(codcas=codcas)
                elif complejidad_num == 'C': content = ate_cq_3.layout(codcas=codcas)
                elif complejidad_num == 'D': content = ate_cq_4.layout(codcas=codcas)
                elif complejidad_num == 'E': content = ate_cq_5.layout(codcas=codcas)
                
                if content:
                    return hide_dash, content, show_page
            except Exception:
                pass # Si falla el parsing, vuelve al dashboard
        
        # Si no coincide con ninguna ruta conocida, mostrar dashboard
        return show_dash, html.Div(), hide_page

    # ========== CALLBACK PRINCIPAL ==========
    @dash_app.callback(
        [Output('summary-container-cq-trans', 'children'),
         Output('charts-container-cq-trans', 'children')],
        Input('search-button-cq-trans', 'n_clicks'),
        State('filter-periodo-cq-trans', 'value'),
        State('filter-anio-cq-trans', 'value'),
        State('filter-tipo-asegurado-cq-trans', 'value'),
        State('url-cq-trans', 'pathname')
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
            SELECT cod_oricentro,
                cod_centro,
                ca.cenasides AS cenasides,
                periodo,
                anio,
                cod_area,
                cod_servicio,
                c.servhosdes AS servicio,
                cod_cpms,
                cp.cpsdes AS cpms,
                cod_tip_cirujano,
                cod_tipdoc_medico,
                dni_medico,
                fec_oper,
                autogenerado,
                cmame_pacsecnum,
                cod_tipdoc_paciente,
                doc_paciente,
                anio_edad,
                meses,
                sexo,
                cod_tip_seguro,
                cod_tipo_parentesco,
                cod_tipo_paciente,
                cod_sala,
                hor_ini_sala,
                hor_fin_sala,
                duracion_sala,
                hor_ini_anest,
                hor_fin_anest,
                duracion_anest,
                hor_ini_operac,
                hor_fin_operac,
                duracion_operac,
                acto_med,
                cod_complejidad,
                cod_anest,
                cod_tipo_programacion,
                num_solicitud,
                cod_quirof,
                fecsolicsalaoperac,
                fecsolicitadaoperac,
                fecprogram,
                cas_adscripcion,
                h_c,
                salopedes,
                cod_destegreso,
                fechcreasolicitud,
                horcreasolic,
                fecaptitud
            FROM dssge.dwe_centro_quirurgico_{anio_str}_{periodo} cq
                LEFT JOIN dwsge.sgss_cmsho10 AS c ON cq.cod_servicio = c.servhoscod
                LEFT JOIN dwsge.sgss_cmcas10 AS ca ON cq.cod_oricentro = ca.oricenasicod AND cq.cod_centro = ca.cenasicod
                LEFT JOIN dwsge.sgss_qmcqs10 AS q ON q.cenasicod = cq.cod_centro AND q.salopecod= cq.cod_sala_operacion AND cq.COD_QUIROF = q.cenquicod
                LEFT JOIN dwsge.sgss_cmcpp10 as cp ON cp.cpscod = cq.cod_cpms
            WHERE cod_centro='{codcas}'
              AND cod_cpms IN (
                '38241',
                '38240',
                '48551',
                '48552',
                '33945',
                '33935',
                '65730',
                '65710',
                '65750',
                '65755',
                '65712',
                '65714',
                '65732',
                '65752',
                '65756',
                '65757',
                '50250',
                '47135',
                '47163',
                '32851',
                '32852',
                '32854',
                '50360',
                '50365',
                '50380'
                )
              AND (
                    CASE
                        WHEN cod_tipo_paciente = '4' THEN '2'
                        ELSE '1'
                    END
                  ) IN {codasegu_clause}
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
SELECT DISTINCT ON (cq.acto_med, cq.num_solicitud)
    cq.cod_oricentro,
    cq.cod_centro,
    ca.cenasides AS cenasides,
    cq.periodo,
    cq.anio,
    cq.cod_area,
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
WHERE cq.cod_centro = '{codcas}'
              AND cod_cpms IN (
                '38241',
                '38240',
                '48551',
                '48552',
                '33945',
                '33935',
                '65730',
                '65710',
                '65750',
                '65755',
                '65712',
                '65714',
                '65732',
                '65752',
                '65756',
                '65757',
                '50250',
                '47135',
                '47163',
                '32851',
                '32852',
                '32854',
                '50360',
                '50365',
                '50380'
                )
              AND (
                    CASE
                        WHEN cod_tipo_paciente = '4' THEN '2'
                        ELSE '1'
                    END
                  ) IN {codasegu_clause}
ORDER BY cq.acto_med, cq.num_solicitud, cq.fec_oper DESC;
        """

        # Ejecutar SOLO UNA VEZ
        df_base = pd.read_sql(query_base, engine)


        # === Procesar por prioridad en Pandas ===

        prioridades_data = {}
        priority_tables = {}

        prioridad_labels = {
            'A': 'Complejidad A',
        }

        for complejidad in ['A']:

            # Filtrar en memoria (no en SQL)
            df_complejidad = df_base[df_base['cod_complejidad'] == complejidad]

            if df_complejidad.empty:
                prioridades_data[complejidad] = 0
                priority_tables[complejidad] = pd.DataFrame(
                    columns=['cod_complejidad', 'Atenciones']
                )
                continue

            df_prioridad_tabla = (
                df_complejidad
                .groupby('cpms')
                .size()
                .reset_index(name='Atenciones')
                .sort_values(by='Atenciones', ascending=False)
            )

            df_prioridad_tabla = df_prioridad_tabla.rename(
                columns={'cpms': 'des_estandar'}
            )

            priority_tables[complejidad] = df_prioridad_tabla
            prioridades_data[complejidad] = len(df_complejidad)


        
        subtitle = f"Año {anio_str} | Periodo {periodo} | {nombre_centro}"

        cards = []

        for prioridad, label in prioridad_labels.items():
            prioridad_table = priority_tables.get(prioridad)

            cards.append({
                "title": label,
                "value": f"{prioridades_data.get(prioridad, 0):,.0f}",
                "border_color": PRIORIDAD_COLORS.get(prioridad, BRAND),
                "href": f"{url_base_pathname}complejidad_{prioridad}/{codcas_url}{detail_query}",
                "subtitle": f"Año {anio_str} | Periodo {periodo} | {nombre_centro}",
                "side_component": render_priority_table(
                    prioridad_table
                )           
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
        Output("download-dataframe-csv-cq-trans", "data"),
        Input("download-button-cq-trans", "n_clicks"),
        State('filter-periodo-cq-trans', 'value'),
        State('filter-anio-cq-trans', 'value'),
        State('filter-tipo-asegurado-cq-trans', 'value'),
        State('url-cq-trans', 'pathname'),
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
            SELECT cod_oricentro,
                cod_centro,
                ca.cenasides AS cenasides,
                periodo,
                anio,
                cod_area,
                cod_servicio,
                c.servhosdes AS servicio,
                cod_cpms,
                cp.cpsdes AS cpms,
                cod_tip_cirujano,
                cod_tipdoc_medico,
                dni_medico,
                fec_oper,
                autogenerado,
                cmame_pacsecnum,
                cod_tipdoc_paciente,
                doc_paciente,
                anio_edad,
                meses,
                sexo,
                cod_tip_seguro,
                cod_tipo_parentesco,
                cod_tipo_paciente,
                cod_sala,
                hor_ini_sala,
                hor_fin_sala,
                duracion_sala,
                hor_ini_anest,
                hor_fin_anest,
                duracion_anest,
                hor_ini_operac,
                hor_fin_operac,
                duracion_operac,
                acto_med,
                cod_complejidad,
                cod_anest,
                cod_tipo_programacion,
                num_solicitud,
                cod_quirof,
                fecsolicsalaoperac,
                fecsolicitadaoperac,
                fecprogram,
                cas_adscripcion,
                h_c,
                salopedes,
                cod_destegreso,
                fechcreasolicitud,
                horcreasolic,
                fecaptitud
            FROM dssge.dwe_centro_quirurgico_{anio_str}_{periodo} cq
                LEFT JOIN dwsge.sgss_cmsho10 AS c ON cq.cod_servicio = c.servhoscod
                LEFT JOIN dwsge.sgss_cmcas10 AS ca ON cq.cod_oricentro = ca.oricenasicod AND cq.cod_centro = ca.cenasicod
                LEFT JOIN dwsge.sgss_qmcqs10 AS q ON q.cenasicod = cq.cod_centro AND q.salopecod= cq.cod_sala_operacion AND cq.COD_QUIROF = q.cenquicod
                LEFT JOIN dwsge.sgss_cmcpp10 as cp ON cp.cpscod = cq.cod_cpms
            WHERE cod_centro='{codcas}'
              AND cod_cpms IN (
                '38241',
                '38240',
                '48551',
                '48552',
                '33945',
                '33935',
                '65730',
                '65710',
                '65750',
                '65755',
                '65712',
                '65714',
                '65732',
                '65752',
                '65756',
                '65757',
                '50250',
                '47135',
                '47163',
                '32851',
                '32852',
                '32854',
                '50360',
                '50365',
                '50380'
                )
              AND (
                    CASE
                        WHEN cod_tipo_paciente = '4' THEN '2'
                        ELSE '1'
                    END
                  ) IN {codasegu_clause}
        """
        df = pd.read_sql(query, engine)
        if df.empty:
            return None
        df = df.astype(str)
        filename = f"atenciones_por_complejidad_{codcas}_{anio_str}_{periodo}.csv"
        return dcc.send_data_frame(df.to_csv, filename, index=False)

    dash_app.layout = serve_layout
    return dash_app
  
