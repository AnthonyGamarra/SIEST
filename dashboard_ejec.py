"""
Modulo Ejecutivo de Patologias (solo admin).

Pestana 1 - Analitica por patologia: vista comparativa (todas las patologias)
    y comorbilidad global, leidas desde las vistas materializadas de rollup
    (dssge.mv_ejec_pat_*). Consultas parametrizadas y pequenas -> respuesta en
    milisegundos.
Pestana 2 - Detalle por patologia: filtro por patologia/red/centro con KPIs,
    evolucion anual, servicios, sexo/edad y top diagnosticos.
Pestana 3 - Comorbilidad del paciente: buscador por documento que arma una
    matriz patologia x anio con checks y el detalle de diagnosticos asociados,
    leido en vivo desde dssge.mv_ejec_base (indexado por doc_paciente).

Requiere ejecutar build_mvs.py una vez (crea las MV). Mientras no existan, la
UI muestra un aviso guiando a construirlas.
"""
import io
from datetime import datetime
from functools import lru_cache

import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, dash_table, no_update
from flask import has_request_context
from flask_login import current_user
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

SCHEMA = "dssge"
ANIO_ORDER = ["2019", "2020", "2021", "2022", "2023", "2024"]
EDAD_ORDER = ["0-11", "12-17", "18-29", "30-44", "45-59", "60+", "SIN DATO"]

# Paleta accesible y consistente (claro). Colores por serie.
PALETTE = ["#0064AF", "#00A3A3", "#F2A900", "#E4572E", "#7B61FF", "#2BB673", "#B23A48"]

SEXO_ORDER = ["M", "F"]
SEXO_LABELS = {"M": "Masculino", "F": "Femenino"}
SEXO_COLORS = {"M": PALETTE[0], "F": PALETTE[3]}

# Un color fijo por grupo etario (identidad, nunca por ranking). SIN DATO en
# gris neutro porque no es una categoria demografica real.
EDAD_COLORS = dict(zip(EDAD_ORDER[:-1], PALETTE[:6]))
EDAD_COLORS["SIN DATO"] = "#9CA3AF"


def _as_list(value):
    """Normaliza el value de un dcc.Dropdown(multi=True): puede llegar como
    None, un escalar (compatibilidad) o una lista."""
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v not in (None, "")]
    return [value]


