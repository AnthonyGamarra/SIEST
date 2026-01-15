import io
import importlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from functools import lru_cache

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, html, dcc, Input, Output, State
from flask import has_request_context
from flask_login import current_user
from sqlalchemy import create_engine, text


def create_dash_app(flask_app, url_base_pathname='/dashboard/'):
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
        
        # Solo esquinas inferiores redondeadas
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
    TAB_STYLE = {
        "padding": "10px 18px",
        "border": f"1px solid {BORDER}",
        "borderBottom": "none",
        "borderTopLeftRadius": "10px",
        "borderTopRightRadius": "10px",
        "fontFamily": FONT_FAMILY,
        "fontWeight": "600",
        "color": MUTED,
        "backgroundColor": CARD_BG,
        "marginRight": "0"
    }
    TAB_SELECTED_STYLE = {
        **TAB_STYLE,
        "color": BRAND,
        "borderBottom": f"3px solid {BRAND}",
        "boxShadow": "0 6px 12px rgba(0,0,0,0.06)"
    }

    def _import_indicator_pages():
        pkg_name = f"{__package__}.Indicadores" if __package__ else "Indicadores"
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception as exc:
            print(f"[Dash Pages] No se pudo importar el paquete '{pkg_name}': {exc}")
            return
        import pkgutil

        for module in pkgutil.iter_modules(pkg.__path__):
            mod_name = f"{pkg_name}.{module.name}"
            try:
                importlib.import_module(mod_name)
                print(f"[Dash Pages] Pagina importada: {mod_name}")
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

    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    valores = [f"{i:02d}" for i in range(1, 13)]
    df_period = pd.DataFrame({'mes': meses, 'periodo': valores})

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
                hover=True,
                responsive=True,
                striped=True,
                className="mb-0",
                style={'fontSize': '10px'}
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

    def build_queries_consulta(periodo_str, params):
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
                    cod_tipdoc_paciente,
                    sexo,
                    fecha_atencion,
                    acto_med
                FROM dwsge.dw_consulta_externa_homologacion_2025_{periodo_str} AS ce
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
                AND ce.cod_actividad = '91'
                AND ce.clasificacion in (2,4,6)
                AND ce.cod_variable = '001'
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
                FROM dwsge.dwe_consulta_externa_horas_efectivas_2025_{periodo_str} AS ce
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
                AND ce.cod_actividad = '91'
                AND ce.cod_variable = '001'
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
                FROM dwsge.dwe_consulta_externa_programacion_2025_{periodo_str} p
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
                WHERE p.cod_variable = '001'
                AND (
                        p.cod_motivo_suspension IS NULL 
                        OR p.cod_motivo_suspension NOT IN ('04','09','10','99','13','16','11')
                    )
                AND p.cod_centro = :codcas
                AND p.cod_actividad = '91'
            """),
            params.copy()),
            ("citados", text(f"""
                SELECT 
                    p.*,
                    c.servhosdes,
                    e.especialidad,
                    a.actespnom,
                    am.actdes,
                    ag.agrupador,
                    ca.cenasides 
                FROM dwsge.dwe_consulta_externa_citados_homologacion_2025_{periodo_str} p
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
                WHERE p.cod_centro = :codcas
                AND p.cod_actividad = '91'
                AND p.cod_variable = '001'
                AND p.cod_estado <> '0'
            """),
            params.copy()),
            ("desercion", text(f"""
                SELECT            
                    c.servhosdes,
                    e.especialidad,
                    a.actespnom,
                    am.actdes,
                    ag.agrupador,
                    ca.cenasides
                FROM dwsge.dw_consulta_externa_homologacion_2025_{periodo_str} ce
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
                AND ce.cod_actividad = '91'
                AND ce.clasificacion IN (1,3,0)
                AND ce.cod_variable = '001'

                UNION ALL

                SELECT 
                    c.servhosdes,
                    e.especialidad,
                    a.actespnom,
                    am.actdes,
                    ag.agrupador,
                    ca.cenasides 
                FROM dwsge.dwe_consulta_externa_citados_homologacion_2025_{periodo_str} p
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
                WHERE p.cod_centro = :codcas
                AND p.cod_actividad = '91'
                AND p.cod_variable = '001'
                AND p.cod_estado IN ('1','2','5')
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
                                    count(*) AS cantidad_medicos
                                FROM (SELECT * FROM dwsge.dw_consulta_externa_homologacion_2025_{periodo_str}) a
                                LEFT JOIN dwsge.dim_agrupador ag 
                                ON a.cod_agrupador = ag.cod_agrupador
                                WHERE a.cod_centro=:codcas
                                AND a.cod_actividad = '91'
                                AND a.cod_variable = '001'
                                AND a.clasificacion in (2,4,6)
                                GROUP BY a.cod_centro, a.dni_medico, ag.agrupador, a.periodo
                                ORDER BY a.dni_medico, a.periodo, (count(*))) b) c
                WHERE c.medico = '1'::bigint
            """),
            params.copy()),
        ]
        primera_vez = text("""
            WITH fecha_min_paciente AS (
                SELECT cod_oricentro,cod_centro,doc_paciente,
                       to_char(MIN(to_date(fecha_atencion,'DD/MM/YYYY')),'YYYYMM') periodo
                FROM dwsge.dwe_consulta_externa_homologacion_2025
                WHERE cod_variable='001' AND cod_actividad='91'
                AND clasificacion IN (2,4,6) AND cod_centro=:codcas
                GROUP BY cod_oricentro,cod_centro,doc_paciente
            )
            SELECT COUNT(DISTINCT doc_paciente) AS cantidad
            FROM fecha_min_paciente WHERE periodo=:periodo_sql
        """)
        primera_vez_agr = text("""
            WITH fecha_min_paciente AS (
                SELECT p.doc_paciente,ag.agrupador,
                       to_char(MIN(to_date(p.fecha_atencion,'DD/MM/YYYY')),'YYYYMM') periodo
                FROM dwsge.dwe_consulta_externa_homologacion_2025 p
                LEFT JOIN dwsge.dim_agrupador ag ON p.cod_agrupador = ag.cod_agrupador
                WHERE p.cod_variable='001' AND p.cod_actividad='91'
                AND p.clasificacion IN (2,4,6) AND p.cod_centro=:codcas
                GROUP BY p.doc_paciente,ag.agrupador
            )
            SELECT agrupador,COUNT(DISTINCT doc_paciente) AS cantidad
            FROM fecha_min_paciente WHERE periodo=:periodo_sql GROUP BY agrupador
        """)
        return {
            "queries": queries,
            "primeras_consultas_query": primera_vez,
            "primeras_consultas_agrupador_query": primera_vez_agr,
        }

    def build_queries_complementaria(periodo_str, params):
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
                    cod_tipdoc_paciente,
                    sexo,
                    fecha_atencion,
                    acto_med
                FROM dwsge.dw_consulta_externa_homologacion_2025_{periodo_str} AS ce
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
                AND cod_servicio= 'A91'
                AND ce.clasificacion in (2,4,6)
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
                FROM dwsge.dwe_consulta_externa_horas_efectivas_2025_{periodo_str} AS ce
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
                AND cod_servicio= 'A91'
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
                FROM dwsge.dwe_consulta_externa_programacion_2025_{periodo_str} p
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
                WHERE (
                        p.cod_motivo_suspension IS NULL 
                        OR p.cod_motivo_suspension NOT IN ('04','09','10','99','13','16','11')
                    )
                AND p.cod_centro = :codcas
                AND cod_servicio= 'A91'
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
                                    count(*) AS cantidad_medicos
                                FROM (SELECT * FROM dwsge.dw_consulta_externa_homologacion_2025_{periodo_str}) a
                                LEFT JOIN dwsge.dim_agrupador ag 
                                ON a.cod_agrupador = ag.cod_agrupador
                                WHERE a.cod_centro=:codcas
                                AND cod_servicio= 'A91'
                                AND a.clasificacion in (2,4,6)
                                GROUP BY a.cod_centro, a.dni_medico, ag.agrupador, a.periodo
                                ORDER BY a.dni_medico, a.periodo, (count(*))) b) c
                WHERE c.medico = '1'::bigint
            """),
            params.copy()),
        ]
        primera_vez = text("""
            WITH fecha_min_paciente AS (
                SELECT cod_oricentro,cod_centro,doc_paciente,
                       to_char(MIN(to_date(fecha_atencion,'DD/MM/YYYY')),'YYYYMM') periodo
                FROM dwsge.dwe_consulta_externa_homologacion_2025
                WHERE cod_servicio='A91'
                AND clasificacion IN (2,4,6) AND cod_centro=:codcas
                GROUP BY cod_oricentro,cod_centro,doc_paciente
            )
            SELECT COUNT(DISTINCT doc_paciente) AS cantidad
            FROM fecha_min_paciente WHERE periodo=:periodo_sql
        """)
        primera_vez_agr = text("""
            WITH fecha_min_paciente AS (
                SELECT p.doc_paciente,ag.agrupador,
                       to_char(MIN(to_date(p.fecha_atencion,'DD/MM/YYYY')),'YYYYMM') periodo
                FROM dwsge.dwe_consulta_externa_homologacion_2025 p
                LEFT JOIN dwsge.dim_agrupador ag ON p.cod_agrupador = ag.cod_agrupador
                WHERE p.cod_servicio='A91'
                AND p.clasificacion IN (2,4,6) AND p.cod_centro=:codcas
                GROUP BY p.doc_paciente,ag.agrupador
            )
            SELECT agrupador,COUNT(DISTINCT doc_paciente) AS cantidad
            FROM fecha_min_paciente WHERE periodo=:periodo_sql GROUP BY agrupador
        """)
        return {
            "queries": queries,
            "primeras_consultas_query": primera_vez,
            "primeras_consultas_agrupador_query": primera_vez_agr,
        }
 
    def _load_dashboard_data(periodo, codcas, engine, query_builder):
        if not periodo or not codcas:
            return None
        periodo_str = f"{int(periodo):02d}" if str(periodo).isdigit() else str(periodo)
        periodo_sql = f"2025{periodo_str}"
        params = {"codcas": codcas}
        builder_payload = query_builder(periodo_str, params)
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
        citados_df = results.get("citados", pd.DataFrame())
        citados_df_agru = (
            citados_df.groupby(["agrupador"])
            .size()
            .reset_index(name='counts')
            .sort_values('counts', ascending=False)
            if not citados_df.empty else pd.DataFrame(columns=['agrupador', 'counts'])
        )
        desercion_df = results.get("desercion", pd.DataFrame())
        desercion_agru = (
            desercion_df.groupby(["agrupador"])
            .size()
            .reset_index(name='counts')
            .sort_values('counts', ascending=False)
            if not desercion_df.empty else pd.DataFrame(columns=['agrupador', 'counts'])
        ) 
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

        total_medicos = atenciones_df['dni_medico'].nunique() if 'dni_medico' in atenciones_df else 0
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

        total_citados = len(citados_df)
        total_desercion_citas = len(desercion_df)

        stats = {
            'total_atenciones': total_atenciones,
            'total_consultantes': total_consultantes,
            'total_medicos': total_medicos,
            'total_horas_efectivas': total_horas_efectivas,
            'total_horas_programadas': total_horas_programadas,
            'total_citados': total_citados,
            'total_desercion_citas': total_desercion_citas
        }

        tables = {
            'atenciones_por_agrupador': total_atenciones_agru,
            'consultantes_por_servicio': total_consultantes_por_servicio,
            'medicos_por_agrupador': medicos_por_agrupador,
            'horas_programadas_por_agrupador': horas_programadas_por_agrupador,
            'horas_efectivas_por_agrupador': horas_efectivas_df_agru,
            'desercion_por_agrupador': desercion_agru,
            'citados_por_agrupador': citados_df_agru
        }

        return {
            'nombre_centro': nombre_centro,
            'stats': stats,
            'tables': tables
        }

    def load_dashboard_data(periodo, codcas, engine):
        return _load_dashboard_data(periodo, codcas, engine, build_queries_consulta)

    def load_dashboard_data_complementaria(periodo, codcas, engine):
        return _load_dashboard_data(periodo, codcas, engine, build_queries_complementaria)

    def build_download_response(periodo, pathname, data_loader, include_citas=True, include_desercion=True):
        if not periodo or not pathname:
            return None
        import secure_code as sc
        codcas_url = pathname.rstrip('/').split('/')[-1] if pathname else None
        codcas = sc.decode_code(codcas_url) if codcas_url else None
        if not codcas:
            return None
        engine = create_connection()
        if engine is None:
            return None
        data = data_loader(periodo, codcas, engine)
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
        return dcc.send_bytes(output.getvalue(), f"reporte_{codcas}_{periodo}.xlsx")

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
                            "Consulta externa 2025 - Atenciones medicas",
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

            content = html.Div([
                dcc.Location(id='url', refresh=True),

                html.Div([
                    header,
                    html.Br(),
                    dcc.Tabs(
                        id='dashboard-tabs',
                        value='tab-atenciones',
                        children=[
                            dcc.Tab(
                                label="Atenciones médicas",
                                value='tab-atenciones',
                                style=TAB_STYLE,
                                selected_style=TAB_SELECTED_STYLE,
                                children=[
                                    html.Div([
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
                                                [html.I(className="bi bi-download me-2"), "Exportar Excel"],
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
                                                    'padding': '8px 12px'
                                                }
                                            ),
                                        ], style={**CONTROL_BAR_STYLE}),
                                        dbc.Tooltip("Regresar al inicio", target='back-button', placement='bottom', style={'zIndex': 9999}),
                                        dbc.Tooltip("Buscar datos", target='search-button', placement='bottom', style={'zIndex': 9999}),
                                        dbc.Tooltip("Descargar Excel", target='download-button', placement='bottom', style={'zIndex': 9999}),
                                        dbc.Row([dbc.Col(html.Div(id='summary-container'), width=12)]),
                                        html.Br(),
                                        dbc.Row([dbc.Col(html.Div(id='charts-container'), width=12)]),
                                        html.Br(),
                                    ], id='tab-atenciones-content')
                                ]
                            ),
                            dcc.Tab(
                                label="Medicina complementaria",
                                value='tab-complementaria',
                                style=TAB_STYLE,
                                selected_style=TAB_SELECTED_STYLE,
                                children=[
                                    html.Div([
                                        html.Div([
                                            html.I(className="bi bi-calendar3", style={'fontSize': '18px', 'color': BRAND, 'marginRight': '8px'}),
                                            dcc.Dropdown(
                                                id='filter-periodo-complementaria',
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
                                                id='search-button-complementaria',
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
                                                [html.I(className="bi bi-download me-2"), "Exportar Excel"],
                                                id='download-button-complementaria',
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
                                            dcc.Download(id="download-dataframe-csv-complementaria"),
                                            dbc.Button(
                                                [html.I(className="bi bi-arrow-left me-1"), "Inicio"],
                                                id='back-button-complementaria',
                                                color='secondary',
                                                outline=True,
                                                n_clicks=0,
                                                style={
                                                    'marginLeft': 'auto',
                                                    'padding': '8px 12px'
                                                }
                                            ),
                                        ], style={**CONTROL_BAR_STYLE}),
                                        dbc.Tooltip("Regresar al inicio", target='back-button-complementaria', placement='bottom', style={'zIndex': 9999}),
                                        dbc.Tooltip("Buscar datos", target='search-button-complementaria', placement='bottom', style={'zIndex': 9999}),
                                        dbc.Tooltip("Descargar Excel", target='download-button-complementaria', placement='bottom', style={'zIndex': 9999}),
                                        dbc.Row([dbc.Col(html.Div(id='summary-container-complementaria'), width=12)]),
                                        html.Br(),
                                        dbc.Row([dbc.Col(html.Div(id='charts-container-complementaria'), width=12)]),
                                        html.Br(),
                                    ], id='tab-complementaria-content')
                                ]
                            )
                        ],
                        style={'backgroundColor': 'transparent', 'marginBottom': '0'},
                        content_style={'padding': '0', 'border': 'none', 'marginTop': '-1px'}
                    )
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
            html.P('Debes iniciar sesion para ver el dashboard.'),
            html.A('Ir a inicio', href='/', target='_top')
        ])

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
            return html.Div("Seleccione un periodo y asegurese de tener un centro valido."), html.Div()

        engine = create_connection()
        if engine is None:
            return html.Div("Error de conexion a la base de datos."), html.Div()

        data = load_dashboard_data(periodo, codcas, engine)
        if not data:
            return html.Div("Sin datos para mostrar."), html.Div()

        stats = data['stats']
        tables = data['tables']
        nombre_centro = data['nombre_centro']

        total_atenciones = stats['total_atenciones']
        total_consultantes = stats['total_consultantes']
        total_medicos = stats['total_medicos']
        total_horas_programadas = stats['total_horas_programadas']
        total_horas_efectivas = stats['total_horas_efectivas']
        total_citados = stats['total_citados']
        total_desercion_citas = stats['total_desercion_citas']

        total_atenciones_agru = tables['atenciones_por_agrupador']
        total_consultantes_por_servicio_table = tables['consultantes_por_servicio']
        medicos_por_agrupador_table = tables['medicos_por_agrupador']
        horas_programadas_table = tables['horas_programadas_por_agrupador']

        desercion_por_agrupador_table = tables.get('desercion_por_agrupador', pd.DataFrame(columns=['agrupador', 'counts']))
        citados_por_agrupador_table = tables.get('citados_por_agrupador', pd.DataFrame(columns=['agrupador', 'counts']))
        horas_efectivas_por_agrupador_table = tables.get('horas_efectivas_por_agrupador', pd.DataFrame(columns=['agrupador', 'counts']))
        base = url_base_pathname.rstrip('/') + '/'
        subtitle = f"Periodo {periodo} | {nombre_centro}"
        total_consultantes_servicio = (
            int(total_consultantes_por_servicio_table['counts'].sum())
            if (not total_consultantes_por_servicio_table.empty and 'counts' in total_consultantes_por_servicio_table)
            else 0
        )
        cards = [
            {
                "title": "Total de consultantes a la atención médica",
                "value": f"{total_consultantes:,.0f}",
                "border_color": ACCENT,
            },
            {
                "title": "Total de consultantes al servicio",
                "value": f"{total_consultantes_servicio:,.0f}",
                "border_color": ACCENT,
                "side_component": render_agrupador_table(
                    total_consultantes_por_servicio_table
                ),
            },
            {
                "title": "Total de Consultas",
                "value": f"{total_atenciones:,.0f}",
                "border_color": BRAND,
                "href": f"{base}dash/total_atenciones/{codcas_url}?periodo={periodo}",
                "side_component": render_agrupador_table(total_atenciones_agru),
            },
            {
                "title": "Número de Médicos",
                "value": f"{total_medicos:,.0f}",
                "border_color": BRAND_SOFT,
                "href": f"{base}dash/total_medicos/{codcas_url}?periodo={periodo}",
                "side_component": render_agrupador_table(medicos_por_agrupador_table),
            },
            {
                "title": "Número de deserciones",
                "value": f"{total_desercion_citas:,.0f}",
                "border_color": BRAND_SOFT,
                "href": f"{base}dash/desercion_citas/{codcas_url}?periodo={periodo}",
                "side_component": render_agrupador_table(
                    desercion_por_agrupador_table
                ),
            },
            {
                "title": "Número de citas otorgadas",
                "value": f"{total_citados:,.0f}",
                "border_color": ACCENT,
                "href": f"{base}dash/total_citados/{codcas_url}?periodo={periodo}",
                "side_component": render_agrupador_table(
                    citados_por_agrupador_table
                ),
            },
            {
                "title": "Total horas programadas",
                "value": f"{total_horas_programadas:,.0f}",
                "border_color": BRAND,
                "href": f"{base}dash/horas_programadas/{codcas_url}?periodo={periodo}",
                "side_component": render_agrupador_table(horas_programadas_table, value_format="{:,.2f}"),
            },
            {
                "title": "Total de horas Efectivas (Ejecutada)",
                "value": f"{total_horas_efectivas:,.0f}",
                "border_color": ACCENT,
                "href": f"{base}dash/horas_efectivas/{codcas_url}?periodo={periodo}",
                "side_component": render_agrupador_table(
                    horas_efectivas_por_agrupador_table,
                    value_format="{:,.2f}"
                ),
            }
        ]
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

        summary_row = dbc.Container(summary_sections, fluid=True)

        charts_container = html.Div()
        return summary_row, charts_container

    @dash_app.callback(
        [Output('summary-container-complementaria', 'children'),
         Output('charts-container-complementaria', 'children')],
        Input('search-button-complementaria', 'n_clicks'),
        State('filter-periodo-complementaria', 'value'),
        State('url', 'pathname')
    )
    def on_search_complementaria(n_clicks, periodo, pathname):
        if not n_clicks:
            return html.Div(), html.Div()

        import secure_code as sc

        codcas_url = pathname.rstrip('/').split('/')[-1] if pathname else None
        codcas = sc.decode_code(codcas_url) if codcas_url else None

        if not periodo or not codcas:
            return html.Div("Seleccione un periodo y asegurese de tener un centro valido."), html.Div()

        engine = create_connection()
        if engine is None:
            return html.Div("Error de conexion a la base de datos."), html.Div()

        data = load_dashboard_data_complementaria(periodo, codcas, engine)
        if not data:
            return html.Div("Sin datos para mostrar."), html.Div()

        stats = data['stats']
        tables = data['tables']
        nombre_centro = data['nombre_centro']

        total_atenciones = stats['total_atenciones']
        total_consultantes = stats['total_consultantes']
        total_medicos = stats['total_medicos']
        total_horas_programadas = stats['total_horas_programadas']
        total_horas_efectivas = stats['total_horas_efectivas']

        total_atenciones_agru = tables['atenciones_por_agrupador']
        total_consultantes_por_servicio_table = tables['consultantes_por_servicio']
        medicos_por_agrupador_table = tables['medicos_por_agrupador']
        horas_programadas_table = tables['horas_programadas_por_agrupador']
        horas_efectivas_por_agrupador_table = tables.get(
            'horas_efectivas_por_agrupador',
            pd.DataFrame(columns=['agrupador', 'counts'])
        )

        subtitle = f"Periodo {periodo} | {nombre_centro}"
        total_consultantes_servicio = (
            int(total_consultantes_por_servicio_table['counts'].sum())
            if (not total_consultantes_por_servicio_table.empty and 'counts' in total_consultantes_por_servicio_table)
            else 0
        )
        cards = [
            {
                "title": "Total de consultantes a medicina complementaria",
                "value": f"{total_consultantes:,.0f}",
                "border_color": ACCENT,
            },
            {
                "title": "Total de consultantes al servicio",
                "value": f"{total_consultantes_servicio:,.0f}",
                "border_color": ACCENT,
                "side_component": render_agrupador_table(
                    total_consultantes_por_servicio_table,
                    title="Consultantes por servicio"
                ),
            },
            {
                "title": "Total de Consultas",
                "value": f"{total_atenciones:,.0f}",
                "border_color": BRAND,
                "href": None,
                "side_component": render_agrupador_table(total_atenciones_agru),
            },
            {
                "title": "Total de Médicos",
                "value": f"{total_medicos:,.0f}",
                "border_color": BRAND_SOFT,
                "href": None,
                "side_component": render_agrupador_table(medicos_por_agrupador_table),
            },
            {
                "title": "Total horas programadas",
                "value": f"{total_horas_programadas:,.0f}",
                "border_color": BRAND,
                "href": None,
                "side_component": render_agrupador_table(horas_programadas_table, value_format="{:,.2f}"),
            },
            {
                "title": "Total de Horas Efectivas",
                "value": f"{total_horas_efectivas:,.0f}",
                "border_color": ACCENT,
                "href": None,
                "side_component": render_agrupador_table(
                    horas_efectivas_por_agrupador_table,
                    value_format="{:,.2f}"
                ),
            }
        ]

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

        summary_row = dbc.Container(summary_sections, fluid=True)

        charts_container = html.Div()
        return summary_row, charts_container

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

    @dash_app.callback(
        Output('url', 'pathname'),
        Input('back-button', 'n_clicks'),
        Input('back-button-complementaria', 'n_clicks'),
        prevent_initial_call=True
    )
    def go_root(*_):
        return "/"

    @dash_app.callback(
        Output("download-dataframe-csv", "data"),
        Input("download-button", "n_clicks"),
        State('filter-periodo', 'value'),
        State('url', 'pathname'),
        prevent_initial_call=True
    )
    def download_csv(n_clicks, periodo, pathname):
        if not n_clicks:
            return None
        return build_download_response(
            periodo,
            pathname,
            load_dashboard_data,
            include_citas=True,
            include_desercion=True
        )
 
    @dash_app.callback(
        Output("download-dataframe-csv-complementaria", "data"),
        Input("download-button-complementaria", "n_clicks"),
        State('filter-periodo-complementaria', 'value'),
        State('url', 'pathname'),
        prevent_initial_call=True
    )
    def download_csv_complementaria(n_clicks, periodo, pathname):
        if not n_clicks:
            return None
        return build_download_response(
            periodo,
            pathname,
            load_dashboard_data_complementaria,
            include_citas=False,
            include_desercion=False
        )

    dash_app.layout = serve_layout
    return dash_app
