import io
import importlib
import json
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
from dash.dependencies import ALL
from flask import has_request_context
from flask_login import current_user
from sqlalchemy import text

import secure_code as sc


def create_dash_app(flask_app, url_base_pathname='/dashboard_odo/'):
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

    TAB_SECTION_BASE_STYLE = {
        "width": "100%",
        "transition": "opacity 0.2s ease"
    }
    NAV_BUTTON_BASE_CLASS = "dashboard-nav-btn"

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
        
        # Solo esquinas inferiores redondeadas
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

        def _import_children(package, package_name):
            for module in pkgutil.iter_modules(package.__path__):
                mod_name = f"{package_name}.{module.name}"
                try:
                    loaded_module = importlib.import_module(mod_name)
                    print(f"[Dash Pages] Página importada: {mod_name}")
                    if module.ispkg:
                        _import_children(loaded_module, mod_name)
                except Exception as exc:
                    print(f"[Dash Pages] Error importando {mod_name}: {exc}")

        _import_children(pkg, pkg_name)

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
        is_placeholder: bool = False
        placeholder_message: Optional[str] = None

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

    def build_nav_button(tab_config):
        return dbc.Button(
            html.Span(tab_config.label, className='dashboard-nav-btn-label'),
            id={'type': 'tab-nav-button_odo', 'value': tab_config.value},
            color='light',
            className=NAV_BUTTON_BASE_CLASS,
            n_clicks=0,
            style={'minWidth': '180px'}
        )

    def build_tab_section(tab_config, is_active=False):
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
                    'zIndex': 4000
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

        section_style = {
            **TAB_SECTION_BASE_STYLE,
            'display': 'block' if is_active else 'none'
        }

        return html.Div([
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
            dbc.Row(
                [dbc.Col(html.Div(id=tab_config.charts_container_id), width=12)],
                style={'marginTop': '16px', 'marginBottom': '24px'}
            ),
        ], id=f'tab-{tab_config.key}-content_odo', className='dashboard-tab-section', style=section_style)

    def build_required_params_message(message=None):
        subtitle = message or (
            "Por favor, seleccione un año y un periodo y asegúrese de tener un centro válido."
        )
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
            html.P(subtitle, style={
                'color': MUTED,
                'fontFamily': FONT_FAMILY
            })
        ], style={
            'textAlign': 'center',
            'padding': '60px',
            'backgroundColor': CARD_BG,
            'borderRadius': '16px',
            'boxShadow': '0 10px 30px rgba(0,0,0,0.08)'
        })

    def fetch_dashboard_payload(periodo, anio_value, tipo_asegurado_value, pathname, data_loader):
        if not periodo or not anio_value:
            return None, build_required_params_message(), None

        codcas_url = pathname.rstrip('/').split('/')[-1] if pathname else None
        codcas = sc.decode_code(codcas_url) if codcas_url else None

        if not codcas:
            return None, build_required_params_message(), None

        engine = create_connection()
        if engine is None:
            return None, html.Div("Error de conexion a la base de datos."), None

        data = data_loader(periodo, anio_value, codcas, engine, tipo_asegurado_value)
        if not data:
            return None, html.Div("Sin datos para mostrar."), None

        return data, None, codcas_url

    def build_atenciones_cards(data, periodo, anio_value, tipo_filter, codcas_url, base_path):
        stats = data['stats']
        tables = data['tables']
        total_consultantes_por_servicio_table = tables['consultantes_por_servicio']
        total_consultantes_servicio = (
            int(total_consultantes_por_servicio_table['counts'].sum())
            if (not total_consultantes_por_servicio_table.empty and 'counts' in total_consultantes_por_servicio_table)
            else 0
        )
        total_atenciones_agru = tables['atenciones_por_agrupador']
        medicos_por_agrupador_table = tables['medicos_por_agrupador']
        horas_programadas_table = tables['horas_programadas_por_agrupador']
        horas_efectivas_por_agrupador_table = tables.get('horas_efectivas_por_agrupador', pd.DataFrame(columns=['agrupador', 'counts']))

        detail_query = f"?periodo={periodo}&anio={anio_value}&codasegu={quote_plus(tipo_filter)}"
        base = base_path

        return [
            {
                "title": "Total de consultantes a la atención médica",
                "value": f"{stats['total_consultantes']:,.0f}",
                "border_color": ACCENT,
            },
            {
                "title": "Total de consultantes al servicio",
                "value": f"{total_consultantes_servicio:,.0f}",
                "border_color": ACCENT,
                "side_component": render_agrupador_table(total_consultantes_por_servicio_table),
            },
            {
                "title": "Total de Consultas",
                "value": f"{stats['total_atenciones']:,.0f}",
                "border_color": BRAND,
                ##"href": f"{base}dash/total_atenciones/{codcas_url}{detail_query}",
                "side_component": render_agrupador_table(total_atenciones_agru),
            },
            {
                "title": "Número de Médicos",
                "value": f"{stats['total_medicos']:,.0f}",
                "border_color": BRAND_SOFT,
                ##"href": f"{base}dash/total_medicos/{codcas_url}{detail_query}",
                "side_component": render_agrupador_table(medicos_por_agrupador_table),
            },
            {
                "title": "Total horas programadas",
                "value": f"{stats['total_horas_programadas']:,.0f}",
                "border_color": BRAND,
                ##"href": f"{base}dash/horas_programadas/{codcas_url}{detail_query}",
                "side_component": render_agrupador_table(horas_programadas_table, value_format="{:,.2f}"),
            },
            {
                "title": "Total de horas Efectivas (Ejecutada)",
                "value": f"{stats['total_horas_efectivas']:,.0f}",
                "border_color": ACCENT,
                ##"href": f"{base}dash/horas_efectivas/{codcas_url}{detail_query}",
                "side_component": render_agrupador_table(
                    horas_efectivas_por_agrupador_table,
                    value_format="{:,.2f}"
                ),
            },
        ]

    def create_generic_cards_builder(primary_title, link_map=None):
        link_map = link_map or {}

        def _builder(data, periodo=None, anio_value=None, tipo_filter=None, codcas_url=None, base_path=None, *_):
            stats = data['stats']
            tables = data['tables']
            total_consultantes_por_servicio_table = tables['consultantes_por_servicio']
            total_consultantes_servicio = (
                int(total_consultantes_por_servicio_table['counts'].sum())
                if (not total_consultantes_por_servicio_table.empty and 'counts' in total_consultantes_por_servicio_table)
                else 0
            )
            total_atenciones_agru = tables['atenciones_por_agrupador']
            medicos_por_agrupador_table = tables['medicos_por_agrupador']
            horas_programadas_table = tables['horas_programadas_por_agrupador']
            horas_efectivas_por_agrupador_table = tables.get(
                'horas_efectivas_por_agrupador',
                pd.DataFrame(columns=['agrupador', 'counts'])
            )

            detail_query = ""
            if periodo and anio_value:
                tipo_value = quote_plus(tipo_filter or 'Todos')
                detail_query = f"?periodo={periodo}&anio={anio_value}&codasegu={tipo_value}"

            def resolve_href(card_key):
                target = link_map.get(card_key)
                if not target or not codcas_url or not base_path:
                    return None
                if callable(target):
                    return target(
                        periodo=periodo,
                        anio=anio_value,
                        tipo=tipo_filter,
                        codcas=codcas_url,
                        base_path=base_path,
                        detail_query=detail_query
                    )
                return f"{base_path}{target.format(codcas=codcas_url)}{detail_query}"

            return [
                {
                    "title": primary_title,
                    "value": f"{stats['total_consultantes']:,.0f}",
                    "border_color": ACCENT,
                    "href": resolve_href('total_consultantes'),
                },
                {
                    "title": "Total de consultantes al servicio",
                    "value": f"{total_consultantes_servicio:,.0f}",
                    "border_color": ACCENT,
                    "href": resolve_href('total_consultantes_servicio'),
                    "side_component": render_agrupador_table(
                        total_consultantes_por_servicio_table,
                        title="Consultantes por servicio"
                    ),
                },
                {
                    "title": "Total de Consultas",
                    "value": f"{stats['total_atenciones']:,.0f}",
                    "border_color": BRAND,
                    "href": resolve_href('total_consultas'),
                    "side_component": render_agrupador_table(total_atenciones_agru),
                },
                {
                    "title": "Total de Médicos",
                    "value": f"{stats['total_medicos']:,.0f}",
                    "border_color": BRAND_SOFT,
                    "href": resolve_href('total_medicos'),
                    "side_component": render_agrupador_table(medicos_por_agrupador_table),
                },
                {
                    "title": "Total horas programadas",
                    "value": f"{stats['total_horas_programadas']:,.0f}",
                    "border_color": BRAND,
                    "href": resolve_href('horas_programadas'),
                    "side_component": render_agrupador_table(
                        horas_programadas_table,
                        value_format="{:,.2f}"
                    ),
                },
                {
                    "title": "Total de Horas Efectivas",
                    "value": f"{stats['total_horas_efectivas']:,.0f}",
                    "border_color": ACCENT,
                    "href": resolve_href('horas_efectivas'),
                    "side_component": render_agrupador_table(
                        horas_efectivas_por_agrupador_table,
                        value_format="{:,.2f}"
                    ),
                },
            ]

        return _builder

    DEFAULT_TIPO_ASEGURADO = 'Todos'
    TIPO_ASEGURADO_SQL = {
        'Asegurado': "('1')",
        'No Asegurado': "('2')",
        'Todos': "('1','2')"
    }

    def resolve_tipo_asegurado_clause(selection):
        normalized = selection if selection in TIPO_ASEGURADO_SQL else DEFAULT_TIPO_ASEGURADO
        return TIPO_ASEGURADO_SQL[normalized]

    FICHA_TECNICA_ID = 13

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

    def create_connection():
        from extensions import get_dw_engine
        return get_dw_engine()

    def build_queries_consulta(anio_str, periodo_str, params):
        codasegu = params.get('codasegu', TIPO_ASEGURADO_SQL[DEFAULT_TIPO_ASEGURADO])
        queries = [
            ("atenciones", text(f"""
                SELECT 
                    ce.cod_servicio,
                    ce.cod_especialidad,
                    ca.cenasides,
                    ag.agrupador AS agrupador,
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
                    CASE WHEN ce.cod_tipo_paciente = '4' THEN '2' ELSE '1' END AS cod_tipo_paciente,
                    sexo,
                    fecha_atencion,
                    acto_med
                FROM dwsge.dw_consulta_externa_odonto_homologacion_{anio_str}_{periodo_str} AS ce
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
                LEFT JOIN dwsge.dim_agrupador as ag ON ce.cod_agrupador = ag.cod_agrupador
                WHERE ce.cod_centro = :codcas
                AND ce.cod_servicio = 'E11'
                AND ce.cod_actividad = '91'
                AND ce.cod_subactividad in ('003','004','074','262')
                AND (
                        CASE 
                            WHEN ce.cod_tipo_paciente = '4' THEN '2'
                            ELSE '1'
                        END
                        ) IN {codasegu}
            """),
            params.copy()),
            ("horas_efectivas", text(f"""
                SELECT 
                    ce.*,
                    c.servhosdes,
                    e.especialidad,
                    a.actespnom,
                    am.actdes,
                    ag.agrupador,
                    ca.cenasides
                FROM dwsge.dwe_consulta_externa_horas_efectivas_nm_{anio_str}_{periodo_str} AS ce
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
                LEFT JOIN dwsge.dim_agrupador as ag ON ce.cod_agrupador = ag.cod_agrupador
                WHERE ce.cod_centro = :codcas
                AND ce.cod_servicio = 'E11'
                AND ce.cod_actividad = '91'
                AND ce.cod_subactividad in ('003','004','074','262')
                AND ce.ate>0
            """),
            params.copy()),
            ("horas_programadas", text(f"""
                SELECT 
                    p.*,
                    c.servhosdes,
                    e.especialidad,
                    ag.agrupador,
                    a.actespnom,
                    am.actdes,
                    ca.cenasides 
                FROM dwsge.dwe_consulta_externa_horas_efectivas_nm_{anio_str}_{periodo_str} p
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
                LEFT JOIN dwsge.dim_agrupador as ag ON p.cod_agrupador = ag.cod_agrupador
                WHERE  (
                        p.cod_mot_suspension IS NULL 
                        OR p.cod_mot_suspension NOT IN ('04','09','10','99','13','16','11')
                    )
                AND p.cod_centro = :codcas
                AND p.cod_servicio = 'E11'
                AND p.cod_actividad = '91'
                AND p.cod_subactividad in ('003','004','074','262')
            """),
            params.copy()),
            ("medicos_agrup", text(f"""
                SELECT c.cod_centro,
                    c.dni_medico,
                    c.agrupador,
                    c.periodo,
                    c.cantidad_medicos,
                    c.medico
                FROM ( SELECT b.cod_centro,
                            b.dni_medico,
                            b.agrupador,
                            b.periodo,
                            b.cantidad_medicos,
                            row_number() OVER (PARTITION BY b.cod_centro, b.dni_medico, b.periodo ORDER BY b.cantidad_medicos DESC) AS medico
                        FROM ( SELECT a.cod_centro,
                                    a.dni_medico,
                                    ag.agrupador,
                                    a.periodo,
                                    CASE WHEN a.cod_tipo_paciente = '4' THEN '2' ELSE '1' END AS cod_tipo_paciente,
                                    count(*) AS cantidad_medicos
                                FROM (SELECT * FROM dwsge.dw_consulta_externa_odonto_homologacion_{anio_str}_{periodo_str}) a
                                LEFT JOIN dwsge.dim_agrupador ag 
                                ON a.cod_agrupador = ag.cod_agrupador
                                WHERE a.cod_centro=:codcas
                                AND a.cod_servicio = 'E11'
                                AND a.cod_actividad = '91'
                                AND a.cod_subactividad in ('003','004','074','262')
                                GROUP BY a.cod_centro, a.dni_medico, ag.agrupador, a.periodo,CASE WHEN a.cod_tipo_paciente = '4' THEN '2' ELSE '1' END
                                ORDER BY a.dni_medico, a.periodo, (count(*))) b) c
                WHERE c.medico = '1'::bigint
            """),
            params.copy()),
        ]
        primera_vez = text(f"""
            WITH fecha_min_paciente AS (
                SELECT cod_oricentro,cod_centro,doc_paciente,
                    CASE WHEN cod_tipo_paciente = '4' THEN '2' ELSE '1' END AS cod_tipo_paciente,
                       to_char(MIN(to_date(fecha_atencion,'DD/MM/YYYY')),'YYYYMM') periodo
                FROM dwsge.dw_consulta_externa_odonto_homologacion_{anio_str}
                WHERE  cod_servicio = 'E11'
                AND cod_actividad = '91'
                AND cod_subactividad in ('003','004','074','262')
                AND cod_centro=:codcas
                AND (
                        CASE 
                            WHEN cod_tipo_paciente = '4' THEN '2'
                            ELSE '1'
                        END
                        ) IN {codasegu}
                GROUP BY cod_oricentro,cod_centro,doc_paciente,CASE WHEN cod_tipo_paciente = '4' THEN '2' ELSE '1' END
            )
            SELECT COUNT(DISTINCT doc_paciente) AS cantidad
            FROM fecha_min_paciente WHERE periodo=:periodo_sql
        """)
        primera_vez_agr = text(f"""
            WITH fecha_min_paciente AS (
                SELECT p.doc_paciente,ag.agrupador,
                    CASE WHEN p.cod_tipo_paciente = '4' THEN '2' ELSE '1' END AS cod_tipo_paciente,
                       to_char(MIN(to_date(p.fecha_atencion,'DD/MM/YYYY')),'YYYYMM') periodo
                FROM dwsge.dw_consulta_externa_odonto_homologacion_{anio_str} p
                LEFT JOIN dwsge.dim_agrupador ag ON p.cod_agrupador = ag.cod_agrupador
                WHERE p.cod_servicio = 'E11'
                AND p.cod_actividad = '91'
                AND p.cod_subactividad in ('003','004','074','262')
                AND p.cod_centro=:codcas
                AND (
                        CASE 
                            WHEN p.cod_tipo_paciente = '4' THEN '2'
                            ELSE '1'
                        END
                        ) IN {codasegu}
                GROUP BY p.doc_paciente,ag.agrupador,CASE WHEN cod_tipo_paciente = '4' THEN '2' ELSE '1' END
            )
            SELECT agrupador,COUNT(DISTINCT doc_paciente) AS cantidad
            FROM fecha_min_paciente WHERE periodo=:periodo_sql GROUP BY agrupador
        """)
        return {
            "queries": queries,
            "primeras_consultas_query": primera_vez,
            "primeras_consultas_agrupador_query": primera_vez_agr,
        }

    def _load_dashboard_data(periodo, anio, codcas, engine, query_builder, tipo_asegurado_value):
        if not periodo or not codcas or not anio:
            return None
        from extensions import validate_anio_periodo
        try:
            anio_str, periodo_str = validate_anio_periodo(anio, periodo)
        except ValueError:
            return None
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

        patient_stmt = builder_payload.get("primeras_consultas_query")
        df7 = (
            pd.read_sql(patient_stmt, engine, params={"codcas": codcas, "periodo_sql": periodo_sql})
            if patient_stmt is not None else pd.DataFrame()
        )
        patient_agr_stmt = builder_payload.get("primeras_consultas_agrupador_query")
        df8 = (
            pd.read_sql(patient_agr_stmt, engine, params={"codcas": codcas, "periodo_sql": periodo_sql})
            if patient_agr_stmt is not None else pd.DataFrame()
        )

        atenciones_df = results.get("atenciones", pd.DataFrame())
        horas_efectivas_df = results.get("horas_efectivas", pd.DataFrame())
        if not horas_efectivas_df.empty and 'horas_efec_def' in horas_efectivas_df:
            horas_efectivas_df['horas_efec_def'] = pd.to_numeric(
                horas_efectivas_df['horas_efec_def'], errors='coerce'
            ).fillna(0)
        horas_efectivas_df_agru = (
            horas_efectivas_df.groupby('agrupador', dropna=False)['horas_efec_def']
            .sum()
            .reset_index(name='counts')
            .sort_values('counts', ascending=False)
            if (
                not horas_efectivas_df.empty
                and 'agrupador' in horas_efectivas_df
                and 'horas_efec_def' in horas_efectivas_df
            )
            else pd.DataFrame(columns=['agrupador', 'counts'])
        )
        horas_programadas_df = results.get("horas_programadas", pd.DataFrame())
        medicos_agr = results.get("medicos_agrup", pd.DataFrame())

        if not horas_programadas_df.empty and 'total_horas' in horas_programadas_df:
            horas_programadas_df['total_horas'] = pd.to_numeric(horas_programadas_df['total_horas'], errors='coerce').fillna(0)

        nombre_centro_values = atenciones_df['cenasides'].dropna().unique() if 'cenasides' in atenciones_df else []
        nombre_centro = nombre_centro_values[0] if len(nombre_centro_values) > 0 else codcas

        total_atenciones = len(atenciones_df)
        total_atenciones_agru = (
            atenciones_df.groupby(["agrupador"])
            .size()
            .reset_index(name='counts')
            .sort_values('counts', ascending=False)
            if not atenciones_df.empty else pd.DataFrame(columns=['agrupador', 'counts'])
        )

        total_consultantes = int(df7['cantidad'].iloc[0]) if not df7.empty else 0
        total_consultantes_por_servicio = (
            df8.rename(columns={"cantidad": "counts"}) if not df8.empty else pd.DataFrame(columns=['agrupador', 'counts'])
        )

        total_medicos = medicos_agr['dni_medico'].nunique() if 'dni_medico' in medicos_agr else 0
        medicos_por_agrupador = (
            medicos_agr.groupby('agrupador')['dni_medico']
            .nunique()
            .reset_index(name='counts')
            .sort_values('counts', ascending=False)
            if not medicos_agr.empty else pd.DataFrame(columns=['agrupador', 'counts'])
        )

        total_horas_efectivas = float(horas_efectivas_df['horas_efec_def'].sum()) if 'horas_efec_def' in horas_efectivas_df else 0
        total_horas_programadas = float(horas_programadas_df['total_horas'].sum()) if 'total_horas' in horas_programadas_df else 0

        horas_programadas_por_agrupador = (
            horas_programadas_df.groupby('agrupador', dropna=False)['total_horas']
            .sum()
            .reset_index(name='counts')
            .sort_values('counts', ascending=False)
            if 'agrupador' in horas_programadas_df else pd.DataFrame(columns=['agrupador', 'counts'])
        )

        if total_horas_efectivas > total_horas_programadas:
            total_horas_efectivas = total_horas_programadas

        if not horas_efectivas_df_agru.empty and not horas_programadas_por_agrupador.empty:
            merged = horas_efectivas_df_agru.merge(
                horas_programadas_por_agrupador[['agrupador', 'counts']],
                on='agrupador',
                how='left',
                suffixes=('_efectivas', '_programadas')
            )
            merged['counts_efectivas'] = merged.apply(
                lambda row: min(row['counts_efectivas'], row['counts_programadas'])
                if pd.notna(row['counts_programadas']) else row['counts_efectivas'],
                axis=1
            )
            horas_efectivas_df_agru = merged[['agrupador', 'counts_efectivas']].rename(
                columns={'counts_efectivas': 'counts'}
            )

        stats = {
            'total_atenciones': total_atenciones,
            'total_consultantes': total_consultantes,
            'total_medicos': total_medicos,
            'total_horas_efectivas': total_horas_efectivas,
            'total_horas_programadas': total_horas_programadas
        }

        tables = {
            'atenciones_por_agrupador': total_atenciones_agru,
            'consultantes_por_servicio': total_consultantes_por_servicio,
            'medicos_por_agrupador': medicos_por_agrupador,
            'horas_programadas_por_agrupador': horas_programadas_por_agrupador,
            'horas_efectivas_por_agrupador': horas_efectivas_df_agru
        }

        return {
            'nombre_centro': nombre_centro,
            'stats': stats,
            'tables': tables
        }

    def load_dashboard_data(periodo, anio, codcas, engine, tipo_asegurado_value=DEFAULT_TIPO_ASEGURADO):
        return _load_dashboard_data(periodo, anio, codcas, engine, build_queries_consulta, tipo_asegurado_value)

    DASHBOARD_TABS = [
        TabConfig(
            key="atenciones",
            label="Sesiones odontológicas",
            value='tab-atenciones',
            filter_ids=FilterIds(
                periodo='filter-periodo_odo',
                anio='filter-anio_odo',
                tipo='filter-tipo-asegurado_odo'
            ),
            search_button_id='search-button_odo',
            download_button_id='download-button_odo',
            download_component_id='download-dataframe-csv_odo',
            back_button_id='back-button_odo',
            summary_container_id='summary-container_odo',
            charts_container_id='charts-container_odo',
            data_loader=load_dashboard_data,
            include_citas=True,
            include_desercion=True,
            cards_builder=build_atenciones_cards
        )
    ]

    def build_download_response(periodo, anio, pathname, tipo_asegurado_value, data_loader, include_citas=True, include_desercion=True):
        from extensions import is_consulta_user
        if is_consulta_user():
            return None
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
            ("Total de Consultas", stats['total_atenciones']),
            ("Total de Consultantes", stats['total_consultantes']),
            ("Total de Medicos", stats['total_medicos']),
            ("Total Horas Efectivas", stats['total_horas_efectivas']),
            ("Total Horas Programadas", stats['total_horas_programadas']),
        ]
        if include_citas:
            indicadores_rows.append(("Total Citados", stats['total_citados']))
        if include_desercion:
            indicadores_rows.append(("Total Desercion de Citas", stats['total_desercion_citas']))
        indicadores = pd.DataFrame(indicadores_rows, columns=['Indicador', 'Valor'])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            indicadores.to_excel(writer, sheet_name="Indicadores_Generales", index=False)
            tables['atenciones_por_agrupador'].to_excel(writer, sheet_name="Atenciones_por_Servicio", index=False)
            tables['consultantes_por_servicio'].to_excel(writer, sheet_name="Consultantes_por_Servicio", index=False)
            tables['medicos_por_agrupador'].to_excel(writer, sheet_name="Medicos_por_Servicio", index=False)
            tables['horas_programadas_por_agrupador'].to_excel(writer, sheet_name="Horas_Programadas_por_Servicio", index=False)
        output.seek(0)
        return dcc.send_bytes(output.getvalue(), f"reporte_{codcas}_{anio}_{periodo}.xlsx")

    def serve_layout():
        if not has_request_context():
            return html.Div()

        if getattr(current_user, "is_authenticated", False):
            engine = create_connection()
            fecha_act_value = fecha_act(engine)
            if not fecha_act_value:
                fecha_act_value = "Sin informacion disponible"
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
                            html.H2([
                                "Consulta externa - Odontológicas",
                                html.Span(
                                    " (En desarrollo- Por validar)",
                                    style={'color': '#dc3545'}
                                )
                            ], style={
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
                            id='download-ficha-tecnica-button_odo',
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
                        dcc.Download(id='download-ficha-tecnica_odo')
                    ], style={'display': 'flex', 'alignItems': 'center', 'gap': '12px', 'flexWrap': 'wrap'}),
                    dbc.Tooltip(
                        "Descargar ficha técnica",
                        target='download-ficha-tecnica-button_odo',
                        placement='bottom',
                        style={'zIndex': 9999}
                    ),
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

            nav_buttons = [build_nav_button(tab) for tab in DASHBOARD_TABS]
            tab_sections = [
                build_tab_section(tab, is_active=(idx == 0))
                for idx, tab in enumerate(DASHBOARD_TABS)
            ]

            tabs_component = html.Div([
                dcc.Store(id='active-dashboard-tab_odo', data=DASHBOARD_TABS[0].value),
                html.Div(nav_buttons, className='dashboard-nav-bar'),
                html.Div(
                    tab_sections,
                    id='tab-content-wrapper_odo',
                    className='dashboard-tab-content-area'
                )
            ], className='dashboard-tab-wrapper')

            main_dashboard = html.Div([
                header,
                html.Br(),
                tabs_component
            ], id='main-dashboard-content_odo')

            content = html.Div([
                dcc.Location(id='url_odo', refresh=True),
                main_dashboard,
                html.Div(
                    children=dash.page_container,
                    id='page-container-wrapper_odo',
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
                id='unauth-back-button',
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
            State('url_odo', 'pathname')
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
            cards_builder = tab.cards_builder or create_generic_cards_builder("Total de consultantes")
            cards = cards_builder(data, periodo, anio_value, tipo_filter, codcas_url, base_path)
            summary_row = build_summary_layout(cards, subtitle)
            return summary_row, html.Div()

    for tab_config in DASHBOARD_TABS:
        register_summary_callback(tab_config)

    @dash_app.callback(
        Output('main-dashboard-content_odo', 'style'),
        Output('page-container-wrapper_odo', 'style'),
        Input('url_odo', 'pathname')
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

    @dash_app.callback(
        Output('active-dashboard-tab_odo', 'data'),
        Input({'type': 'tab-nav-button_odo', 'value': ALL}, 'n_clicks'),
        State('active-dashboard-tab_odo', 'data'),
        prevent_initial_call=True
    )
    def set_active_tab(_clicks, current_value):
        ctx = dash.callback_context
        triggered = getattr(ctx, 'triggered_id', None)
        if triggered is None:
            if not ctx.triggered:
                return dash.no_update
            triggered = ctx.triggered[0]['prop_id'].split('.')[0]
            triggered = json.loads(triggered)
        if isinstance(triggered, str):
            return dash.no_update
        return triggered.get('value', current_value)

    @dash_app.callback(
        Output({'type': 'tab-nav-button_odo', 'value': ALL}, 'className'),
        Input('active-dashboard-tab_odo', 'data')
    )
    def highlight_active_button(active_value):
        classes = []
        for tab in DASHBOARD_TABS:
            base_class = NAV_BUTTON_BASE_CLASS
            if tab.value == active_value:
                base_class += ' dashboard-nav-btn--active'
            classes.append(base_class)
        return classes

    tab_visibility_outputs = [
        Output(f'tab-{tab.key}-content_odo', 'style')
        for tab in DASHBOARD_TABS
    ]

    @dash_app.callback(
        tab_visibility_outputs,
        Input('active-dashboard-tab_odo', 'data')
    )
    def toggle_tab_visibility(active_value):
        styles = []
        for tab in DASHBOARD_TABS:
            section_style = dict(TAB_SECTION_BASE_STYLE)
            section_style['display'] = 'block' if tab.value == active_value else 'none'
            styles.append(section_style)
        return styles

    def register_download_callback(tab_config):
        @dash_app.callback(
            Output(tab_config.download_component_id, "data"),
            Input(tab_config.download_button_id, "n_clicks"),
            State(tab_config.filter_ids.periodo, 'value'),
            State(tab_config.filter_ids.anio, 'value'),
            State(tab_config.filter_ids.tipo, 'value'),
            State('url_odo', 'pathname'),
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
        Output('download-ficha-tecnica_odo', 'data'),
        Input('download-ficha-tecnica-button_odo', 'n_clicks'),
        prevent_initial_call=True
    )
    def download_ficha_tecnica(n_clicks):
        from extensions import is_consulta_user
        if is_consulta_user():
            return dash.no_update
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