def create_dash_app(flask_app, url_base_pathname="/dashboard_ejec_embed/"):
    brand = "#0064AF"
    brand_soft = "#D7E9FF"
    card_bg = "#FFFFFF"
    muted = "#6B7280"
    border = "#E5E7EB"
    font_family = "Inter, 'Segoe UI', Calibri, sans-serif"

    external_stylesheets = [
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
    ]

    dash_app = Dash(
        __name__,
        server=flask_app,
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
        requests_pathname_prefix=url_base_pathname,
        routes_pathname_prefix=url_base_pathname,
    )
    dash_app.title = "SIEST - Patologias"

    card_style = {
        "border": f"1px solid {border}",
        "borderRadius": "16px",
        "backgroundColor": card_bg,
        "boxShadow": "0 8px 20px rgba(0,0,0,0.08)",
        "padding": "18px",
    }

    # =====================================================================
    # CAPA DE DATOS
    # =====================================================================
    def get_engine():
        from extensions import get_dw_engine
        return get_dw_engine()

    def run_df(sql, params=None):
        """Devuelve (df, error_str). error_str no nulo si la MV no existe u otro fallo."""
        try:
            engine = get_engine()
            with engine.connect() as conn:
                df = pd.read_sql_query(text(sql), conn, params=params or {})
            return df, None
        except SQLAlchemyError as exc:
            msg = str(getattr(exc, "orig", exc))
            if "mv_ejec" in msg and ("no existe" in msg.lower() or "does not exist" in msg.lower()):
                return None, (
                    "Las vistas materializadas aun no existen. Ejecute una vez "
                    "build_mvs.py con credenciales de administrador para crearlas."
                )
            print(f"[Ejec] Error SQL: {exc}")
            return None, "Ocurrio un error al consultar la base de datos."
        except Exception as exc:  # pragma: no cover
            print(f"[Ejec] Error: {exc}")
            return None, "Ocurrio un error inesperado."

    def get_patologia_options():
        df, err = run_df(
            f"SELECT DISTINCT patologia FROM {SCHEMA}.mv_ejec_pat_resumen "
            f"WHERE patologia NOT IN ('TOTAL GENERAL', 'TOTAL CATALOGADO', 'SIN PATOLOGIA') ORDER BY patologia"
        )
        if err or df is None or df.empty:
            return []
        return [{"label": p.replace("_", " ").title(), "value": p} for p in df["patologia"]]

    def get_anio_options():
        df, err = run_df(f"SELECT DISTINCT anio FROM {SCHEMA}.mv_ejec_pat_resumen ORDER BY anio")
        if err or df is None or df.empty:
            base = [{"label": a, "value": a} for a in ANIO_ORDER]
            return base + [{"label": "Todos los anios", "value": "TODOS"}]
        opts = []
        for a in df["anio"]:
            opts.append({"label": "Todos los anios" if a == "TODOS" else a, "value": a})
        return opts

    def get_edad_options():
        return [{"label": "Todos los grupos", "value": "TODOS"}] + [{"label": a, "value": a} for a in EDAD_ORDER]

    @lru_cache(maxsize=1)
    def load_red_centro_df():
        """Dimension red/centro (activos), cargada directamente y cacheada en
        memoria del proceso: es pequena (unos cientos de filas) y ya viene
        indexada por PK en el DW, no amerita una vista materializada."""
        sql = (
            "SELECT c.redasiscod, r.redasisdes, c.cenasicod, c.cenasides "
            "FROM dwsge.sgss_cmcas10 c "
            "LEFT JOIN dwsge.sgss_cmras10 r ON c.redasiscod = r.redasiscod "
            "WHERE c.estregcod = '1' "
            "ORDER BY r.redasisdes, c.cenasides"
        )
        df, err = run_df(sql)
        if err or df is None:
            return pd.DataFrame(columns=["redasiscod", "redasisdes", "cenasicod", "cenasides"])
        return df

    def get_red_detalle_options():
        df = load_red_centro_df()
        base = [{"label": "Todas las redes", "value": "TODAS"}]
        if df.empty:
            return base
        redes = df.drop_duplicates(subset=["redasiscod"]).dropna(subset=["redasiscod"])
        return base + [
            {"label": row["redasisdes"], "value": row["redasiscod"]}
            for _, row in redes.sort_values("redasisdes").iterrows()
        ]

    def get_centro_detalle_options(red_value=None):
        df = load_red_centro_df()
        base = [{"label": "Todos los centros", "value": "TODOS"}]
        if df.empty:
            return base
        red_list = _as_list(red_value)
        sub = df if not red_list or "TODAS" in red_list else df[df["redasiscod"].isin(red_list)]
        sub = sub.drop_duplicates(subset=["cenasicod"]).dropna(subset=["cenasicod"])
        return base + [
            {"label": row["cenasides"], "value": row["cenasicod"]}
            for _, row in sub.sort_values("cenasides").iterrows()
        ]

    # =====================================================================
    # HELPERS DE UI
    # =====================================================================
    def kpi_card(title, value, icon, color=brand, subtitle=None):
        body = [
            html.Div(value, style={"fontSize": "26px", "fontWeight": 800, "color": "#111827", "lineHeight": "1.1"}),
            html.Small(title, style={"color": muted, "fontWeight": 600}),
        ]
        if subtitle:
            body.append(html.Small(subtitle, style={"color": color, "fontWeight": 600, "fontSize": "11px"}))
        return html.Div(
            [
                html.Div(
                    html.I(className=f"bi {icon}", style={"fontSize": "22px", "color": color}),
                    style={
                        "width": "46px", "height": "46px", "borderRadius": "12px",
                        "backgroundColor": brand_soft, "display": "flex",
                        "alignItems": "center", "justifyContent": "center", "flexShrink": "0",
                    },
                ),
                html.Div(body, style={"display": "flex", "flexDirection": "column", "gap": "2px", "minWidth": 0}),
            ],
            style={**card_style, "display": "flex", "alignItems": "center", "gap": "14px", "flex": "1 1 230px", "padding": "16px 18px"},
        )

    def empty_fig(msg="Sin datos"):
        fig = go.Figure()
        fig.add_annotation(text=msg, showarrow=False, font=dict(size=14, color=muted))
        fig.update_layout(
            xaxis={"visible": False}, yaxis={"visible": False},
            margin=dict(l=10, r=10, t=10, b=10), height=300,
            paper_bgcolor="white", plot_bgcolor="white",
        )
        return fig

    def style_fig(fig, height=320, title=None):
        fig.update_layout(
            margin=dict(l=12, r=12, t=42 if title else 12, b=12),
            height=height, paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family=font_family, size=12, color="#374151"),
            title=dict(text=title, font=dict(size=15, color=brand, family=font_family)) if title else None,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="#F1F5F9")
        return fig

    def graph_card(title, graph_id, height=340, subtitle=None, flex="1 1 380px", figure=None):
        header = [html.Div(title, style={"fontWeight": 700, "color": brand, "fontSize": "15px"})]
        if subtitle:
            header.append(html.Small(subtitle, style={"color": muted}))
        return html.Div(
            [
                html.Div(header, style={"marginBottom": "8px", "display": "flex", "flexDirection": "column", "gap": "2px"}),
                dcc.Loading(
                    dcc.Graph(id=graph_id, figure=figure if figure is not None else {}, config={"displayModeBar": False}),
                    type="default",
                ),
            ],
            style={**card_style, "flex": flex, "minWidth": "320px"},
        )

    GLOBAL_PATOLOGIAS = ["Raras", "Oncologico", "Renal"]
    GLOBAL_COLORS = {"Oncologico": brand, "Renal": "#00A3A3", "Raras": "#F2A900"}

    def _build_pacientes_total_fig():
        """Pacientes totales por patologia (Raras/Oncologico/Renal), historico
        completo (anio='TODOS', igual criterio que el resto del modulo)."""
        df, err = run_df(
            f"SELECT patologia, pacientes FROM {SCHEMA}.mv_ejec_pat_resumen "
            f"WHERE anio = 'TODOS' AND patologia = ANY(:pats)",
            {"pats": GLOBAL_PATOLOGIAS},
        )
        if err or df is None or df.empty:
            return empty_fig(err or "Sin datos")

        d = df.copy()
        d = d.sort_values("pacientes", ascending=False)
        labels = [_pat_label(p) for p in d["patologia"]]
        colors = [GLOBAL_COLORS.get(p, brand) for p in d["patologia"]]
        fig = go.Figure(
            data=go.Bar(
                x=labels,
                y=d["pacientes"],
                text=d["pacientes"],
                texttemplate="%{text:,}",
                textposition="outside",
                marker_color=colors,
                hovertemplate="%{x}<br>%{y:,} pacientes<extra></extra>",
            )
        )
        fig.update_yaxes(title="Pacientes")
        fig.update_xaxes(title=None)
        style_fig(fig, height=340)
        fig.update_layout(showlegend=False)
        return fig

    def _build_comorbilidad_global_fig():
        """Evolucion anual de pacientes por patologia de alto costo
        (Raras/Oncologico/Renal): una linea por patologia, con etiquetas de
        dato visibles en cada punto."""
        df, err = run_df(
            f"SELECT patologia, anio, pacientes FROM {SCHEMA}.mv_ejec_pat_resumen "
            f"WHERE anio <> 'TODOS' AND patologia = ANY(:pats) ORDER BY anio",
            {"pats": GLOBAL_PATOLOGIAS},
        )
        if err or df is None or df.empty:
            return empty_fig(err or "Sin datos")

        d = df.copy()
        d["patologia_label"] = d["patologia"].map(_pat_label)
        color_map = {_pat_label(k): v for k, v in GLOBAL_COLORS.items()}
        fig = px.line(
            d, x="anio", y="pacientes", color="patologia_label", markers=True,
            color_discrete_map=color_map, text="pacientes",
        )
        fig.update_traces(
            texttemplate="%{text:,}",
            textposition="top center",
            textfont=dict(size=11),
            marker=dict(size=8),
            line=dict(width=3),
            hovertemplate="%{x}<br>%{fullData.name}: %{y:,} pacientes<extra></extra>",
        )
        fig.update_yaxes(title="Pacientes")
        fig.update_xaxes(title=None)
        style_fig(fig, height=340)
        fig.update_layout(legend_title_text=None)
        return fig

    def _build_comorbilidad_grupo_fig(patologia_global, patron_comorbilidad, color=brand):
        """% de pacientes de la patologia global (Oncologico/Renal) que TAMBIEN
        tienen cada una de las comorbilidades curadas de su grupo (columna
        patron de dwsge.mt_patologia). Historico completo, sin filtro de anio,
        igual criterio que la matriz de comorbilidad general."""
        df, err = run_df(
            f"""SELECT c.patologia_b, c.pacientes
                FROM {SCHEMA}.mv_ejec_comorbilidad c
                JOIN dwsge.mt_patologia p ON p.patologia = c.patologia_b
                WHERE c.patologia_a = :pat AND p.patron = :patron
                ORDER BY c.pacientes DESC""",
            {"pat": patologia_global, "patron": patron_comorbilidad},
        )
        if err or df is None or df.empty:
            return empty_fig(err or "Sin datos")

        total_df, _ = run_df(
            f"SELECT pacientes FROM {SCHEMA}.mv_ejec_comorbilidad WHERE patologia_a = :pat AND patologia_b = :pat",
            {"pat": patologia_global},
        )
        total = int(total_df["pacientes"].iloc[0]) if total_df is not None and not total_df.empty else 0
        if not total:
            return empty_fig("Sin pacientes para esta patologia")

        d = df.copy()
        d["pct"] = d["pacientes"] / total * 100
        d = d.sort_values("pct")
        fig = px.bar(d, x="pct", y="patologia_b", orientation="h", text="pacientes")
        fig.update_traces(
            marker_color=color,
            texttemplate="%{text:,} (%{x:.1f}%)",
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x:.1f}% (%{text:,} pacientes)<extra></extra>",
        )
        fig.update_yaxes(title=None)
        fig.update_xaxes(title="% de pacientes", range=[0, max(d["pct"].max() * 1.25, 10)])
        style_fig(fig, height=max(320, 34 * len(d)))
        return fig

    # =====================================================================
    # LAYOUT
    # =====================================================================
    def build_header():
        return html.Div(
            [
                html.Div(
                    [
                        html.I(className="bi bi-clipboard2-pulse", style={"fontSize": "30px", "color": brand}),
                        html.H2(
                            "Perfil de Comorbilidades Asociadas al Paciente",
                            style={"color": brand, "fontFamily": font_family, "fontSize": "24px", "fontWeight": 800, "margin": 0},
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "10px"},
                ),
                html.P(
                    "Analitica por patologia y comorbilidad del paciente | Sistema de Gestion Estadistica",
                    style={"color": muted, "fontFamily": font_family, "fontSize": "13px", "margin": "6px 0 0 0"},
                ),
            ],
            style={"padding": "16px 20px", "backgroundColor": card_bg, "borderRadius": "16px", "boxShadow": "0 8px 20px rgba(0,0,0,0.08)"},
        )

    def section_title(text_, icon):
        return html.Div(
            [
                html.I(className=f"bi {icon}", style={"color": brand, "fontSize": "18px"}),
                html.H4(text_, style={"color": brand, "fontFamily": font_family, "fontSize": "17px", "fontWeight": 800, "margin": 0}),
            ],
            style={"display": "flex", "alignItems": "center", "gap": "8px", "margin": "6px 0 2px 0"},
        )

    def build_tab1():
        dropdown_style = {"width": "100%", "fontFamily": font_family, "fontSize": "13px"}
        anio_opts = get_anio_options()

        shared_controls = html.Div(
            [
                html.Div(
                    [
                        html.Small("Anio", style={"fontWeight": 600, "color": muted}),
                        dcc.Dropdown(id="ejec-anio", options=anio_opts, value=["TODOS"], multi=True, clearable=True, style=dropdown_style),
                    ],
                    style={"flex": "1 1 180px", "display": "flex", "flexDirection": "column", "gap": "4px"},
                ),
            ],
            style={**card_style, "display": "flex", "gap": "14px", "flexWrap": "wrap", "alignItems": "flex-end", "padding": "14px 16px"},
        )

        comparativa = html.Div(
            [
                shared_controls,
                html.Div(id="ejec-comp-feedback"),
                html.Div(id="ejec-comp-kpis", style={"display": "flex", "gap": "14px", "flexWrap": "wrap"}),
                html.Div(
                    [
                        graph_card(
                            "Pacientes por patologia de alto costo: Raras / Oncologico / Renal",
                            "ejec-fig-comorbilidad-total",
                            height=340,
                            subtitle="Total de pacientes por patologia (2019-2025)",
                            flex="1 1 420px",
                            figure=_build_pacientes_total_fig(),
                        ),
                        graph_card(
                            "Evolucion anual · patologias de alto costo (Raras / Oncologico / Renal)",
                            "ejec-fig-comorbilidad",
                            height=340,
                            subtitle="Pacientes por anio y patologia (2019-2025)",
                            flex="2 1 560px",
                            figure=_build_comorbilidad_global_fig(),
                        ),
                    ],
                    style={"display": "flex", "gap": "14px", "flexWrap": "wrap"},
                ),
                graph_card(
                    "Ranking por red · patologias de alto costo",
                    "ejec-fig-ranking-red",
                    height=320,
                    subtitle="Pacientes de Raras + Oncologico + Renal por red asistencial, distinguidos por patologia · top 15",
                    flex="1 1 100%",
                ),
                html.Div(
                    [
                        graph_card(
                            "¿Que otras enfermedades tienen los pacientes de Oncologico? (alto costo)",
                            "ejec-fig-comorb-oncologico",
                            height=max(320, 34 * 14),
                            subtitle="% de pacientes con Oncologico que en algun momento tambien tuvo cada diagnostico (2019 - 2025).",
                            flex="1 1 480px",
                            figure=_build_comorbilidad_grupo_fig("Oncologico", "Coomorbilidad Oncología", brand),
                        ),
                        graph_card(
                            "¿Que otras enfermedades tienen los pacientes de Renal? (alto costo)",
                            "ejec-fig-comorb-renal",
                            height=max(320, 34 * 14),
                            subtitle="% de pacientes con Renal que en algun momento tambien tuvo cada diagnostico (2019 - 2025).",
                            flex="1 1 480px",
                            figure=_build_comorbilidad_grupo_fig("Renal", "Coomorbilidad Renal", "#00A3A3"),
                        ),
                    ],
                    style={"display": "flex", "gap": "14px", "flexWrap": "wrap"},
                ),
            ],
            style={"display": "flex", "flexDirection": "column", "gap": "14px"},
        )

        return html.Div(
            [
                section_title("Vista comparativa (todas las patologias)", "bi-grid-3x3-gap-fill"),
                comparativa,
            ],
            style={"display": "flex", "flexDirection": "column", "gap": "10px"},
        )

    def build_tab_detalle():
        dropdown_style = {"width": "100%", "fontFamily": font_family, "fontSize": "13px"}
        pat_opts = get_patologia_options()
        default_pat = pat_opts[0]["value"] if pat_opts else None

        detalle_controls = html.Div(
            [
                html.Div(
                    [
                        html.Small("Anio", style={"fontWeight": 600, "color": muted}),
                        dcc.Dropdown(id="ejec-anio-detalle", options=get_anio_options(), value=["TODOS"], multi=True, clearable=True, style=dropdown_style),
                    ],
                    style={"flex": "1 1 180px", "display": "flex", "flexDirection": "column", "gap": "4px"},
                ),
                html.Div(
                    [
                        html.Small("Patologia", style={"fontWeight": 600, "color": muted}),
                        dcc.Dropdown(id="ejec-pat", options=pat_opts, value=[default_pat] if default_pat else [], multi=True, clearable=True, style=dropdown_style),
                    ],
                    style={"flex": "2 1 260px", "display": "flex", "flexDirection": "column", "gap": "4px"},
                ),
                html.Div(
                    [
                        html.Small("Grupo etario", style={"fontWeight": 600, "color": muted}),
                        dcc.Dropdown(id="ejec-edad-detalle", options=get_edad_options(), value=["TODOS"], multi=True, clearable=True, style=dropdown_style),
                    ],
                    style={"flex": "2 1 220px", "display": "flex", "flexDirection": "column", "gap": "4px"},
                ),
                html.Div(
                    [
                        html.Small("Red asistencial", style={"fontWeight": 600, "color": muted}),
                        dcc.Dropdown(id="ejec-red-detalle", options=get_red_detalle_options(), value=["TODAS"], multi=True, clearable=True, style=dropdown_style),
                    ],
                    style={"flex": "2 1 260px", "display": "flex", "flexDirection": "column", "gap": "4px"},
                ),
                html.Div(
                    [
                        html.Small("Centro asistencial", style={"fontWeight": 600, "color": muted}),
                        dcc.Dropdown(id="ejec-centro-detalle", options=get_centro_detalle_options(), value=["TODOS"], multi=True, clearable=True, style=dropdown_style),
                    ],
                    style={"flex": "2 1 260px", "display": "flex", "flexDirection": "column", "gap": "4px"},
                ),
            ],
            style={**card_style, "display": "flex", "gap": "14px", "flexWrap": "wrap", "alignItems": "flex-end", "padding": "14px 16px"},
        )

        return html.Div(
            [
                section_title("Detalle por patologia", "bi-search-heart"),
                detalle_controls,
                html.Div(id="ejec-feedback"),
                html.Div(id="ejec-kpis", style={"display": "flex", "gap": "14px", "flexWrap": "wrap"}),
                graph_card("Evolucion anual", "ejec-fig-tendencia", height=340, flex="1 1 100%"),
                graph_card("Pacientes por servicio", "ejec-fig-servicio", height=380, flex="1 1 100%"),
                graph_card(
                    "Ranking por centro",
                    "ejec-fig-centro",
                    height=380,
                    subtitle="Top 15 centros asistenciales · ignora el filtro de centro (para poder rankearlos) y de grupo etario",
                    flex="1 1 100%",
                ),
                html.Div(
                    [
                        graph_card("Distribucion por sexo", "ejec-fig-sexo", height=320, flex="1 1 260px"),
                        graph_card("Distribucion por grupo etario", "ejec-fig-edad", height=320, flex="1 1 300px"),
                        html.Div(
                            [
                                html.Div("Top diagnosticos (CIE-10)", style={"fontWeight": 700, "color": brand, "marginBottom": "8px", "fontSize": "15px"}),
                                dcc.Loading(html.Div(id="ejec-tabla-diag"), type="default"),
                            ],
                            style={**card_style, "flex": "1 1 380px", "minWidth": "320px"},
                        ),
                    ],
                    style={"display": "flex", "gap": "14px", "flexWrap": "wrap"},
                ),
            ],
            style={"display": "flex", "flexDirection": "column", "gap": "14px"},
        )

    def build_tab2():
        return html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Small("Documento del paciente", style={"fontWeight": 600, "color": muted}),
                                dbc.Input(id="ejec-doc", type="text", placeholder="Ej: 00000971", debounce=True, style={"fontFamily": font_family}),
                            ],
                            style={"flex": "2 1 260px", "display": "flex", "flexDirection": "column", "gap": "4px"},
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-search me-1"), "Buscar"],
                            id="ejec-buscar", color="primary",
                            style={"backgroundColor": brand, "borderColor": brand, "fontWeight": 600, "alignSelf": "flex-end", "height": "38px"},
                        ),
                    ],
                    style={**card_style, "display": "flex", "gap": "14px", "flexWrap": "wrap", "alignItems": "flex-end", "padding": "14px 16px"},
                ),
                html.Div(id="ejec-paciente-info"),
                html.Div(
                    [
                        html.Div("Matriz de patologias por anio", style={"fontWeight": 700, "color": brand, "marginBottom": "8px", "fontSize": "15px"}),
                        html.Small("Marca (v) los anios en que el paciente presento cada patologia.", style={"color": muted}),
                        dcc.Loading(html.Div(id="ejec-matriz", style={"marginTop": "10px"}), type="default"),
                    ],
                    style=card_style,
                ),
                html.Div(
                    [
                        html.Div("Diagnosticos asociados (detalle)", style={"fontWeight": 700, "color": brand, "marginBottom": "8px", "fontSize": "15px"}),
                        dcc.Loading(html.Div(id="ejec-detalle"), type="default"),
                        html.Div(
                            dbc.Button([html.I(className="bi bi-download me-1"), "Descargar detalle"], id="ejec-dl-btn", color="secondary", outline=True, style={"borderColor": brand, "color": brand, "marginTop": "10px"}),
                        ),
                        dcc.Download(id="ejec-download"),
                        dcc.Store(id="ejec-detalle-store"),
                    ],
                    style=card_style,
                ),
            ],
            style={"display": "flex", "flexDirection": "column", "gap": "14px"},
        )

    def unauthorized_layout():
        return html.Div(
            [html.H3("Acceso restringido"), html.P("Este modulo esta disponible solo para administradores.")],
            style={"padding": "40px", "fontFamily": font_family},
        )

    def serve_layout():
        if not has_request_context():
            return html.Div()
        if not getattr(current_user, "is_authenticated", False) or getattr(current_user, "role", None) != "admin":
            return unauthorized_layout()
        return dbc.Container(
            [
                build_header(),
                html.Br(),
                dcc.Tabs(
                    id="ejec-tabs", value="tab1",
                    children=[
                        dcc.Tab(label="Analítica por patologia de alto costo", value="tab1", children=[html.Div(build_tab1(), style={"paddingTop": "16px"})]),
                        dcc.Tab(label="Detalle por patologia", value="tab-detalle", children=[html.Div(build_tab_detalle(), style={"paddingTop": "16px"})]),
                        dcc.Tab(label="Comorbilidad del paciente", value="tab2", children=[html.Div(build_tab2(), style={"paddingTop": "16px"})]),
                    ],
                ),
            ],
            fluid=True,
            style={
                "backgroundColor": "#F3F6FB",
                "minHeight": "100vh",
                "padding": "18px 12px 26px 12px",
                "fontFamily": font_family,
            },
        )

    dash_app.layout = serve_layout

    # =====================================================================
    # CALLBACKS - TAB 1
    # =====================================================================
    def _fmt(n):
        try:
            return f"{int(n):,}".replace(",", " ")
        except (TypeError, ValueError):
            return "0"

    EXCLUDE_COMPARATIVA_SQL = "patologia <> 'SIN PATOLOGIA'"  # no es una patologia catalogada: domina y no aporta al comparativo

    @dash_app.callback(
        Output("ejec-comp-kpis", "children"),
        Output("ejec-comp-feedback", "children"),
        Output("ejec-fig-ranking-red", "figure"),
        Input("ejec-anio", "value"),
    )
    def update_comparativa(anio):
        anio_list = _as_list(anio)
        if not anio_list:
            return [], None, empty_fig()

        # --- Total general / patologias activas (mv_ejec_pat_resumen) ---
        rank_df, err = run_df(
            f"SELECT patologia, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_resumen "
            f"WHERE anio = ANY(:anio) AND patologia NOT IN ('TOTAL GENERAL', 'TOTAL CATALOGADO', 'SIN PATOLOGIA') "
            f"GROUP BY patologia ORDER BY pacientes DESC",
            {"anio": anio_list},
        )
        if err:
            return [], dbc.Alert(err, color="warning"), empty_fig(err)
        if rank_df is None or rank_df.empty:
            return [], dbc.Alert("Sin datos para el filtro seleccionado.", color="info"), empty_fig()

        total_df, _ = run_df(
            f"SELECT COALESCE(SUM(pacientes),0) AS pacientes FROM {SCHEMA}.mv_ejec_pat_resumen "
            f"WHERE anio = ANY(:anio) AND patologia = ANY(:pats)",
            {"anio": anio_list, "pats": GLOBAL_PATOLOGIAS},
        )
        pac_total = int(total_df["pacientes"].iloc[0]) if total_df is not None and not total_df.empty else 0

        rd = rank_df.copy()

        # --- KPIs: hotspots (top-1 por red y por centro = combinacion a identificar rapido) ---
        kpis = [
            kpi_card("Pacientes · Alto costo (Raras + Oncologico + Renal)", _fmt(pac_total), "bi-people-fill"),
            kpi_card("Patologias activas", _fmt(len(rd)), "bi-clipboard2-pulse", "#00A3A3"),
        ]
        top_red_df, _ = run_df(
            f"SELECT patologia, redasisdes, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_red "
            f"WHERE anio = ANY(:anio) AND {EXCLUDE_COMPARATIVA_SQL} AND redasisdes IS NOT NULL "
            f"GROUP BY patologia, redasisdes ORDER BY pacientes DESC LIMIT 1",
            {"anio": anio_list},
        )
        if top_red_df is not None and not top_red_df.empty:
            top_red = top_red_df.iloc[0]
            kpis.append(kpi_card(
                "Mayor concentracion · Red",
                _fmt(top_red["pacientes"]),
                "bi-diagram-3", "#F2A900",
                subtitle=f"{_pat_label(top_red['patologia'])} en {top_red['redasisdes']}",
            ))
        top_centro_df, _ = run_df(
            f"SELECT patologia, cenasides, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_centro "
            f"WHERE anio = ANY(:anio) AND {EXCLUDE_COMPARATIVA_SQL} AND cenasides IS NOT NULL "
            f"GROUP BY patologia, cenasides ORDER BY pacientes DESC LIMIT 1",
            {"anio": anio_list},
        )
        if top_centro_df is not None and not top_centro_df.empty:
            top_centro = top_centro_df.iloc[0]
            kpis.append(kpi_card(
                "Mayor concentracion · Centro",
                _fmt(top_centro["pacientes"]),
                "bi-hospital", "#E4572E",
                subtitle=f"{_pat_label(top_centro['patologia'])} en {top_centro['cenasides']}",
            ))

        # --- Ranking por red: Raras + Oncologico + Renal, distinguidas por color ---
        red_df, _ = run_df(
            f"SELECT redasisdes, patologia, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_red "
            f"WHERE anio = ANY(:anio) AND patologia = ANY(:pats) AND redasisdes IS NOT NULL "
            f"GROUP BY redasisdes, patologia",
            {"anio": anio_list, "pats": GLOBAL_PATOLOGIAS},
        )
        if red_df is None or red_df.empty:
            fig_ranking_red = empty_fig()
        else:
            rdf = red_df.copy()
            rdf["patologia_label"] = rdf["patologia"].map(_pat_label)
            totales_red = rdf.groupby("redasisdes")["pacientes"].sum().sort_values(ascending=False)
            top_redes = totales_red.head(15).index.tolist()
            rdf = rdf[rdf["redasisdes"].isin(top_redes)]
            color_map = {_pat_label(k): v for k, v in GLOBAL_COLORS.items()}
            fig_ranking_red = px.bar(
                rdf, x="pacientes", y="redasisdes", color="patologia_label", orientation="h",
                color_discrete_map=color_map, text="pacientes",
            )
            fig_ranking_red.update_traces(
                texttemplate="%{text:,}",
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white", size=13),
                hovertemplate="%{y}<br>%{fullData.name}: %{x:,} pacientes<extra></extra>",
            )
            fig_ranking_red.update_layout(barmode="stack", legend_title_text=None)
            fig_ranking_red.update_yaxes(title=None, categoryorder="total ascending")
            fig_ranking_red.update_xaxes(title="Pacientes")
            style_fig(fig_ranking_red, height=max(320, 34 * len(top_redes)))

        return kpis, None, fig_ranking_red

    @dash_app.callback(
        Output("ejec-centro-detalle", "options"),
        Output("ejec-centro-detalle", "value"),
        Input("ejec-red-detalle", "value"),
    )
    def sync_centro_detalle(red_value):
        return get_centro_detalle_options(red_value), ["TODOS"]

    @dash_app.callback(
        Output("ejec-kpis", "children"),
        Output("ejec-feedback", "children"),
        Output("ejec-fig-tendencia", "figure"),
        Output("ejec-fig-servicio", "figure"),
        Output("ejec-fig-centro", "figure"),
        Output("ejec-fig-sexo", "figure"),
        Output("ejec-fig-edad", "figure"),
        Output("ejec-tabla-diag", "children"),
        Input("ejec-pat", "value"),
        Input("ejec-anio-detalle", "value"),
        Input("ejec-red-detalle", "value"),
        Input("ejec-centro-detalle", "value"),
        Input("ejec-edad-detalle", "value"),
    )
    def update_detalle(pat, anio, red_cod, centro_cod, edad_grupo):
        pat_list = _as_list(pat)
        anio_list = _as_list(anio)
        if not pat_list or not anio_list:
            return [], None, empty_fig(), empty_fig(), empty_fig(), empty_fig(), empty_fig(), None
        red_list = _as_list(red_cod) or ["TODAS"]
        centro_list = _as_list(centro_cod) or ["TODOS"]
        edad_list = _as_list(edad_grupo) or ["TODOS"]
        base_params = {"pat": pat_list, "anio": anio_list, "red": red_list, "centro": centro_list}
        base_where = "patologia = ANY(:pat) AND anio = ANY(:anio) AND redasiscod = ANY(:red) AND cod_centro = ANY(:centro)"
        filtro_params = {**base_params, "edad": edad_list}
        filtro_where = f"{base_where} AND grupo_edad = ANY(:edad)"

        res_df, err = run_df(
            f"SELECT COALESCE(SUM(pacientes),0) AS pacientes FROM {SCHEMA}.mv_ejec_pat_detalle WHERE {filtro_where}",
            filtro_params,
        )
        if err:
            return [], dbc.Alert(err, color="warning"), empty_fig(err), empty_fig(), empty_fig(), empty_fig(), empty_fig(), None

        pac_pat = 0
        if res_df is not None and not res_df.empty:
            pac_pat = res_df["pacientes"].iloc[0]

        diag_count_df, _ = run_df(
            f"SELECT COUNT(DISTINCT cod_diagnostico) AS n FROM {SCHEMA}.mv_ejec_pat_diag WHERE {filtro_where}",
            filtro_params,
        )
        n_diag = int(diag_count_df["n"].iloc[0]) if diag_count_df is not None and not diag_count_df.empty else 0
        pat_label = _pat_label(pat_list[0]) if len(pat_list) == 1 else f"{len(pat_list)} patologias"
        kpis = [
            kpi_card(f"Pacientes · {pat_label}", _fmt(pac_pat), "bi-person-badge", "#00A3A3"),
            kpi_card("Diagnosticos distintos", _fmt(n_diag), "bi-diagram-3", "#7B61FF"),
        ]

        # Evolucion anual (ignora el filtro de anio: se ve todo el historico;
        # respeta patologia/red/centro/grupo_edad). Una linea por patologia
        # seleccionada.
        trend_df, _ = run_df(
            f"SELECT anio, patologia, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_detalle "
            f"WHERE patologia = ANY(:pat) AND anio <> 'TODOS' AND redasiscod = ANY(:red) "
            f"AND cod_centro = ANY(:centro) AND grupo_edad = ANY(:edad) "
            f"GROUP BY anio, patologia ORDER BY anio",
            {"pat": pat_list, "red": red_list, "centro": centro_list, "edad": edad_list},
        )
        if trend_df is None or trend_df.empty:
            fig_trend = empty_fig()
        else:
            trend_df = trend_df.copy()
            trend_df["patologia"] = trend_df["patologia"].map(_pat_label)
            if len(pat_list) > 1:
                fig_trend = px.line(trend_df, x="anio", y="pacientes", color="patologia", markers=True, color_discrete_sequence=PALETTE)
            else:
                fig_trend = px.line(trend_df, x="anio", y="pacientes", markers=True)
                fig_trend.update_traces(line_color=brand, marker=dict(size=8))
            fig_trend.update_yaxes(title="Pacientes")
            fig_trend.update_xaxes(title=None)
            style_fig(fig_trend, height=340)

        # Servicios
        serv_df, _ = run_df(
            f"SELECT servhosdes, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_servicio "
            f"WHERE {filtro_where} AND servhosdes IS NOT NULL "
            f"GROUP BY servhosdes ORDER BY pacientes DESC LIMIT 15",
            filtro_params,
        )
        if serv_df is None or serv_df.empty:
            fig_serv = empty_fig()
        else:
            sd = serv_df.sort_values("pacientes")
            fig_serv = px.bar(sd, x="pacientes", y="servhosdes", orientation="h", text="pacientes")
            fig_serv.update_traces(marker_color=brand, texttemplate="%{text:,}", textposition="outside", cliponaxis=False)
            fig_serv.update_yaxes(title=None)
            fig_serv.update_xaxes(title="Pacientes")
            style_fig(fig_serv, height=380)

        # Ranking por centro (ignora el filtro de centro, para poder
        # rankearlos entre si, y el de grupo_edad, que mv_ejec_pat_centro no
        # tiene; respeta patologia/anio/red). Top 15, apilado por patologia
        # cuando hay mas de una seleccionada.
        centro_df, _ = run_df(
            f"SELECT cenasides, patologia, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_centro "
            f"WHERE patologia = ANY(:pat) AND anio = ANY(:anio) AND redasiscod = ANY(:red) "
            f"AND cenasides IS NOT NULL "
            f"GROUP BY cenasides, patologia",
            {"pat": pat_list, "anio": anio_list, "red": red_list},
        )
        if centro_df is None or centro_df.empty:
            fig_centro = empty_fig()
        else:
            cdf = centro_df.copy()
            cdf["patologia_label"] = cdf["patologia"].map(_pat_label)
            totales_centro = cdf.groupby("cenasides")["pacientes"].sum().sort_values(ascending=False)
            top_centros = totales_centro.head(15).index.tolist()
            cdf = cdf[cdf["cenasides"].isin(top_centros)]
            if len(pat_list) > 1:
                fig_centro = px.bar(
                    cdf, x="pacientes", y="cenasides", color="patologia_label", orientation="h",
                    color_discrete_sequence=PALETTE, text="pacientes",
                )
                fig_centro.update_traces(
                    texttemplate="%{text:,}", textposition="inside", insidetextanchor="middle",
                    textfont=dict(color="white", size=12),
                    hovertemplate="%{y}<br>%{fullData.name}: %{x:,} pacientes<extra></extra>",
                )
                fig_centro.update_layout(barmode="stack", legend_title_text=None)
            else:
                fig_centro = px.bar(cdf, x="pacientes", y="cenasides", orientation="h", text="pacientes")
                fig_centro.update_traces(
                    marker_color=brand, texttemplate="%{text:,}", textposition="outside", cliponaxis=False,
                    hovertemplate="%{y}<br>%{x:,} pacientes<extra></extra>",
                )
            fig_centro.update_yaxes(title=None, categoryorder="total ascending")
            fig_centro.update_xaxes(title="Pacientes")
            style_fig(fig_centro, height=max(320, 34 * len(top_centros)))

        # Sexo: respeta el grupo etario seleccionado (si es "Todos", es el
        # marginal exacto de siempre; si son grupos especificos, es el cruce
        # sexo x grupo_edad de esos grupos).
        sexo_df, _ = run_df(
            f"SELECT sexo, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_sexo_edad "
            f"WHERE {filtro_where} AND sexo <> 'TODOS' "
            f"GROUP BY sexo",
            filtro_params,
        )
        fig_sexo = _build_pie(sexo_df, "sexo", SEXO_ORDER, SEXO_COLORS, label_map=SEXO_LABELS)

        # Grupo etario: ignora el filtro de grupo etario (se ve la composicion
        # completa, igual que la evolucion anual ignora el filtro de anio);
        # respeta patologia/anio/red/centro. Marginal exacto (no la suma de
        # las celdas cruzadas, que sobrecontaria pacientes que cambiaron de
        # grupo_edad entre anios).
        edad_df, _ = run_df(
            f"SELECT grupo_edad, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_sexo_edad "
            f"WHERE {base_where} AND sexo = 'TODOS' AND grupo_edad <> 'TODOS' "
            f"GROUP BY grupo_edad",
            base_params,
        )
        fig_edad = _build_pie(edad_df, "grupo_edad", EDAD_ORDER, EDAD_COLORS)

        # Tabla diagnosticos
        diag_df, _ = run_df(
            f"SELECT cod_diagnostico, diagdes, tipodiagnom, SUM(pacientes) AS pacientes, SUM(registros) AS registros "
            f"FROM {SCHEMA}.mv_ejec_pat_diag WHERE {filtro_where} "
            f"GROUP BY cod_diagnostico, diagdes, tipodiagnom "
            f"ORDER BY pacientes DESC",
            filtro_params,
        )
        tabla = _build_diag_table(diag_df)

        return kpis, None, fig_trend, fig_serv, fig_centro, fig_sexo, fig_edad, tabla

    def _build_pie(df, cat_col, order, color_map, label_map=None, height=320):
        if df is None or df.empty:
            return empty_fig()
        d = df.copy()
        d[cat_col] = pd.Categorical(d[cat_col], categories=order, ordered=True)
        d = d.sort_values(cat_col)
        keys = d[cat_col].astype(str).tolist()
        labels = [label_map.get(k, k) if label_map else k for k in keys]
        colors = [color_map.get(k, "#C3C2B7") for k in keys]
        fig = go.Figure(
            data=go.Pie(
                labels=labels,
                values=d["pacientes"],
                hole=0.45,
                sort=False,
                marker=dict(colors=colors, line=dict(color="white", width=2)),
                textinfo="percent",
                hovertemplate="%{label}<br>Pacientes: %{value:,}<br>%{percent}<extra></extra>",
            )
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=height,
            paper_bgcolor="white",
            font=dict(family=font_family, size=12, color="#374151"),
            showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
        )
        return fig

    def _build_diag_table(diag_df):
        if diag_df is None or diag_df.empty:
            return html.Div("Sin diagnosticos para el filtro seleccionado.", style={"color": muted, "padding": "10px"})
        d = diag_df.copy()
        d["pacientes"] = pd.to_numeric(d["pacientes"], errors="coerce").fillna(0).round().astype(int)
        d = d.drop(columns=["registros"], errors="ignore").fillna("").astype(str)
        return dash_table.DataTable(
            columns=[
                {"name": "CIE-10", "id": "cod_diagnostico"},
                {"name": "Diagnostico", "id": "diagdes"},
                {"name": "Tipo", "id": "tipodiagnom"},
                {"name": "Pacientes", "id": "pacientes"},
            ],
            data=d.to_dict("records"),
            page_action="none",
            fixed_rows={"headers": True},
            style_table={"overflowX": "auto", "overflowY": "auto", "maxHeight": "320px"},
            style_cell={"textAlign": "left", "fontFamily": font_family, "fontSize": "12px", "padding": "7px"},
            style_header={"backgroundColor": brand_soft, "fontWeight": 700, "border": f"1px solid {border}"},
            style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#F8FAFF"}],
        )

    # =====================================================================
    # CALLBACKS - TAB 2
    # =====================================================================
    @dash_app.callback(
        Output("ejec-paciente-info", "children"),
        Output("ejec-matriz", "children"),
        Output("ejec-detalle", "children"),
        Output("ejec-detalle-store", "data"),
        Input("ejec-buscar", "n_clicks"),
        Input("ejec-doc", "n_submit"),
        State("ejec-doc", "value"),
        prevent_initial_call=True,
    )
    def buscar_paciente(n_clicks, n_submit, doc):
        doc = (doc or "").strip()
        if not doc:
            return dbc.Alert("Ingrese un documento de paciente.", color="warning"), None, None, None

        df, err = run_df(
            f"""SELECT anio, patologia, area, cenasides, servhosdes,
                       cod_diagnostico, diagdes, tipodiagnom, sexo, anio_edad
                FROM {SCHEMA}.mv_ejec_base
                WHERE doc_paciente = :doc
                ORDER BY anio, patologia, cod_diagnostico""",
            {"doc": doc},
        )
        if err:
            return dbc.Alert(err, color="warning"), None, None, None
        if df is None or df.empty:
            return dbc.Alert(f"No se encontraron registros para el documento {doc}.", color="info"), None, None, None

        # Info del paciente
        sexo = df["sexo"].dropna().iloc[0] if df["sexo"].notna().any() else "-"
        edades = pd.to_numeric(df["anio_edad"], errors="coerce").dropna()
        edad_rango = f"{int(edades.min())}-{int(edades.max())} anios" if not edades.empty else "-"
        n_pat = df.loc[df["patologia"] != "SIN PATOLOGIA", "patologia"].nunique()
        centros = df["cenasides"].dropna().nunique()
        info = html.Div(
            [
                _pill("Documento", doc, "bi-person-vcard"),
                _pill("Sexo", "Masculino" if sexo == "M" else ("Femenino" if sexo == "F" else "-"), "bi-gender-ambiguous"),
                _pill("Rango de edad", edad_rango, "bi-calendar-heart"),
                _pill("Patologias", str(n_pat), "bi-clipboard2-pulse"),
                _pill("Centros", str(centros), "bi-hospital"),
            ],
            style={**card_style, "display": "flex", "gap": "12px", "flexWrap": "wrap", "padding": "14px 16px"},
        )

        matriz = _build_matriz(df)
        detalle = _build_detalle(df)
        store = df.fillna("").astype(str).to_dict("records")
        return info, matriz, detalle, {"doc": doc, "rows": store}

    def _pill(label, value, icon):
        return html.Div(
            [
                html.I(className=f"bi {icon}", style={"color": brand, "fontSize": "18px"}),
                html.Div(
                    [html.Div(value, style={"fontWeight": 700, "color": "#111827"}), html.Small(label, style={"color": muted})],
                    style={"display": "flex", "flexDirection": "column"},
                ),
            ],
            style={"display": "flex", "alignItems": "center", "gap": "8px", "flex": "1 1 150px"},
        )

    def _build_matriz(df):
        pat_df = df[df["patologia"] != "SIN PATOLOGIA"]
        if pat_df.empty:
            return html.Div("El paciente no presenta patologias catalogadas.", style={"color": muted, "padding": "10px"})
        presence = pat_df.groupby(["patologia", "anio"]).size().reset_index(name="n")
        anios = [a for a in ANIO_ORDER if a in presence["anio"].unique()] or sorted(presence["anio"].unique())
        rows = []
        for pat in sorted(presence["patologia"].unique()):
            row = {"patologia": pat.replace("_", " ").title()}
            for a in anios:
                has = not presence[(presence["patologia"] == pat) & (presence["anio"] == a)].empty
                row[a] = "✓" if has else ""
            rows.append(row)
        columns = [{"name": "Patologia", "id": "patologia"}] + [{"name": a, "id": a} for a in anios]
        return dash_table.DataTable(
            columns=columns,
            data=rows,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "center", "fontFamily": font_family, "fontSize": "13px", "padding": "8px"},
            style_cell_conditional=[{"if": {"column_id": "patologia"}, "textAlign": "left", "fontWeight": 600, "minWidth": "180px"}],
            style_header={"backgroundColor": brand_soft, "fontWeight": 700, "border": f"1px solid {border}"},
            style_data_conditional=[
                {"if": {"filter_query": "{" + a + "} = '✓'", "column_id": a}, "backgroundColor": "#DCFCE7", "color": "#166534", "fontWeight": 700}
                for a in anios
            ],
        )

    def _build_detalle(df):
        d = df.copy()
        d["anio_edad"] = pd.to_numeric(d["anio_edad"], errors="coerce")
        d = d.fillna("").astype(str)
        d["patologia"] = d["patologia"].str.replace("_", " ").str.title()
        return dash_table.DataTable(
            columns=[
                {"name": "Anio", "id": "anio"},
                {"name": "Patologia", "id": "patologia"},
                {"name": "Area", "id": "area"},
                {"name": "Centro", "id": "cenasides"},
                {"name": "Servicio", "id": "servhosdes"},
                {"name": "CIE-10", "id": "cod_diagnostico"},
                {"name": "Diagnostico", "id": "diagdes"},
                {"name": "Tipo", "id": "tipodiagnom"},
            ],
            data=d.to_dict("records"),
            page_size=15,
            filter_action="native",
            sort_action="native",
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "fontFamily": font_family, "fontSize": "12px", "padding": "7px", "maxWidth": "280px", "whiteSpace": "normal"},
            style_header={"backgroundColor": brand_soft, "fontWeight": 700, "border": f"1px solid {border}"},
            style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#F8FAFF"}],
        )

    @dash_app.callback(
        Output("ejec-download", "data"),
        Input("ejec-dl-btn", "n_clicks"),
        State("ejec-detalle-store", "data"),
        prevent_initial_call=True,
    )
    def descargar_detalle(n_clicks, store):
        if not n_clicks or not store or not store.get("rows"):
            return no_update
        df = pd.DataFrame(store["rows"])
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        filename = f"comorbilidad_{store.get('doc','paciente')}_{datetime.now():%Y%m%d_%H%M%S}.csv"
        return {"content": "﻿" + buffer.getvalue(), "filename": filename, "type": "text/csv"}

    return dash_app


def _pat_label(value):
    return str(value).replace("_", " ").title()
