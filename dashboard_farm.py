from dash import Dash, html, dcc, Input, Output, State
from flask import has_request_context
from flask_login import current_user
from sqlalchemy import text
import pandas as pd
import dash_bootstrap_components as dbc
import os
from urllib.parse import quote_plus


def create_dash_app(flask_app, url_base_pathname='/dashboard_farm_embed/'):
    external_stylesheets = [
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
    ]

    # Paleta y estilos consistentes con el resto de dashboards
    BRAND = "#0064AF"
    BRAND_SOFT = "#D7E9FF"
    ACCENT = "#00AEEF"
    CARD_BG = "#FFFFFF"
    TEXT = "#1C1F26"
    MUTED = "#6B7280"
    BORDER = "#E5E7EB"
    FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"

    # Color fijo por area (dwsge.sgss_cmaho10.arehoscod), solo para el acento
    # de las tarjetas: no es un grafico categorico multi-serie, asi que no
    # requiere la validacion CVD del resto de dashboards.
    AREA_COLORS = {
        '01': '#0064AF',  # Consulta Externa
        '02': '#dc3545',  # Urgencias / Emergencia
        '03': '#28a745',  # Hospitalizacion
        '04': '#6f42c1',  # Ayuda al Diagnostico
        '05': '#fd7e14',  # Centro Quirurgico
        '06': '#e83e8c',  # Centro Obstetrico
        '07': '#17a2b8',  # Unidad de Cuidados Intensivos
        '08': '#20c997',  # Unidad de Cuidados Intermedios
        '09': '#ffc107',  # Hospital de Dia
        '11': '#6610f2',  # Unidad de Cuidados Coronarios
        '13': '#795548',  # Atencion Domiciliaria
        '15': '#8d6e63',  # Produccion
        '19': '#6c757d',  # Areas Administrativas
    }

    CARD_STYLE = {
        "cursor": "default",
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
        "borderTopLeftRadius": "14px",
        "borderTopRightRadius": "14px",
        "borderBottomLeftRadius": "14px",
        "borderBottomRightRadius": "14px",
        "boxShadow": "0 4px 10px rgba(0,0,0,0.05)",
        "backdropFilter": "blur(3px)",
        "overflow": "visible",
        "position": "relative",
        "zIndex": 1100,
    }

    # Use a unique name for the Dash instance to avoid conflicts when mounting multiple apps on the same Flask server
    app_name = f"dash_{url_base_pathname.strip('/').replace('/', '_') or 'alt'}"

    # asegurar carpeta de assets correcta (assets junto a este archivo) y assets_url_path consistente
    assets_path = os.path.join(os.path.dirname(__file__), "assets")
    assets_url_path = f"{url_base_pathname.rstrip('/')}/assets"

    dash_app = Dash(
        name=app_name,
        server=flask_app,
        url_base_pathname=url_base_pathname,
        assets_folder=assets_path,
        assets_url_path=assets_url_path,
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
    )

    dash_app.title = "SIEST"

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

    def render_card(title, value, border_color, subtitle_text, icon=None, extra_style=None):
        header_children = []
        if icon:
            header_children.append(html.I(className=f"bi {icon} me-2", style={'color': border_color}))
        header_children.append(title)

        card_style = {**CARD_STYLE, "borderLeft": f"5px solid {border_color}", "height": "100%"}
        if extra_style:
            card_style.update(extra_style)

        return dbc.Card(
            dbc.CardBody([
                html.H5(header_children, className="card-title", style={
                    'color': BRAND, 'marginBottom': '6px', 'fontFamily': FONT_FAMILY,
                    'letterSpacing': '-0.1px', 'display': 'flex', 'alignItems': 'center'
                }),
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

        fecha_col_value = row.get('fecha_act') if row else None
        if not fecha_col_value:
            return None
        return fecha_col_value

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
                dcc.Location(id='url-farm', refresh=False),

                html.Div([
                    # ENCABEZADO
                    html.Div([
                        html.Div([
                            html.Div([
                                html.Div([
                                    html.I(className="bi bi-capsule", style={
                                        'fontSize': '26px',
                                        'color': BRAND,
                                        'marginRight': '10px'
                                    }),
                                    html.H2(
                                        "Farmacia - Recetas Atendidas",
                                        style={
                                            'fontFamily': FONT_FAMILY,
                                            'fontSize': '26px',
                                            'margin': '0',
                                            'fontWeight': '700',
                                            'color': BRAND,
                                            'lineHeight': '1.1'
                                        }
                                    )
                                ], style={'display': 'flex', 'alignItems': 'center'}),
                            ], style={
                                'display': 'flex',
                                'alignItems': 'center',
                                'justifyContent': 'flex-start',
                                'gap': '12px',
                                'flexWrap': 'nowrap',
                                'width': '100%'
                            }),
                            html.Div([
                                html.Span(
                                    [html.I(className="bi bi-clock me-1"), f"Actualizado: {fecha_act_value}"],
                                    style={
                                        'backgroundColor': BRAND_SOFT,
                                        'color': BRAND,
                                        'fontFamily': FONT_FAMILY,
                                        'fontSize': '11px',
                                        'fontWeight': '600',
                                        'padding': '3px 10px',
                                        'borderRadius': '999px',
                                        'display': 'inline-flex',
                                        'alignItems': 'center',
                                        'gap': '4px',
                                    }
                                ),
                                html.Span(
                                    "Sistema de Gestión Estadística",
                                    style={
                                        'color': MUTED,
                                        'fontFamily': FONT_FAMILY,
                                        'fontSize': '12px',
                                    }
                                ),
                            ], style={'display': 'flex', 'alignItems': 'center', 'gap': '10px', 'marginTop': '6px'})
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
                        id='filter-anio-farm',
                        options=anio_options,
                        placeholder='Año',
                        clearable=True,
                        style={'width': '160px', 'fontFamily': FONT_FAMILY, 'position': 'relative', 'zIndex': 4000}
                    ),
                    dcc.Dropdown(
                        id='filter-periodo-farm',
                        options=[{'label': row['mes'], 'value': row['periodo']} for _, row in df_period.iterrows()],
                        placeholder='Periodo',
                        clearable=True,
                        style={'width': '240px', 'fontFamily': FONT_FAMILY, 'position': 'relative', 'zIndex': 1200}
                    ),
                    dcc.Dropdown(
                        id='filter-tipo-asegurado-farm',
                        options=tipo_asegurado_options,
                        value=DEFAULT_TIPO_ASEGURADO,
                        clearable=False,
                        style={'width': '200px', 'fontFamily': FONT_FAMILY, 'position': 'relative', 'zIndex': 1200}
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-search me-2"), "Buscar"],
                        id='search-button-farm',
                        color='primary',
                        className='dashboard-control-btn',
                        style={
                            'backgroundColor': BRAND, 'borderColor': BRAND, 'padding': '8px 12px',
                            'boxShadow': '0 4px 10px rgba(0,100,175,0.2)', 'fontFamily': FONT_FAMILY,
                            'fontWeight': '600', 'borderRadius': '8px'
                        }
                    ),
                    dcc.Loading(
                        id="loading-download-farm",
                        type="circle",
                        color=BRAND,
                        style={'display': 'inline-block'},
                        children=[
                            dbc.Button(
                                [html.I(className="bi bi-download me-2"), "Exportar CSV"],
                                id='download-button-farm',
                                color='success',
                                className='dashboard-control-btn',
                                style={
                                    'backgroundColor': '#28a745', 'borderColor': '#28a745', 'padding': '8px 12px',
                                    'boxShadow': '0 4px 10px rgba(40,167,69,0.18)', 'fontFamily': FONT_FAMILY,
                                    'fontWeight': '600', 'borderRadius': '8px'
                                }
                            ),
                            dcc.Download(id="download-dataframe-csv-farm"),
                        ]
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-arrow-left me-1"), "Volver"],
                        id="btn-volver-farm",
                        color='secondary',
                        outline=True,
                        className='dashboard-control-btn dashboard-control-btn-back',
                        href='javascript:history.back();',
                        external_link=True,
                        style={'marginLeft': 'auto', 'padding': '8px 12px'}
                    ),
                ], className='dashboard-control-bar', style={**CONTROL_BAR_STYLE}),
                dbc.Tooltip("Volver a la página anterior", target='btn-volver-farm', placement='bottom', style={'zIndex': 9999}),
                dbc.Tooltip("Buscar datos", target='search-button-farm', placement='bottom', style={'zIndex': 9999}),
                dbc.Tooltip("Descargar Excel", target='download-button-farm', placement='bottom', style={'zIndex': 9999}),

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
                                children=html.Div(id='summary-container-farm')
                            ),
                            className='dashboard-loading-shell'
                        ),
                        width=12
                    )
                ]),
                dbc.Row([
                    dbc.Col(
                        html.Div(
                            dcc.Loading(
                                className='dashboard-loading-inline',
                                parent_className='dashboard-loading-parent',
                                parent_style={'width': '100%'},
                                type='default',
                                style={'width': '100%'},
                                children=html.Div(id='charts-container-farm')
                            ),
                            className='dashboard-loading-shell'
                        ),
                        width=12
                    )
                ], style={'marginTop': '16px', 'marginBottom': '24px'}),

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
                id='unauth-back-button-farm',
                color='primary',
                href='javascript:history.back();',
                external_link=True,
                style={'marginTop': '12px'}
            )
        ])

    # ========== CONEXIÓN DB ==========
    def create_connection():
        from extensions import get_dw_engine
        return get_dw_engine()

    # ========== CALLBACK PRINCIPAL ==========
    @dash_app.callback(
        [Output('summary-container-farm', 'children'),
         Output('charts-container-farm', 'children')],
        Input('search-button-farm', 'n_clicks'),
        State('filter-periodo-farm', 'value'),
        State('filter-anio-farm', 'value'),
        State('filter-tipo-asegurado-farm', 'value'),
        State('url-farm', 'pathname')
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
                    'fontSize': '64px', 'color': '#ffc107', 'marginBottom': '20px'
                }),
                html.H4("Información requerida", style={
                    'color': TEXT, 'fontFamily': FONT_FAMILY, 'marginBottom': '10px'
                }),
                html.P("Por favor, seleccione un año y un periodo y asegúrese de tener un centro válido.", style={
                    'color': MUTED, 'fontFamily': FONT_FAMILY
                })
            ], style={
                'textAlign': 'center', 'padding': '60px', 'backgroundColor': CARD_BG,
                'borderRadius': '16px', 'boxShadow': '0 10px 30px rgba(0,0,0,0.08)'
            }), html.Div()

        from extensions import validate_anio_periodo
        try:
            anio_str, periodo = validate_anio_periodo(anio, periodo)
        except ValueError as _ve:
            return html.Div(f"Parámetros inválidos: {_ve}"), html.Div()

        tipo_filter = tipo_asegurado or DEFAULT_TIPO_ASEGURADO
        codasegu_clause = resolve_tipo_asegurado_clause(tipo_filter)

        engine = create_connection()
        if engine is None:
            return html.Div("Error de conexión a la base de datos."), html.Div()

        # Recetas atendidas por area: cod_area se mapea a su descripcion via
        # dwsge.sgss_cmaho10 (misma tabla de dimension de area usada en el
        # resto de dashboards). cenasides sale del join a sgss_cmcas10 para
        # mostrar el nombre del centro en el subtitulo de las tarjetas.
        query = f"""
            SELECT
                f.cod_area,
                COALESCE(a.arehosdes, 'SIN ÁREA (' || f.cod_area || ')') AS area,
                ca.cenasides,
                COUNT(*) AS recetas
            FROM dssge.dw_farm_{anio_str}_{periodo} f
            LEFT JOIN dwsge.sgss_cmaho10 a ON a.arehoscod = f.cod_area
            LEFT JOIN dwsge.sgss_cmcas10 ca
                ON ca.oricenasicod = f.cod_oricentro AND ca.cenasicod = f.cod_centro
            WHERE f.cod_centro = '{codcas}'
                AND (
                        CASE
                            WHEN f.cod_tipo_paciente = '4' THEN '2'
                            ELSE '1'
                        END
                    ) IN {codasegu_clause}
                AND cant_atendida > 0
            GROUP BY f.cod_area, a.arehosdes, ca.cenasides
            ORDER BY recetas DESC
        """

        df = pd.read_sql(query, engine)
        if df.empty:
            return html.Div([
                html.I(className="bi bi-inbox", style={
                    'fontSize': '64px', 'color': MUTED, 'marginBottom': '20px'
                }),
                html.H4("Sin registros", style={
                    'color': TEXT, 'fontFamily': FONT_FAMILY, 'marginBottom': '10px'
                }),
                html.P("No hay recetas atendidas para el año y periodo seleccionados.", style={
                    'color': MUTED, 'fontFamily': FONT_FAMILY
                }),
                html.P(f"Centro: {codcas} | Año: {anio_str} | Periodo: {periodo}", style={
                    'color': MUTED, 'fontFamily': FONT_FAMILY, 'fontSize': '12px'
                })
            ], style={
                'textAlign': 'center', 'padding': '60px', 'backgroundColor': CARD_BG,
                'borderRadius': '16px', 'boxShadow': '0 10px 30px rgba(0,0,0,0.08)'
            }), html.Div()

        nombre_centro_series = df['cenasides'].dropna().unique()
        nombre_centro = nombre_centro_series[0] if len(nombre_centro_series) > 0 else codcas
        subtitle = f"Año {anio_str} | Periodo {periodo} | {nombre_centro}"

        total_recetas = int(df['recetas'].sum())

        # === Tarjetas resumen ===
        summary_cards = [
            render_card(
                title="RECETAS ATENDIDAS (TOTAL)",
                value=f"{total_recetas:,.0f}",
                border_color=BRAND,
                subtitle_text=subtitle,
                icon="bi-capsule",
            ),
        ]

        for _, row in df.iterrows():
            summary_cards.append(render_card(
                title=row['area'],
                value=f"{row['recetas']:,.0f}",
                border_color=AREA_COLORS.get(row['cod_area'], BRAND),
                subtitle_text=subtitle,
                icon="bi-capsule",
            ))

        summary_row = dbc.Container(
            [
                dbc.Row(
                    dbc.Col(html.Div(card, style={'width': '100%'}), width=12, lg=8,
                             style={'display': 'flex'}),
                    justify="center",
                    style={'marginBottom': '16px'}
                )
                for card in summary_cards
            ],
            fluid=True,
        )

        return summary_row, html.Div()

    # ========== CALLBACK DESCARGA CSV ==========
    @dash_app.callback(
        Output("download-dataframe-csv-farm", "data"),
        Input("download-button-farm", "n_clicks"),
        State('filter-periodo-farm', 'value'),
        State('filter-anio-farm', 'value'),
        State('filter-tipo-asegurado-farm', 'value'),
        State('url-farm', 'pathname'),
        prevent_initial_call=True
    )
    def download_csv(n_clicks, periodo, anio, tipo_asegurado, pathname):
        from extensions import is_consulta_user
        if is_consulta_user():
            return None
        if not n_clicks or not periodo or not anio or not pathname:
            return None

        import secure_code as sc
        codcas_encoded = pathname.rstrip('/').split('/')[-1] if pathname else None
        codcas = sc.decode_code(codcas_encoded) if codcas_encoded else None
        if not codcas:
            return None

        from extensions import validate_anio_periodo
        try:
            anio_str, periodo = validate_anio_periodo(anio, periodo)
        except ValueError:
            return None

        tipo_filter = tipo_asegurado or DEFAULT_TIPO_ASEGURADO
        codasegu_clause = resolve_tipo_asegurado_clause(tipo_filter)

        engine = create_connection()
        if engine is None:
            return None

        query = f"""
            SELECT
                f.anio,
                f.periodo,
                f.cod_centro,
                ca.cenasides,
                f.cod_area,
                a.arehosdes AS area,
                f.cod_topico,
                f.cod_servicio,
                s.servhosdes AS servicio,
                f.cod_actividad,
                f.cod_subactividad,
                f.num_actomed,
                f.dni_profesional,
                f.cmp,
                f.fecha_solicitud,
                f.num_receta,
                f.cod_medicamento,
                f.cant_solicitud,
                f.cant_atendida,
                f.unidad,
                f.duracion_med,
                f.cod_dx,
                f.dni,
                f.sexo,
                f.edad_anio,
                f.meses,
                f.dias,
                f.cod_farmacia,
                f.fecha_despacho,
                f.hora_despacho,
                f.numrecetmanual,
                f.precio,
                f.cod_tipo_seguro,
                f.cod_tipo_parentesco,
                f.cod_tipo_paciente,
                f.cod_prioridad,
                f.tipo_movimiento
            FROM dssge.dw_farm_{anio_str}_{periodo} f
            LEFT JOIN dwsge.sgss_cmaho10 a ON a.arehoscod = f.cod_area
            LEFT JOIN dwsge.sgss_cmsho10 s ON s.servhoscod = f.cod_servicio
            LEFT JOIN dwsge.sgss_cmcas10 ca
                ON ca.oricenasicod = f.cod_oricentro AND ca.cenasicod = f.cod_centro
            WHERE f.cod_centro = '{codcas}'
                AND (
                        CASE
                            WHEN f.cod_tipo_paciente = '4' THEN '2'
                            ELSE '1'
                        END
                    ) IN {codasegu_clause}
                AND cant_atendida > 0
            ORDER BY f.fecha_despacho, f.num_receta
        """
        df = pd.read_sql(query, engine)
        if df.empty:
            return None
        df = df.astype(str)
        filename = f"recetas_atendidas_{codcas}_{anio_str}_{periodo}.csv"
        return dcc.send_data_frame(df.to_csv, filename, index=False)

    dash_app.layout = serve_layout
    return dash_app
