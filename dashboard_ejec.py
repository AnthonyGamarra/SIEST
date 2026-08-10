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

# Paleta categorica validada (orden fijo = mecanismo de seguridad CVD, no
# cosmetico: no reordenar ni ciclar). Pasa lightness band, chroma floor,
# separacion CVD y piso de vision normal en modo claro.
PALETTE = ["#2A78D6", "#008300", "#E87BA4", "#EDA100", "#1BAF7A", "#EB6834", "#4A3AA7", "#E34948"]

SEXO_ORDER = ["M", "F"]
SEXO_LABELS = {"M": "Masculino", "F": "Femenino"}
SEXO_COLORS = {"M": PALETTE[0], "F": PALETTE[7]}

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
    def _tint(hex_color, alpha=0.14):
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    def kpi_card(title, value, icon, color=brand, subtitle=None):
        body = [
            html.Div(value, style={"fontSize": "28px", "fontWeight": 800, "color": "#111827", "lineHeight": "1.15", "fontVariantNumeric": "tabular-nums"}),
            html.Small(title, style={"color": muted, "fontWeight": 600}),
        ]
        if subtitle:
            body.append(html.Small(subtitle, style={"color": color, "fontWeight": 600, "fontSize": "11px"}))
        return html.Div(
            [
                html.Div(
                    html.I(className=f"bi {icon} ejec-kpi-icon", style={"fontSize": "22px", "color": color}),
                    style={
                        "width": "46px", "height": "46px", "borderRadius": "12px",
                        "backgroundColor": _tint(color), "display": "flex",
                        "alignItems": "center", "justifyContent": "center", "flexShrink": "0",
                    },
                ),
                html.Div(body, style={"display": "flex", "flexDirection": "column", "gap": "2px", "minWidth": 0}),
            ],
            className="ejec-card",
            style={
                **card_style, "display": "flex", "alignItems": "center", "gap": "14px",
                "flex": "1 1 230px", "padding": "16px 18px", "borderLeft": f"3px solid {color}",
            },
        )

    def empty_fig(msg="Sin datos"):
        fig = go.Figure()
        fig.add_annotation(
            text=f"<span style='font-size:20px'>&#128202;</span><br>{msg}",
            showarrow=False, font=dict(size=13, color=muted, family=font_family), align="center",
        )
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
            hoverlabel=dict(bgcolor="white", bordercolor="#E5E7EB", font=dict(family=font_family, size=12, color="#111827")),
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="#F1F5F9", zerolinecolor="#F1F5F9")
        return fig

    def graph_card(title, graph_id, height=340, subtitle=None, flex="1 1 380px", figure=None):
        header = [html.Div(title, style={"fontWeight": 700, "color": brand, "fontSize": "15px"})]
        if subtitle:
            header.append(html.Small(subtitle, style={"color": muted, "lineHeight": "1.4"}))
        return html.Div(
            [
                html.Div(header, style={"marginBottom": "10px", "display": "flex", "flexDirection": "column", "gap": "3px"}),
                dcc.Loading(
                    dcc.Graph(id=graph_id, figure=figure if figure is not None else {}, config={"displayModeBar": False}),
                    type="default",
                    color=brand,
                ),
            ],
            className="ejec-card",
            style={**card_style, "flex": flex, "minWidth": "320px"},
        )

    ALERT_STYLES = {
        "warning": {"bg": "#FFF7E6", "border": "#F5C451", "ink": "#8A5B00", "icon": "bi-exclamation-triangle-fill"},
        "info": {"bg": "#EFF6FF", "border": "#93C5FD", "ink": "#1D4ED8", "icon": "bi-info-circle-fill"},
    }

    def alert_box(msg, kind="info"):
        s = ALERT_STYLES.get(kind, ALERT_STYLES["info"])
        return html.Div(
            [
                html.I(className=f"bi {s['icon']}", style={"fontSize": "16px", "color": s["ink"], "flexShrink": "0", "marginTop": "1px"}),
                html.Span(msg, style={"color": s["ink"], "fontFamily": font_family, "fontSize": "13px", "fontWeight": 600, "lineHeight": "1.4"}),
            ],
            style={
                "display": "flex", "alignItems": "flex-start", "gap": "10px",
                "backgroundColor": s["bg"], "border": f"1px solid {s['border']}",
                "borderRadius": "12px", "padding": "12px 16px",
            },
        )

    GLOBAL_PATOLOGIAS = ["Raras", "Oncologico", "Renal"]
    GLOBAL_COLORS = {"Oncologico": brand, "Renal": PALETTE[4], "Raras": PALETTE[3]}

    GROWTH_GOOD_COLOR = "#1BAF7A"  # baja de pacientes = mejora (verde)
    GROWTH_BAD_COLOR = "#E34948"   # sube de pacientes = empeora (rojo)
    GROWTH_FLAT_COLOR = "#6B7280"

    def _with_growth_labels(df, group_col, value_col="pacientes"):
        """Agrega 'label_text' (valor + variacion vs el anio anterior dentro
        del mismo grupo, con icono ▲/▼/►) y 'growth_color' (color de estado
        del icono/porcentaje, independiente del color categorico de la
        linea). Sin variacion en el primer anio de cada grupo, no hay anio
        previo con que comparar."""
        d = df.copy()
        prev = d.groupby(group_col)[value_col].shift(1)

        def _fmt_row(value, prev_value):
            val_txt = f"{int(value):,}"
            if pd.isna(prev_value) or prev_value == 0:
                return val_txt, GROWTH_FLAT_COLOR
            pct = (value - prev_value) / prev_value * 100
            if pct > 0:
                icon, sign, color = "▲", "+", GROWTH_BAD_COLOR
            elif pct < 0:
                icon, sign, color = "▼", "", GROWTH_GOOD_COLOR
            else:
                icon, sign, color = "►", "", GROWTH_FLAT_COLOR
            return f"{val_txt}<br>{icon} {sign}{pct:.1f}%", color

        formatted = [_fmt_row(v, p) for v, p in zip(d[value_col], prev)]
        d["label_text"] = [f[0] for f in formatted]
        d["growth_color"] = [f[1] for f in formatted]
        return d

    def _apply_growth_textcolor(fig, df, group_col, x_col="anio"):
        """Colorea cada etiqueta de texto (icono + %%) con su color de estado
        (verde/rojo/gris), independiente del color categorico de la linea,
        que sigue identificando la patologia."""
        for trace in fig.data:
            sub = df[df[group_col] == trace.name] if trace.name in set(df[group_col]) else df
            sub = sub.set_index(x_col).reindex(trace.x).reset_index()
            trace.textfont = dict(size=11, color=sub["growth_color"].tolist())
        return fig

    TREND_ESTIMATE_UNTIL_YEAR = 2030

    def _add_trendlines(fig, df, group_col, x_col="anio", y_col="pacientes", exclude_x=None):
        """Agrega, por cada serie ya presente en el grafico, una recta de
        tendencia (regresion lineal simple sobre el orden de los anios)
        punteada del mismo color que su linea, visible por defecto (se puede
        ocultar haciendo clic en la leyenda). Excluye 2019, 2020 y 2021 del
        ajuste (y del propio trazo) por ser anios atipicos, y tambien el
        anio en curso (calculado dinamicamente) por no ser un anio cerrado
        todavia: la linea de datos real si los sigue mostrando, solo la
        tendencia los ignora. Extiende la tendencia anio a anio desde el
        ultimo anio considerado hasta TREND_ESTIMATE_UNTIL_YEAR y marca esos
        puntos como estimados (simbolo distinto + etiqueta), sin
        confundirlos con datos reales."""
        if exclude_x is None:
            exclude_x = {"2019", "2020", "2021", str(datetime.now().year)}
        traces = list(fig.data)

        def _color_for(group):
            t = traces[0] if len(traces) == 1 else next((t for t in traces if t.name == group), None)
            if t is None:
                return "#9CA3AF"
            if t.line and t.line.color:
                return t.line.color
            if t.marker and t.marker.color:
                return t.marker.color
            return "#9CA3AF"

        for group, sub in df.groupby(group_col):
            sub = sub.sort_values(x_col)
            if exclude_x:
                sub = sub[~sub[x_col].isin(exclude_x)]
            if len(sub) < 2:
                continue
            color = _color_for(group)
            x_idx = np.arange(len(sub))
            slope, intercept = np.polyfit(x_idx, sub[y_col].astype(float), 1)
            y_fit = slope * x_idx + intercept

            try:
                last_year_int = int(sub[x_col].iloc[-1])
            except (TypeError, ValueError):
                last_year_int = None

            future_years = (
                [str(y) for y in range(last_year_int + 1, TREND_ESTIMATE_UNTIL_YEAR + 1)]
                if last_year_int is not None else []
            )

            if future_years:
                y_future = [slope * (len(sub) + i) + intercept for i in range(len(future_years))]
                x_line = list(sub[x_col]) + future_years
                y_line = list(y_fit) + y_future
            else:
                x_line, y_line = list(sub[x_col]), list(y_fit)

            fig.add_trace(go.Scatter(
                x=x_line, y=y_line, mode="lines",
                line=dict(dash="dot", width=2, color=color),
                name=f"Tendencia {group}", legendgroup=str(group),
                showlegend=True, visible=True, hoverinfo="skip",
            ))

            if future_years:
                fig.add_trace(go.Scatter(
                    x=future_years, y=y_future, mode="markers+text",
                    marker=dict(symbol="diamond-open", size=11, color=color, line=dict(width=2, color=color)),
                    text=[f"{v:,.0f}<br>(estimado)" for v in y_future], textposition="top center",
                    textfont=dict(size=11, color=color),
                    name=f"Tendencia {group}", legendgroup=str(group), showlegend=False,
                    hovertemplate="%{x} (estimado)<br>%{y:,.0f} pacientes<extra></extra>",
                ))
        return fig

    def _build_pacientes_total_fig():
        """% de pacientes por patologia de alto costo (Raras/Oncologico/
        Renal) sobre el total de las 3, historico completo (anio='TODOS',
        igual criterio que el resto del modulo)."""
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
            data=go.Pie(
                labels=labels,
                values=d["pacientes"],
                hole=0.5,
                marker=dict(colors=colors, line=dict(color="white", width=2)),
                texttemplate="%{label}<br>%{percent:.1%} (%{value:,})",
                textposition="outside",
                hovertemplate="%{label}<br>%{value:,} pacientes (%{percent:.1%})<extra></extra>",
                sort=False,
            )
        )
        style_fig(fig, height=480)
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
        d = _with_growth_labels(d, "patologia_label")
        color_map = {_pat_label(k): v for k, v in GLOBAL_COLORS.items()}
        fig = px.line(
            d, x="anio", y="pacientes", color="patologia_label", markers=True,
            color_discrete_map=color_map, text="label_text",
        )
        fig.update_traces(
            texttemplate="%{text}",
            textposition="top center",
            textfont=dict(size=11),
            marker=dict(size=8),
            line=dict(width=3),
            hovertemplate="%{x}<br>%{fullData.name}: %{y:,} pacientes<extra></extra>",
        )
        _apply_growth_textcolor(fig, d, "patologia_label")
        _add_trendlines(fig, d, "patologia_label")
        fig.update_yaxes(title="Pacientes")
        fig.update_xaxes(title=None)
        style_fig(fig, height=480)
        fig.update_layout(legend_title_text=None, margin=dict(t=50))
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

    def _build_comorbilidad_burbujas_fig():
        """Todas las intersecciones entre patologias, con un solo eje
        categorico (patologia en Y) para no terminar armando una grilla de
        dos ejes (que en la practica ya es un heatmap). Cada fila muestra,
        como una nube de burbujas horizontal, con que otras patologias se
        cruza esa patologia; posicion en X, tamaño y color = pacientes en
        comun. Diagonal excluida porque no es una interseccion real.
        Historico completo, sin filtro de anio."""
        df, err = run_df(
            f"SELECT patologia_a, patologia_b, pacientes FROM {SCHEMA}.mv_ejec_comorbilidad "
            f"WHERE patologia_a <> patologia_b AND pacientes > 0"
        )
        if err or df is None or df.empty:
            return empty_fig(err or "Sin datos")

        total_df, _ = run_df(
            f"SELECT patologia_a, pacientes FROM {SCHEMA}.mv_ejec_comorbilidad WHERE patologia_a = patologia_b"
        )
        totals = total_df.set_index("patologia_a")["pacientes"] if total_df is not None and not total_df.empty else pd.Series(dtype=float)

        order = sorted(set(df["patologia_a"]), key=lambda p: -totals.get(p, 0))
        order_labels = [_pat_label(p) for p in order]

        d = df.copy()
        d["patologia_a_label"] = d["patologia_a"].map(_pat_label)
        d["patologia_b_label"] = d["patologia_b"].map(_pat_label)

        fig = go.Figure(
            data=go.Scatter(
                x=d["pacientes"],
                y=d["patologia_a_label"],
                mode="markers",
                marker=dict(
                    size=d["pacientes"],
                    sizemode="area",
                    sizeref=2.0 * d["pacientes"].max() / (64.0 ** 2),
                    sizemin=6,
                    color=d["pacientes"],
                    colorscale=[[0, "#CDE2FB"], [1, "#104281"]],
                    showscale=True,
                    colorbar=dict(title="Pacientes", thickness=14, len=0.9, tickfont=dict(size=13), title_font=dict(size=14)),
                    line=dict(width=0.5, color="white"),
                ),
                customdata=d["patologia_b_label"],
                hovertemplate="%{y} ∩ %{customdata}<br>%{x:,} pacientes<extra></extra>",
            )
        )
        fig.update_yaxes(
            categoryorder="array", categoryarray=list(reversed(order_labels)),
            automargin=True, showgrid=False, title=None,
            tickfont=dict(size=16),
        )
        fig.update_xaxes(
            title="Pacientes en común", showgrid=True, gridcolor="#F1F5F9",
            tickfont=dict(size=15), title_font=dict(size=15),
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=max(460, 30 * len(order_labels)),
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family=font_family, size=15, color="#374151"),
        )
        return fig

    def _soften(hex_color, alpha=0.45):
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    def _build_flujo_area_fig(anio_list, top_n_servicio=6):
        """Sankey de 3 etapas: Patologia de alto costo -> Area asistencial ->
        Servicio. Etapa 1->2: pacientes por patologia y area (Raras/
        Oncologico/Renal). Etapa 2->3: dentro de cada area, sus servicios mas
        frecuentes agregados entre las 3 patologias; top N_SERVICIO por area,
        el resto plegado en 'Otros servicios' (hay areas con 40-97 servicios
        distintos, sin plegar se satura). Responde al filtro de Anio.
        Ojo: NO es una secuencia cronologica del paciente (mv_ejec_base no
        tiene fecha, solo anio, asi que no se puede reconstruir el orden en
        que un paciente paso por cada area/servicio) — es la distribucion
        patologia -> area -> servicio, leida de mv_ejec_pat_area_servicio."""
        df, err = run_df(
            f"SELECT patologia, area, servhosdes, SUM(pacientes) AS pacientes "
            f"FROM {SCHEMA}.mv_ejec_pat_area_servicio "
            f"WHERE anio = ANY(:anio) AND patologia = ANY(:pats) AND area IS NOT NULL "
            f"GROUP BY patologia, area, servhosdes",
            {"anio": anio_list, "pats": GLOBAL_PATOLOGIAS},
        )
        if err or df is None or df.empty:
            return empty_fig(err or "Sin datos")

        d = df.copy()
        d["patologia_label"] = d["patologia"].map(_pat_label)
        pat_color_map = {_pat_label(p): GLOBAL_COLORS.get(p, brand) for p in GLOBAL_PATOLOGIAS}

        # Etapa 1 -> 2: patologia -> area (suma sobre servicios)
        pat_area = d.groupby(["patologia_label", "area"])["pacientes"].sum().reset_index()

        # Etapa 2 -> 3: area -> servicio (suma sobre patologias), top N por area
        area_serv = d.groupby(["area", "servhosdes"])["pacientes"].sum().reset_index()
        rows = []
        for area, grupo in area_serv.groupby("area"):
            grupo = grupo.sort_values("pacientes", ascending=False)
            rows.append(grupo.head(top_n_servicio))
            resto = grupo.iloc[top_n_servicio:]
            if not resto.empty:
                rows.append(pd.DataFrame([{
                    "area": area,
                    "servhosdes": f"Otros servicios ({len(resto)})",
                    "pacientes": resto["pacientes"].sum(),
                }]))
        area_serv2 = pd.concat(rows, ignore_index=True)
        # Nodo scoped por area: el mismo nombre de servicio puede existir en mas de un area
        area_serv2["servicio_nodo"] = area_serv2["area"] + " · " + area_serv2["servhosdes"]

        pat_nodes = [p for p in pat_color_map if p in set(pat_area["patologia_label"])]
        area_order = ["CONSULTA EXTERNA", "EMERGENCIA", "HOSPITALIZACION", "CENTRO QUIRURGICO"]
        area_nodes = [a for a in area_order if a in set(pat_area["area"])]
        serv_nodes = area_serv2["servicio_nodo"].tolist()

        nodes = pat_nodes + area_nodes + serv_nodes
        idx = {label: i for i, label in enumerate(nodes)}
        node_labels = (
            [n.title() for n in pat_nodes]
            + [n.title() for n in area_nodes]
            + [row["servhosdes"].title() for _, row in area_serv2.iterrows()]
        )
        node_colors = (
            [pat_color_map[p] for p in pat_nodes]
            + ["#D1D5DB"] * len(area_nodes)
            + ["#E5E7EB"] * len(serv_nodes)
        )

        sources, targets, values, link_colors = [], [], [], []
        for _, row in pat_area.iterrows():
            pl, ar = row["patologia_label"], row["area"]
            if pl not in idx or ar not in idx:
                continue
            sources.append(idx[pl])
            targets.append(idx[ar])
            values.append(row["pacientes"])
            link_colors.append(_soften(pat_color_map.get(pl, brand)))
        for _, row in area_serv2.iterrows():
            ar, sv = row["area"], row["servicio_nodo"]
            if ar not in idx or sv not in idx:
                continue
            sources.append(idx[ar])
            targets.append(idx[sv])
            values.append(row["pacientes"])
            link_colors.append("rgba(156,163,175,0.45)")

        fig = go.Figure(
            data=go.Sankey(
                node=dict(
                    label=node_labels,
                    color=node_colors,
                    pad=14, thickness=16,
                    line=dict(color="white", width=0.5),
                ),
                link=dict(
                    source=sources, target=targets, value=values, color=link_colors,
                    hovertemplate="%{source.label} → %{target.label}<br>%{value:,} pacientes<extra></extra>",
                ),
            )
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=640,
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family=font_family, size=11, color="#374151"),
        )
        return fig

    def _build_diag_treemap_fig(anio_list, top_n=10, top_n_servicio=5):
        """Treemap de 3 niveles: Patologia de alto costo -> Diagnostico
        (CIE-10) -> Servicio. Top N diagnosticos por patologia (el resto se
        pliega en 'Otros diagnosticos'); dentro de cada uno de esos top N,
        top N_SERVICIO servicios (el resto se pliega en 'Otros servicios') —
        hay patologias con 40-99 servicios distintos por diagnostico, asi que
        sin plegar se satura. Responde al filtro de Anio. Tamaño = pacientes,
        color = patologia (heredado por toda su rama)."""
        df, err = run_df(
            f"SELECT patologia, diagdes, servhosdes, SUM(pacientes) AS pacientes "
            f"FROM {SCHEMA}.mv_ejec_pat_diag_servicio "
            f"WHERE anio = ANY(:anio) AND patologia = ANY(:pats) "
            f"GROUP BY patologia, diagdes, servhosdes",
            {"anio": anio_list, "pats": GLOBAL_PATOLOGIAS},
        )
        if err or df is None or df.empty:
            return empty_fig(err or "Sin datos")

        d = df.copy()
        d["patologia_label"] = d["patologia"].map(_pat_label)

        totales_diag = d.groupby(["patologia_label", "diagdes"])["pacientes"].sum().reset_index()
        rows = []
        for pat_label, grupo_pat in totales_diag.groupby("patologia_label"):
            grupo_pat = grupo_pat.sort_values("pacientes", ascending=False)
            top_diags = grupo_pat.head(top_n)["diagdes"].tolist()
            resto_diags = grupo_pat.iloc[top_n:]

            for diag in top_diags:
                sub = d[(d["patologia_label"] == pat_label) & (d["diagdes"] == diag)]
                sub = sub.sort_values("pacientes", ascending=False)
                rows.append(sub.head(top_n_servicio)[["patologia_label", "diagdes", "servhosdes", "pacientes"]])
                resto_serv = sub.iloc[top_n_servicio:]
                if not resto_serv.empty:
                    rows.append(pd.DataFrame([{
                        "patologia_label": pat_label, "diagdes": diag,
                        "servhosdes": f"Otros servicios ({len(resto_serv)})",
                        "pacientes": resto_serv["pacientes"].sum(),
                    }]))

            if not resto_diags.empty:
                rows.append(pd.DataFrame([{
                    "patologia_label": pat_label,
                    "diagdes": f"Otros diagnosticos ({len(resto_diags)})",
                    "servhosdes": "Varios servicios",
                    "pacientes": resto_diags["pacientes"].sum(),
                }]))
        d2 = pd.concat(rows, ignore_index=True)

        color_map = {_pat_label(k): v for k, v in GLOBAL_COLORS.items()}
        fig = px.treemap(
            d2, path=["patologia_label", "diagdes", "servhosdes"], values="pacientes",
            color="patologia_label", color_discrete_map=color_map,
        )
        fig.update_traces(
            texttemplate="%{label}<br>%{value:,}",
            hovertemplate="%{parent} · %{label}<br>%{value:,} pacientes<extra></extra>",
            marker=dict(line=dict(width=1, color="white")),
            pathbar=dict(visible=True, thickness=28, textfont=dict(size=13)),
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=36, b=10),
            height=560,
            paper_bgcolor="white",
            font=dict(family=font_family, size=12, color="#374151"),
        )
        return fig

    def build_header():
        return html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            html.I(className="bi bi-clipboard2-pulse", style={"fontSize": "24px", "color": brand}),
                            style={
                                "width": "48px", "height": "48px", "borderRadius": "14px",
                                "backgroundColor": brand_soft, "display": "flex",
                                "alignItems": "center", "justifyContent": "center", "flexShrink": "0",
                            },
                        ),
                        html.H2(
                            "Perfil de Comorbilidades Asociadas al Paciente",
                            style={"color": "#111827", "fontFamily": font_family, "fontSize": "23px", "fontWeight": 800, "margin": 0, "letterSpacing": "-0.01em"},
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "14px"},
                ),
                html.P(
                    "Analitica por patología y comorbilidad del paciente | Sistema de Gestion Estadistica",
                    style={"color": muted, "fontFamily": font_family, "fontSize": "13px", "margin": "8px 0 0 62px"},
                ),
            ],
            style={
                "padding": "18px 22px", "backgroundColor": card_bg, "borderRadius": "16px",
                "boxShadow": "0 8px 20px rgba(0,0,0,0.08)", "borderTop": f"3px solid {brand}",
            },
        )

    def section_title(text_, icon):
        return html.Div(
            [
                html.Div(
                    [
                        html.I(className=f"bi {icon}", style={"color": brand, "fontSize": "18px"}),
                        html.H4(text_, style={"color": "#111827", "fontFamily": font_family, "fontSize": "17px", "fontWeight": 800, "margin": 0}),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "8px"},
                ),
                html.Div(style={"flex": "1 1 auto", "height": "1px", "backgroundColor": border, "marginLeft": "12px"}),
            ],
            style={"display": "flex", "alignItems": "center", "margin": "6px 0 2px 0"},
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
                            "Pacientes por patología de alto costo: Raras / Oncológico / Renal",
                            "ejec-fig-comorbilidad-total",
                            height=480,
                            subtitle="Total de pacientes por patología (2019-2026)",
                            flex="1 1 420px",
                            figure=_build_pacientes_total_fig(),
                        ),
                        graph_card(
                            "Evolucion anual · patologías de alto costo (Raras / Oncológico / Renal)",
                            "ejec-fig-comorbilidad",
                            height=480,
                            subtitle="Pacientes por anio y patología (2019-2026)",
                            flex="2 1 560px",
                            figure=_build_comorbilidad_global_fig(),
                        ),
                    ],
                    style={"display": "flex", "gap": "14px", "flexWrap": "wrap"},
                ),
                graph_card(
                    "Ranking por red · patologías de alto costo",
                    "ejec-fig-ranking-red",
                    height=320,
                    subtitle="Pacientes de Raras + Oncológico + Renal por red asistencial, distinguidos por patología · top 15 . Responde al filtro de año",
                    flex="1 1 100%",
                ),
                html.Div(
                    [
                        graph_card(
                            "Comorbilidades asociadas a Oncológico (alto costo)",
                            "ejec-fig-comorb-oncologico",
                            height=max(320, 34 * 14),
                            subtitle="% de pacientes con Oncológico que en algun momento también tuvo cada comorbilidad asociada (lista según comorbilidades) · 2019-2026.",
                            flex="1 1 480px",
                            figure=_build_comorbilidad_grupo_fig("Oncologico", "Coomorbilidad Oncología", brand),
                        ),
                        graph_card(
                            "Comorbilidades asociadas a Renal (alto costo)",
                            "ejec-fig-comorb-renal",
                            height=max(320, 34 * 14),
                            subtitle="% de pacientes con Renal que en algun momento también tuvo cada comorbilidad asociada (lista según comorbilidades) · 2019-2026.",
                            flex="1 1 480px",
                            figure=_build_comorbilidad_grupo_fig("Renal", "Coomorbilidad Renal", "#1BAF7A"),
                        ),
                    ],
                    style={"display": "flex", "gap": "14px", "flexWrap": "wrap"},
                ),
                graph_card(
                    "Diagnosticos y servicios mas frecuentes por patología de alto costo",
                    "ejec-fig-diag-treemap",
                    height=480,
                    subtitle="Top 10 diagnosticos (CIE-10) por patología y, dentro de cada uno, sus servicios mas frecuentes · tamaño = pacientes · responde al filtro de Anio",
                    flex="1 1 100%",
                ),
                graph_card(
                    "Todas las intersecciones entre comorbilidades",
                    "ejec-fig-comorb-burbujas",
                    height=560,
                    subtitle="Cada fila = una patologia; posicion, tamaño y color de cada burbuja = pacientes que comparte con la otra patología · (2019-2026)",
                    flex="1 1 100%",
                    figure=_build_comorbilidad_burbujas_fig(),
                ),
                graph_card(
                    "Flujo de atencion: patología de alto costo → area → servicio",
                    "ejec-fig-flujo-area",
                    height=640,
                    subtitle="En que area y servicio se concentra la atencion de cada patología de alto costo · responde al filtro de Anio.",
                    flex="1 1 100%",
                ),
            ],
            style={"display": "flex", "flexDirection": "column", "gap": "14px"},
        )

        return html.Div(
            [
                section_title("Vista comparativa (todas las patologías)", "bi-grid-3x3-gap-fill"),
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
                html.Div(
                    [
                        graph_card("Distribucion por sexo", "ejec-fig-sexo", height=320, flex="1 1 260px"),
                        graph_card("Distribucion por grupo etario", "ejec-fig-edad", height=320, flex="1 1 300px"),
                        html.Div(
                            [
                                html.Div("Top diagnosticos (CIE-10)", style={"fontWeight": 700, "color": brand, "marginBottom": "8px", "fontSize": "15px"}),
                                dcc.Loading(html.Div(id="ejec-tabla-diag"), type="default"),
                            ],
                            className="ejec-card",
                            style={**card_style, "flex": "1 1 380px", "minWidth": "320px"},
                        ),
                    ],
                    style={"display": "flex", "gap": "14px", "flexWrap": "wrap"},
                ),
                graph_card("Evolucion anual", "ejec-fig-tendencia", height=400, flex="1 1 100%"),
                graph_card("Pacientes por servicio", "ejec-fig-servicio", height=380, flex="1 1 100%"),
                graph_card(
                    "Ranking por centro",
                    "ejec-fig-centro",
                    height=380,
                    subtitle="Top 15 centros asistenciales · ignora el filtro de centro (para poder rankearlos) y de grupo etario · sin filtro de red asistencial, suma entre todas",
                    flex="1 1 100%",
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
                        html.Div("Matriz de patologías por anio", style={"fontWeight": 700, "color": brand, "marginBottom": "8px", "fontSize": "15px"}),
                        html.Small("Marca (v) los anios en que el paciente presento cada patologia.", style={"color": muted}),
                        dcc.Loading(html.Div(id="ejec-matriz", style={"marginTop": "10px"}), type="default"),
                    ],
                    className="ejec-card",
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
                    className="ejec-card",
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
                    id="ejec-tabs", value="tab-detalle",
                    children=[
                        dcc.Tab(label="Detalle por patología", value="tab-detalle", children=[html.Div(build_tab_detalle(), style={"paddingTop": "16px"})]),
                        dcc.Tab(label="Analítica por patología de alto costo", value="tab1", children=[html.Div(build_tab1(), style={"paddingTop": "16px"})]),
                        dcc.Tab(label="Comorbilidad del paciente", value="tab2", children=[html.Div(build_tab2(), style={"paddingTop": "16px"})]),
                    ],
                ),
            ],
            fluid=True,
            className="ejec-dashboard-root",
            style={
                "backgroundColor": "#F3F6FB",
                "minHeight": "100vh",
                "padding": "18px 12px 26px 12px",
                "fontFamily": font_family,
            },
        )

    dash_app.layout = serve_layout


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
        Output("ejec-fig-flujo-area", "figure"),
        Output("ejec-fig-diag-treemap", "figure"),
        Input("ejec-anio", "value"),
    )
    def update_comparativa(anio):
        anio_list = _as_list(anio)
        if not anio_list:
            return [], None, empty_fig(), empty_fig(), empty_fig()

        # --- Total general / patologias activas (mv_ejec_pat_resumen) ---
        rank_df, err = run_df(
            f"SELECT patologia, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_resumen "
            f"WHERE anio = ANY(:anio) AND patologia NOT IN ('TOTAL GENERAL', 'TOTAL CATALOGADO', 'SIN PATOLOGIA') "
            f"GROUP BY patologia ORDER BY pacientes DESC",
            {"anio": anio_list},
        )
        if err:
            return [], alert_box(err, "warning"), empty_fig(err), empty_fig(), empty_fig()
        if rank_df is None or rank_df.empty:
            return [], alert_box("Sin datos para el filtro seleccionado.", "info"), empty_fig(), empty_fig(), empty_fig()

        total_df, _ = run_df(
            f"SELECT COALESCE(SUM(pacientes),0) AS pacientes FROM {SCHEMA}.mv_ejec_pat_resumen "
            f"WHERE anio = ANY(:anio) AND patologia = ANY(:pats)",
            {"anio": anio_list, "pats": GLOBAL_PATOLOGIAS},
        )
        pac_total = int(total_df["pacientes"].iloc[0]) if total_df is not None and not total_df.empty else 0

        rd = rank_df.copy()

        # --- KPIs: hotspots (top-1 por red y por centro = combinacion a identificar rapido) ---
        kpis = [
            kpi_card("Pacientes · Alto costo (Raras + Oncológico + Renal)", _fmt(pac_total), "bi-people-fill"),
            kpi_card("Patologías activas", _fmt(len(rd)), "bi-clipboard2-pulse", "#1BAF7A"),
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
                "bi-diagram-3", "#EDA100",
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
                "bi-hospital", "#EB6834",
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

        fig_flujo_area = _build_flujo_area_fig(anio_list)
        fig_diag_treemap = _build_diag_treemap_fig(anio_list)

        return kpis, None, fig_ranking_red, fig_flujo_area, fig_diag_treemap

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
            return [], alert_box(err, "warning"), empty_fig(err), empty_fig(), empty_fig(), empty_fig(), empty_fig(), None

        pac_pat = 0
        if res_df is not None and not res_df.empty:
            pac_pat = res_df["pacientes"].iloc[0]

        diag_count_df, _ = run_df(
            f"SELECT COUNT(DISTINCT cod_diagnostico) AS n FROM {SCHEMA}.mv_ejec_pat_diag WHERE {filtro_where}",
            filtro_params,
        )
        n_diag = int(diag_count_df["n"].iloc[0]) if diag_count_df is not None and not diag_count_df.empty else 0
        pat_label = _pat_label(pat_list[0]) if len(pat_list) == 1 else f"{len(pat_list)} patologías"
        kpis = [
            kpi_card(f"Pacientes · {pat_label}", _fmt(pac_pat), "bi-person-badge", "#1BAF7A"),
            kpi_card("Diagnosticos distintos", _fmt(n_diag), "bi-diagram-3", "#4A3AA7"),
        ]

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
            trend_df = _with_growth_labels(trend_df, "patologia")
            if len(pat_list) > 1:
                fig_trend = px.line(trend_df, x="anio", y="pacientes", color="patologia", markers=True, color_discrete_sequence=PALETTE, text="label_text")
                fig_trend.update_traces(
                    texttemplate="%{text}", textposition="top center", textfont=dict(size=11),
                    marker=dict(size=8), line=dict(width=3),
                )
            else:
                fig_trend = px.line(trend_df, x="anio", y="pacientes", markers=True, text="label_text")
                fig_trend.update_traces(
                    line_color=brand, marker=dict(size=8),
                    texttemplate="%{text}", textposition="top center", textfont=dict(size=11),
                )
            _apply_growth_textcolor(fig_trend, trend_df, "patologia")
            _add_trendlines(fig_trend, trend_df, "patologia")
            max_pacientes = max(v for trace in fig_trend.data for v in (trace.y if trace.y is not None else []) if v is not None)
            fig_trend.update_yaxes(title="Pacientes", range=[0, max_pacientes * 1.22])
            fig_trend.update_xaxes(title=None)
            style_fig(fig_trend, height=400)
            fig_trend.update_layout(margin=dict(t=30))

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

        # mv_ejec_pat_centro no tiene fila colapsada 'TODAS' para redasiscod
        # (a diferencia de mv_ejec_pat_servicio/_detalle, que sí la tienen via
        # CUBE): si no se filtra una red especifica, se omite el predicado y
        # se suma entre todas las redes (top de centros en general).
        red_filter_sql = "AND redasiscod = ANY(:red) " if "TODAS" not in red_list else ""
        centro_df, _ = run_df(
            f"SELECT cenasides, patologia, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_centro "
            f"WHERE patologia = ANY(:pat) AND anio = ANY(:anio) {red_filter_sql}"
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


        sexo_df, _ = run_df(
            f"SELECT sexo, SUM(pacientes) AS pacientes FROM {SCHEMA}.mv_ejec_pat_sexo_edad "
            f"WHERE {filtro_where} AND sexo <> 'TODOS' "
            f"GROUP BY sexo",
            filtro_params,
        )
        fig_sexo = _build_pie(sexo_df, "sexo", SEXO_ORDER, SEXO_COLORS, label_map=SEXO_LABELS)


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
        d["pacientes"] = d["pacientes"].apply(lambda v: f"{int(v):,}")
        return dash_table.DataTable(
            columns=[
                {"name": "CIE-10", "id": "cod_diagnostico"},
                {"name": "Diagnostico", "id": "diagdes"},
                {"name": "Tipo", "id": "tipodiagnom"},
                {"name": "Pacientes", "id": "pacientes"},
            ],
            data=d.to_dict("records"),
            page_action="none",
            css=[{"selector": ".dash-spreadsheet-container table", "rule": "table-layout: fixed; width: 100%;"}],
            style_table={"overflowX": "auto", "overflowY": "auto", "maxHeight": "320px"},
            style_cell={
                "textAlign": "left", "fontFamily": font_family, "fontSize": "12px", "padding": "7px",
                "overflow": "hidden", "textOverflow": "ellipsis",
            },
            style_cell_conditional=[
                {"if": {"column_id": "cod_diagnostico"}, "width": "14%", "minWidth": "14%", "maxWidth": "14%"},
                {"if": {"column_id": "diagdes"}, "width": "48%", "minWidth": "48%", "maxWidth": "48%", "whiteSpace": "normal", "textOverflow": "clip"},
                {"if": {"column_id": "tipodiagnom"}, "width": "20%", "minWidth": "20%", "maxWidth": "20%"},
                {"if": {"column_id": "pacientes"}, "width": "18%", "minWidth": "18%", "maxWidth": "18%"},
            ],
            style_header={"backgroundColor": brand_soft, "fontWeight": 700, "border": f"1px solid {border}"},
            style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#F8FAFF"}],
        )


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
            return alert_box("Ingrese un documento de paciente.", "warning"), None, None, None

        df, err = run_df(
            f"""SELECT anio, patologia, area, cenasides, servhosdes,
                       cod_diagnostico, diagdes, tipodiagnom, sexo, anio_edad
                FROM {SCHEMA}.mv_ejec_base
                WHERE doc_paciente = :doc
                ORDER BY anio, patologia, cod_diagnostico""",
            {"doc": doc},
        )
        if err:
            return alert_box(err, "warning"), None, None, None
        if df is None or df.empty:
            return alert_box(f"No se encontraron registros para el documento {doc}.", "info"), None, None, None

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
            className="ejec-card",
            style={**card_style, "display": "flex", "gap": "12px", "flexWrap": "wrap", "padding": "14px 16px"},
        )

        matriz = _build_matriz(df)
        detalle = _build_detalle(df)
        store = df.fillna("").astype(str).to_dict("records")
        return info, matriz, detalle, {"doc": doc, "rows": store}

    def _pill(label, value, icon):
        return html.Div(
            [
                html.Div(
                    html.I(className=f"bi {icon}", style={"color": brand, "fontSize": "16px"}),
                    style={
                        "width": "34px", "height": "34px", "borderRadius": "10px",
                        "backgroundColor": brand_soft, "display": "flex",
                        "alignItems": "center", "justifyContent": "center", "flexShrink": "0",
                    },
                ),
                html.Div(
                    [html.Div(value, style={"fontWeight": 700, "color": "#111827"}), html.Small(label, style={"color": muted})],
                    style={"display": "flex", "flexDirection": "column"},
                ),
            ],
            style={"display": "flex", "alignItems": "center", "gap": "10px", "flex": "1 1 150px"},
        )

    def _build_matriz(df):
        pat_df = df[df["patologia"] != "SIN PATOLOGIA"]
        if pat_df.empty:
            return html.Div("El paciente no presenta patologías catalogadas.", style={"color": muted, "padding": "10px"})
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
