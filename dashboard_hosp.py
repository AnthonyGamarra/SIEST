from dash import Dash, html, dcc, Input, Output, State
from flask import has_request_context
from flask_login import current_user
from sqlalchemy import create_engine, text
import pandas as pd
import dash_bootstrap_components as dbc
import plotly.express as px
from datetime import date
import os
import threading


def create_dash_app(flask_app, url_base_pathname='/dashboard_hosp/'):
    external_stylesheets = [
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
    ]

    BRAND = "#0064AF"
    BRAND_SOFT = "#D7E9FF"
    ACCENT = "#00AEEF"
    CARD_BG = "#FFFFFF"
    TEXT = "#1C1F26"
    MUTED = "#6B7280"
    BORDER = "#E5E7EB"
    FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"

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
        "borderRadius": "14px",
        "boxShadow": "0 4px 10px rgba(0,0,0,0.05)",
        "backdropFilter": "blur(3px)",
        "overflow": "visible",
        "position": "relative",
        "zIndex": 1100,
    }

    app_name = f"dash_{url_base_pathname.strip('/').replace('/', '_') or 'hosp'}"
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

    dash_app.title = "SIEST - Hospitalización"

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

    def resolve_tipo_asegurado_clause(selection):
        normalized = selection if selection in TIPO_ASEGURADO_SQL else DEFAULT_TIPO_ASEGURADO
        return TIPO_ASEGURADO_SQL[normalized]

    def render_card(title, value, border_color, subtitle_text, icon=None):
        return dbc.Card(
            dbc.CardBody([
                html.Div([
                    html.I(className=f"bi {icon}", style={
                        'fontSize': '22px', 'color': border_color, 'marginRight': '8px'
                    }) if icon else None,
                    html.H5(
                        title,
                        className="card-title",
                        style={
                            'color': BRAND,
                            'marginBottom': '6px',
                            'fontFamily': FONT_FAMILY,
                            'letterSpacing': '-0.1px'
                        }
                    )
                ], style={'display': 'flex', 'alignItems': 'center'}),
                html.H2(value, style={
                    'fontWeight': '800', 'color': TEXT, 'fontSize': '34px', 'margin': 0,
                    'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.2px'
                }),
                html.P(subtitle_text, style={
                    'fontSize': '12px', 'color': MUTED, 'margin': '6px 0 0 0', 'fontFamily': FONT_FAMILY
                })
            ], style=CARD_BODY_STYLE),
            style={**CARD_STYLE, "borderLeft": f"5px solid {border_color}", "height": "100%"}
        )

    def render_chart_card(figure, title):
        return dbc.Card(
            dbc.CardBody([
                html.H6(title, style={
                    'color': BRAND, 'fontFamily': FONT_FAMILY,
                    'fontWeight': '600', 'marginBottom': '12px'
                }),
                dcc.Graph(figure=figure, config={'displayModeBar': False},
                          style={'height': '320px'})
            ], style=CARD_BODY_STYLE),
            style={**CARD_STYLE}
        )

    def render_table_card(title, dataframe, col_label, col_value='Egresos', extra_cols=None):
        extra_cols = extra_cols or []
        td_style = {'padding': '5px 8px', 'lineHeight': '1.2', 'fontSize': '12px', 'fontFamily': FONT_FAMILY}
        th_style = {'fontSize': '12px', 'fontFamily': FONT_FAMILY, 'padding': '5px 8px', 'color': BRAND}
        if dataframe is None or dataframe.empty:
            body = html.P("Sin registros", className="text-muted mb-0",
                          style={'fontFamily': FONT_FAMILY, 'fontSize': '12px'})
        else:
            rows = [
                html.Tr([
                    html.Td(str(r[col_label]), style=td_style),
                    *[html.Td(str(r[c]), style=td_style) for c in extra_cols],
                    html.Td(f"{r[col_value]:,.0f}", style={**td_style, 'textAlign': 'right', 'fontWeight': '600'})
                ])
                for _, r in dataframe.iterrows()
            ]
            body = dbc.Table(
                [
                    html.Thead(html.Tr([
                        html.Th(col_label, style=th_style),
                        *[html.Th(c, style=th_style) for c in extra_cols],
                        html.Th(col_value, style={**th_style, 'textAlign': 'right'}),
                    ])),
                    html.Tbody(rows)
                ],
                bordered=False, hover=True, responsive=True,
                striped=True, className="mb-0"
            )
        return dbc.Card(
            dbc.CardBody([
                html.H6(title, style={
                    'color': BRAND, 'fontFamily': FONT_FAMILY,
                    'fontWeight': '600', 'marginBottom': '12px'
                }),
                html.Div(body, style={'maxHeight': '340px', 'overflowY': 'auto'})
            ], style=CARD_BODY_STYLE),
            style={**CARD_STYLE}
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
        fecha_col_value = row.get('fecha_act') or row.get('fecha_Act') if row else None
        return fecha_col_value

    # ========== LAYOUT ==========
    def serve_layout():
        if not has_request_context():
            return html.Div()

        if getattr(current_user, "is_authenticated", False):
            engine = create_connection()
            fecha_act_value = fecha_act(engine) or "Sin información disponible"
            return dbc.Container([
                dcc.Location(id='url-hosp', refresh=False),

                html.Div([
                    # ENCABEZADO
                    html.Div([
                        html.Div([
                            html.Img(
                                src=dash_app.get_asset_url('logo.png'),
                                style={
                                    'width': '120px', 'height': '60px',
                                    'objectFit': 'contain', 'marginRight': '20px'
                                }
                            ),
                            html.Div([
                                html.Div([
                                    html.I(className="bi bi-hospital-fill", style={
                                        'fontSize': '32px', 'color': BRAND, 'marginRight': '12px'
                                    }),
                                    html.H2(
                                        "Hospitalización - Egresos",
                                        style={
                                            'color': BRAND, 'fontFamily': FONT_FAMILY,
                                            'fontSize': '26px', 'margin': '0', 'fontWeight': '700'
                                        }
                                    )
                                ], style={'display': 'flex', 'alignItems': 'center'}),
                                html.Div([
                                    html.Span(
                                        [html.I(className="bi bi-clock me-1"), f"Actualizado: {fecha_act_value}"],
                                        style={
                                            'backgroundColor': BRAND_SOFT, 'color': BRAND,
                                            'fontFamily': FONT_FAMILY, 'fontSize': '11px',
                                            'fontWeight': '600', 'padding': '3px 10px',
                                            'borderRadius': '999px', 'display': 'inline-flex',
                                            'alignItems': 'center', 'gap': '4px',
                                        }
                                    ),
                                    html.Span(
                                        "Sistema de Gestión Estadística",
                                        style={'color': MUTED, 'fontFamily': FONT_FAMILY, 'fontSize': '12px'}
                                    ),
                                ], style={'display': 'flex', 'alignItems': 'center', 'gap': '10px', 'marginTop': '6px'})
                            ], style={
                                'display': 'flex', 'flexDirection': 'column',
                                'justifyContent': 'center', 'flex': '1'
                            })
                        ], style={
                            'display': 'flex', 'alignItems': 'center',
                            'padding': '16px 20px', 'backgroundColor': CARD_BG,
                            'borderRadius': '14px', 'boxShadow': '0 8px 20px rgba(0,0,0,0.08)',
                            'gap': '20px'
                        }),
                        html.Br(),
                    ]),

                    # FILTROS + BOTONES
                    html.Div([
                        html.I(className="bi bi-calendar-week dashboard-control-icon", style={
                            'fontSize': '20px', 'color': BRAND, 'marginRight': '10px'
                        }),
                        dcc.Dropdown(
                            id='filter-anio-hosp',
                            options=anio_options,
                            placeholder='Año',
                            clearable=True,
                            style={'width': '160px', 'fontFamily': FONT_FAMILY,
                                   'position': 'relative', 'zIndex': 4000}
                        ),
                        dcc.Dropdown(
                            id='filter-periodo-hosp',
                            options=[{'label': row['mes'], 'value': row['periodo']} for _, row in df_period.iterrows()],
                            placeholder='Periodo',
                            clearable=True,
                            style={'width': '240px', 'fontFamily': FONT_FAMILY,
                                   'position': 'relative', 'zIndex': 1200}
                        ),
                        dcc.Dropdown(
                            id='filter-tipo-asegurado-hosp',
                            options=tipo_asegurado_options,
                            value=DEFAULT_TIPO_ASEGURADO,
                            clearable=False,
                            style={'width': '200px', 'fontFamily': FONT_FAMILY,
                                   'position': 'relative', 'zIndex': 1200}
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-search me-2"), "Buscar"],
                            id='search-button-hosp',
                            color='primary',
                            className='dashboard-control-btn',
                            style={
                                'backgroundColor': BRAND, 'borderColor': BRAND,
                                'padding': '8px 12px', 'boxShadow': '0 4px 10px rgba(0,100,175,0.2)',
                                'fontFamily': FONT_FAMILY, 'fontWeight': '600', 'borderRadius': '8px'
                            }
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-download me-2"), "Exportar CSV"],
                            id='download-button-hosp',
                            color='success',
                            className='dashboard-control-btn',
                            style={
                                'backgroundColor': '#28a745', 'borderColor': '#28a745',
                                'padding': '8px 12px', 'boxShadow': '0 4px 10px rgba(40,167,69,0.18)',
                                'fontFamily': FONT_FAMILY, 'fontWeight': '600', 'borderRadius': '8px'
                            }
                        ),
                        dcc.Download(id="download-hosp-csv"),
                        dbc.Button(
                            [html.I(className="bi bi-arrow-left me-1"), "Volver"],
                            id="btn-volver-hosp",
                            color='secondary',
                            outline=True,
                            className='dashboard-control-btn dashboard-control-btn-back',
                            href='javascript:history.back();',
                            external_link=True,
                            style={'marginLeft': 'auto', 'padding': '8px 12px'}
                        ),
                    ], className='dashboard-control-bar', style={**CONTROL_BAR_STYLE}),
                    dbc.Tooltip("Volver a la página anterior", target='btn-volver-hosp', placement='bottom', style={'zIndex': 9999}),
                    dbc.Tooltip("Buscar datos", target='search-button-hosp', placement='bottom', style={'zIndex': 9999}),
                    dbc.Tooltip("Descargar CSV", target='download-button-hosp', placement='bottom', style={'zIndex': 9999}),

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
                                    children=html.Div(id='summary-container-hosp')
                                ),
                                className='dashboard-loading-shell'
                            ),
                            width=12
                        )
                    ]),
                    html.Div(id='charts-container-hosp', style={'display': 'none'}),

                ], id='main-hosp-content'),

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
                id='unauth-back-button-hosp',
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
        nonlocal _engine, _engine_lock

        if _engine_lock is None:
            _engine_lock = threading.Lock()

        with _engine_lock:
            if _engine is not None:
                try:
                    with _engine.connect() as conn:
                        pass
                    return _engine
                except Exception:
                    _engine = None

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
                    with engine.connect() as conn:
                        pass
                    _engine = engine
                    return _engine
                except Exception as e:
                    print(f"[Dashboard HOSP] Intento {attempt + 1}/{max_retries} - Failed to connect: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(1 * (attempt + 1))
                    else:
                        print("[Dashboard HOSP] No se pudo establecer conexión después de todos los reintentos")
                        return None

    # ========== CALLBACK PRINCIPAL ==========
    @dash_app.callback(
        [Output('summary-container-hosp', 'children'),
         Output('charts-container-hosp', 'children')],
        Input('search-button-hosp', 'n_clicks'),
        State('filter-periodo-hosp', 'value'),
        State('filter-anio-hosp', 'value'),
        State('filter-tipo-asegurado-hosp', 'value'),
        State('url-hosp', 'pathname')
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
                'textAlign': 'center', 'padding': '60px',
                'backgroundColor': CARD_BG, 'borderRadius': '16px',
                'boxShadow': '0 10px 30px rgba(0,0,0,0.08)'
            }), html.Div()

        anio_str = str(anio)
        tipo_filter = tipo_asegurado or DEFAULT_TIPO_ASEGURADO
        codasegu_clause = resolve_tipo_asegurado_clause(tipo_filter)

        engine = create_connection()
        if engine is None:
            return html.Div("Error de conexión a la base de datos."), html.Div()

        query = f"""
            select
                ca.redasiscod,
                r.redasisdes,
                ce.cod_centro,
                ce.periodo,
                ce.anio,
                ce.cod_servicio,
                c.servhosdes AS servicio,
                ce.cod_actividad,
                am.actdes AS actividad,
                ce.cod_estacion,
                enf.estenfdes,
                ce.anio_edad,
                ce.sexo,
                ce.cod_tip_seguro,
                ts.tipsegdes as tipo_seguro,
                ce.cod_tipo_paciente,
                tp.tipopacinom as tipo_paciente,
                ce.fec_ingr,
                ce.fec_altmed,
                ce.fec_egreso,
                ce.dias_hospit,
                ce.cuarto,
                ce.cama,
                ce.diag_cod,
                d.diagdes,
                d.edxcapdes AS capitulo
            from dwsge.dwe_hosp_egresos_{anio_str}_{periodo} ce
            LEFT JOIN dwsge.sgss_cmdia10_chapter d ON ce.diag_cod = d.diagcod
            LEFT JOIN dwsge.sgss_cmsho10 AS c ON ce.cod_servicio = c.servhoscod
            LEFT JOIN dwsge.sgss_cmcas10 AS ca ON ce.cod_oricentro = ca.oricenasicod AND ce.cod_centro = ca.cenasicod
            LEFT JOIN dwsge.sgss_cmact10 AS am ON ce.cod_actividad = am.actcod
            LEFT JOIN dwsge.sgss_cmras10 r ON ca.redasiscod = r.redasiscod
            LEFT JOIN dwsge.sgss_cmtse10 ts ON ts.tipsegcod = ce.cod_tip_seguro
            LEFT JOIN dwsge.sgss_cbtpc10 tp ON tp.tipopacicod = ce.cod_tipo_paciente
            LEFT JOIN dwsge.sgss_hmese10 enf
                ON enf.oricenasicod = ce.cod_oricentro
                AND enf.cenasicod = ce.cod_centro
                AND enf.servhoscod = ce.cod_serv_inter
                AND enf.estenfcod = ce.cod_estacion
                AND enf.estenfestregcod = '1'
                AND enf.arehoscod = '03'
            WHERE ce.cod_centro = '{codcas}'
            AND (CASE WHEN ce.cod_tipo_paciente = '4' THEN '2' ELSE '1' END) IN {codasegu_clause}
            AND ce.cod_tipo_cama IN ('1')
        """

        try:
            df = pd.read_sql(query, engine)
        except Exception as e:
            return html.Div(f"Error al ejecutar la consulta: {e}"), html.Div()

        if df.empty:
            return html.Div([
                html.I(className="bi bi-inbox", style={
                    'fontSize': '64px', 'color': MUTED, 'marginBottom': '20px'
                }),
                html.H4("Sin registros", style={
                    'color': TEXT, 'fontFamily': FONT_FAMILY, 'marginBottom': '10px'
                }),
                html.P("No hay egresos de hospitalización para el año y periodo seleccionados.", style={
                    'color': MUTED, 'fontFamily': FONT_FAMILY
                }),
                html.P(f"Centro: {codcas} | Año: {anio_str} | Periodo: {periodo}", style={
                    'color': MUTED, 'fontFamily': FONT_FAMILY, 'fontSize': '12px'
                })
            ], style={
                'textAlign': 'center', 'padding': '60px',
                'backgroundColor': CARD_BG, 'borderRadius': '16px',
                'boxShadow': '0 10px 30px rgba(0,0,0,0.08)'
            }), html.Div()

        subtitle = f"Año {anio_str} | Periodo {periodo}"
        total_egresos = len(df)

        dias_col = df['dias_hospit'] if 'dias_hospit' in df.columns else pd.Series(dtype=float)
        dias_col = pd.to_numeric(dias_col, errors='coerce').dropna()
        promedio_dias = round(dias_col.mean(), 1) if not dias_col.empty else 0

        # ---- TARJETAS RESUMEN ----
        summary_row = dbc.Row([
            dbc.Col(render_card(
                "Total Egresos", f"{total_egresos:,.0f}",
                BRAND, subtitle, icon="bi-person-check-fill"
            ), width=12, md=6, className="mb-3"),
            dbc.Col(render_card(
                "Promedio Días Hospitalización", f"{promedio_dias}",
                ACCENT, subtitle, icon="bi-calendar2-week"
            ), width=12, md=6, className="mb-3"),
        ], className="mb-2")

        # ---- GRÁFICOS ----
        charts = []

        # Top 10 diagnósticos
        if 'diagdes' in df.columns and df['diagdes'].notna().any():
            df_diag = (
                df[df['diagdes'].notna()]
                .groupby('diagdes')
                .size()
                .reset_index(name='Egresos')
                .sort_values('Egresos', ascending=False)
                .head(10)
            )
            fig_diag = px.bar(
                df_diag, x='Egresos', y='diagdes', orientation='h',
                text='Egresos',
                color_discrete_sequence=[BRAND],
                labels={'diagdes': 'Diagnóstico', 'Egresos': 'Egresos'}
            )
            fig_diag.update_traces(textposition='outside', texttemplate='%{text:,}')
            fig_diag.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                xaxis={'showticklabels': False},
                margin=dict(l=10, r=40, t=10, b=10),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font_family=FONT_FAMILY
            )
            charts.append(dbc.Col(render_chart_card(fig_diag, "Top 10 Diagnósticos"), width=12, lg=6, className="mb-3"))

        # Egresos por servicio
        if 'servicio' in df.columns and df['servicio'].notna().any():
            df_serv = (
                df[df['servicio'].notna()]
                .groupby('servicio')
                .size()
                .reset_index(name='Egresos')
                .sort_values('Egresos', ascending=False)
                .head(10)
            )
            fig_serv = px.bar(
                df_serv, x='Egresos', y='servicio', orientation='h',
                text='Egresos',
                color_discrete_sequence=[ACCENT],
                labels={'servicio': 'Servicio', 'Egresos': 'Egresos'}
            )
            fig_serv.update_traces(textposition='outside', texttemplate='%{text:,}')
            fig_serv.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                xaxis={'showticklabels': False},
                margin=dict(l=10, r=40, t=10, b=10),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font_family=FONT_FAMILY
            )
            charts.append(dbc.Col(render_chart_card(fig_serv, "Egresos por Servicio"), width=12, lg=6, className="mb-3"))

        # Distribución por sexo
        if 'sexo' in df.columns and df['sexo'].notna().any():
            df_sexo = (
                df[df['sexo'].notna()]
                .groupby('sexo')
                .size()
                .reset_index(name='Egresos')
            )
            fig_sexo = px.pie(
                df_sexo, values='Egresos', names='sexo',
                color_discrete_sequence=[BRAND, ACCENT, '#28a745', '#ffc107'],
                hole=0.4
            )
            fig_sexo.update_traces(textinfo='label+value+percent', textposition='auto')
            fig_sexo.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font_family=FONT_FAMILY,
                showlegend=True
            )
            charts.append(dbc.Col(render_chart_card(fig_sexo, "Distribución por Sexo"), width=12, lg=6, className="mb-3"))

        # Egresos por capítulo CIE-10
        if 'capitulo' in df.columns and df['capitulo'].notna().any():
            df_cap = (
                df[df['capitulo'].notna()]
                .groupby('capitulo')
                .size()
                .reset_index(name='Egresos')
                .sort_values('Egresos', ascending=False)
                .head(10)
            )
            fig_cap = px.bar(
                df_cap, x='Egresos', y='capitulo', orientation='h',
                text='Egresos',
                color_discrete_sequence=['#6f42c1'],
                labels={'capitulo': 'Capítulo CIE-10', 'Egresos': 'Egresos'}
            )
            fig_cap.update_traces(textposition='outside', texttemplate='%{text:,}')
            fig_cap.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                xaxis={'showticklabels': False},
                margin=dict(l=10, r=40, t=10, b=10),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font_family=FONT_FAMILY
            )
            charts.append(dbc.Col(render_chart_card(fig_cap, "Egresos por Capítulo CIE-10"), width=12, lg=6, className="mb-3"))

        # Tabla combinada: Servicio - Estación de Enfermería - Cama - Egresos
        group_cols_comb = [c for c in ['servicio', 'estenfdes', 'cama'] if c in df.columns]
        if group_cols_comb:
            mask_comb = df['cama'].notna() & (df['cama'].astype(str).str.strip() != '') if 'cama' in df.columns else pd.Series([True] * len(df))
            df_comb = (
                df[mask_comb]
                .groupby(group_cols_comb, dropna=False)
                .size()
                .reset_index(name='Egresos')
                .sort_values(group_cols_comb)
            )
            df_comb[group_cols_comb] = df_comb[group_cols_comb].fillna('Sin registro')
            first_col = group_cols_comb[0]
            extra = group_cols_comb[1:]
            charts.append(dbc.Col(
                render_table_card("Servicio · Estación de Enfermería · Camas", df_comb, first_col, extra_cols=extra),
                width=12, className="mb-3"
            ))

        charts_row = dbc.Row(charts, style={'marginTop': '16px'}) if charts else html.Div()

        return html.Div([summary_row, charts_row]), html.Div()

    # ========== CALLBACK DESCARGA CSV ==========
    @dash_app.callback(
        Output("download-hosp-csv", "data"),
        Input("download-button-hosp", "n_clicks"),
        State('filter-periodo-hosp', 'value'),
        State('filter-anio-hosp', 'value'),
        State('filter-tipo-asegurado-hosp', 'value'),
        State('url-hosp', 'pathname'),
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

        query = f"""
            select
                ca.redasiscod,
                r.redasisdes,
                ce.cod_centro,
                ce.periodo,
                ce.anio,
                ce.cod_servicio,
                c.servhosdes AS servicio,
                ce.cod_actividad,
                am.actdes AS actividad,
                ce.cod_estacion,
                enf.estenfdes,
                ce.anio_edad,
                ce.sexo,
                ce.cod_tip_seguro,
                ts.tipsegdes as tipo_seguro,
                ce.cod_tipo_paciente,
                tp.tipopacinom as tipo_paciente,
                ce.fec_ingr,
                ce.fec_altmed,
                ce.fec_egreso,
                ce.dias_hospit,
                ce.cuarto,
                ce.cama,
                ce.diag_cod,
                d.diagdes,
                d.edxcapdes AS capitulo
            from dwsge.dwe_hosp_egresos_{anio_str}_{periodo} ce
            LEFT JOIN dwsge.sgss_cmdia10_chapter d ON ce.diag_cod = d.diagcod
            LEFT JOIN dwsge.sgss_cmsho10 AS c ON ce.cod_servicio = c.servhoscod
            LEFT JOIN dwsge.sgss_cmcas10 AS ca ON ce.cod_oricentro = ca.oricenasicod AND ce.cod_centro = ca.cenasicod
            LEFT JOIN dwsge.sgss_cmact10 AS am ON ce.cod_actividad = am.actcod
            LEFT JOIN dwsge.sgss_cmras10 r ON ca.redasiscod = r.redasiscod
            LEFT JOIN dwsge.sgss_cmtse10 ts ON ts.tipsegcod = ce.cod_tip_seguro
            LEFT JOIN dwsge.sgss_cbtpc10 tp ON tp.tipopacicod = ce.cod_tipo_paciente
            LEFT JOIN dwsge.sgss_hmese10 enf
                ON enf.oricenasicod = ce.cod_oricentro
                AND enf.cenasicod = ce.cod_centro
                AND enf.servhoscod = ce.cod_serv_inter
                AND enf.estenfcod = ce.cod_estacion
                AND enf.estenfestregcod = '1'
                AND enf.arehoscod = '03'
            WHERE ce.cod_centro = '{codcas}'
            AND (CASE WHEN ce.cod_tipo_paciente = '4' THEN '2' ELSE '1' END) IN {codasegu_clause}
            AND ce.cod_tipo_cama IN ('1','2','4')
        """

        try:
            df = pd.read_sql(query, engine)
        except Exception:
            return None

        if df.empty:
            return None

        df = df.astype(str)
        filename = f"hospitalizacion_egresos_{codcas}_{anio_str}_{periodo}.csv"
        return dcc.send_data_frame(df.to_csv, filename, index=False)

    dash_app.layout = serve_layout
    return dash_app
