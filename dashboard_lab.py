from dash import Dash, html, dcc, Input, Output, State
from flask import has_request_context
from flask_login import current_user
from sqlalchemy import text
import pandas as pd
import dash_bootstrap_components as dbc
import os


def create_dash_app(flask_app, url_base_pathname='/dashboard_lab_embed/'):
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

    # tipexacod de dwsge.sgss_emsea10 / sgss_emaea10:
    # '1' = Imagenes, '2' = Laboratorio clinico, '3' = Anatomia patologica
    TIPO_EXAMEN_LAB = '2'

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

        card_style = {**CARD_STYLE, "borderLeft": f"5px solid {border_color}", "height": "100%", "width": "100%"}
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

    def render_breakdown_table(dataframe, col_label, side_color):
        """Desglose Descripcion + Cantidad, mismo estilo que render_area_table
        de dashboard_proc.py."""
        th_style = {'padding': '6px 8px', 'fontSize': '11px', 'color': BRAND,
                    'fontWeight': '600', 'borderBottom': f'2px solid {BORDER}'}
        td_style = {'padding': '4px 8px', 'lineHeight': '1.1', 'fontSize': '11px'}
        if dataframe.empty:
            return dbc.Card(
                dbc.CardBody(
                    [html.H6(col_label, className="fw-semibold",
                             style={'fontSize': '11px', 'color': BRAND, 'letterSpacing': '0.6px', 'marginBottom': '8px'}),
                     html.P("Sin registros", className="text-muted mb-0",
                            style={'fontFamily': FONT_FAMILY, 'fontSize': '12px'})],
                    style={**CARD_BODY_STYLE, 'padding': '14px'}
                ),
                style={**CARD_STYLE, "borderLeft": f"5px solid {side_color}", "height": "100%"}
            )
        table_head = html.Thead([
            html.Tr([
                html.Th(col_label, style=th_style),
                html.Th('Cantidad', style={**th_style, 'textAlign': 'right'})
            ])
        ])
        table_body = html.Tbody([
            html.Tr([
                html.Td(str(r['descripcion']), style=td_style),
                html.Td(f"{r['total']:,.0f}", style={**td_style, 'textAlign': 'right', 'fontWeight': '600'})
            ])
            for _, r in dataframe.iterrows()
        ])
        return dbc.Card(
            dbc.CardBody(
                [dbc.Table([table_head, table_body], bordered=False, hover=True,
                           responsive=True, striped=True,
                           className="mb-0", style={'fontSize': '13px'})],
                style={**CARD_BODY_STYLE, 'padding': '14px'}
            ),
            style={**CARD_STYLE, "borderLeft": f"5px solid {side_color}", "height": "100%"}
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
                dcc.Location(id='url-lab', refresh=False),

                html.Div([
                    # ENCABEZADO
                    html.Div([
                        html.Div([
                            html.Div([
                                html.Div([
                                    html.I(className="bi bi-eyedropper", style={
                                        'fontSize': '26px',
                                        'color': BRAND,
                                        'marginRight': '10px'
                                    }),
                                    html.H2(
                                        ["Laboratorio Clínico - Exámenes ",
                                         html.Span("(En proceso de validación)", style={'color': '#dc3545'})],
                                        style={
                                            'fontFamily': FONT_FAMILY,
                                            'fontSize': '26px',
                                            'margin': '0',
                                            'fontWeight': '700',
                                            'color': BRAND,
                                            'lineHeight': '1.1'
                                        }
                                    ),
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
                        id='filter-anio-lab',
                        options=anio_options,
                        placeholder='Año',
                        clearable=True,
                        style={'width': '160px', 'fontFamily': FONT_FAMILY, 'position': 'relative', 'zIndex': 4000}
                    ),
                    dcc.Dropdown(
                        id='filter-periodo-lab',
                        options=[{'label': row['mes'], 'value': row['periodo']} for _, row in df_period.iterrows()],
                        placeholder='Periodo',
                        clearable=True,
                        style={'width': '240px', 'fontFamily': FONT_FAMILY, 'position': 'relative', 'zIndex': 1200}
                    ),
                    dcc.Dropdown(
                        id='filter-tipo-asegurado-lab',
                        options=tipo_asegurado_options,
                        value=DEFAULT_TIPO_ASEGURADO,
                        clearable=False,
                        style={'width': '200px', 'fontFamily': FONT_FAMILY, 'position': 'relative', 'zIndex': 1200}
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-search me-2"), "Buscar"],
                        id='search-button-lab',
                        color='primary',
                        className='dashboard-control-btn',
                        style={
                            'backgroundColor': BRAND, 'borderColor': BRAND, 'padding': '8px 12px',
                            'boxShadow': '0 4px 10px rgba(0,100,175,0.2)', 'fontFamily': FONT_FAMILY,
                            'fontWeight': '600', 'borderRadius': '8px'
                        }
                    ),
                    dcc.Loading(
                        id="loading-download-lab",
                        type="circle",
                        color=BRAND,
                        style={'display': 'inline-block'},
                        children=[
                            dbc.Button(
                                [html.I(className="bi bi-download me-2"), "Exportar CSV"],
                                id='download-button-lab',
                                color='success',
                                className='dashboard-control-btn',
                                style={
                                    'backgroundColor': '#28a745', 'borderColor': '#28a745', 'padding': '8px 12px',
                                    'boxShadow': '0 4px 10px rgba(40,167,69,0.18)', 'fontFamily': FONT_FAMILY,
                                    'fontWeight': '600', 'borderRadius': '8px'
                                }
                            ),
                            dcc.Download(id="download-dataframe-csv-lab"),
                        ]
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-arrow-left me-1"), "Volver"],
                        id="btn-volver-lab",
                        color='secondary',
                        outline=True,
                        className='dashboard-control-btn dashboard-control-btn-back',
                        href='javascript:history.back();',
                        external_link=True,
                        style={'marginLeft': 'auto', 'padding': '8px 12px'}
                    ),
                ], className='dashboard-control-bar', style={**CONTROL_BAR_STYLE}),
                dbc.Tooltip("Volver a la página anterior", target='btn-volver-lab', placement='bottom', style={'zIndex': 9999}),
                dbc.Tooltip("Buscar datos", target='search-button-lab', placement='bottom', style={'zIndex': 9999}),
                dbc.Tooltip("Descargar CSV", target='download-button-lab', placement='bottom', style={'zIndex': 9999}),

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
                                children=html.Div(id='summary-container-lab')
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
                                children=html.Div(id='charts-container-lab')
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
                id='unauth-back-button-lab',
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

    # Un examen = (acto_med, cod_arealab, cod_cpms) distinto; dw_lab_pat trae una
    # fila por linea de resultado (plantilla), por eso se deduplica antes de contar.
    # sgss_emaea10 se une por (tipexacod, areaexacod): areaexacod solo se repite
    # entre tipos de examen (p.ej. '1' = Radiologia / Bioquimica / Citologia), asi
    # que unir solo por areaexacod triplicaba las descripciones.
    def lab_base_cte(anio_str, periodo, codcas, codasegu_clause):
        return f"""
            WITH base AS (
                SELECT DISTINCT
                    COALESCE(e.sedexades, 'SIN SEDE (' || l.cod_sede || ')') AS sede,
                    COALESCE(a.arehosdes, 'SIN ÁREA (' || l.cod_area || ')') AS area,
                    COALESCE(al.areaexades, 'SIN TIPO (' || l.cod_arealab || ')') AS tipo_examen,
                    l.acto_med,
                    l.cod_arealab,
                    l.cod_cpms
                FROM dssge.dw_lab_pat_{anio_str}_{periodo} l
                INNER JOIN dwsge.sgss_emsea10 e
                        ON e.oricenasicod = l.cod_oricentro
                       AND e.cenasicod    = l.cod_centro
                       AND e.sedexacod    = l.cod_sede
                LEFT JOIN dwsge.sgss_cmaho10 a
                        ON a.arehoscod = l.cod_area
                LEFT JOIN dwsge.sgss_emaea10 al
                        ON al.tipexacod  = e.tipexacod
                       AND al.areaexacod = l.cod_arealab
                WHERE l.cod_centro = '{codcas}'
                  AND e.tipexacod = '{TIPO_EXAMEN_LAB}'
                  AND (
                        CASE
                            WHEN l.cod_tipo_paciente = '4' THEN '2'
                            ELSE '1'
                        END
                      ) IN {codasegu_clause}
            )
        """

    # ========== CALLBACK PRINCIPAL ==========
    @dash_app.callback(
        [Output('summary-container-lab', 'children'),
         Output('charts-container-lab', 'children')],
        Input('search-button-lab', 'n_clicks'),
        State('filter-periodo-lab', 'value'),
        State('filter-anio-lab', 'value'),
        State('filter-tipo-asegurado-lab', 'value'),
        State('url-lab', 'pathname')
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

        # Una sola pasada sobre la particion: el CTE base se reutiliza para el
        # total y los conteos por sede, area y tipo de examen.
        query = lab_base_cte(anio_str, periodo, codcas, codasegu_clause) + """
            SELECT 'total' AS dimension, 'TOTAL' AS descripcion, COUNT(*) AS total
            FROM (SELECT DISTINCT acto_med, cod_arealab, cod_cpms FROM base) t
            UNION ALL
            SELECT 'sede', sede, COUNT(*)
            FROM (SELECT DISTINCT sede, acto_med, cod_arealab, cod_cpms FROM base) t
            GROUP BY sede
            UNION ALL
            SELECT 'area', area, COUNT(*)
            FROM (SELECT DISTINCT area, acto_med, cod_arealab, cod_cpms FROM base) t
            GROUP BY area
            UNION ALL
            SELECT 'tipo', tipo_examen, COUNT(*)
            FROM (SELECT DISTINCT tipo_examen, acto_med, cod_arealab, cod_cpms FROM base) t
            GROUP BY tipo_examen
        """

        df = pd.read_sql(query, engine)
        total_examenes = int(df.loc[df['dimension'] == 'total', 'total'].sum()) if not df.empty else 0
        if total_examenes == 0:
            return html.Div([
                html.I(className="bi bi-inbox", style={
                    'fontSize': '64px', 'color': MUTED, 'marginBottom': '20px'
                }),
                html.H4("Sin registros", style={
                    'color': TEXT, 'fontFamily': FONT_FAMILY, 'marginBottom': '10px'
                }),
                html.P("No hay exámenes de laboratorio para el año y periodo seleccionados.", style={
                    'color': MUTED, 'fontFamily': FONT_FAMILY
                }),
                html.P(f"Centro: {codcas} | Año: {anio_str} | Periodo: {periodo}", style={
                    'color': MUTED, 'fontFamily': FONT_FAMILY, 'fontSize': '12px'
                })
            ], style={
                'textAlign': 'center', 'padding': '60px', 'backgroundColor': CARD_BG,
                'borderRadius': '16px', 'boxShadow': '0 10px 30px rgba(0,0,0,0.08)'
            }), html.Div()

        # cenasicod no es unico en sgss_cmcas10 (p.ej. '422'), por eso se acota
        # con el cod_oricentro que trae la propia particion.
        nombre_centro = codcas
        try:
            with engine.connect() as connection:
                row = connection.execute(
                    text(f"""
                        SELECT ca.cenasides
                        FROM dwsge.sgss_cmcas10 ca
                        WHERE ca.cenasicod = :c
                          AND ca.oricenasicod IN (
                              SELECT l.cod_oricentro
                              FROM dssge.dw_lab_pat_{anio_str}_{periodo} l
                              WHERE l.cod_centro = :c
                              LIMIT 1
                          )
                        LIMIT 1
                    """),
                    {'c': codcas}
                ).first()
            if row and row[0]:
                nombre_centro = row[0]
        except Exception as exc:
            print(f"Failed to fetch cenasides: {exc}")
        subtitle = f"Año {anio_str} | Periodo {periodo} | {nombre_centro}"

        def dim(nombre):
            return (
                df[df['dimension'] == nombre][['descripcion', 'total']]
                .sort_values('total', ascending=False)
                .reset_index(drop=True)
            )

        df_sede = dim('sede')
        df_area = dim('area')
        df_tipo = dim('tipo')

        # === Tarjeta de total + tabla de desglose (mismo layout que dashboard_proc) ===
        # Un examen puede figurar en mas de una sede, por eso la suma de la tabla
        # de sedes puede superar el total; area y tipo de examen si suman exacto.
        secciones = [
            ("EXÁMENES POR SEDE", BRAND, "bi-building", 'Sede', df_sede),
            ("EXÁMENES POR ÁREA", ACCENT, "bi-hospital", 'Área', df_area),
            ("EXÁMENES POR TIPO DE EXAMEN", '#6f42c1', "bi-clipboard2-pulse", 'Tipo de examen', df_tipo),
        ]

        summary_row = dbc.Container([
            dbc.Row(
                [
                    dbc.Col(
                        render_card(titulo, f"{total_examenes:,.0f}", color, subtitle, icon=icon),
                        width=12, lg=4,
                        style={'display': 'flex'}
                    ),
                    dbc.Col(
                        html.Div(render_breakdown_table(df_dim, col_label, color), style={'width': '100%'}),
                        width=12, lg=4,
                        style={'display': 'flex'}
                    ),
                ],
                justify="center",
                style={'marginBottom': '10px'}
            )
            for titulo, color, icon, col_label, df_dim in secciones
        ], fluid=True)

        return summary_row, html.Div()

    # ========== CALLBACK DESCARGA CSV ==========
    @dash_app.callback(
        Output("download-dataframe-csv-lab", "data"),
        Input("download-button-lab", "n_clicks"),
        State('filter-periodo-lab', 'value'),
        State('filter-anio-lab', 'value'),
        State('filter-tipo-asegurado-lab', 'value'),
        State('url-lab', 'pathname'),
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

        # Un registro por examen (sin las lineas de resultado de la plantilla)
        query = f"""
            SELECT DISTINCT
                l.anio,
                l.periodo,
                l.cod_centro,
                l.cod_sede,
                e.sedexades AS sede,
                l.cod_area,
                a.arehosdes AS area,
                l.cod_servicio,
                l.cod_arealab,
                al.areaexades AS tipo_examen,
                l.cod_cpms,
                l.acto_med::text AS acto_med,
                l.fecha_examen,
                l.cod_tipo_paciente,
                l.tipo_doc_paciente,
                l.doc_paciente,
                l.sexo,
                l.anio_edad
            FROM dssge.dw_lab_pat_{anio_str}_{periodo} l
            INNER JOIN dwsge.sgss_emsea10 e
                    ON e.oricenasicod = l.cod_oricentro
                   AND e.cenasicod    = l.cod_centro
                   AND e.sedexacod    = l.cod_sede
            LEFT JOIN dwsge.sgss_cmaho10 a
                    ON a.arehoscod = l.cod_area
            LEFT JOIN dwsge.sgss_emaea10 al
                    ON al.tipexacod  = e.tipexacod
                   AND al.areaexacod = l.cod_arealab
            WHERE l.cod_centro = '{codcas}'
              AND e.tipexacod = '{TIPO_EXAMEN_LAB}'
              AND (
                    CASE
                        WHEN l.cod_tipo_paciente = '4' THEN '2'
                        ELSE '1'
                    END
                  ) IN {codasegu_clause}
            ORDER BY fecha_examen, acto_med
        """
        df = pd.read_sql(query, engine)
        if df.empty:
            return None
        df = df.astype(str)
        filename = f"examenes_laboratorio_{codcas}_{anio_str}_{periodo}.csv"
        return dcc.send_data_frame(df.to_csv, filename, index=False)

    dash_app.layout = serve_layout
    return dash_app
