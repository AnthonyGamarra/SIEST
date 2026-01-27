import io
import importlib
import pkgutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Optional
from urllib.parse import quote_plus

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, html, dcc, Input, Output, State
from flask import has_request_context
from flask_login import current_user
from sqlalchemy import create_engine, text

import secure_code as sc


def create_dash_app(flask_app, url_base_pathname='/dashboard_nm/'):
    external_stylesheets = [
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
    ]

    BRAND = "#0064AF"
    BRAND_SOFT = "#D7E9FF"
    ACCENT = "#00AEEF"
    CARD_BG = "#FFFFFF"
    TEXT = "#1C1F26"
    MUTED = "#6B7280"
    BORDER = "#E5E7EB"
    FONT_FAMILY = "Inter, 'Segoe UI', Calibri, sans-serif"

    TAB_STYLE = {
        "padding": "10px 18px",
        "border": f"1px solid {BORDER}",
        "borderBottom": "none",
        "borderTopLeftRadius": "10px",
        "borderTopRightRadius": "10px",
        "fontFamily": FONT_FAMILY,
        "fontWeight": "600",
        "fontSize": "12px",   
        "color": MUTED,
        "backgroundColor": CARD_BG,
        "marginRight": "0"
    }
    TAB_SELECTED_STYLE = {
        **TAB_STYLE,
        'color': BRAND,
        'backgroundColor': CARD_BG,
        'borderBottom': f'3px solid {BRAND}'
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
    CONTROL_BAR_STYLE = {
        "display": "flex",
        "alignItems": "center",
        "gap": "12px",
        "marginBottom": "18px",
        "backgroundColor": CARD_BG,
        "border": f"1px solid {BORDER}",
        "padding": "14px 16px",
        
        "borderTopLeftRadius": "0px",
        "borderTopRightRadius": "0px",
        "borderBottomLeftRadius": "14px",
        "borderBottomRightRadius": "14px",

        "boxShadow": "0 4px 10px rgba(0,0,0,0.05)",
        "backdropFilter": "blur(3px)",
        "overflow": "visible",
        "position": "relative",
        "zIndex": 1100,
    }

    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    anios = ['2025', '2026']
    tipo_asegurado = ['Asegurado', 'No Asegurado', 'Todos']
    anio_options = [{'label': year, 'value': year} for year in anios]
    valores = [f"{i:02d}" for i in range(1, 13)]
    df_period = pd.DataFrame({'mes': meses, 'periodo': valores})
    tipo_asegurado_options = [{'label': tipo, 'value': tipo} for tipo in tipo_asegurado]

    def _import_indicator_pages():
        pkg_name = f"{__package__}.Indicadores" if __package__ else "Indicadores"
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception as exc:
            print(f"[Dash Pages] No se pudo importar el paquete '{pkg_name}': {exc}")
            return

        for module in pkgutil.iter_modules(pkg.__path__):
            mod_name = f"{pkg_name}.{module.name}"
            try:
                importlib.import_module(mod_name)
                print(f"[Dash Pages] Página importada: {mod_name}")
            except Exception as exc:
                print(f"[Dash Pages] Error importando {mod_name}: {exc}")

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

    @dataclass(frozen=True)
    class FilterIds:
        periodo: str
        anio: str
        tipo: str

    @dataclass(frozen=True)
    class TabConfig:
        key: str
        label: str
        value: str
        filter_ids: FilterIds
        search_button_id: str
        download_button_id: str
        download_component_id: str
        back_button_id: str
        summary_container_id: str
        charts_container_id: str
        data_loader: Callable
        include_citas: bool = False
        include_desercion: bool = False
        cards_builder: Optional[Callable] = None

    def build_summary_layout(cards, subtitle):
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
                            lg=12,
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

        return dbc.Container(summary_sections, fluid=True)

    def build_tab_panel(tab_config):
        periodo_options = [
            {'label': row['mes'], 'value': row['periodo']}
            for _, row in df_period.iterrows()
        ]
        controls = html.Div([
            html.I(
                className="bi bi-calendar3 dashboard-control-icon",
                style={'fontSize': '18px', 'color': BRAND, 'marginRight': '8px'}
            ),
            dcc.Dropdown(
                id=tab_config.filter_ids.anio,
                className='anio-dropdown',
                options=anio_options,
                placeholder='Año',
                clearable=True,
                style={
                    'width': '160px',
                    'fontFamily': FONT_FAMILY,
                    'position': 'relative',
                    'zIndex': 1200
                }
            ),
            dcc.Dropdown(
                id=tab_config.filter_ids.periodo,
                className='periodo-dropdown',
                options=periodo_options,
                placeholder='Periodo',
                clearable=True,
                style={
                    'width': '240px',
                    'fontFamily': FONT_FAMILY,
                    'position': 'relative',
                    'zIndex': 1200
                }
            ),
            dcc.Dropdown(
                id=tab_config.filter_ids.tipo,
                className='tipo-dropdown',
                options=tipo_asegurado_options,
                value=DEFAULT_TIPO_ASEGURADO,
                clearable=False,
                placeholder='Tipo asegurado',
                style={
                    'width': '200px',
                    'fontFamily': FONT_FAMILY,
                    'position': 'relative',
                    'zIndex': 1200
                }
            ),
            dbc.Button(
                [html.I(className="bi bi-search me-2"), "Buscar"],
                id=tab_config.search_button_id,
                color='primary',
                size='md',
                className='dashboard-control-btn',
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
            # dbc.Button(
            #     [html.I(className="bi bi-download me-2"), "Exportar Excel"],
            #     id=tab_config.download_button_id,
            #     color='success',
            #     size='md',
            #     style={
            #         'backgroundColor': '#28a745',
            #         'borderColor': '#28a745',
            #         'padding': '8px 12px',
            #         'boxShadow': '0 4px 10px rgba(40,167,69,0.18)',
            #         'fontFamily': FONT_FAMILY,
            #         'fontWeight': '600',
            #         'borderRadius': '8px'
            #     }
            # ),
            dcc.Download(id=tab_config.download_component_id),
            dbc.Button(
                [html.I(className="bi bi-arrow-left me-1"), "Volver"],
                id=tab_config.back_button_id,
                color='secondary',
                outline=True,
                className='dashboard-control-btn dashboard-control-btn-back',
                href='javascript:history.back();',
                external_link=True,
                style={'marginLeft': 'auto', 'padding': '8px 12px'}
            ),
        ], className='dashboard-control-bar', style={**CONTROL_BAR_STYLE})

        return dcc.Tab(
            label=tab_config.label,
            value=tab_config.value,
            style=TAB_STYLE,
            selected_style=TAB_SELECTED_STYLE,
            children=[
                html.Div([
                    controls,
                    dbc.Tooltip("Volver a la página anterior", target=tab_config.back_button_id, placement='bottom', style={'zIndex': 9999}),
                    dbc.Tooltip("Buscar datos", target=tab_config.search_button_id, placement='bottom', style={'zIndex': 9999}),
                    dbc.Tooltip("Descargar Excel", target=tab_config.download_button_id, placement='bottom', style={'zIndex': 9999}),
                    dbc.Row([
                        dbc.Col(
                            html.Div(
                                dcc.Loading(
                                    className='dashboard-loading-inline',
                                    parent_className='dashboard-loading-parent',
                                    parent_style={'width': '100%'},
                                    type='default',
                                    style={'width': '100%'},
                                    children=html.Div(id=tab_config.summary_container_id)
                                ),
                                className='dashboard-loading-shell'
                            ),
                            width=12
                        )
                    ]),
                    html.Br(),
                    dbc.Row([dbc.Col(html.Div(id=tab_config.charts_container_id), width=12)]),
                    html.Br(),
                ], id=f'tab-{tab_config.key}-content')
            ]
        )

    def fetch_dashboard_payload(periodo, anio_value, tipo_asegurado_value, pathname, data_loader):
        if not periodo or not anio_value:
            return None, html.Div("Seleccione un año y un periodo, y asegurese de tener un centro valido."), None

        codcas_url = pathname.rstrip('/').split('/')[-1] if pathname else None
        codcas = sc.decode_code(codcas_url) if codcas_url else None

        if not codcas:
            return None, html.Div("Seleccione un centro valido."), None

        engine = create_connection()
        if engine is None:
            return None, html.Div("Error de conexion a la base de datos."), None

        data = data_loader(periodo, anio_value, codcas, engine, tipo_asegurado_value)
        if not data:
            return None, html.Div("Sin datos para mostrar."), None

        return data, None, codcas_url

    def build_cards_from_template(stats, tables, template):
        default_df = pd.DataFrame(columns=['agrupador', 'counts'])
        cards = []
        for card in template:
            table_key = card.get('table_key')
            table_title = card.get('table_title')
            side_component = None
            if table_key:
                dataset = tables.get(table_key, default_df)
                side_component = render_agrupador_table(dataset, title=table_title)
            cards.append({
                "title": card['title'],
                "value": f"{stats.get(card['stat_key'], 0):,.0f}",
                "border_color": card.get('border_color', ACCENT),
                "side_component": side_component
            })
        return cards

    def create_cards_builder(template):
        def _builder(data, *_):
            stats = data['stats']
            tables = data['tables']
            return build_cards_from_template(stats, tables, template)
        return _builder

    COMPLEMENTARIA_CARD_TEMPLATE = [
        {
            "title": "Total de atenciones Obstétricas",
            "stat_key": "total_atenciones",
            "border_color": ACCENT,
        },
        {
            "title": "Atenciones prenatales",
            "stat_key": "total_atenciones_prenatal",
            "border_color": BRAND,
            "table_key": "atenciones_prenatal_por_sub_act",
            "table_title": "Subactividades prenatales",
        },
        {
            "title": "Atención de planificación familiar",
            "stat_key": "total_atenciones_familiar",
            "border_color": BRAND_SOFT,
            "table_key": "atenciones_familiar_por_sub_act",
            "table_title": "Subactividades familiares",
        },
        {
            "title": "Actividades complementarias",
            "stat_key": "total_atenciones_complementarias",
            "border_color": ACCENT,
            "table_key": "atenciones_complementarias_por_sub_act",
            "table_title": "Subactividades complementarias",
        },
        {
            "title": "Atención preconcepcional",
            "stat_key": "total_atenciones_preconcepcional",
            "border_color": BRAND,
            "table_key": "atenciones_preconcepcional_por_sub_act",
            "table_title": "Subactividades preconcepcional",
        },
    ]

    PROGRAMAS_CARD_TEMPLATE = [
        {
            "title": "Total de atenciones preventivo promocional",
            "stat_key": "total_atenciones_p",
            "border_color": BRAND,
        },
        {
            "title": "Visitas domiciliarias",
            "stat_key": "total_atenciones_domiciliaria",
            "border_color": ACCENT,
            "table_key": "atenciones_domiciliaria_por_sub_act",
            "table_title": "Detalle domicilio",
        },
        {
            "title": "Educación grupal",
            "stat_key": "total_atenciones_grupal",
            "border_color": BRAND_SOFT,
            "table_key": "atenciones_grupal_por_sub_act",
            "table_title": "Detalle grupal",
        },
        {
            "title": "Psicoprofilaxis",
            "stat_key": "total_atenciones_psicoprofilaxis",
            "border_color": ACCENT,
            "table_key": "atenciones_psicoprofilaxis_por_sub_act",
            "table_title": "Detalle psicoprofilaxis",
        },
        {
            "title": "Consejería",
            "stat_key": "total_atenciones_consejeria",
            "border_color": BRAND,
            "table_key": "atenciones_consejeria_por_sub_act",
            "table_title": "Detalle consejería",
        },
    ]

    build_complementaria_cards = create_cards_builder(COMPLEMENTARIA_CARD_TEMPLATE)
    build_programas_cards = create_cards_builder(PROGRAMAS_CARD_TEMPLATE)
    NUTRICION_CARD_TEMPLATE = [
        {
            "title": "Total de atenciones de nutrición",
            "stat_key": "total_nutricion_atenciones",
            "border_color": BRAND,
            "table_key": "nutricion_individual_por_sub_act",
            "table_title": "Detalle consulta individual",
        },
    ]

    build_nutricion_cards = create_cards_builder(NUTRICION_CARD_TEMPLATE)

    ENFERMERIA_CARD_TEMPLATE = [
        {
            "title": "Total atenciones de enfermería",
            "stat_key": "total_enfermeria_atenciones",
            "border_color": BRAND,
        },
        {
            "title": "Atenciones en tuberculosis",
            "stat_key": "total_enfermeria_tuberculosis",
            "border_color": ACCENT,
            "table_key": "enfermeria_tuberculosis_por_sub_act",
            "table_title": "Detalle tuberculosis",
        },
        {
            "title": "Atenciones en ITS-HIV/SIDA",
            "stat_key": "total_enfermeria_vih",
            "border_color": BRAND_SOFT,
            "table_key": "enfermeria_vih_por_sub_act",
            "table_title": "Detalle VIH",
        },
        {
            "title": "Atención en Enfermedades crónicas no trasmisibles-adulto mayor",
            "stat_key": "total_enfermeria_cronicas_am",
            "border_color": ACCENT,
            "table_key": "enfermeria_cronicas_am_por_sub_act",
            "table_title": "Detalle crónicos AM",
        },
        {
            "title": "Otras actividades ambulatorias",
            "stat_key": "total_enfermeria_otros",
            "border_color": BRAND,
            "table_key": "enfermeria_otros_por_sub_act",
            "table_title": "Detalle otros",
        },
        {
            "title": "Atenciones en prevención y control de la anemia",
            "stat_key": "total_enfermeria_prev_anemia",
            "border_color": ACCENT,
            "table_key": "enfermeria_prev_anemia_por_sub_act",
            "table_title": "Detalle prevención anemia",
        },
    ]

    build_enfermeria_cards = create_cards_builder(ENFERMERIA_CARD_TEMPLATE)



    PSICOLOGIA_CARD_TEMPLATE = [
        {
            "title": "Total atenciones de psicología",
            "stat_key": "total_psicologia_atenciones",
            "border_color": BRAND,
        },
    ]
    build_psicologia_cards = create_cards_builder(PSICOLOGIA_CARD_TEMPLATE)

    TRASOCIAL_CARD_TEMPLATE = [
        {
            "title": "Total atenciones de trabajo social",
            "stat_key": "total_trasocial_atenciones",
            "border_color": BRAND,
        },
    ]
    build_trasocial_cards = create_cards_builder(TRASOCIAL_CARD_TEMPLATE)
    


    PROC_TERA_CARD_TEMPLATE = [
        {
            "title": "Total atenciones de procedimiento terapéutico",
            "stat_key": "total_proc_tera_atenciones",
            "border_color": BRAND,
        },
        {
            "title": "Terapia individual",
            "stat_key": "total_terap_indiv_atenciones",
            "border_color": ACCENT,
            "table_key": "terap_indiv_por_sub_act",
            "table_title": "Detalle terapia individual",
        },
        {
            "title": "Terapia pareja/familiar",
            "stat_key": "total_terap_par_fam_atenciones",
            "border_color": BRAND_SOFT,
            "table_key": "terap_par_fam_por_sub_act",
            "table_title": "Detalle terapia pareja/familiar",
        },
        {
            "title": "Terapia grupal",
            "stat_key": "total_terap_grup_atenciones",
            "border_color": ACCENT,
            "table_key": "terap_grup_por_sub_act",
            "table_title": "Detalle terapia grupal",
        },
    ]

    build_proc_tera_cards = create_cards_builder(PROC_TERA_CARD_TEMPLATE)

    PROC_DIAG_CARD_TEMPLATE = [
        {
            "title": "Total atenciones de procedimiento diagnóstico",
            "stat_key": "total_proc_diag_atenciones",
            "border_color": BRAND,
        },
    ]
    build_proc_diag_cards = create_cards_builder(PROC_DIAG_CARD_TEMPLATE)
    

    DEFAULT_TIPO_ASEGURADO = 'Todos'
    TIPO_ASEGURADO_SQL = {
        'Asegurado': "('1')",
        'No Asegurado': "('2')",
        'Todos': "('1','2')"
    }

    def resolve_tipo_asegurado_clause(selection):
        normalized = selection if selection in TIPO_ASEGURADO_SQL else DEFAULT_TIPO_ASEGURADO
        return TIPO_ASEGURADO_SQL[normalized]

    FICHA_TECNICA_ID = 11

    def _build_safe_pdf_name(raw_name: Optional[str]) -> str:
        base = (raw_name or "ficha_tecnica").strip()
        safe_chars = [ch if ch.isalnum() or ch in (" ", "-", "_") else "_" for ch in base]
        normalized = ''.join(safe_chars).strip().replace(' ', '_').lower()
        normalized = normalized or "ficha_tecnica"
        return normalized if normalized.endswith('.pdf') else f"{normalized}.pdf"

    def fetch_ficha_tecnica(engine, ficha_id: int = FICHA_TECNICA_ID):
        if engine is None:
            return None

        try:
            with engine.connect() as connection:
                row = connection.execute(
                    text("SELECT nombre, archivo_pdf FROM dwsge.f_tecnicas WHERE id = :id"),
                    {"id": ficha_id}
                ).mappings().first()
        except Exception as exc:
            print(f"Failed to fetch ficha tecnica {ficha_id}: {exc}")
            return None

        if not row or not row.get('archivo_pdf'):
            return None

        filename = _build_safe_pdf_name(row.get('nombre'))
        pdf_bytes = bytes(row['archivo_pdf'])
        return filename, pdf_bytes

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

    def render_agrupador_table(dataframe, value_format="{:,.0f}", title=None):
        heading = html.H6(
            title,
            className="fw-semibold",
            style={
                'fontSize': '11px',
                'color': BRAND,
                'letterSpacing': '0.6px',
                'marginBottom': '8px',
            }
        ) if title else None

        if dataframe.empty:
            body_children = [heading] if heading else []
            body_children.append(
                html.P(
                    "Sin registros",
                    className="text-muted mb-0",
                    style={'fontFamily': FONT_FAMILY, 'fontSize': '12px'}
                )
            )
            return dbc.Card(
                dbc.CardBody(
                    body_children,
                    style={**CARD_BODY_STYLE, 'padding': '14px'}
                ),
                style={**CARD_STYLE, "borderLeft": f"5px solid {ACCENT}", "height": "100%"}
            )

        table_body = html.Tbody([
            html.Tr([
                html.Td(
                    row.get('agrupador') or "Sin agrupador",
                    style={'padding': '4px 8px', 'lineHeight': '1.1'}
                ),
                html.Td(
                    "-" if pd.isna(row.get('counts')) else value_format.format(row.get('counts')),
                    style={'textAlign': 'right', 'padding': '4px 8px', 'lineHeight': '1.1'}
                )
            ])
            for _, row in dataframe.iterrows()
        ])

        body_children = [heading] if heading else []
        body_children.append(
            dbc.Table(
                [table_body],
                bordered=False,
                hover=False,
                responsive=True,
                striped=False,
                className="mb-0",
                style={'fontSize': '13px'}
            )
        )

        return dbc.Card(
            dbc.CardBody(
                body_children,
                style={**CARD_BODY_STYLE, 'padding': '14px'}
            ),
            style={**CARD_STYLE, "borderLeft": f"5px solid {ACCENT}", "height": "100%"}
        )

    @lru_cache(maxsize=1)
    def create_connection():
        try:
            engine = create_engine('postgresql+psycopg2://postgres:4dm1n@10.0.29.117:5433/DW_ESTADISTICA')
            with engine.connect():
                pass
            return engine
        except Exception as exc:
            print(f"Failed to connect to the database: {exc}")
            return None

    def build_queries_complementaria(anio_str, periodo_str, params):
        codasegu = params.get('codasegu', TIPO_ASEGURADO_SQL[DEFAULT_TIPO_ASEGURADO])
        queries = [
            ("atenciones", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='F21'
                        AND ce.cod_subactividad in ('007', '480', '643','694','417', '418', '127', '008','040')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
            ("prenatal", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE ce.cod_centro = :codcas
                        AND ce.cod_servicio ='F21'
                        AND ce.cod_subactividad in ('007', '480', '643')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
            ("familiar", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE ce.cod_centro = :codcas
                        AND ce.cod_servicio ='F21'
                        AND ce.cod_subactividad ='694'
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
            ("complementarias", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE ce.cod_centro = :codcas
                        AND ce.cod_servicio ='F21'
                        AND ce.cod_subactividad in ('417', '418', '127', '008')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
            ("preconcepcional", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE ce.cod_centro = :codcas
                        AND ce.cod_servicio ='F21'
                        AND ce.cod_subactividad ='040'
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
        ]
        return {
            "queries": queries,
        }

    def build_queries_programas(anio_str, periodo_str, params):
        """Consultas para la pestaña de programas especiales."""
        codasegu = params.get('codasegu', TIPO_ASEGURADO_SQL[DEFAULT_TIPO_ASEGURADO])
        queries = [
            ("atenciones_p", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='F21'
                        AND ce.cod_subactividad in ('079', '078', '685','724','416')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
            ("domiciliaria", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE ce.cod_centro = :codcas
                        AND ce.cod_servicio ='F21'
                        AND ce.cod_subactividad in ('079', '078')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
            ("grupal", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE ce.cod_centro = :codcas
                        AND ce.cod_servicio ='F21'
                        AND ce.cod_subactividad ='685'
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
            ("psicoprofilaxis", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE ce.cod_centro = :codcas
                        AND ce.cod_servicio ='F21'
                        AND ce.cod_subactividad in ('724')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
            ("consejeria", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE ce.cod_centro = :codcas
                        AND ce.cod_servicio ='F21'
                        AND ce.cod_subactividad ='416'
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
        ]
        return {
            "queries": queries,
        }

    def build_queries_nutricion(anio_str, periodo_str, params):
        """Consultas base para la pestaña de nutrición (ajusta los filtros según tus requerimientos)."""
        codasegu = params.get('codasegu', TIPO_ASEGURADO_SQL[DEFAULT_TIPO_ASEGURADO])
        queries = [
            ("nutricion_total", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='F31'
                        AND ce.cod_subactividad in ('050', '056', '203', '093', '322')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
        ]
        return {
            "queries": queries,
        }

    def build_queries_enfermeria(anio_str, periodo_str, params):
        codasegu = params.get('codasegu', TIPO_ASEGURADO_SQL[DEFAULT_TIPO_ASEGURADO])
        queries = [
            ("enfermeria_total", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='F11'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad in ('072','073','093','576','680','010','801','056')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
            ("enfermeria_tuberculosis", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='F11'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad in ('072','073','093')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),

            ("enfermeria_vih", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='F11'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad in ('576','680')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
    
            ("enfermeria_cronicas_am", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='F11'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad in ('010')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),

            ("enfermeria_otros", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='F11'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad in ('801')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),

            ("enfermeria_prev_anemia", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='F11'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad in ('056')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
        ]
        return {
            "queries": queries,
        }



    def build_queries_psicologia(anio_str, periodo_str, params):
        codasegu = params.get('codasegu', TIPO_ASEGURADO_SQL[DEFAULT_TIPO_ASEGURADO])
        queries = [
            ("psicologia_total", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='E21'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad ='005'
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
        ]
        return {
            "queries": queries,
        }

    def build_queries_trasocial(anio_str, periodo_str, params):
        codasegu = params.get('codasegu', TIPO_ASEGURADO_SQL[DEFAULT_TIPO_ASEGURADO])
        queries = [
            ("trasocial_total", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='F51'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad ='055'
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
        ]
        return {
            "queries": queries,
        }

    def build_queries_proc_tera(anio_str, periodo_str, params):
        codasegu = params.get('codasegu', TIPO_ASEGURADO_SQL[DEFAULT_TIPO_ASEGURADO])
        queries = [
            ("proc_tera_total", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='E21'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad in ('752','760','763','006')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
            ("terap_indiv", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='E21'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad in ('752')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),

            ("terap_par_fam", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='E21'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad in ('760','763')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
    
            ("terap_grup", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='E21'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad in ('006')
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
        ]
        return {
            "queries": queries,
        }

    def build_queries_proc_diag(anio_str, periodo_str, params):
        codasegu = params.get('codasegu', TIPO_ASEGURADO_SQL[DEFAULT_TIPO_ASEGURADO])
        queries = [
            ("proc_diag_total", text(f"""
                    SELECT ce.cod_oricentro, ce.cod_centro,a.actespnom,c.servhosdes,ce.cod_servicio, ce.cod_actividad, ce.cod_subactividad,ce.acto_med, ce.doc_paciente, ce.diagcod, dg.diagdes
                    FROM dwsge.dwe_consulta_externa_no_medicas_{anio_str}_{periodo_str} ce
                    LEFT OUTER JOIN dwsge.sgss_cmdia10 dg 
                        ON dg.diagcod=ce.diagcod
                    LEFT JOIN dwsge.sgss_cmsho10 AS c 
                        ON ce.cod_servicio = c.servhoscod
                    LEFT JOIN dwsge.sgss_cmace10 AS a
                        ON ce.cod_actividad = a.actcod
                        AND ce.cod_subactividad = a.actespcod
                    LEFT JOIN dwsge.sgss_cmact10 AS am
                        ON ce.cod_actividad = am.actcod
                    LEFT JOIN dwsge.sgss_cmcas10 AS ca
                        ON ce.cod_oricentro = ca.oricenasicod
                        AND ce.cod_centro = ca.cenasicod
                        WHERE cod_centro = :codcas
                        AND cod_servicio ='E21'
                        AND cod_actividad ='B1'
                        AND ce.cod_subactividad ='705'
                        AND (
                                CASE 
                                    WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                    ELSE '1'
                                END
                                ) IN {codasegu}
            """),
            params.copy()),
        ]
        return {
            "queries": queries,
        }



    def _load_dashboard_data(periodo, anio, codcas, engine, query_builder, tipo_asegurado_value):
        if not periodo or not codcas or not anio:
            return None
        periodo_str = f"{int(periodo):02d}" if str(periodo).isdigit() else str(periodo)
        anio_str = str(anio)
        periodo_sql = f"{anio_str}{periodo_str}"
        params = {
            "codcas": codcas,
            "codasegu": resolve_tipo_asegurado_clause(tipo_asegurado_value)
        }
        builder_payload = query_builder(anio_str, periodo_str, params)
        queries = builder_payload.get("queries", [])
        results = {}

        def run_query(job):
            key, stmt, job_params = job
            return key, pd.read_sql(stmt, engine, params=job_params)

        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            for key, df in executor.map(run_query, queries):
                results[key] = df

        atenciones_df = results.get("atenciones", pd.DataFrame())
        atenciones_prenatal_df = results.get("prenatal", pd.DataFrame())
        atenciones_familiar_df = results.get("familiar", pd.DataFrame())
        atenciones_complementarias_df = results.get("complementarias", pd.DataFrame())
        atenciones_preconcepcional_df = results.get("preconcepcional", pd.DataFrame())


        atenciones_p_df = results.get("atenciones_p", pd.DataFrame())
        atenciones_domiciliaria_df = results.get("domiciliaria", pd.DataFrame())
        atenciones_grupal_df = results.get("grupal", pd.DataFrame())
        atenciones_psicoprofilaxis_df = results.get("psicoprofilaxis", pd.DataFrame())
        atenciones_consejeria_df = results.get("consejeria", pd.DataFrame())

        nutricion_total_df = results.get("nutricion_total", pd.DataFrame())

        atenciones_e_df = results.get("enfermeria_total", pd.DataFrame())
        atenciones_tuberculosis_df = results.get("enfermeria_tuberculosis", pd.DataFrame())
        atenciones_vih_df = results.get("enfermeria_vih", pd.DataFrame())
        atenciones_cronicas_am_df = results.get("enfermeria_cronicas_am", pd.DataFrame())
        atenciones_enfermeria_otros_df = results.get("enfermeria_otros", pd.DataFrame())
        atenciones_prev_anemia_df = results.get("enfermeria_prev_anemia", pd.DataFrame())

        atenciones_psicologia_df = results.get("psicologia_total", pd.DataFrame())

        atenciones_trasocial_df = results.get("trasocial_total", pd.DataFrame())

        atenciones_proc_tera_df = results.get("proc_tera_total", pd.DataFrame())
        terap_indiv_df = results.get("terap_indiv", pd.DataFrame())
        terap_par_fam_df = results.get("terap_par_fam", pd.DataFrame())
        terap_grup_df = results.get("terap_grup", pd.DataFrame())
       
        atenciones_proc_diag_df = results.get("proc_diag_total", pd.DataFrame())

        def summarize_sub_activities(frame):
            if frame.empty or 'actespnom' not in frame:
                return pd.DataFrame(columns=['agrupador', 'counts'])
            return (
                frame.groupby('actespnom', dropna=False)
                .size()
                .reset_index(name='counts')
                .rename(columns={'actespnom': 'agrupador'})
                .sort_values('counts', ascending=False)
            )

        def resolve_nombre_centro(dataframes):
            for frame in dataframes:
                if frame.empty or 'cod_centro' not in frame:
                    continue
                values = frame['cod_centro'].dropna().unique()
                if len(values) > 0:
                    return values[0]
            return codcas

        total_atenciones = len(atenciones_df)
        total_atenciones_prenatal = len(atenciones_prenatal_df)
        total_atenciones_familiar = len(atenciones_familiar_df)
        total_atenciones_complementarias = len(atenciones_complementarias_df)
        total_atenciones_preconcepcional = len(atenciones_preconcepcional_df)

        total_atenciones_p = len(atenciones_p_df)
        total_atenciones_domiciliaria = len(atenciones_domiciliaria_df)
        total_atenciones_grupal = len(atenciones_grupal_df)
        total_atenciones_psicoprofilaxis = len(atenciones_psicoprofilaxis_df)
        total_atenciones_consejeria = len(atenciones_consejeria_df)

        total_nutricion_atenciones = len(nutricion_total_df)
        total_enfermeria_atenciones = len(atenciones_e_df)
        total_enfermeria_tuberculosis = len(atenciones_tuberculosis_df)
        total_enfermeria_vih = len(atenciones_vih_df)
        total_enfermeria_cronicas_am = len(atenciones_cronicas_am_df)
        total_enfermeria_otros = len(atenciones_enfermeria_otros_df)
        total_enfermeria_prev_anemia = len(atenciones_prev_anemia_df)

        atenciones_prenatal_df_agru = summarize_sub_activities(atenciones_prenatal_df)
        atenciones_familiar_df_agru = summarize_sub_activities(atenciones_familiar_df)
        atenciones_complementarias_df_agru = summarize_sub_activities(atenciones_complementarias_df)
        atenciones_preconcepcional_df_agru = summarize_sub_activities(atenciones_preconcepcional_df)

        atenciones_domiciliaria_df_agru = summarize_sub_activities(atenciones_domiciliaria_df)
        atenciones_grupal_df_agru = summarize_sub_activities(atenciones_grupal_df)
        atenciones_psicoprofilaxis_df_agru = summarize_sub_activities(atenciones_psicoprofilaxis_df)
        atenciones_consejeria_df_agru = summarize_sub_activities(atenciones_consejeria_df)

        nutricion_total_df_agru = summarize_sub_activities(nutricion_total_df)

        atenciones_tuberculosis_df_agru = summarize_sub_activities(atenciones_tuberculosis_df)
        atenciones_vih_df_agru = summarize_sub_activities(atenciones_vih_df)
        atenciones_cronicas_am_df_agru = summarize_sub_activities(atenciones_cronicas_am_df)
        atenciones_enfermeria_otros_df_agru = summarize_sub_activities(atenciones_enfermeria_otros_df)
        atenciones_prev_anemia_df_agru = summarize_sub_activities(atenciones_prev_anemia_df)

        total_atenciones_psicologia_df = len(atenciones_psicologia_df)
        total_atenciones_trasocial_df = len(atenciones_trasocial_df)

        total_atenciones_proc_tera_df = len(atenciones_proc_tera_df)
        total_terap_indiv_df = len(terap_indiv_df)
        total_terap_par_fam_df = len(terap_par_fam_df)
        total_terap_grup_df = len(terap_grup_df)

        total_terap_indiv_df_agru = summarize_sub_activities(terap_indiv_df)
        total_terap_par_fam_df_agru = summarize_sub_activities(terap_par_fam_df)
        total_terap_grup_df_agru = summarize_sub_activities(terap_grup_df)

        total_proc_diag_df = len(atenciones_proc_diag_df)

        nombre_centro = resolve_nombre_centro([
            atenciones_df,
            atenciones_prenatal_df,
            atenciones_familiar_df,
            atenciones_complementarias_df,
            atenciones_preconcepcional_df,
            atenciones_p_df,
            atenciones_domiciliaria_df,
            atenciones_grupal_df,
            atenciones_psicoprofilaxis_df,
            atenciones_consejeria_df,
            nutricion_total_df,
            atenciones_e_df,
            atenciones_tuberculosis_df,
            atenciones_vih_df,
            atenciones_cronicas_am_df,
            atenciones_enfermeria_otros_df,
            atenciones_prev_anemia_df,
            atenciones_psicologia_df,
            atenciones_trasocial_df,
            atenciones_proc_diag_df,
            terap_indiv_df,
            terap_par_fam_df,
            terap_grup_df,
            
        ])

        stats = {
            'total_atenciones': total_atenciones,
            'total_atenciones_prenatal': total_atenciones_prenatal,
            'total_atenciones_familiar': total_atenciones_familiar,
            'total_atenciones_complementarias': total_atenciones_complementarias,
            'total_atenciones_preconcepcional': total_atenciones_preconcepcional,
            'total_atenciones_p': total_atenciones_p,
            'total_atenciones_domiciliaria': total_atenciones_domiciliaria,
            'total_atenciones_grupal': total_atenciones_grupal,
            'total_atenciones_psicoprofilaxis': total_atenciones_psicoprofilaxis,
            'total_atenciones_consejeria': total_atenciones_consejeria,
            'total_nutricion_atenciones': total_nutricion_atenciones,
            'total_nutricion_individual': total_nutricion_atenciones,
            'total_enfermeria_atenciones': total_enfermeria_atenciones,
            'total_enfermeria_tuberculosis': total_enfermeria_tuberculosis,
            'total_enfermeria_vih': total_enfermeria_vih,
            'total_enfermeria_cronicas_am': total_enfermeria_cronicas_am,
            'total_enfermeria_otros': total_enfermeria_otros,
            'total_enfermeria_prev_anemia': total_enfermeria_prev_anemia,
            'total_psicologia_atenciones': total_atenciones_psicologia_df,
            'total_trasocial_atenciones': total_atenciones_trasocial_df,
            'total_proc_tera_atenciones': total_atenciones_proc_tera_df,
            'total_terap_indiv_atenciones': total_terap_indiv_df,
            'total_terap_par_fam_atenciones': total_terap_par_fam_df,
            'total_terap_grup_atenciones': total_terap_grup_df,
            'total_proc_diag_atenciones': total_proc_diag_df,
        }

        tables = {
            'atenciones_prenatal_por_sub_act': atenciones_prenatal_df_agru,
            'atenciones_familiar_por_sub_act': atenciones_familiar_df_agru,
            'atenciones_complementarias_por_sub_act': atenciones_complementarias_df_agru,
            'atenciones_preconcepcional_por_sub_act': atenciones_preconcepcional_df_agru,
            'atenciones_domiciliaria_por_sub_act': atenciones_domiciliaria_df_agru,
            'atenciones_grupal_por_sub_act': atenciones_grupal_df_agru,
            'atenciones_psicoprofilaxis_por_sub_act': atenciones_psicoprofilaxis_df_agru,
            'atenciones_consejeria_por_sub_act': atenciones_consejeria_df_agru,
            'nutricion_individual_por_sub_act': nutricion_total_df_agru,
            'enfermeria_tuberculosis_por_sub_act': atenciones_tuberculosis_df_agru,
            'enfermeria_vih_por_sub_act': atenciones_vih_df_agru,
            'enfermeria_cronicas_am_por_sub_act': atenciones_cronicas_am_df_agru,
            'enfermeria_otros_por_sub_act': atenciones_enfermeria_otros_df_agru,
            'enfermeria_prev_anemia_por_sub_act': atenciones_prev_anemia_df_agru,
            'terap_indiv_por_sub_act': total_terap_indiv_df_agru,
            'terap_par_fam_por_sub_act': total_terap_par_fam_df_agru,
            'terap_grup_por_sub_act': total_terap_grup_df_agru, 
        }

        return {
            'nombre_centro': nombre_centro,
            'stats': stats,
            'tables': tables
        }

    def load_dashboard_data_complementaria(periodo, anio, codcas, engine, tipo_asegurado_value=DEFAULT_TIPO_ASEGURADO):
        return _load_dashboard_data(periodo, anio, codcas, engine, build_queries_complementaria, tipo_asegurado_value)

    def load_dashboard_data_programas(periodo, anio, codcas, engine, tipo_asegurado_value=DEFAULT_TIPO_ASEGURADO):
        return _load_dashboard_data(periodo, anio, codcas, engine, build_queries_programas, tipo_asegurado_value)

    def load_dashboard_data_nutricion(periodo, anio, codcas, engine, tipo_asegurado_value=DEFAULT_TIPO_ASEGURADO):
        return _load_dashboard_data(periodo, anio, codcas, engine, build_queries_nutricion, tipo_asegurado_value)

    def load_dashboard_data_enfermeria(periodo, anio, codcas, engine, tipo_asegurado_value=DEFAULT_TIPO_ASEGURADO):
        return _load_dashboard_data(periodo, anio, codcas, engine, build_queries_enfermeria, tipo_asegurado_value)

    def load_dashboard_data_psicologia(periodo, anio, codcas, engine, tipo_asegurado_value=DEFAULT_TIPO_ASEGURADO):
        return _load_dashboard_data(periodo, anio, codcas, engine, build_queries_psicologia, tipo_asegurado_value)

    def load_dashboard_data_trasocial(periodo, anio, codcas, engine, tipo_asegurado_value=DEFAULT_TIPO_ASEGURADO):
        return _load_dashboard_data(periodo, anio, codcas, engine, build_queries_trasocial, tipo_asegurado_value)

    # if 'build_trasocial_cards' not in locals():
    #     build_trasocial_cards = create_cards_builder(TRASOCIAL_CARD_TEMPLATE)
    
    def load_dashboard_data_trasocial(periodo, anio, codcas, engine, tipo_asegurado_value=DEFAULT_TIPO_ASEGURADO):
        return _load_dashboard_data(periodo, anio, codcas, engine, build_queries_trasocial, tipo_asegurado_value)

    def load_dashboard_data_proc(periodo, anio, codcas, engine, tipo_asegurado_value=DEFAULT_TIPO_ASEGURADO):
        return _load_dashboard_data(periodo, anio, codcas, engine, build_queries_proc_tera, tipo_asegurado_value)
    
    def load_dashboard_data_proc_diag(periodo, anio, codcas, engine, tipo_asegurado_value=DEFAULT_TIPO_ASEGURADO):
        return _load_dashboard_data(periodo, anio, codcas, engine, build_queries_proc_diag, tipo_asegurado_value)


    DASHBOARD_TABS = [
        TabConfig(
            key="complementaria",
            label="Obstetrícia",
            value='tab-complementaria',
            filter_ids=FilterIds(
                periodo='filter-periodo-complementaria',
                anio='filter-anio-complementaria',
                tipo='filter-tipo-asegurado-complementaria'
            ),
            search_button_id='search-button-complementaria',
            download_button_id='download-button-complementaria',
            download_component_id='download-dataframe-csv-complementaria',
            back_button_id='back-button-complementaria',
            summary_container_id='summary-container-complementaria',
            charts_container_id='charts-container-complementaria',
            data_loader=load_dashboard_data_complementaria,
            cards_builder=build_complementaria_cards
        ),
        TabConfig(
            key="programas",
            label="Preventivo promocional",
            value='tab-programas',
            filter_ids=FilterIds(
                periodo='filter-periodo-programas',
                anio='filter-anio-programas',
                tipo='filter-tipo-asegurado-programas'
            ),
            search_button_id='search-button-programas',
            download_button_id='download-button-programas',
            download_component_id='download-dataframe-csv-programas',
            back_button_id='back-button-programas',
            summary_container_id='summary-container-programas',
            charts_container_id='charts-container-programas',
            data_loader=load_dashboard_data_programas,
            cards_builder=build_programas_cards
        ),
        TabConfig(
            key="nutricion",
            label="Nutrición",
            value='tab-nutricion',
            filter_ids=FilterIds(
                periodo='filter-periodo-nutricion',
                anio='filter-anio-nutricion',
                tipo='filter-tipo-asegurado-nutricion'
            ),
            search_button_id='search-button-nutricion',
            download_button_id='download-button-nutricion',
            download_component_id='download-dataframe-csv-nutricion',
            back_button_id='back-button-nutricion',
            summary_container_id='summary-container-nutricion',
            charts_container_id='charts-container-nutricion',
            data_loader=load_dashboard_data_nutricion,
            cards_builder=build_nutricion_cards
        ),
        TabConfig(
            key="enfermeria",
            label="Enfermería",
            value='tab-enfermeria',
            filter_ids=FilterIds(
                periodo='filter-periodo-enfermeria',
                anio='filter-anio-enfermeria',
                tipo='filter-tipo-asegurado-enfermeria'
            ),
            search_button_id='search-button-enfermeria',
            download_button_id='download-button-enfermeria',
            download_component_id='download-dataframe-csv-enfermeria',
            back_button_id='back-button-enfermeria',
            summary_container_id='summary-container-enfermeria',
            charts_container_id='charts-container-enfermeria',
            data_loader=load_dashboard_data_enfermeria,
            cards_builder=build_enfermeria_cards
        ),
        TabConfig(
            key="psicologia",
            label="Psicología",
            value='tab-psicologia',
            filter_ids=FilterIds(
                periodo='filter-periodo-psicologia',
                anio='filter-anio-psicologia',
                tipo='filter-tipo-asegurado-psicologia'
            ),
            search_button_id='search-button-psicologia',
            download_button_id='download-button-psicologia',
            download_component_id='download-dataframe-csv-psicologia',
            back_button_id='back-button-psicologia',
            summary_container_id='summary-container-psicologia',
            charts_container_id='charts-container-psicologia',
            data_loader=load_dashboard_data_psicologia,
            cards_builder=build_psicologia_cards
        ),
        TabConfig(
            key="trasocial",
            label="Trabajo social",
            value='tab-trasocial',
            filter_ids=FilterIds(
                periodo='filter-periodo-trasocial',
                anio='filter-anio-trasocial',
                tipo='filter-tipo-asegurado-trasocial'
            ),
            search_button_id='search-button-trasocial',
            download_button_id='download-button-trasocial',
            download_component_id='download-dataframe-csv-trasocial',
            back_button_id='back-button-trasocial',
            summary_container_id='summary-container-trasocial',
            charts_container_id='charts-container-trasocial',
            data_loader=load_dashboard_data_trasocial,
            cards_builder=build_trasocial_cards
        ),
        TabConfig(
            key="proc_tera",
            label="Procedimientos terapéuticos",
            value='tab-proc-tera',
            filter_ids=FilterIds(
                periodo='filter-periodo-proc-tera',
                anio='filter-anio-proc-tera',
                tipo='filter-tipo-asegurado-proc-tera'
            ),
            search_button_id='search-button-proc-tera',
            download_button_id='download-button-proc-tera',
            download_component_id='download-dataframe-csv-proc-tera',
            back_button_id='back-button-proc-tera',
            summary_container_id='summary-container-proc-tera',
            charts_container_id='charts-container-proc-tera',
            data_loader=load_dashboard_data_proc,
            cards_builder=build_proc_tera_cards
        ),
    
            TabConfig(
            key="proc_diag",
            label="Procedimientos diagnósticos",
            value='tab-proc-diag',
            filter_ids=FilterIds(
                periodo='filter-periodo-proc-diag',
                anio='filter-anio-proc-diag',
                tipo='filter-tipo-asegurado-proc-diag'
            ),
            search_button_id='search-button-proc-diag',
            download_button_id='download-button-proc-diag',
            download_component_id='download-dataframe-csv-proc-diag',
            back_button_id='back-button-proc-diag',
            summary_container_id='summary-container-proc-diag',
            charts_container_id='charts-container-proc-diag',
            data_loader=load_dashboard_data_proc_diag,
            cards_builder=build_proc_diag_cards
        ),
    ]

    def build_download_response(periodo, anio, pathname, tipo_asegurado_value, data_loader, include_citas=True, include_desercion=True):
        if not periodo or not pathname or not anio:
            return None
        codcas_url = pathname.rstrip('/').split('/')[-1] if pathname else None
        codcas = sc.decode_code(codcas_url) if codcas_url else None
        if not codcas:
            return None
        engine = create_connection()
        if engine is None:
            return None
        data = data_loader(periodo, anio, codcas, engine, tipo_asegurado_value)
        if not data:
            return None
        stats = data['stats']
        tables = data['tables']
        indicadores_rows = [
            ("Total de Consultas", stats.get('total_atenciones', 0)),
            ("Consulta prenatal", stats.get('total_atenciones_prenatal', 0)),
            ("Consultas familiar", stats.get('total_atenciones_familiar', 0)),
            ("Consultas complementarias", stats.get('total_atenciones_complementarias', 0)),
            ("Consultas preconcepcional", stats.get('total_atenciones_preconcepcional', 0)),
            ("Total programa", stats.get('total_atenciones_p', 0)),
            ("Visitas domiciliarias", stats.get('total_atenciones_domiciliaria', 0)),
            ("Sesiones grupales", stats.get('total_atenciones_grupal', 0)),
            ("Psicoprofilaxis", stats.get('total_atenciones_psicoprofilaxis', 0)),
            ("Consejería", stats.get('total_atenciones_consejeria', 0)),
            ("Total atenciones nutrición", stats.get('total_nutricion_atenciones', 0)),
            ("Total atenciones enfermería", stats.get('total_enfermeria_atenciones', 0)),
            ("Atención en Tuberculosis", stats.get('total_enfermeria_tuberculosis', 0)),
            ("Atención en ITS-HIV/SIDA", stats.get('total_enfermeria_vih', 0)),
            ("Atención en Enfermedades crónicas no trasmisibles-adulto mayor", stats.get('total_enfermeria_cronicas_am', 0)),
            ("Otras actividades ambulatorias", stats.get('total_enfermeria_otros', 0)),
            ("Atención en prevención y control de la anemia", stats.get('total_enfermeria_prev_anemia', 0)),
            ("Total atenciones psicología", stats.get('total_psicologia_atenciones', 0)),
            ("Total atenciones trabajo social", stats.get('total_trasocial_atenciones', 0)),
        ]
        if include_citas:
            indicadores_rows.append(("Total Citados", stats.get('total_citados', 0)))
        if include_desercion:
            indicadores_rows.append(("Total Desercion de Citas", stats.get('total_desercion_citas', 0)))

        indicadores = pd.DataFrame(indicadores_rows, columns=['Indicador', 'Valor'])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            indicadores.to_excel(writer, sheet_name="Indicadores", index=False)
            for sheet_key, dataframe in tables.items():
                sheet_name = sheet_key[:31]
                dataframe.to_excel(writer, sheet_name=sheet_name or "Tabla", index=False)
        output.seek(0)
        filename = f"reporte_{codcas}_{anio}_{periodo}.xlsx"
        return dcc.send_bytes(output.getvalue(), filename)


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
                        html.Div([
                            html.I(className="bi bi-hospital", style={'fontSize': '30px', 'color': BRAND, 'marginRight': '10px'}),
                            html.H2(
                                "Consulta externa - No médicas",
                                style={
                                    'color': BRAND,
                                    'fontFamily': FONT_FAMILY,
                                    'fontSize': '26px',
                                    'fontWeight': 800,
                                    'margin': '0'
                                }
                            ),
                        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '8px'}),
                        dbc.Button(
                            [html.I(className="bi bi-file-earmark-arrow-down me-2"), "Ficha técnica"],
                            id='download-ficha-tecnica-button-nm',
                            color='light',
                            outline=True,
                            size='sm',
                            style={
                                'borderColor': BRAND,
                                'color': BRAND,
                                'fontFamily': FONT_FAMILY,
                                'fontWeight': '600',
                                'borderRadius': '8px',
                                'padding': '4px 12px'
                            }
                        ),
                        dcc.Download(id='download-ficha-tecnica-nm')
                    ], style={'display': 'flex', 'alignItems': 'center', 'gap': '12px', 'flexWrap': 'wrap'}),
                    dbc.Tooltip(
                        "Descargar ficha técnica",
                        target='download-ficha-tecnica-button-nm',
                        placement='bottom',
                        style={'zIndex': 9999}
                    ),
                    html.P(
                        f"Informacion actualizada al 31/12/2025 | Sistema de Gestion Estadística",
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

            tabs_component = dcc.Tabs(
                id='dashboard-tabs',
                value=DASHBOARD_TABS[0].value,
                children=[build_tab_panel(tab) for tab in DASHBOARD_TABS],
                style={'backgroundColor': 'transparent', 'marginBottom': '0'},
                content_style={'padding': '0', 'border': 'none', 'marginTop': '-1px'}
            )

            main_dashboard = html.Div([
                header,
                html.Br(),
                tabs_component
            ], id='main-dashboard-content')

            content = html.Div([
                dcc.Location(id='url', refresh=True),
                main_dashboard,
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
            html.P('Debes iniciar sesion para ver el dashboard.'),
            dbc.Button(
                'Volver',
                id='unauth-back-button-nm',
                color='primary',
                href='javascript:history.back();',
                external_link=True,
                style={'marginTop': '12px'}
            )
        ])

    def register_summary_callback(tab_config):
        @dash_app.callback(
            [Output(tab_config.summary_container_id, 'children'),
             Output(tab_config.charts_container_id, 'children')],
            Input(tab_config.search_button_id, 'n_clicks'),
            State(tab_config.filter_ids.periodo, 'value'),
            State(tab_config.filter_ids.anio, 'value'),
            State(tab_config.filter_ids.tipo, 'value'),
            State('url', 'pathname')
        )
        def _handle_summary(n_clicks, periodo, anio_value, tipo_asegurado_value, pathname, tab=tab_config):
            if not n_clicks:
                return html.Div(), html.Div()

            data, error_component, codcas_url = fetch_dashboard_payload(
                periodo,
                anio_value,
                tipo_asegurado_value,
                pathname,
                tab.data_loader
            )

            if error_component:
                return error_component, html.Div()

            tipo_filter = tipo_asegurado_value or DEFAULT_TIPO_ASEGURADO
            subtitle = f"Periodo {anio_value}-{periodo} | {data['nombre_centro']}"
            base_path = url_base_pathname.rstrip('/') + '/'
            cards_builder = tab.cards_builder or build_complementaria_cards
            cards = cards_builder(data, periodo, anio_value, tipo_filter, codcas_url, base_path)
            summary_row = build_summary_layout(cards, subtitle)
            return summary_row, html.Div()

    for tab_config in DASHBOARD_TABS:
        register_summary_callback(tab_config)

    @dash_app.callback(
        Output('main-dashboard-content', 'style'),
        Output('page-container-wrapper', 'style'),
        Input('url', 'pathname')
    )
    def toggle_main_content(pathname):
        base = url_base_pathname.rstrip('/') + '/'
        if pathname and pathname.startswith(f"{base}dash/"):
            return {'display': 'none'}, {'display': 'block'}
        return {'display': 'block'}, {'display': 'none'}

    primary_filters = DASHBOARD_TABS[0].filter_ids

    def register_filter_sync(target_filters):
        @dash_app.callback(
            Output(target_filters.periodo, 'value'),
            Output(target_filters.anio, 'value'),
            Output(target_filters.tipo, 'value'),
            Input(primary_filters.periodo, 'value'),
            Input(primary_filters.anio, 'value'),
            Input(primary_filters.tipo, 'value')
        )
        def _sync_filters(periodo_value, anio_value, tipo_asegurado_value, _target=target_filters):
            return periodo_value, anio_value, tipo_asegurado_value or DEFAULT_TIPO_ASEGURADO

    for tab_config in DASHBOARD_TABS[1:]:
        register_filter_sync(tab_config.filter_ids)

    def register_download_callback(tab_config):
        @dash_app.callback(
            Output(tab_config.download_component_id, "data"),
            Input(tab_config.download_button_id, "n_clicks"),
            State(tab_config.filter_ids.periodo, 'value'),
            State(tab_config.filter_ids.anio, 'value'),
            State(tab_config.filter_ids.tipo, 'value'),
            State('url', 'pathname'),
            prevent_initial_call=True
        )
        def _download(n_clicks, periodo, anio_value, tipo_asegurado_value, pathname, tab=tab_config):
            if not n_clicks:
                return None
            return build_download_response(
                periodo,
                anio_value,
                pathname,
                tipo_asegurado_value,
                tab.data_loader,
                include_citas=tab.include_citas,
                include_desercion=tab.include_desercion
            )

    for tab_config in DASHBOARD_TABS:
        register_download_callback(tab_config)

    @dash_app.callback(
        Output('download-ficha-tecnica-nm', 'data'),
        Input('download-ficha-tecnica-button-nm', 'n_clicks'),
        prevent_initial_call=True
    )
    def download_ficha_tecnica(n_clicks):
        if not n_clicks:
            return dash.no_update

        engine = create_connection()
        ficha = fetch_ficha_tecnica(engine)
        if not ficha:
            return dash.no_update

        filename, pdf_bytes = ficha
        return dcc.send_bytes(pdf_bytes, filename)

    dash_app.layout = serve_layout
    return dash_app
