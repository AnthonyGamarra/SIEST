from dash import Dash, html, dcc, Input, Output, State
from flask import has_request_context
from flask_login import current_user
from sqlalchemy import create_engine
import pandas as pd
import dash_bootstrap_components as dbc
import plotly.express as px
from datetime import date
import dash_ag_grid as dag
import dash
import importlib

def create_dash_app(flask_app, url_base_pathname='/dashboard/'):
    external_stylesheets = [
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
    ]

    # Paleta y estilos
    BRAND = "#0064AF"
    BRAND_SOFT = "#D7E9FF"
    ACCENT = "#00AEEF"
    EXEC_BG = "#F6F8FB"
    CARD_BG = "#FFFFFF"
    TEXT = "#1C1F26"
    MUTED = "#6B7280"
    BORDER = "#E5E7EB"
    FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"
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
    CONTROL_BAR_STYLE = {
        "display": "flex",
        "alignItems": "center",
        "gap": "12px",
        "marginBottom": "18px",
        "backgroundColor": CARD_BG,
        "border": f"1px solid {BORDER}",
        "padding": "14px 16px",
        "borderRadius": "14px",
        "boxShadow": "0 4px 10px rgba(0,0,0,0.05)",
        "backdropFilter": "blur(3px)",
        "overflow": "visible",
        "position": "relative",
        "zIndex": 1100,
    }

    def _import_indicator_pages():
        pkg_name = f"{__package__}.Indicadores" if __package__ else "Indicadores"
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception as e:
            print(f"[Dash Pages] No se pudo importar el paquete '{pkg_name}': {e}")
            return
        import pkgutil
        for m in pkgutil.iter_modules(pkg.__path__):
            mod_name = f"{pkg_name}.{m.name}"
            try:
                importlib.import_module(mod_name)
                print(f"[Dash Pages] Página importada: {mod_name}")
            except Exception as e:
                print(f"[Dash Pages] Error importando {mod_name}: {e}")

    dash_app = Dash(
        __name__,
        server=flask_app,
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
        requests_pathname_prefix=url_base_pathname,
        routes_pathname_prefix=url_base_pathname,
        use_pages=True,
        pages_folder=""
    )

    dash_app.title = "SIEST"


    _import_indicator_pages()

    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    valores = [f"{i:02d}" for i in range(1, 13)]
    df_period = pd.DataFrame({'mes': meses, 'periodo': valores})

    # LAYOUT ==========
    def serve_layout():
        if not has_request_context():
            return html.Div()

        if getattr(current_user, "is_authenticated", False):
            header = html.Div([
                html.Img(
                    src=dash_app.get_asset_url('logo.png'),
                    style={
                        'width': '120px',
                        'height': '60px',
                        'objectFit': 'contain',
                        'marginRight': '16px'
                    }
                ),
                html.Div([
                    html.Div([
                        html.I(className="bi bi-hospital", style={'fontSize': '30px', 'color': BRAND, 'marginRight': '10px'}),
                        html.H2(
                            "Consulta externa 2025 - Atenciones médicas",
                            style={
                                'color': BRAND,
                                'fontFamily': FONT_FAMILY,
                                'fontSize': '26px',
                                'fontWeight': 800,
                                'margin': '0'
                            }
                        ),
                    ], style={'display': 'flex', 'alignItems': 'center', 'gap': '8px'}),
                    html.P(
                        f"📅 Información actualizada al {date.today().strftime('%d/%m/%Y')} | Sistema de Gestión Hospitalaria",
                        style={
                            'color': MUTED,
                            'fontFamily': FONT_FAMILY,
                            'fontSize': '13px',
                            'margin': '6px 0 0 0'
                        }
                    )
                ], style={
                    'display': 'flex',
                    'flexDirection': 'column',
                    'justifyContent': 'center'
                })
            ], style={
                'display': 'flex',
                'alignItems': 'center',
                'padding': '16px 20px',
                'backgroundColor': CARD_BG,
                'borderRadius': '16px',
                'boxShadow': '0 8px 20px rgba(0,0,0,0.08)',
                'gap': '14px'
            })

            content = html.Div([
                dcc.Location(id='url', refresh=True),

                html.Div([
                    header,
                    html.Br(),

                    html.Div([
                        html.I(className="bi bi-calendar3", style={'fontSize': '18px', 'color': BRAND, 'marginRight': '8px'}),
                        dcc.Dropdown(
                            id='filter-periodo',
                            className='periodo-dropdown',
                            options=[{'label': row['mes'], 'value': row['periodo']} for _, row in df_period.iterrows()],
                            placeholder='Seleccione un periodo',
                            clearable=True,
                            style={
                                'width': '240px',
                                'fontFamily': FONT_FAMILY,
                                'position': 'relative',
                                'zIndex': 1200
                            }
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-search me-2"), "Buscar"],
                            id='search-button',
                            color='primary',
                            size='md',
                            style={
                                'backgroundColor': BRAND,
                                'borderColor': BRAND,
                                'padding': '8px 12px',
                                'boxShadow': '0 4px 10px rgba(0,100,175,0.2)',
                                'fontFamily': FONT_FAMILY,
                                'fontWeight': '600',
                                'borderRadius': '8px'
                            }
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-download me-2"), "Exportar CSV"],
                            id='download-button',
                            color='success',
                            size='md',
                            style={
                                'backgroundColor': '#28a745',
                                'borderColor': '#28a745',
                                'padding': '8px 12px',
                                'boxShadow': '0 4px 10px rgba(40,167,69,0.18)',
                                'fontFamily': FONT_FAMILY,
                                'fontWeight': '600',
                                'borderRadius': '8px'
                            }
                        ),
                        dcc.Download(id="download-dataframe-csv"),
                        dbc.Button(
                            [html.I(className="bi bi-arrow-left me-1"), "Inicio"],
                            id='back-button',
                            color='secondary',
                            outline=True,
                            n_clicks=0,
                            style={
                                'marginLeft': 'auto',
                                'color': BRAND,
                                'borderColor': BRAND,
                                'padding': '8px 12px'
                            }
                        ),
                    ], style={
                        **CONTROL_BAR_STYLE
                        
                    }),

                    dbc.Tooltip("Regresar al inicio", target='back-button', placement='bottom'),
                    dbc.Tooltip("Buscar datos", target='search-button', placement='bottom'),
                    dbc.Tooltip("Descargar CSV", target='download-button', placement='bottom'),

                    dbc.Row([dbc.Col(html.Div(id='summary-container'), width=12)]),
                    html.Br(),
                    dbc.Row([dbc.Col(
                        html.Div(id='charts-container')
                    , width=12)]),
                    html.Br(),
                ], id='main-dashboard-content'),

                html.Div(
                    children=dash.page_container,
                    id='page-container-wrapper',
                    style={'display': 'none'} 
                )
            ], style={
                'marginTop': '10px',
                'width': '100%',
                'padding': '0'
            })

            return dbc.Container([content], fluid=True, style={
                'backgroundImage': "url('/static/76824.jpg')",
                'backgroundSize': 'cover',
                'backgroundPosition': 'center center',
                'backgroundRepeat': 'no-repeat',
                'backgroundAttachment': 'fixed',
                'minHeight': '100vh',
                'padding': '18px 12px 26px 12px',
                'fontFamily': FONT_FAMILY
            })

        return html.Div([
            html.H3('No autenticado'),
            html.P('Debes iniciar sesión para ver el dashboard.'),
            html.A('Ir a inicio', href='/', target='_top')
        ])

    # CONEXIÓN DB ==========
    def create_connection():
        try:
            engine = create_engine('postgresql+psycopg2://postgres:4dm1n@10.0.29.117:5433/DW_ESTADISTICA')
            with engine.connect() as conn:
                pass
            return engine
        except Exception as e:
            print(f"Failed to connect to the database: {e}")
            return None

    # CALLBACK PRINCIPAL ==========
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
        
        import secure_code as sc

        codcas_url = pathname.rstrip('/').split('/')[-1] if pathname else None
        codcas = sc.decode_code(codcas_url) if codcas_url else None

        if not periodo or not codcas:
            return html.Div("Seleccione un periodo y asegúrese de tener un centro válido."), html.Div()

        engine = create_connection()
        if engine is None:
            return html.Div("Error de conexión a la base de datos."), html.Div()

        query = f"""
            SELECT 
                ce.cod_servicio,
                ce.cod_especialidad,
                ca.cenasides,
                am.actdes AS actividad,
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
            LEFT JOIN dwsge.sgss_cmsho10 AS c 
                ON ce.cod_servicio = c.servhoscod
            LEFT JOIN dwsge.dim_especialidad AS e
                ON ce.cod_especialidad = e.cod_especialidad
            LEFT JOIN dwsge.sgss_cmtco10 AS t
                ON ce.cod_tipo_consulta = t.tipconcod
            LEFT JOIN dwsge.sgss_cmdia10 AS d
                ON ce.cod_diag = d.diagcod
            LEFT JOIN dwsge.sgss_cmace10 AS a
                ON ce.cod_actividad = a.actcod
                AND ce.cod_subactividad = a.actespcod
            LEFT JOIN dwsge.sgss_cmact10 AS am
                ON ce.cod_actividad = am.actcod
            LEFT JOIN dwsge.sgss_cmcas10 AS ca
                ON ce.cod_oricentro = ca.oricenasicod
                AND ce.cod_centro = ca.cenasicod
            WHERE ce.cod_centro = '{codcas}'
            AND ce.cod_actividad = '91'
            AND ce.clasificacion in (2,4,6)
            AND ce.cod_variable = '001';
        """
        query2 = f"""
            SELECT 
                ce.*,
				c.servhosdes,
				e.especialidad,
				a.actespnom,
				am.actdes,
				ca.cenasides
            FROM dwsge.dwe_consulta_externa_horas_efectivas_2025_{periodo} AS ce
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
            WHERE ce.cod_centro = '{codcas}'
            AND ce.cod_actividad = '91'
            AND ce.cod_variable = '001';
        """
        query3 = f"""
            SELECT 			
                p.*,c.servhosdes,
                e.especialidad,
                a.actespnom,
                am.actdes,
                ca.cenasides 
            FROM dwsge.dwe_consulta_externa_programacion_2025_{periodo} p
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
            WHERE p.cod_variable = '001'
            AND (
                    p.cod_motivo_suspension IS NULL 
                    OR p.cod_motivo_suspension NOT IN ('04','09','10','99','13','16','11')
                )
            AND p.cod_centro = '{codcas}'
            AND p.cod_actividad = '91'
            AND p.cod_variable = '001'
        """
        query4=f"""
            SELECT 			
                p.*,c.servhosdes,
                e.especialidad,
                a.actespnom,
                am.actdes,
                ca.cenasides 
            FROM dwsge.dwe_consulta_externa_citados_homologacion_2025_{periodo} p
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
            WHERE p.cod_centro = '{codcas}'
            AND p.cod_actividad = '91'
            AND p.cod_variable = '001'
            AND p.cod_estado <>'0';
        """
        query5=f"""
                SELECT            
                    c.servhosdes,
                    e.especialidad,
                    a.actespnom,
                    am.actdes,
                    ca.cenasides
                FROM dwsge.dw_consulta_externa_homologacion_2025_{periodo} ce
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
                WHERE ce.cod_centro = '{codcas}'
                AND ce.cod_actividad = '91'
                AND ce.clasificacion IN (1,3,0)
                AND ce.cod_variable = '001'

                UNION ALL

                SELECT 			
                    c.servhosdes,
                    e.especialidad,
                    a.actespnom,
                    am.actdes,
                    ca.cenasides 
                FROM dwsge.dwe_consulta_externa_citados_homologacion_2025_{periodo} p
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
                WHERE p.cod_centro = '{codcas}'
                AND p.cod_actividad = '91'
                AND p.cod_variable = '001'
                AND p.cod_estado IN ('1','2','5');

        """
        query6=f"""
            SELECT
                f.periodo,
                f.cod_oricentro,	
                f.cod_centro,
                TRUNC(
                    CASE 
                        WHEN SUM(f.num_citas::int) = 0 THEN NULL
                        ELSE SUM(f.diferimiento::int * f.num_citas::int)::numeric 
                            / SUM(f.num_citas::int)
                    END
                , 2) AS promedio_ponderado_diferimiento
            FROM dwsge.dwe_consulta_externa_citados_homologacion_2025_{periodo} f
            WHERE f.flag_calidad IN ('1','2','3','6')
            AND f.cod_estado = '4'
            AND f.cod_actividad = '91'
            AND f.diferimiento IS NOT NULL
            AND f.diferimiento::int >= 0
            AND f.cod_variable = '001'
            AND f.cod_centro = '{codcas}'
            GROUP BY 
                f.periodo,
                f.cod_oricentro,
                f.cod_centro;
        """
        
        from concurrent.futures import ThreadPoolExecutor

        def read_fast(q):
            return pd.concat(
                pd.read_sql(q, engine, chunksize=400_000),
                ignore_index=True
            )

        # ---------- Grupo 1: df y df2 ----------
        with ThreadPoolExecutor(max_workers=2) as executor:
            df, df2 = executor.map(read_fast, [query, query2])

        # ---------- Grupo 2: df3 y df4 ----------
        with ThreadPoolExecutor(max_workers=2) as executor:
            df3, df4 = executor.map(read_fast, [query3, query4])

        # ---------- Grupo 3: df5 ----------
        df5 = read_fast(query5)

        # ---------- Validación ----------
        if df.empty or df2.empty or df3.empty:
            return html.Div("No hay registros para el periodo seleccionado."), html.Div()
        
        

        # NOMBRE DEL CENTRO ===
        nombre_centro = df['cenasides'].dropna().unique()
        nombre_centro = nombre_centro[0] if len(nombre_centro) > 0 else codcas

        # TARJETAS RESUMEN ===
        total_atenciones = len(df)
        total_atendidos = df[['doc_paciente', 'cod_tipdoc_paciente']].drop_duplicates().shape[0]
        total_medicos = df['dni_medico'].nunique()
        df2["hras_prog"] = pd.to_numeric(df2["hras_prog"], errors="coerce")
        total_horas_efectivas = df2['hras_prog'].sum()
        df3["total_horas"] = pd.to_numeric(df3["total_horas"], errors="coerce")
        total_horas_programadas = df3['total_horas'].sum()
        total_citados = df4.shape[0]
        total_desercion_citas = df5.shape[0]
        ##promedio_ponderado_diferimiento = (round(df6['promedio_ponderado_diferimiento'].iloc[0], 2)if not df6.empty else None)

        # Construir hrefs usando url_base_pathname para evitar rutas hardcodeadas
        base = url_base_pathname.rstrip('/') + '/'

        summary_row = dbc.Container([
            dbc.Row([
                dbc.Col(
                    dbc.Spinner(
                        dbc.Card(
                            dbc.CardBody([
                                dcc.Link(
                                    html.H5("Total de Atenciones", className="card-title",
                                            style={'color': BRAND, 'marginBottom': '6px', 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.1px'}),
                                    href=f"{base}dash/total_atenciones/{codcas_url}?periodo={periodo}",
                                    className="link-underline-primary link-underline-opacity-0 link-underline-opacity-100-hover link-offset-2-hover text-reset"
                            ),
                            html.H2(f"{total_atenciones:,.0f}",
                                    style={'fontWeight': '800', 'color': TEXT, 'fontSize': '34px', 'margin': 0, 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.2px'}),
                            html.P(f"Periodo {periodo} | {nombre_centro}",
                                   style={'fontSize': '12px', 'color': MUTED, 'margin': '6px 0 0 0', 'fontFamily': FONT_FAMILY})
                        ], style=CARD_BODY_STYLE),
                        style={**CARD_STYLE, "borderLeft": f"5px solid {BRAND}"}
                    ),
                    color="light",
                    spinner_style={"width": "2.5rem", "height": "2.5rem"}
                ),
                md=6, xs=12
                ),
                dbc.Col(
                    dbc.Spinner(
                        dbc.Card(
                            dbc.CardBody([
                                            html.H5(
                                                "Total de Pacientes Atendidos en el mes",
                                                className="card-title",
                                                style={
                                                    'color': BRAND,
                                                    'marginBottom': '6px',
                                                    'fontFamily': FONT_FAMILY,
                                                    'letterSpacing': '-0.1px'
                                                }
                                            ),
                                            html.H2(
                                                f"{total_atendidos:,.0f}",
                                                style={
                                                    'fontWeight': '800',
                                                    'color': TEXT,
                                                    'fontSize': '34px',
                                                    'margin': 0,
                                                    'fontFamily': FONT_FAMILY,
                                                    'letterSpacing': '-0.2px'
                                                }
                                            ),
                                            html.P(
                                                f"Periodo {periodo} | {nombre_centro}",
                                                style={
                                                    'fontSize': '12px',
                                                    'color': MUTED,
                                                    'margin': '6px 0 0 0',
                                                    'fontFamily': FONT_FAMILY
                                                }
                                            )
                        ], style=CARD_BODY_STYLE),
                        style={**CARD_STYLE, "borderLeft": f"5px solid {ACCENT}"}
                    ),
                    color="light",
                    spinner_style={"width": "2.5rem", "height": "2.5rem"}
                ),
                md=6, xs=12
                ),
            ], justify="center", align="stretch", style={'marginBottom': '10px', 'rowGap': '10px'}),

            dbc.Row([
                dbc.Col(
                    dbc.Spinner(
                        dbc.Card(
                            dbc.CardBody([
                            dcc.Link(
                                html.H5("Total de Médicos Programados", className="card-title",
                                        style={'color': BRAND, 'marginBottom': '6px', 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.1px'}),
                                href=f"{base}dash/total_medicos/{codcas_url}?periodo={periodo}",
                                className="link-underline-primary link-underline-opacity-0 link-underline-opacity-100-hover link-offset-2-hover text-reset"
                            ),
                            html.H2(f"{total_medicos:,.0f}",
                                    style={'fontWeight': '800', 'color': TEXT, 'fontSize': '34px', 'margin': 0, 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.2px'}),
                            html.P(f"Periodo {periodo} | {nombre_centro}",
                                   style={'fontSize': '12px', 'color': MUTED, 'margin': '6px 0 0 0', 'fontFamily': FONT_FAMILY})
                        ], style=CARD_BODY_STYLE),
                        style={**CARD_STYLE, "borderLeft": f"5px solid {BRAND_SOFT}"}
                    ),
                    color="light",
                    spinner_style={"width": "2.5rem", "height": "2.5rem"}
                ),
                md=6, xs=12
                ),
                dbc.Col(
                    dbc.Spinner(
                        dbc.Card(
                            dbc.CardBody([
                            dcc.Link(
                                html.H5("Total de Horas Efectivas", className="card-title",
                                        style={'color': BRAND, 'marginBottom': '6px', 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.1px'}),
                                href=f"{base}dash/horas_efectivas/{codcas}?periodo={periodo}",
                                className="link-underline-primary link-underline-opacity-0 link-underline-opacity-100-hover link-offset-2-hover text-reset"
                            ),
                            html.H2(f"{total_horas_efectivas:,.0f}",
                                    style={'fontWeight': '800', 'color': TEXT, 'fontSize': '34px', 'margin': 0, 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.2px'}),
                            html.P(f"Periodo {periodo} | {nombre_centro}",
                                   style={'fontSize': '12px', 'color': MUTED, 'margin': '6px 0 0 0', 'fontFamily': FONT_FAMILY})
                        ], style=CARD_BODY_STYLE),
                        style={**CARD_STYLE, "borderLeft": f"5px solid {ACCENT}"}
                    ),
                    color="light",
                    spinner_style={"width": "2.5rem", "height": "2.5rem"}
                ),
                md=6, xs=12
                )
            ], justify="center", align="stretch", style={'marginBottom': '10px', 'rowGap': '10px'}),

            dbc.Row([
                dbc.Col(
                    dbc.Spinner(
                        dbc.Card(
                            dbc.CardBody([
                            dcc.Link(
                                html.H5("Total horas programadas", className="card-title",
                                        style={'color': BRAND, 'marginBottom': '6px', 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.1px'}),
                                href=f"{base}dash/horas_programadas/{codcas_url}?periodo={periodo}",
                                className="link-underline-primary link-underline-opacity-0 link-underline-opacity-100-hover link-offset-2-hover text-reset"
                            ),
                            html.H2(f"{total_horas_programadas:,.0f}",
                                    style={'fontWeight': '800', 'color': TEXT, 'fontSize': '34px', 'margin': 0, 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.2px'}),
                            html.P(f"Periodo {periodo} | {nombre_centro}",
                                   style={'fontSize': '12px', 'color': MUTED, 'margin': '6px 0 0 0', 'fontFamily': FONT_FAMILY})
                        ], style=CARD_BODY_STYLE),
                        style={**CARD_STYLE, "borderLeft": f"5px solid {BRAND}"}
                    ),
                    color="light",
                    spinner_style={"width": "2.5rem", "height": "2.5rem"}
                ),
                md=6, xs=12
                ),
                dbc.Col(
                    dbc.Spinner(
                        dbc.Card(
                            dbc.CardBody([
                            dcc.Link(
                                html.H5("Total Citas", className="card-title",
                                        style={'color': BRAND, 'marginBottom': '6px', 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.1px'}),
                                href=f"{base}dash/total_citados/{codcas_url}?periodo={periodo}",
                                className="link-underline-primary link-underline-opacity-0 link-underline-opacity-100-hover link-offset-2-hover text-reset"
                            ),
                            html.H2(f"{total_citados:,.0f}",
                                    style={'fontWeight': '800', 'color': TEXT, 'fontSize': '34px', 'margin': 0, 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.2px'}),
                            html.P(f"Periodo {periodo} | {nombre_centro}",
                                   style={'fontSize': '12px', 'color': MUTED, 'margin': '6px 0 0 0', 'fontFamily': FONT_FAMILY})
                        ], style=CARD_BODY_STYLE),
                        style={**CARD_STYLE, "borderLeft": f"5px solid {ACCENT}"}
                    ),
                    color="light",
                    spinner_style={"width": "2.5rem", "height": "2.5rem"}
                ),
                md=6, xs=12
                )
            ], justify="center", align="stretch", style={'marginBottom': '10px', 'rowGap': '10px'}),

            dbc.Row([
                dbc.Col(
                    dbc.Spinner(
                        dbc.Card(
                            dbc.CardBody([
                                dcc.Link(
                                    html.H5(
                                        "Total desercion citas",
                                        className="card-title",
                                        style={'color': BRAND, 'marginBottom': '6px', 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.1px'}
                                    ),
                                    href=f"{base}dash/desercion_citas/{codcas_url}?periodo={periodo}",
                                    className="link-underline-primary link-underline-opacity-0 link-underline-opacity-100-hover link-offset-2-hover text-reset"
                                ),
                                html.H2(
                                    f"{total_desercion_citas:,.0f}",
                                    style={'fontWeight': '800', 'color': TEXT, 'fontSize': '34px', 'margin': 0, 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.2px'}
                                ),
                                html.P(
                                    f"Periodo {periodo} | {nombre_centro}",
                                    style={'fontSize': '12px', 'color': MUTED, 'margin': '6px 0 0 0', 'fontFamily': FONT_FAMILY}
                                )
                            ], style=CARD_BODY_STYLE),
                            style={**CARD_STYLE, "borderLeft": f"5px solid {BRAND_SOFT}"}
                        ),
                        color="light",
                        spinner_style={"width": "2.5rem", "height": "2.5rem"}
                    ),
                    md=6, xs=12
                )
                ,dbc.Col(
                    dbc.Spinner(
                        dbc.Card(
                            dbc.CardBody([
                                dcc.Link(
                                    html.H5(
                                        "Promedio diferimiento de citas",
                                        className="card-title",
                                        style={'color': BRAND, 'marginBottom': '6px', 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.1px'}
                                    ),
                                    href=f"{base}dash/diferimiento/{codcas_url}?periodo={periodo}",
                                    className="link-underline-primary link-underline-opacity-0 link-underline-opacity-100-hover link-offset-2-hover text-reset"
                                ),
                                html.H2(
                                    #f"{promedio_ponderado_diferimiento:,.2f}",
                                    style={'fontWeight': '800', 'color': TEXT, 'fontSize': '34px', 'margin': 0, 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.2px'}
                                ),
                                html.P(
                                    f"Periodo {periodo} | {nombre_centro}",
                                    style={'fontSize': '12px', 'color': MUTED, 'margin': '6px 0 0 0', 'fontFamily': FONT_FAMILY}
                                )
                            ], style=CARD_BODY_STYLE),
                            style={**CARD_STYLE, "borderLeft": f"5px solid {ACCENT}" , 'display': 'none'}
                        ),
                        color="light",
                        spinner_style={"width": "2.5rem", "height": "2.5rem"}
                    ),
                    md=6, xs=12
                ),
            ], justify="center", align="stretch", style={'marginBottom': '10px', 'rowGap': '10px' }),

        ], fluid=True)

        # COLORES 
        color_principal = "#0064AF"
        color_secundario = "#00AEEF"
        font_family = "Calibri"

        charts_container = html.Div() 
        return summary_row, charts_container

    # Callback para ocultar/mostrar el contenido principal y el contenedor de páginas según la ruta
    @dash_app.callback(
        Output('main-dashboard-content', 'style'),
        Output('page-container-wrapper', 'style'),
        Input('url', 'pathname')
    )
    def toggle_main_content(pathname):
        base = url_base_pathname.rstrip('/') + '/'
        if pathname and pathname.startswith(f"{base}dash/"):
            # Estamos en una página registrada -> ocultar principal, mostrar page container
            return {'display': 'none'}, {'display': 'block'}
        # Ruta principal -> mostrar principal, ocultar page container
        return {'display': 'block'}, {'display': 'none'}

    # Callback botón retroceso: redirigir a raíz del sitio (ip/)
    @dash_app.callback(
        Output('url', 'pathname'),
        Input('back-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def go_root(n):
        return "/"

    # CALLBACK DESCARGA CSV ==========
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


        query = f"""
            SELECT 
                ce.cod_servicio,
                ce.cod_especialidad,
                ca.cenasides,
                am.actdes AS actividad,
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
            LEFT JOIN dwsge.sgss_cmsho10 AS c 
                ON ce.cod_servicio = c.servhoscod
            LEFT JOIN dwsge.dim_especialidad AS e
                ON ce.cod_especialidad = e.cod_especialidad
            LEFT JOIN dwsge.sgss_cmtco10 AS t
                ON ce.cod_tipo_consulta = t.tipconcod
            LEFT JOIN dwsge.sgss_cmdia10 AS d
                ON ce.cod_diag = d.diagcod
            LEFT JOIN dwsge.sgss_cmace10 AS a
                ON ce.cod_actividad = a.actcod
                AND ce.cod_subactividad = a.actespcod
            LEFT JOIN dwsge.sgss_cmact10 AS am
                ON ce.cod_actividad = am.actcod
            LEFT JOIN dwsge.sgss_cmcas10 AS ca
                ON ce.cod_oricentro = ca.oricenasicod
                AND ce.cod_centro = ca.cenasicod
            WHERE ce.cod_centro = '{codcas}'
            AND ce.cod_actividad = '91'
            AND ce.clasificacion in (2,4,6)
            AND ce.cod_variable = '001';
        """
        query2 = f"""
            SELECT 
                ce.*,
				c.servhosdes,
				e.especialidad,
				a.actespnom,
				am.actdes,
				ca.cenasides
            FROM dwsge.dwe_consulta_externa_horas_efectivas_2025_{periodo} AS ce
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
            WHERE ce.cod_centro = '{codcas}'
            AND ce.cod_actividad = '91'
            AND ce.cod_variable = '001';
        """
        query3 = f"""
            SELECT 			
                p.*,c.servhosdes,
                e.especialidad,
                a.actespnom,
                am.actdes,
                ca.cenasides 
            FROM dwsge.dwe_consulta_externa_programacion_2025_{periodo} p
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
            WHERE p.cod_variable = '001'
            AND (
                    p.cod_motivo_suspension IS NULL 
                    OR p.cod_motivo_suspension NOT IN ('04','09','10','99','13','16','11')
                )
            AND p.cod_centro = '{codcas}'
            AND p.cod_actividad = '91'
            AND p.cod_variable = '001'
        """
        query4=f"""
            SELECT 			
                p.*,c.servhosdes,
                e.especialidad,
                a.actespnom,
                am.actdes,
                ca.cenasides 
            FROM dwsge.dwe_consulta_externa_citados_homologacion_2025_{periodo} p
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
            WHERE p.cod_centro = '{codcas}'
            AND p.cod_actividad = '91'
            AND p.cod_variable = '001'
            AND p.cod_estado <>'0';
        """
        query5=f"""
            SELECT 			
                p.*,c.servhosdes,
                e.especialidad,
                a.actespnom,
                am.actdes,
                ca.cenasides 
            FROM dwsge.dwe_consulta_externa_citados_homologacion_2025_{periodo} p
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
            WHERE p.cod_centro = '{codcas}'
            AND p.cod_actividad = '91'
            AND p.cod_variable = '001'
            AND p.cod_estado ='5';

        """

        query6=f"""
            SELECT
                f.periodo,
                f.cod_oricentro,	
                f.cod_centro,
                TRUNC(
                    CASE 
                        WHEN SUM(f.num_citas::int) = 0 THEN NULL
                        ELSE SUM(f.diferimiento::int * f.num_citas::int)::numeric 
                            / SUM(f.num_citas::int)
                    END
                , 2) AS promedio_ponderado_diferimiento
            FROM dwsge.dwe_consulta_externa_citados_homologacion_2025_{periodo} f
            WHERE f.flag_calidad IN ('1','2','3','6')
            AND f.cod_estado = '4'
            AND f.cod_actividad = '91'
            AND f.diferimiento IS NOT NULL
            AND f.diferimiento::int >= 0
            AND f.cod_variable = '001'
            AND f.cod_centro = '{codcas}'
            GROUP BY 
                f.periodo,
                f.cod_oricentro,
                f.cod_centro;
        """

        df = pd.read_sql(query, engine)
        df2 = pd.read_sql(query2, engine)
        df3 = pd.read_sql(query3, engine)
        df4= pd.read_sql(query4, engine)
        df5= pd.read_sql(query5, engine)
        #df6= pd.read_sql(query6, engine)

        total_atenciones = len(df)
        total_atendidos = df[['doc_paciente', 'cod_tipdoc_paciente']].drop_duplicates().shape[0]
        total_medicos = df['dni_medico'].nunique()
        df2["hras_prog"] = pd.to_numeric(df2["hras_prog"], errors="coerce")
        total_horas_efectivas = df2['hras_prog'].sum()
        df3["total_horas"] = pd.to_numeric(df3["total_horas"], errors="coerce")
        total_horas_programadas = df3['total_horas'].sum()
        total_citados = df4.shape[0]
        total_desercion_citas = df5.shape[0]
        #promedio_ponderado_diferimiento = df6['promedio_ponderado_diferimiento'].iloc[0] if not df6.empty else None

        # Crear un diccionario con los totales
        resumen = {
            'Total de Atenciones': total_atenciones,
            'Total de Atendidos': total_atendidos,
            'Total de Medicos': total_medicos,
            'Total Horas Efectivas': total_horas_efectivas,
            'Total Horas Programadas': total_horas_programadas,
            'Total Citados': total_citados,
            'Total Desercion de Citas': total_desercion_citas
        }

        # Convertir a DataFrame
        df_resumen = pd.DataFrame(list(resumen.items()), columns=['Métrica', 'Valor'])
      
        if df_resumen.empty:
            return None

        filename = f"variables_{codcas}_{periodo}.csv"
        return dcc.send_data_frame(df_resumen.to_csv, filename, index=False)

    dash_app.layout = serve_layout
    return dash_app
