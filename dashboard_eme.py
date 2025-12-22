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
    EXEC_BG = "#F5F7FB"
    CARD_BG = "#FFFFFF"
    TEXT = "#212529"
    MUTED = "#6c757d"
    FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"
    
    # Colores por prioridad
    PRIORIDAD_COLORS = {
        '1': {'gradient': 'linear-gradient(135deg, #dc3545 0%, #c82333 100%)', 'icon': 'bi-exclamation-triangle-fill', 'bg': '#dc3545'},
        '2': {'gradient': 'linear-gradient(135deg, #fd7e14 0%, #e8590c 100%)', 'icon': 'bi-exclamation-circle-fill', 'bg': '#fd7e14'},
        '3': {'gradient': 'linear-gradient(135deg, #ffc107 0%, #e0a800 100%)', 'icon': 'bi-exclamation-diamond-fill', 'bg': '#ffc107'},
        '4': {'gradient': 'linear-gradient(135deg, #28a745 0%, #218838 100%)', 'icon': 'bi-check-circle-fill', 'bg': '#28a745'},
        '5': {'gradient': 'linear-gradient(135deg, #17a2b8 0%, #138496 100%)', 'icon': 'bi-info-circle-fill', 'bg': '#17a2b8'}
    }
    
    CARD_STYLE = {
        "cursor": "pointer",
        "border": "none",
        "borderRadius": "16px",
        "backgroundColor": CARD_BG,
        "boxShadow": "0 10px 30px rgba(0,0,0,0.1)",
        "transition": "all 0.3s ease",
        "position": "relative",
        "overflow": "hidden"
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


    # Generar periodos "01".."12"
    valores = [f"{i:02d}" for i in range(1, 13)]
    df_period = pd.DataFrame({'mes': meses, 'periodo': valores})

    # ========== LAYOUT ==========
    def serve_layout():
        if not has_request_context():
            return html.Div()

        if getattr(current_user, "is_authenticated", False):
            return dbc.Container([
                dcc.Location(id='url', refresh=False),
                dcc.Location(id='location-redirect', refresh=True),

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
                                    "Emergencias - Atenciones por Tópico y Prioridad",
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
                        dbc.Button(
                                [html.I(className="bi bi-arrow-left me-1"), "Inicio"],
                                id="btn-volver-eme",
                                color='secondary',
                                outline=True,
                                n_clicks=0
                            ),
                        dbc.Tooltip("Regresar a la página principal", target='btn-volver-eme', placement='bottom')
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
                    html.Div([
                        html.I(className="bi bi-calendar3", style={
                            'fontSize': '20px',
                            'color': BRAND,
                            'marginRight': '10px'
                        }),
                        dcc.Dropdown(
                            id='filter-periodo',
                            options=[{'label': row['mes'], 'value': row['periodo']} for _, row in df_period.iterrows()],
                            placeholder='Seleccione un periodo',
                            clearable=True,
                            style={
                                'width': '240px',
                                'fontFamily': FONT_FAMILY
                            }
                        ),
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                    dbc.Button(
                        [html.I(className="bi bi-search me-2"), "Buscar"],
                        id='search-button',
                        color='primary',
                        style={
                            'backgroundColor': BRAND,
                            'borderColor': BRAND,
                            'marginRight': '10px',
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
                        style={
                            'backgroundColor': '#28a745',
                            'borderColor': '#28a745',
                            'fontFamily': FONT_FAMILY,
                            'fontWeight': '600',
                            'borderRadius': '8px',
                            'padding': '8px 20px'
                        }
                    ),
                    dcc.Download(id="download-dataframe-csv")
                ], style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'marginBottom': '30px',
                    'padding': '20px',
                    'backgroundColor': CARD_BG,
                    'borderRadius': '14px',
                    'boxShadow': '0 8px 20px rgba(0,0,0,0.08)'
                }),

                # CONTENEDORES
                dbc.Row([dbc.Col(html.Div(id='summary-container'), width=12)]),
                html.Br(),
                dbc.Row([dbc.Col(html.Div(id='charts-container'), width=12)]),
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
            html.A('Ir a inicio', href='/', target='_top')
        ])

    # ========== CONEXIÓN DB ==========
    def create_connection():
        try:
            engine = create_engine('postgresql+psycopg2://postgres:admin@10.0.29.117:5433/DW_ESTADISTICA')
            with engine.connect() as conn:
                pass
            return engine
        except Exception as e:
            print(f"Failed to connect to the database: {e}")
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
        State('url', 'pathname')
    )
    def on_search(n_clicks, periodo, pathname):
        if not n_clicks:
            return html.Div(), html.Div()

        codcas = pathname.rstrip('/').split('/')[-1] if pathname else None
        if not periodo or not codcas:
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
                html.P("Por favor, seleccione un periodo y asegúrese de tener un centro válido.", style={
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
            FROM dwsge.dwe_emergencia_atenciones_homologacion_2025_{periodo} AS ce
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
        """

        query_defunciones= f"""
        SELECT * FROM dwsge.dwe_emergencia_defunciones_homologacion_2025_{periodo}
        WHERE cod_centro='{codcas}'
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
                html.P("No hay registros de atenciones para el periodo seleccionado.", style={
                    'color': MUTED,
                    'fontFamily': FONT_FAMILY
                }),
                html.P(f"Centro: {codcas} | Periodo: {periodo}", style={
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

        # === TARJETAS RESUMEN POR PRIORIDAD ===
        # Query base para obtener datos con cod_prioridad_n
        query_base = f"""
            SELECT
            d.cod_centro,d.periodo,d.cod_topico,d.acto_med,d.fecha_aten,d.hora_aten,d.cod_tipo_paciente,
            d.cod_prioridad,d.cod_emergencia,
            d.secuen_aten,d.cod_estandar,d.cod_prioridad_n
            FROM (
                SELECT 
                    ROW_NUMBER() OVER (PARTITION BY cod_centro, cod_estandar, 
            acto_med,cod_emergencia ORDER BY cast(secuen_aten as integer) asc) AS SECUENCIA, c.*
                 FROM (SELECT
                        a.cod_centro, 
                        a.periodo, 
                        a.cod_topico, 
                        acto_med, 
                        fecha_aten, 
                        hora_aten, 
                        cod_tipo_paciente,
                        cod_prioridad, 
                        a.cod_emergencia, 
                        secuen_aten, 
                        a.cod_estandar, 
                        a.cod_diagnostico,
                (case when a.cod_estandar = '04' then '1'
                else (case when a.cod_prioridad='1' then '2'
                            else (a.cod_prioridad) 
                            end) 
                end )as cod_prioridad_n
                        FROM 
                            dwsge.dwe_emergencia_atenciones_homologacion_2025_{periodo} a
                where (a.cod_diagnostico IS not NULL )
                and a.cod_estandar in ('04','05','06','07','08','09','10','11','12','13','14')
                 ) c	
            ) d
            WHERE
                d.SECUENCIA = '1'
            and cod_centro = '{codcas}'
        """
        
        # Obtener datos para cada prioridad (1-5)
        prioridades_data = {}
        prioridad_labels = {
            '1': 'Total de Atenciones por Prioridad 1',
            '2': 'Total de Atenciones por Prioridad 2',
            '3': 'Total de Atenciones por Prioridad 3',
            '4': 'Total de Atenciones por Prioridad 4',
            '5': 'Total de Atenciones por Prioridad 5'
        }
        
        for prioridad in ['1', '2', '3', '4', '5']:
            query_prioridad = query_base + f" and cod_prioridad_n = '{prioridad}'"
            try:
                df_prioridad = pd.read_sql(query_prioridad, engine)
                prioridades_data[prioridad] = len(df_prioridad)
            except Exception as e:
                print(f"Error en query de prioridad {prioridad}: {e}")
                prioridades_data[prioridad] = 0
        
        # Crear 5 cards manualmente con layout responsivo
        def crear_card_prioridad(prioridad, codcas, periodo, nombre_centro, cantidad):
            color_config = PRIORIDAD_COLORS[prioridad]
            return dbc.Col(
                html.A([
                    dbc.Card([
                        # Barra de color superior
                        html.Div(style={
                            'height': '6px',
                            'background': color_config['gradient'],
                            'borderRadius': '16px 16px 0 0'
                        }),
                        dbc.CardBody([
                            # Header con icono y prioridad
                            html.Div([
                                html.Div([
                                    html.I(className=f"bi {color_config['icon']}", style={
                                        'fontSize': '40px',
                                        'background': color_config['gradient'],
                                        '-webkit-background-clip': 'text',
                                        '-webkit-text-fill-color': 'transparent',
                                        'marginRight': '15px'
                                    }),
                                    html.Div([
                                        html.H5(f"Prioridad {prioridad}", style={
                                            'color': color_config['bg'],
                                            'marginBottom': '4px',
                                            'fontFamily': FONT_FAMILY,
                                            'fontSize': '16px',
                                            'fontWeight': '700'
                                        }),
                                        html.P(prioridad_labels[prioridad], style={
                                            'fontSize': '13px',
                                            'color': MUTED,
                                            'margin': 0,
                                            'fontFamily': FONT_FAMILY
                                        })
                                    ])
                                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '15px'})
                            ]),
                            # Cantidad grande
                            html.H2(f"{cantidad:,.0f}", style={
                                'fontWeight': '800',
                                'background': color_config['gradient'],
                                '-webkit-background-clip': 'text',
                                '-webkit-text-fill-color': 'transparent',
                                'fontSize': '48px',
                                'margin': '15px 0',
                                'fontFamily': FONT_FAMILY,
                                'textAlign': 'center'
                            }),
                            # Footer info
                            html.Div([
                                html.I(className="bi bi-calendar-check me-2", style={'color': MUTED}),
                                html.Span(f"Periodo {periodo}", style={
                                    'fontSize': '12px',
                                    'color': MUTED,
                                    'fontFamily': FONT_FAMILY
                                })
                            ], style={'marginTop': '15px', 'paddingTop': '15px', 'borderTop': f'1px solid #e9ecef'}),
                            html.Div([
                                html.I(className="bi bi-hospital me-2", style={'color': MUTED}),
                                html.Span(nombre_centro, style={
                                    'fontSize': '11px',
                                    'color': MUTED,
                                    'fontFamily': FONT_FAMILY
                                })
                            ], style={'marginTop': '8px'})
                        ])
                    ], style={
                        **CARD_STYLE,
                        'height': '100%'
                    }, className='h-100')
                ], href=f"{url_base_pathname}prioridad_{prioridad}/{codcas}?periodo={periodo}",
                   style={'textDecoration': 'none'},
                   className='hover-scale'),
                lg=4, md=6, sm=12, xs=12, className='mb-4'
            )
        
        # Card 1
        card1 = crear_card_prioridad('1', codcas, periodo, nombre_centro, prioridades_data.get('1', 0))
        
        # Cards 2-5 usando la función auxiliar
        card2 = crear_card_prioridad('2', codcas, periodo, nombre_centro, prioridades_data.get('2', 0))
        card3 = crear_card_prioridad('3', codcas, periodo, nombre_centro, prioridades_data.get('3', 0))
        card4 = crear_card_prioridad('4', codcas, periodo, nombre_centro, prioridades_data.get('4', 0))
        card5 = crear_card_prioridad('5', codcas, periodo, nombre_centro, prioridades_data.get('5', 0))
        
        # Card Defunciones
        color_defunciones = {'gradient': 'linear-gradient(135deg, #6c757d 0%, #5a6268 100%)', 'icon': 'bi-exclamation-triangle-fill', 'bg': '#6c757d'}
        card_defunciones = dbc.Col(
            html.A([
                dbc.Card([
                    # Barra de color superior
                    html.Div(style={
                        'height': '6px',
                        'background': color_defunciones['gradient'],
                        'borderRadius': '16px 16px 0 0'
                    }),
                    dbc.CardBody([
                        # Header con icono y prioridad
                        html.Div([
                            html.Div([
                                html.I(className=f"bi {color_defunciones['icon']}", style={
                                    'fontSize': '40px',
                                    'background': color_defunciones['gradient'],
                                    '-webkit-background-clip': 'text',
                                    '-webkit-text-fill-color': 'transparent',
                                    'marginRight': '15px'
                                }),
                                html.Div([
                                    html.H5("Defunciones", style={
                                        'color': color_defunciones['bg'],
                                        'marginBottom': '4px',
                                        'fontFamily': FONT_FAMILY,
                                        'fontSize': '16px',
                                        'fontWeight': '700'
                                    }),
                                    html.P("Total de Defunciones", style={
                                        'fontSize': '13px',
                                        'color': MUTED,
                                        'margin': 0,
                                        'fontFamily': FONT_FAMILY
                                    })
                                ])
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '15px'})
                        ]),
                        # Cantidad grande
                        html.H2(f"{defunciones_data:,.0f}", style={
                            'fontWeight': '800',
                            'background': color_defunciones['gradient'],
                            '-webkit-background-clip': 'text',
                            '-webkit-text-fill-color': 'transparent',
                            'fontSize': '48px',
                            'margin': '15px 0',
                            'fontFamily': FONT_FAMILY,
                            'textAlign': 'center'
                        }),
                        # Footer info
                        html.Div([
                            html.I(className="bi bi-calendar-check me-2", style={'color': MUTED}),
                            html.Span(f"Periodo {periodo}", style={
                                'fontSize': '12px',
                                'color': MUTED,
                                'fontFamily': FONT_FAMILY
                            })
                        ], style={'marginTop': '15px', 'paddingTop': '15px', 'borderTop': f'1px solid #e9ecef'}),
                        html.Div([
                            html.I(className="bi bi-hospital me-2", style={'color': MUTED}),
                            html.Span(nombre_centro, style={
                                'fontSize': '11px',
                                'color': MUTED,
                                'fontFamily': FONT_FAMILY
                            })
                        ], style={'marginTop': '8px'})
                    ])
                ], style={
                    **CARD_STYLE,
                    'height': '100%'
                }, className='h-100')
            ], style={'textDecoration': 'none'}, className='hover-scale'),
            lg=4, md=6, sm=12, xs=12, className='mb-4'
        )
        
        # Estadísticas totales con estadísticas adicionales
        total_atenciones = sum(prioridades_data.values())
        stats_header = html.Div([
            # Card principal de total
            html.Div([
                html.Div([
                    html.I(className="bi bi-clipboard2-pulse", style={
                        'fontSize': '64px',
                        'background': 'linear-gradient(135deg, #0064AF 0%, #0085d4 100%)',
                        '-webkit-background-clip': 'text',
                        '-webkit-text-fill-color': 'transparent',
                        'marginRight': '25px'
                    }),
                    html.Div([
                        html.H3("Total de Atenciones de Emergencia", style={
                            'color': TEXT,
                            'fontFamily': FONT_FAMILY,
                            'fontSize': '20px',
                            'margin': 0,
                            'fontWeight': '700',
                            'letterSpacing': '-0.5px'
                        }),
                        html.H1(f"{total_atenciones:,.0f}", style={
                            'background': 'linear-gradient(135deg, #0064AF 0%, #0085d4 100%)',
                            '-webkit-background-clip': 'text',
                            '-webkit-text-fill-color': 'transparent',
                            'fontFamily': FONT_FAMILY,
                            'fontSize': '56px',
                            'margin': '12px 0 8px 0',
                            'fontWeight': '900',
                            'letterSpacing': '-2px',
                            'lineHeight': '1'
                        }),
                        html.P(f"📍 {nombre_centro} | 📅 Periodo {periodo}", style={
                            'fontSize': '14px',
                            'color': MUTED,
                            'margin': 0,
                            'fontFamily': FONT_FAMILY,
                            'fontWeight': '500'
                        })
                    ], style={'flex': '1'})
                ], style={'display': 'flex', 'alignItems': 'center'})
            ], style={
                'padding': '35px 40px',
                'backgroundColor': CARD_BG,
                'borderRadius': '20px',
                'boxShadow': '0 15px 40px rgba(0,100,175,0.12)',
                'marginBottom': '30px',
                'background': f'linear-gradient(135deg, {CARD_BG} 0%, #f0f7ff 100%)',
                'border': '1px solid rgba(0,100,175,0.1)'
            }),
            
        ])
        
        summary_row = dbc.Container([
            stats_header,
            html.H4("📊 Atenciones por Nivel de Prioridad", style={
                'color': '#ffffff',
                'fontFamily': FONT_FAMILY,
                'fontSize': '20px',
                'fontWeight': '700',
                'marginBottom': '25px',
                'marginTop': '10px'
            }),
            dbc.Row([card1, card2, card3, card4, card5, card_defunciones], className='g-4')
        ], fluid=True)

        return summary_row, html.Div()
       # ========== CALLBACK DESCARGA CSV ==========
    @dash_app.callback(
        Output("download-dataframe-csv", "data"),
        Input("download-button", "n_clicks"),
        State('filter-periodo', 'value'),
        State('url', 'pathname'),
        prevent_initial_call=True
    )
    def download_csv(n_clicks, periodo, pathname):
        if not n_clicks or not periodo or not pathname:
            return None

        codcas = pathname.rstrip('/').split('/')[-1] if pathname else None
        if not codcas:
            return None

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
            and cod_prioridad_n != '0'
        """
        df = pd.read_sql(query, engine)
        if df.empty:
            return None

        filename = f"atenciones_por_prioridad_{codcas}_{periodo}.csv"
        return dcc.send_data_frame(df.to_csv, filename, index=False)

    @dash_app.callback(
        Output("location-redirect", "href"),
        Input("btn-volver-eme", "n_clicks"),
        prevent_initial_call=True
    )
    def navegar_volver_eme(n_clicks):
        if n_clicks:
            return "/"
        return ""



    dash_app.layout = serve_layout
    return dash_app
  
