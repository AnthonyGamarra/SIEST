from __future__ import annotations

from datetime import datetime
import traceback

import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from dash import (
    Dash,
    Input,
    Output,
    State,
    ctx,
    dash_table,
    dcc,
    html,
    no_update,
)

from backend.establecimientos_repository_v3 import (
    actualizar_establecimiento,
    buscar_establecimientos,
    crear_version_renipress,
    obtener_auditoria_establecimiento,
    obtener_calidad_maestro,
    obtener_distribucion,
    obtener_establecimiento_por_id,
    obtener_historial_establecimiento,
    obtener_redes,
    obtener_resumen_ejecutivo,
    obtener_centros_caracterizacion,
)
from backend.establecimientos_service_v3 import (
    FIELD_DEFINITIONS,
    generar_csv_maestro,
    generar_excel_maestro,
    generar_excel_resumen_ejecutivo,
    normalizar_renipress,
    preparar_cambios_edicion,
    construir_caracterizacion_establecimientos,
    CHAR_LEVEL_ORDER,
)


BRAND = "#005EA8"
BRAND_DARK = "#17365D"
BRAND_SOFT = "#EAF3F9"
TEXT = "#172033"
MUTED = "#687386"
BORDER = "#E5EAF0"
BG = "#F4F7FA"
SUCCESS = "#198754"
WARNING = "#C58A00"
DANGER = "#B42318"


def _ttl_cached(fn, seconds):
    """Memoiza fn(**kwargs) por `seconds`. Solo se usa en el modo publico
    (public_establecimientos.py), para no consultar SQL Server en cada visita."""
    import threading
    import time

    store = {}
    lock = threading.Lock()

    def wrapper(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        now = time.monotonic()
        with lock:
            hit = store.get(key)
            if hit and now - hit[0] < seconds:
                return hit[1]
        value = fn(*args, **kwargs)
        with lock:
            store[key] = (now, value)
        return value

    return wrapper


def _usuario_actual():
    try:
        from flask_login import current_user

        if getattr(current_user, "is_authenticated", False):
            for attr in ("username", "email", "name", "id"):
                value = getattr(current_user, attr, None)
                if value:
                    return str(value)
    except Exception:
        pass

    return "SISTEMA_SIEST"


def _display(value):
    if value is None:
        return "-"

    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M:%S")

    text = str(value).strip()

    if not text or text.lower() in {"none", "nan", "nat"}:
        return "-"

    return text


def _si_no(value):
    if value in (1, True, "1", "SI", "SÍ", "TRUE"):
        return "SI"
    if value in (0, False, "0", "NO", "FALSE"):
        return "NO"
    return _display(value)


def _serialize_row(row):
    if not row:
        return None

    result = {}

    for key, value in row.items():
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif hasattr(value, "as_tuple"):
            value = float(value)

        result[key] = value

    return result


def _figure_bar(records, title, horizontal=True):
    labels = [str(x.get("CATEGORIA") or "SIN INFORMACIÓN") for x in records]
    values = [int(x.get("CANTIDAD") or 0) for x in records]

    if horizontal:
        labels = labels[::-1]
        values = values[::-1]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=values if horizontal else labels,
            y=labels if horizontal else values,
            orientation="h" if horizontal else "v",
            marker_color=BRAND,
            hovertemplate=(
                "%{y}: %{x}<extra></extra>"
                if horizontal
                else "%{x}: %{y}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title={
            "text": title,
            "font": {"size": 16, "color": TEXT},
        },
        margin={"l": 20, "r": 20, "t": 55, "b": 30},
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"family": "Segoe UI, Arial", "color": TEXT},
        showlegend=False,
        height=390,
    )

    fig.update_xaxes(
        showgrid=True if horizontal else False,
        gridcolor="#EEF1F5",
        zeroline=False,
    )
    fig.update_yaxes(
        showgrid=False,
        automargin=True,
    )

    return fig


def _figure_donut(records, title):
    labels = [str(x.get("CATEGORIA") or "SIN INFORMACIÓN") for x in records]
    values = [int(x.get("CANTIDAD") or 0) for x in records]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                textinfo="label+percent",
                hovertemplate="%{label}: %{value}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title={
            "text": title,
            "font": {"size": 16, "color": TEXT},
        },
        margin={"l": 15, "r": 15, "t": 55, "b": 15},
        paper_bgcolor="white",
        font={"family": "Segoe UI, Arial", "color": TEXT},
        height=390,
        showlegend=False,
    )

    return fig


def create_dash_app(
    flask_app,
    url_base_pathname="/establecimientos_v3_embed/",
    public=False,
    public_cache_seconds=300,
):
    """public=True: sin login, solo la pestaña Caracterizacion y con cache de
    lecturas. Lo usa public_establecimientos.py (proceso aparte, red interna)."""
    app = Dash(
        __name__,
        server=flask_app,
        url_base_pathname=url_base_pathname,
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            dbc.icons.BOOTSTRAP,
        ],
        suppress_callback_exceptions=True,
    )

    app.title = "Centro de Gestión de Establecimientos"

    # Lecturas de Caracterizacion: cacheadas solo en modo publico, para que
    # dentro de SIEST los admin vean al instante lo que acaban de editar.
    if public:
        fetch_redes = _ttl_cached(obtener_redes, public_cache_seconds)
        fetch_centros_caracterizacion = _ttl_cached(
            obtener_centros_caracterizacion, public_cache_seconds
        )
    else:
        fetch_redes = obtener_redes
        fetch_centros_caracterizacion = obtener_centros_caracterizacion

    # Este Dash edita el maestro en SQL Server (UPDATE + versionado RENIPRESS),
    # asi que se protege todo lo que cuelga de su prefijo (layout, callbacks
    # _dash-update-component y assets), no solo la ruta Flask que lo envuelve.
    # Cualquier usuario autenticado entra, pero los que no son admin solo
    # pueden ejecutar los callbacks de la pestaña Caracterizacion: ocultar las
    # otras pestañas en el layout no basta, los callbacks se pueden invocar
    # directo con un POST.
    OUTPUTS_CARACTERIZACION = {
        "est-v3-char-red.options",
        "est-v3-characterization-content.children",
        "est-v3-char-status.children",
    }

    def _callback_outputs(payload):
        # Dash envia "id.prop" para un output y "..id1.prop1...id2.prop2.."
        # para varios.
        output = str((payload or {}).get("output") or "")
        return {o for o in output.strip(".").split("...") if o}

    @flask_app.before_request
    def _require_access_establecimientos_v3():
        from flask import request, abort
        from flask_login import current_user

        if not request.path.startswith(url_base_pathname):
            return None
        if not public:
            if not getattr(current_user, "is_authenticated", False):
                abort(401)
            if getattr(current_user, "is_admin", False):
                return None
        if request.path.endswith("/_dash-update-component"):
            outputs = _callback_outputs(request.get_json(silent=True))
            if not outputs or not outputs <= OUTPUTS_CARACTERIZACION:
                abort(403)
        return None

    def kpi_card(title, value_id, subtitle, icon, accent=BRAND):
        return dbc.Col(
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(title, className="est-v3-kpi-title"),
                                    html.Div(
                                        "-",
                                        id=value_id,
                                        className="est-v3-kpi-value",
                                    ),
                                ]
                            ),
                            html.Div(
                                html.I(className=icon),
                                className="est-v3-kpi-icon",
                                style={"color": accent},
                            ),
                        ],
                        className="est-v3-kpi-top",
                    ),
                    html.Div(
                        subtitle,
                        className="est-v3-kpi-subtitle",
                    ),
                ],
                className="est-v3-kpi-card",
            ),
            xl=3,
            md=6,
            xs=12,
        )

    def _char_center_line(center, show_red=False):
        pieces = []

        center_type = center.get("TIPO_CENTRO")
        if center_type and center_type != "SIN TIPO":
            pieces.append(
                html.Span(
                    center_type,
                    className="est-v3-char-type-badge",
                )
            )

        pieces.append(
            html.Span(
                center.get("NOMBRE_ESTABLECIMIENTO") or "-",
                className="est-v3-char-center-name",
            )
        )

        if show_red:
            pieces.append(
                html.Span(
                    center.get("RED_ASISTENCIAL") or "",
                    className="est-v3-char-center-red",
                )
            )

        return html.Li(pieces)


    def _char_popover_groups(groups, max_centers=15):
        children = []

        for title, centers in groups:
            centers = centers or []

            if not centers:
                continue

            visible = centers[:max_centers]
            remaining = max(len(centers) - len(visible), 0)

            children.append(
                html.Div(
                    [
                        html.Div(
                            f"{title} ({len(centers)})",
                            className="est-v3-char-popover-sub",
                        ),
                        html.Ul(
                            [
                                _char_center_line(center)
                                for center in visible
                            ],
                            className="est-v3-char-popover-list",
                        ),
                        (
                            html.Div(
                                f"+ {remaining} centro(s) adicional(es)",
                                className="est-v3-char-popover-more",
                            )
                            if remaining
                            else None
                        ),
                    ],
                    className="est-v3-char-popover-group",
                )
            )

        if not children:
            return html.Div(
                "Sin detalle disponible.",
                className="text-muted small",
            )

        return children


    def _char_breakdown_list(items):
        return html.Div(
            [
                html.Div(
                    [
                        html.Span(label),
                        html.Strong(str(value)),
                    ],
                    className="est-v3-char-breakdown-row",
                )
                for label, value in items
                if int(value or 0) > 0
            ],
            className="est-v3-char-breakdown",
        )


    def char_card(
        card_id,
        label,
        value,
        icon,
        accent,
        subtitle=None,
        note=None,
        popover_title=None,
        popover_body=None,
        width=3,
    ):
        card = html.Div(
            [
                html.Div(
                    html.I(className=icon),
                    className="est-v3-char-icon",
                    style={
                        "--char-accent": accent,
                    },
                ),
                html.Div(
                    [
                        html.Div(
                            label,
                            className="est-v3-char-label",
                        ),
                        html.Div(
                            str(value),
                            className="est-v3-char-value",
                        ),
                        (
                            html.Div(
                                subtitle,
                                className="est-v3-char-subtitle",
                            )
                            if subtitle
                            else None
                        ),
                        (
                            html.Div(
                                note,
                                className="est-v3-char-note",
                            )
                            if note
                            else None
                        ),
                    ],
                    className="est-v3-char-body",
                ),
                (
                    html.Div(
                        html.I(className="bi bi-info-circle"),
                        className="est-v3-char-info",
                    )
                    if popover_body is not None
                    else None
                ),
            ],
            id=card_id,
            tabIndex=0,
            className="est-v3-char-card",
            style={
                "--char-accent": accent,
            },
        )

        children = [card]

        if popover_body is not None:
            children.append(
                dbc.Popover(
                    [
                        dbc.PopoverHeader(
                            popover_title or label,
                        ),
                        dbc.PopoverBody(
                            popover_body,
                        ),
                    ],
                    target=card_id,
                    trigger="hover focus",
                    placement="auto",
                    className="est-v3-char-popover",
                )
            )

        return dbc.Col(
            children,
            xl=width,
            md=6 if width <= 4 else 12,
            xs=12,
        )


    def _char_level_matrix(level_name, level_data, open_level=False):
        categories = level_data.get("categories", {})
        level_count = int(level_data.get("count") or 0)

        category_blocks = []

        for category, centers in categories.items():
            center_items = [
                html.Li(
                    [
                        html.Span(
                            center.get("TIPO_CENTRO") or "SIN TIPO",
                            className="est-v3-char-type-badge",
                        ),
                        html.Span(
                            center.get("NOMBRE_ESTABLECIMIENTO") or "-",
                            className="est-v3-char-center-name",
                        ),
                        html.Span(
                            center.get("RED_ASISTENCIAL") or "",
                            className="est-v3-char-center-red",
                        ),
                    ]
                )
                for center in centers
            ]

            category_blocks.append(
                html.Details(
                    [
                        html.Summary(
                            [
                                html.Span(category),
                                html.Span(
                                    str(len(centers)),
                                    className="est-v3-char-count-pill",
                                ),
                            ],
                            className="est-v3-char-category-summary",
                        ),
                        html.Ul(
                            center_items,
                            className="est-v3-char-center-list",
                        ),
                    ],
                    className="est-v3-char-category-detail",
                )
            )

        return html.Details(
            [
                html.Summary(
                    [
                        html.Span(
                            level_name.title()
                            if level_name != "SIN NIVEL"
                            else "Sin nivel"
                        ),
                        html.Span(
                            str(level_count),
                            className="est-v3-char-level-count",
                        ),
                    ],
                    className="est-v3-char-level-summary",
                ),
                html.Div(
                    category_blocks,
                    className="est-v3-char-category-container",
                ),
            ],
            open=open_level,
            className="est-v3-char-level-detail",
        )


    def render_characterization(summary):
        total = int(summary.get("total") or 0)
        condition_counts = summary.get(
            "condition_counts",
            {},
        )
        levels = summary.get("levels", {})
        condition_levels = summary.get(
            "condition_levels",
            {},
        )
        condition_centers = summary.get(
            "centers_by_condition_level",
            {},
        )

        propio = int(condition_counts.get("PROPIO") or 0)
        extra = int(condition_counts.get("EXTRA") or 0)

        level_counts = {
            level: int(
                levels.get(level, {}).get("count") or 0
            )
            for level in CHAR_LEVEL_ORDER
        }

        total_popover = html.Div(
            [
                html.Div(
                    "Composición del maestro oficial",
                    className="est-v3-char-popover-intro",
                ),
                _char_breakdown_list(
                    [
                        ("Oferta propia", propio),
                        ("Oferta extrainstitucional", extra),
                        ("Nivel I", level_counts["NIVEL I"]),
                        ("Nivel II", level_counts["NIVEL II"]),
                        ("Nivel III", level_counts["NIVEL III"]),
                        ("Sin nivel", level_counts["SIN NIVEL"]),
                    ]
                ),
            ]
        )

        own_popover = _char_breakdown_list(
            [
                (
                    "Nivel I",
                    condition_levels
                    .get("PROPIO", {})
                    .get("NIVEL I", 0),
                ),
                (
                    "Nivel II",
                    condition_levels
                    .get("PROPIO", {})
                    .get("NIVEL II", 0),
                ),
                (
                    "Nivel III",
                    condition_levels
                    .get("PROPIO", {})
                    .get("NIVEL III", 0),
                ),
                (
                    "Sin nivel",
                    condition_levels
                    .get("PROPIO", {})
                    .get("SIN NIVEL", 0),
                ),
            ]
        )

        extra_groups = [
            (
                level.title(),
                condition_centers
                .get("EXTRA", {})
                .get(level, []),
            )
            for level in CHAR_LEVEL_ORDER
        ]

        cards_top = dbc.Row(
            [
                char_card(
                    "est-v3-char-total",
                    "Establecimientos de salud",
                    total,
                    "bi bi-hospital",
                    "#2A78D6",
                    subtitle=(
                        f"{propio} Oferta propia · "
                        f"{extra} Oferta extrainstitucional"
                    ),
                    note=(
                        f"Nivel I {level_counts['NIVEL I']} · "
                        f"Nivel II {level_counts['NIVEL II']} · "
                        f"Nivel III {level_counts['NIVEL III']} · "
                        f"Sin nivel {level_counts['SIN NIVEL']}"
                    ),
                    popover_title="Universo oficial",
                    popover_body=total_popover,
                    width=12,
                )
            ],
            className="g-3 mb-3",
        )

        cards_condition = dbc.Row(
            [
                char_card(
                    "est-v3-char-propio",
                    "Oferta propia",
                    propio,
                    "bi bi-heart-pulse",
                    "#2A78D6",
                    subtitle="Establecimientos propios EsSalud",
                    popover_title="Oferta propia por nivel",
                    popover_body=own_popover,
                    width=6,
                ),
                char_card(
                    "est-v3-char-extra",
                    "Oferta extrainstitucional",
                    extra,
                    "bi bi-box-arrow-up-right",
                    "#EB6834",
                    subtitle=(
                        "IPRESS / APP validadas por "
                        "GCOP / Operaciones"
                    ),
                    popover_title=(
                        "Centros de oferta extrainstitucional"
                    ),
                    popover_body=_char_popover_groups(
                        extra_groups,
                        max_centers=30,
                    ),
                    width=6,
                ),
            ],
            className="g-3 mb-3",
        )

        level_cards = []

        level_meta = {
            "NIVEL I": (
                "bi bi-1-circle",
                "#1BAF7A",
            ),
            "NIVEL II": (
                "bi bi-2-circle",
                "#1BAF7A",
            ),
            "NIVEL III": (
                "bi bi-3-circle",
                "#1BAF7A",
            ),
            "SIN NIVEL": (
                "bi bi-slash-circle",
                "#687386",
            ),
        }

        for index, level in enumerate(CHAR_LEVEL_ORDER):
            level_data = levels.get(
                level,
                {
                    "count": 0,
                    "categories": {},
                    "centers": [],
                },
            )

            icon, accent = level_meta[level]

            if level == "SIN NIVEL":
                popover_body = _char_popover_groups(
                    [
                        (
                            "Sin nivel",
                            level_data.get("centers", []),
                        )
                    ],
                    max_centers=30,
                )
            else:
                category_counts = [
                    (category, len(centers))
                    for category, centers
                    in level_data.get(
                        "categories",
                        {},
                    ).items()
                ]

                popover_body = _char_breakdown_list(
                    category_counts
                )

            level_cards.append(
                char_card(
                    f"est-v3-char-level-{index}",
                    (
                        level.title()
                        if level != "SIN NIVEL"
                        else "Sin nivel"
                    ),
                    int(level_data.get("count") or 0),
                    icon,
                    accent,
                    subtitle="Clasificación EsSalud",
                    popover_title=(
                        "Centros sin nivel"
                        if level == "SIN NIVEL"
                        else f"{level.title()} por categoría MINSA"
                    ),
                    popover_body=popover_body,
                    width=3,
                )
            )

        cards_levels = dbc.Row(
            level_cards,
            className="g-3 mb-3",
        )

        matrix = html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            "Por nivel y categoría",
                            className="est-v3-panel-title",
                        ),
                        html.Div(
                            (
                                "Nivel EsSalud y categoría MINSA. "
                                "Despliegue una categoría para ver "
                                "sus establecimientos."
                            ),
                            className="est-v3-panel-subtitle",
                        ),
                    ]
                ),
                html.Div(
                    [
                        _char_level_matrix(
                            level,
                            levels.get(
                                level,
                                {
                                    "count": 0,
                                    "categories": {},
                                },
                            ),
                            open_level=(level == "NIVEL I"),
                        )
                        for level in CHAR_LEVEL_ORDER
                        if int(
                            levels.get(
                                level,
                                {},
                            ).get("count") or 0
                        ) > 0
                    ],
                    className="est-v3-char-matrix",
                ),
            ],
            className="est-v3-panel h-100",
        )

        types = list(
            summary.get(
                "type_counts",
                {},
            ).items()
        )[:14]

        type_records = [
            {
                "CATEGORIA": label,
                "CANTIDAD": value,
            }
            for label, value in types
        ]

        networks = list(
            summary.get(
                "red_counts",
                {},
            ).items()
        )[:15]

        network_records = [
            {
                "CATEGORIA": label,
                "CANTIDAD": value,
            }
            for label, value in networks
        ]

        side = html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            "Por tipo de establecimiento",
                            className="est-v3-panel-title",
                        ),
                        html.Div(
                            (
                                "Caracterización funcional: hospitales, "
                                "policlínicos, centros médicos, CAP y otros."
                            ),
                            className="est-v3-panel-subtitle",
                        ),
                        dcc.Graph(
                            figure=_figure_bar(
                                type_records,
                                " ",
                                horizontal=True,
                            ),
                            config={
                                "displayModeBar": False,
                            },
                            className="est-v3-char-graph",
                        ),
                    ],
                    className="est-v3-panel",
                ),
                html.Div(
                    [
                        html.Div(
                            "Redes con mayor oferta",
                            className="est-v3-panel-title",
                        ),
                        html.Div(
                            (
                                "Ranking de centros oficiales bajo "
                                "el filtro activo."
                            ),
                            className="est-v3-panel-subtitle",
                        ),
                        dcc.Graph(
                            figure=_figure_bar(
                                network_records,
                                " ",
                                horizontal=True,
                            ),
                            config={
                                "displayModeBar": False,
                            },
                            className="est-v3-char-graph",
                        ),
                    ],
                    className="est-v3-panel",
                ),
            ]
        )

        return html.Div(
            [
                cards_top,
                cards_condition,
                cards_levels,
                dbc.Row(
                    [
                        dbc.Col(
                            matrix,
                            xl=7,
                            xs=12,
                        ),
                        dbc.Col(
                            side,
                            xl=5,
                            xs=12,
                        ),
                    ],
                    className="g-3",
                ),
            ]
        )


    def info_pair(label, value, width=4):
        return dbc.Col(
            html.Div(
                [
                    html.Div(label, className="est-v3-field-label"),
                    html.Div(
                        _display(value),
                        className="est-v3-field-value",
                    ),
                ],
                className="est-v3-field-box",
            ),
            md=width,
            xs=12,
            className="mb-2",
        )

    def render_ficha(row):
        if not row:
            return html.Div(
                [
                    html.I(className="bi bi-building fs-2"),
                    html.Div(
                        "Seleccione un establecimiento",
                        className="fw-bold mt-2",
                    ),
                    html.Div(
                        "La ficha institucional aparecerá en este panel.",
                        className="text-muted small",
                    ),
                ],
                className="est-v3-empty-state",
            )

        official = _si_no(row.get("ES_OFICIAL"))
        current = _si_no(row.get("ES_VERSION_ACTUAL"))
        active = _si_no(row.get("ACTIVO_ESSALUD"))

        badges = [
            dbc.Badge(
                row.get("CONDICION_CENTRO") or "-",
                color="primary"
                if row.get("CONDICION_CENTRO") == "PROPIO"
                else "info",
                pill=True,
                className="me-2",
            ),
            dbc.Badge(
                "OFICIAL" if official == "SI" else "FUERA DEL MAESTRO OFICIAL",
                color="success" if official == "SI" else "warning",
                pill=True,
                className="me-2",
            ),
            dbc.Badge(
                "ACTIVO ESSALUD" if active == "SI" else "INACTIVO ESSALUD",
                color="success" if active == "SI" else "secondary",
                pill=True,
                className="me-2",
            ),
            dbc.Badge(
                "VERSIÓN ACTUAL" if current == "SI" else "VERSIÓN HISTÓRICA",
                color="dark" if current == "SI" else "secondary",
                pill=True,
            ),
        ]

        general_tab = html.Div(
            [
                dbc.Row(
                    [
                        info_pair("Código EESS", row.get("COD_EESS")),
                        info_pair("Código SES", row.get("COD_SES")),
                        info_pair("RENIPRESS", row.get("RENIPRESS")),
                        info_pair("Red asistencial", row.get("RED_ASISTENCIAL"), 6),
                        info_pair("Red abreviada", row.get("RED_ABREVIADA")),
                        info_pair("Nivel EsSalud", row.get("NIVEL_ESSALUD")),
                        info_pair("Tipo de centro", row.get("TIPO_CENTRO")),
                        info_pair("Descripción", row.get("DESCRIPCION_TIPO"), 6),
                        info_pair("Estado EsSalud", row.get("ESTADO_ESSALUD")),
                        info_pair("Activo EsSalud", _si_no(row.get("ACTIVO_ESSALUD"))),
                    ],
                    className="g-2",
                )
            ],
            className="pt-3",
        )

        renipress_tab = html.Div(
            [
                dbc.Row(
                    [
                        info_pair("Estado RENIPRESS", row.get("ESTADO_RENIPRESS")),
                        info_pair("Categoría", row.get("CATEGORIA")),
                        info_pair("Inicio de actividad", row.get("INICIO_ACTIVIDAD")),
                        info_pair(
                            "Tipo doc. categorización",
                            row.get("TIPO_DOC_CATEGORIZACION"),
                        ),
                        info_pair(
                            "Nro. doc. categorización",
                            row.get("NRO_DOC_CATEGORIZACION"),
                        ),
                        info_pair(
                            "Entidad validadora",
                            row.get("ENTIDAD_VALIDADORA"),
                        ),
                        info_pair(
                            "Resolución categorización",
                            row.get("RESOLUCION_CATEGORIZACION_GCPS"),
                            12,
                        ),
                        info_pair(
                            "Fuente RENIPRESS",
                            row.get("FUENTE_RENIPRESS"),
                        ),
                        info_pair(
                            "RENIPRESS anterior",
                            row.get("COD_RENIPRES_ANTERIOR"),
                        ),
                        info_pair(
                            "Fecha cambio RENIPRESS",
                            row.get("FECHA_CAMBIO_RENIPRES"),
                        ),
                    ],
                    className="g-2",
                )
            ],
            className="pt-3",
        )

        location_tab = html.Div(
            [
                dbc.Row(
                    [
                        info_pair("Departamento", row.get("DEPARTAMENTO")),
                        info_pair("Provincia", row.get("PROVINCIA")),
                        info_pair("Distrito", row.get("DISTRITO")),
                        info_pair("UBIGEO", row.get("UBIGEO")),
                        info_pair("Dirección", row.get("DIRECCION"), 12),
                        info_pair("Latitud", row.get("LATITUD")),
                        info_pair("Longitud", row.get("LONGITUD")),
                        info_pair("Camas", row.get("CAMAS")),
                    ],
                    className="g-2",
                )
            ],
            className="pt-3",
        )

        link = row.get("LINK_RESOLUCION")

        docs_children = [
            dbc.Row(
                [
                    info_pair(
                        "Resolución EsSalud",
                        row.get("NUMERO_RESOLUCION_ESSALUD"),
                        6,
                    ),
                    info_pair(
                        "Observación",
                        row.get("OBSERVACION"),
                        6,
                    ),
                    info_pair(
                        "Observación consolidación",
                        row.get("OBSERVACION_CONSOLIDACION"),
                        12,
                    ),
                ],
                className="g-2",
            )
        ]

        if link:
            docs_children.append(
                html.A(
                    [
                        html.I(className="bi bi-box-arrow-up-right me-2"),
                        "Abrir documento de resolución",
                    ],
                    href=link,
                    target="_blank",
                    className="btn btn-outline-primary btn-sm mt-2",
                )
            )

        docs_tab = html.Div(docs_children, className="pt-3")

        history_tab = html.Div(
            [
                dbc.Row(
                    [
                        info_pair(
                            "ID establecimiento",
                            row.get("ID_ESTABLECIMIENTO"),
                        ),
                        info_pair("ID registro", row.get("ID_REGISTRO")),
                        info_pair(
                            "ID registro anterior",
                            row.get("ID_REGISTRO_ANTERIOR"),
                        ),
                    ],
                    className="g-2",
                ),
                dbc.Button(
                    [
                        html.I(className="bi bi-clock-history me-2"),
                        "Abrir historial y auditoría",
                    ],
                    id="est-v3-btn-historial",
                    color="secondary",
                    outline=True,
                    className="mt-2",
                ),
            ],
            className="pt-3",
        )

        is_current = current == "SI"

        return html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    row.get("NOMBRE_ESTABLECIMIENTO") or "-",
                                    className="est-v3-record-title",
                                ),
                                html.Div(
                                    (
                                        f"ID lógico {row.get('ID_ESTABLECIMIENTO')} · "
                                        f"Registro {row.get('ID_REGISTRO')}"
                                    ),
                                    className="est-v3-record-subtitle",
                                ),
                            ]
                        ),
                        html.Div(badges, className="est-v3-badges"),
                    ],
                    className="est-v3-record-header",
                ),

                dbc.Tabs(
                    [
                        dbc.Tab(general_tab, label="General"),
                        dbc.Tab(renipress_tab, label="RENIPRESS"),
                        dbc.Tab(location_tab, label="Ubicación"),
                        dbc.Tab(docs_tab, label="Documentos"),
                        dbc.Tab(history_tab, label="Historial"),
                    ],
                    className="est-v3-detail-tabs",
                ),

                html.Div(
                    [
                        dbc.Button(
                            [
                                html.I(className="bi bi-pencil-square me-2"),
                                "Editar información",
                            ],
                            id="est-v3-btn-editar",
                            color="primary",
                            disabled=not is_current,
                        ),
                        dbc.Button(
                            [
                                html.I(className="bi bi-arrow-repeat me-2"),
                                "Actualizar RENIPRESS",
                            ],
                            id="est-v3-btn-renipress",
                            color="warning",
                            outline=True,
                            disabled=not is_current,
                        ),
                    ],
                    className="est-v3-actions",
                ),
            ],
            className="est-v3-detail-card",
        )

    def build_edit_control(definition):
        field = definition["field"]
        component_id = f"est-v3-edit-{field.lower()}"
        field_type = definition["type"]

        if field_type == "boolean":
            control = dcc.Dropdown(
                id=component_id,
                options=[
                    {"label": "SI", "value": 1},
                    {"label": "NO", "value": 0},
                ],
                clearable=False,
            )
        elif field_type == "select":
            control = dcc.Dropdown(
                id=component_id,
                options=[
                    {"label": x, "value": x}
                    for x in definition.get("options", [])
                ],
                clearable=True,
            )
        elif field_type == "textarea":
            control = dbc.Textarea(
                id=component_id,
                rows=2,
            )
        elif field_type == "integer":
            control = dbc.Input(
                id=component_id,
                type="number",
                step=1,
            )
        elif field_type == "decimal":
            control = dbc.Input(
                id=component_id,
                type="number",
                step="any",
            )
        elif field_type == "date":
            control = dbc.Input(
                id=component_id,
                type="date",
            )
        else:
            control = dbc.Input(
                id=component_id,
                type="text",
            )

        width = definition.get("width", 4)

        return dbc.Col(
            [
                dbc.Label(
                    definition["label"],
                    className="est-v3-edit-label",
                ),
                control,
            ],
            md=width,
            xs=12,
            className="mb-3",
        )

    edit_groups = []

    for group_name in dict.fromkeys(
        definition["group"]
        for definition in FIELD_DEFINITIONS
    ):
        controls = [
            build_edit_control(definition)
            for definition in FIELD_DEFINITIONS
            if definition["group"] == group_name
        ]

        edit_groups.append(
            html.Div(
                [
                    html.Div(
                        group_name,
                        className="est-v3-form-section-title",
                    ),
                    dbc.Row(controls, className="g-2"),
                ],
                className="mb-3",
            )
        )

    executive_layout = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                "Resumen Ejecutivo",
                                className="est-v3-section-title",
                            ),
                            html.Div(
                                (
                                    "Panorama institucional del maestro de "
                                    "establecimientos para toma de decisiones."
                                ),
                                className="est-v3-section-subtitle",
                            ),
                        ]
                    ),
                    html.Div(
                        id="est-v3-corte",
                        className="est-v3-cutoff",
                    ),
                ],
                className="est-v3-section-header",
            ),

            dbc.Row(
                [
                    kpi_card(
                        "Centros oficiales",
                        "est-v3-kpi-oficiales",
                        "Universo institucional publicado",
                        "bi bi-patch-check",
                    ),
                    kpi_card(
                        "Propios oficiales",
                        "est-v3-kpi-propios",
                        "Validados por GCPS",
                        "bi bi-hospital",
                    ),
                    kpi_card(
                        "Extras oficiales",
                        "est-v3-kpi-extras",
                        "Validados por GCOP / Operaciones",
                        "bi bi-plus-square",
                    ),
                    kpi_card(
                        "Fuera del maestro oficial",
                        "est-v3-kpi-historicos",
                        "Conservados para trazabilidad",
                        "bi bi-archive",
                        WARNING,
                    ),
                ],
                className="g-3 mb-3",
            ),

            dbc.Row(
                [
                    dbc.Col(
                        dcc.Graph(
                            id="est-v3-chart-redes",
                            config={"displayModeBar": False},
                        ),
                        xl=7,
                        xs=12,
                    ),
                    dbc.Col(
                        dcc.Graph(
                            id="est-v3-chart-condicion",
                            config={"displayModeBar": False},
                        ),
                        xl=5,
                        xs=12,
                    ),
                ],
                className="g-3",
            ),

            dbc.Row(
                [
                    dbc.Col(
                        dcc.Graph(
                            id="est-v3-chart-nivel",
                            config={"displayModeBar": False},
                        ),
                        xl=6,
                        xs=12,
                    ),
                    dbc.Col(
                        dcc.Graph(
                            id="est-v3-chart-categoria",
                            config={"displayModeBar": False},
                        ),
                        xl=6,
                        xs=12,
                    ),
                ],
                className="g-3",
            ),

            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                "Calidad y completitud del maestro",
                                className="est-v3-panel-title",
                            ),
                            html.Div(
                                (
                                    "Indicadores calculados sobre los centros "
                                    "oficiales vigentes."
                                ),
                                className="est-v3-panel-subtitle",
                            ),
                        ]
                    ),
                    html.Div(
                        id="est-v3-quality-panel",
                        className="mt-3",
                    ),
                ],
                className="est-v3-panel",
            ),
        ]
    )

    characterization_layout = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                "Caracterización de Establecimientos",
                                className="est-v3-section-title",
                            ),
                            html.Div(
                                (
                                    "Composición de la oferta institucional "
                                    "por condición, nivel, categoría MINSA, "
                                    "tipo de centro y red."
                                ),
                                className="est-v3-section-subtitle",
                            ),
                        ]
                    ),
                    dbc.Badge(
                        "Universo oficial vigente",
                        color="primary",
                        pill=True,
                    ),
                ],
                className="est-v3-section-header",
            ),

            html.Div(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Condición EsSalud",
                                        className="est-v3-filter-label",
                                    ),
                                    dcc.Dropdown(
                                        id="est-v3-char-condition",
                                        options=[
                                            {
                                                "label": "Todos",
                                                "value": "",
                                            },
                                            {
                                                "label": "Oferta propia",
                                                "value": "PROPIO",
                                            },
                                            {
                                                "label": (
                                                    "Oferta "
                                                    "extrainstitucional"
                                                ),
                                                "value": "EXTRA",
                                            },
                                        ],
                                        value="",
                                        clearable=False,
                                    ),
                                ],
                                xl=3,
                                md=6,
                                xs=12,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Red asistencial / prestacional",
                                        className="est-v3-filter-label",
                                    ),
                                    dcc.Dropdown(
                                        id="est-v3-char-red",
                                        options=[
                                            {
                                                "label": "Todas",
                                                "value": "",
                                            }
                                        ],
                                        value="",
                                        clearable=False,
                                    ),
                                ],
                                xl=5,
                                md=6,
                                xs=12,
                            ),
                            dbc.Col(
                                html.Div(
                                    [
                                        html.Div(
                                            "Fuente operativa",
                                            className=(
                                                "est-v3-char-source-label"
                                            ),
                                        ),
                                        html.Div(
                                            (
                                                "Maestro oficial SIEST · "
                                                "ES_VERSION_ACTUAL = 1 · "
                                                "ES_OFICIAL = 1"
                                            ),
                                            className=(
                                                "est-v3-char-source-value"
                                            ),
                                        ),
                                    ],
                                    className="est-v3-char-source",
                                ),
                                xl=4,
                                xs=12,
                            ),
                        ],
                        className="g-2 align-items-end",
                    ),
                    html.Div(
                        id="est-v3-char-status",
                        className="est-v3-char-filter-status",
                    ),
                ],
                className="est-v3-filter-panel",
            ),

            dcc.Loading(
                html.Div(
                    id="est-v3-characterization-content",
                ),
                type="circle",
                color=BRAND,
            ),
        ]
    )

    management_layout = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        "Gestión de Centros",
                        className="est-v3-section-title",
                    ),
                    html.Div(
                        (
                            "Consulta, edición controlada, versionado RENIPRESS "
                            "y trazabilidad."
                        ),
                        className="est-v3-section-subtitle",
                    ),
                ],
                className="mb-3",
            ),

            html.Div(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Buscar establecimiento",
                                        className="est-v3-filter-label",
                                    ),
                                    dbc.Input(
                                        id="est-v3-search",
                                        placeholder=(
                                            "Código EESS, SES, RENIPRESS, "
                                            "nombre o red..."
                                        ),
                                        debounce=True,
                                    ),
                                ],
                                xl=8,
                                xs=12,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Condición EsSalud",
                                        className="est-v3-filter-label",
                                    ),
                                    dcc.Dropdown(
                                        id="est-v3-condition",
                                        options=[
                                            {"label": "Todos", "value": ""},
                                            {"label": "Propio", "value": "PROPIO"},
                                            {"label": "Extra", "value": "EXTRA"},
                                        ],
                                        value="",
                                        clearable=False,
                                    ),
                                ],
                                xl=2,
                                md=6,
                                xs=12,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Vigencia del maestro",
                                        className="est-v3-filter-label",
                                    ),
                                    dcc.Dropdown(
                                        id="est-v3-vigencia",
                                        options=[
                                            {
                                                "label": "Activos",
                                                "value": "ACTIVO",
                                            },
                                            {
                                                "label": "Histórico completo",
                                                "value": "HISTORICO",
                                            },
                                        ],
                                        value="ACTIVO",
                                        clearable=False,
                                    ),
                                ],
                                xl=2,
                                md=6,
                                xs=12,
                            ),
                        ],
                        className="g-2",
                    ),

                    html.Div(
                        [
                            html.Div(
                                id="est-v3-search-message",
                                className="small text-muted",
                            ),
                            html.Div(
                                [
                                    dbc.Button(
                                        "Limpiar",
                                        id="est-v3-clear",
                                        color="secondary",
                                        outline=True,
                                        size="sm",
                                    ),
                                ]
                            ),
                        ],
                        className="est-v3-filter-footer",
                    ),
                ],
                className="est-v3-filter-panel",
            ),

            html.Div(
                [
                    dash_table.DataTable(
                        id="est-v3-table",
                        columns=[
                            {"name": "EESS", "id": "COD_EESS"},
                            {"name": "SES", "id": "COD_SES"},
                            {"name": "RENIPRESS", "id": "RENIPRESS"},
                            {
                                "name": "ESTABLECIMIENTO",
                                "id": "NOMBRE_ESTABLECIMIENTO",
                            },
                            {"name": "RED", "id": "RED_ASISTENCIAL"},
                            {"name": "NIVEL", "id": "NIVEL_ESSALUD"},
                            {
                                "name": "CONDICIÓN",
                                "id": "CONDICION_CENTRO",
                            },
                            {
                                "name": "VALIDADOR",
                                "id": "ENTIDAD_VALIDADORA",
                            },
                            {
                                "name": "VERSIÓN",
                                "id": "ES_VERSION_ACTUAL",
                            },
                        ],
                        data=[],
                        row_selectable="single",
                        selected_row_ids=[],
                        page_size=15,
                        sort_action="native",
                        style_table={"overflowX": "auto"},
                        style_header={
                            "backgroundColor": BRAND_DARK,
                            "color": "white",
                            "fontWeight": 700,
                            "border": "none",
                        },
                        style_cell={
                            "fontFamily": "Segoe UI, Arial",
                            "fontSize": "12px",
                            "padding": "10px",
                            "textAlign": "left",
                            "whiteSpace": "normal",
                            "height": "auto",
                            "border": f"1px solid {BORDER}",
                        },
                        style_data_conditional=[
                            {
                                "if": {
                                    "filter_query": "{ES_VERSION_ACTUAL} = 0"
                                },
                                "backgroundColor": "#F3F4F6",
                                "color": "#667085",
                            },
                            {
                                "if": {
                                    "filter_query": "{ES_OFICIAL} = 0"
                                },
                                "backgroundColor": "#FFF8E7",
                            },
                        ],
                    ),
                ],
                className="est-v3-table-card",
            ),

            html.Div(
                id="est-v3-record-detail",
                className="mt-3",
            ),
        ]
    )

    reports_layout = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        "Datos y Reportes",
                        className="est-v3-section-title",
                    ),
                    html.Div(
                        (
                            "Exportación operativa del maestro y generación "
                            "de resumen ejecutivo."
                        ),
                        className="est-v3-section-subtitle",
                    ),
                ],
                className="mb-3",
            ),

            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.I(
                                            className="bi bi-database-down me-2"
                                        ),
                                        "Exportar maestro",
                                    ],
                                    className="est-v3-panel-title",
                                ),
                                html.Div(
                                    (
                                        "Seleccione el universo y descargue "
                                        "la información detallada."
                                    ),
                                    className="est-v3-panel-subtitle",
                                ),

                                dbc.Label(
                                    "Universo",
                                    className="est-v3-filter-label mt-3",
                                ),
                                dcc.Dropdown(
                                    id="est-v3-export-universe",
                                    options=[
                                        {
                                            "label": "Centros oficiales vigentes",
                                            "value": "OFICIAL",
                                        },
                                        {
                                            "label": "Maestro actual completo",
                                            "value": "MAESTRO_ACTUAL",
                                        },
                                        {
                                            "label": "Histórico completo de versiones",
                                            "value": "HISTORICO",
                                        },
                                    ],
                                    value="OFICIAL",
                                    clearable=False,
                                ),

                                dbc.Label(
                                    "Condición EsSalud",
                                    className="est-v3-filter-label mt-3",
                                ),
                                dcc.Dropdown(
                                    id="est-v3-export-condition",
                                    options=[
                                        {"label": "Todos", "value": ""},
                                        {"label": "Propio", "value": "PROPIO"},
                                        {"label": "Extra", "value": "EXTRA"},
                                    ],
                                    value="",
                                    clearable=False,
                                ),

                                dbc.Label(
                                    "Red asistencial",
                                    className="est-v3-filter-label mt-3",
                                ),
                                dcc.Dropdown(
                                    id="est-v3-export-red",
                                    options=[],
                                    value="",
                                    clearable=False,
                                ),

                                html.Div(
                                    id="est-v3-export-preview",
                                    className="est-v3-export-preview",
                                ),

                                html.Div(
                                    [
                                        dbc.Button(
                                            [
                                                html.I(
                                                    className=(
                                                        "bi bi-file-earmark-excel me-2"
                                                    )
                                                ),
                                                "Descargar Excel",
                                            ],
                                            id="est-v3-download-xlsx",
                                            color="success",
                                        ),
                                        dbc.Button(
                                            [
                                                html.I(
                                                    className=(
                                                        "bi bi-filetype-csv me-2"
                                                    )
                                                ),
                                                "Descargar CSV",
                                            ],
                                            id="est-v3-download-csv",
                                            color="secondary",
                                            outline=True,
                                        ),
                                    ],
                                    className="est-v3-report-actions",
                                ),
                            ],
                            className="est-v3-panel h-100",
                        ),
                        xl=7,
                        xs=12,
                    ),

                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.I(
                                            className="bi bi-bar-chart-line me-2"
                                        ),
                                        "Reporte ejecutivo",
                                    ],
                                    className="est-v3-panel-title",
                                ),
                                html.Div(
                                    (
                                        "Libro Excel para alta dirección con "
                                        "KPIs, distribución y calidad de datos."
                                    ),
                                    className="est-v3-panel-subtitle",
                                ),

                                html.Div(
                                    [
                                        html.I(
                                            className=(
                                                "bi bi-file-earmark-spreadsheet "
                                                "est-v3-report-icon"
                                            )
                                        ),
                                        html.Div(
                                            (
                                                "Incluye Resumen, Red, Nivel, "
                                                "Categoría, Departamento y "
                                                "Calidad de Datos."
                                            ),
                                            className="text-muted small mt-3",
                                        ),
                                    ],
                                    className="est-v3-report-hero",
                                ),

                                dbc.Button(
                                    [
                                        html.I(
                                            className="bi bi-download me-2"
                                        ),
                                        "Descargar resumen ejecutivo",
                                    ],
                                    id="est-v3-download-executive",
                                    color="primary",
                                    className="w-100",
                                ),
                            ],
                            className="est-v3-panel h-100",
                        ),
                        xl=5,
                        xs=12,
                    ),
                ],
                className="g-3",
            ),
        ]
    )

    # Admin ve las 4 pestañas; el resto de roles solo Caracterizacion (lectura).
    def _main_tabs(es_admin):
        characterization_tab = dbc.Tab(
            characterization_layout,
            label="Caracterización",
            tab_id="characterization",
        )
        if not es_admin:
            return dbc.Tabs(
                [characterization_tab],
                id="est-v3-main-tabs",
                active_tab="characterization",
                className="est-v3-main-tabs",
            )
        return dbc.Tabs(
            [
                dbc.Tab(
                    executive_layout,
                    label="Resumen Ejecutivo",
                    tab_id="executive",
                ),
                characterization_tab,
                dbc.Tab(
                    management_layout,
                    label="Gestión de Centros",
                    tab_id="management",
                ),
                dbc.Tab(
                    reports_layout,
                    label="Datos y Reportes",
                    tab_id="reports",
                ),
            ],
            id="est-v3-main-tabs",
            active_tab="executive",
            className="est-v3-main-tabs",
        )

    def _build_layout(es_admin):
        return dbc.Container(
            fluid=True,
            children=[
                dcc.Interval(
                    id="est-v3-init",
                    interval=200,
                    n_intervals=0,
                    max_intervals=1,
                ),
                dcc.Store(
                    id="est-v3-refresh",
                    data=0,
                ),
                dcc.Store(id="est-v3-selected-record"),
                dcc.Store(id="est-v3-edit-changes"),
                dcc.Download(id="est-v3-download"),

                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            html.I(className="bi bi-buildings"),
                                            className="est-v3-brand-icon",
                                        ),
                                        html.Div(
                                            [
                                                html.Div(
                                                    "Centro de Gestión de Establecimientos",
                                                    className="est-v3-app-title",
                                                ),
                                                html.Div(
                                                    (
                                                        "Maestro institucional · "
                                                        "Gobierno de datos · "
                                                        "Gestión y trazabilidad"
                                                    ),
                                                    className="est-v3-app-subtitle",
                                                ),
                                            ]
                                        ),
                                    ],
                                    className="est-v3-brand",
                                ),
                                dbc.Badge(
                                    "SIEST",
                                    color="primary",
                                    pill=True,
                                    className="est-v3-siest-badge",
                                ),
                            ],
                            className="est-v3-app-header",
                        ),

                        _main_tabs(es_admin),

                        html.Div(
                            id="est-v3-action-message",
                            className="est-v3-floating-message",
                        ),
                    ],
                    className="est-v3-shell",
                ),

                # ---------------------------------------------------------------
                # MODAL HISTORIAL
                # ---------------------------------------------------------------
                dbc.Modal(
                    [
                        dbc.ModalHeader(
                            dbc.ModalTitle(
                                id="est-v3-history-title"
                            )
                        ),
                        dbc.ModalBody(
                            dbc.Tabs(
                                [
                                    dbc.Tab(
                                        dash_table.DataTable(
                                            id="est-v3-history-table",
                                            columns=[
                                                {"name": "ID", "id": "ID_REGISTRO"},
                                                {
                                                    "name": "RENIPRESS",
                                                    "id": "RENIPRESS",
                                                },
                                                {
                                                    "name": "RENIPRESS anterior",
                                                    "id": "COD_RENIPRES_ANTERIOR",
                                                },
                                                {
                                                    "name": "ID anterior",
                                                    "id": "ID_REGISTRO_ANTERIOR",
                                                },
                                                {
                                                    "name": "Fecha cambio",
                                                    "id": "FECHA_CAMBIO_RENIPRES",
                                                },
                                                {
                                                    "name": "Actual",
                                                    "id": "ES_VERSION_ACTUAL",
                                                },
                                                {
                                                    "name": "Oficial",
                                                    "id": "ES_OFICIAL",
                                                },
                                            ],
                                            data=[],
                                            page_size=10,
                                            sort_action="native",
                                            style_table={"overflowX": "auto"},
                                            style_cell={
                                                "fontSize": "12px",
                                                "padding": "8px",
                                                "textAlign": "left",
                                            },
                                            style_header={
                                                "backgroundColor": BRAND_DARK,
                                                "color": "white",
                                                "fontWeight": 700,
                                            },
                                        ),
                                        label="Versiones",
                                    ),
                                    dbc.Tab(
                                        dash_table.DataTable(
                                            id="est-v3-audit-table",
                                            columns=[
                                                {
                                                    "name": "Fecha",
                                                    "id": "FECHA_EVENTO",
                                                },
                                                {
                                                    "name": "Usuario",
                                                    "id": "USUARIO",
                                                },
                                                {
                                                    "name": "Operación",
                                                    "id": "OPERACION",
                                                },
                                                {
                                                    "name": "Campo",
                                                    "id": "CAMPO",
                                                },
                                                {
                                                    "name": "Anterior",
                                                    "id": "VALOR_ANTERIOR",
                                                },
                                                {
                                                    "name": "Nuevo",
                                                    "id": "VALOR_NUEVO",
                                                },
                                                {
                                                    "name": "Observación",
                                                    "id": "OBSERVACION",
                                                },
                                            ],
                                            data=[],
                                            page_size=10,
                                            sort_action="native",
                                            style_table={"overflowX": "auto"},
                                            style_cell={
                                                "fontSize": "12px",
                                                "padding": "8px",
                                                "textAlign": "left",
                                                "whiteSpace": "normal",
                                                "height": "auto",
                                            },
                                            style_header={
                                                "backgroundColor": BRAND_DARK,
                                                "color": "white",
                                                "fontWeight": 700,
                                            },
                                        ),
                                        label="Auditoría",
                                    ),
                                ]
                            )
                        ),
                        dbc.ModalFooter(
                            dbc.Button(
                                "Cerrar",
                                id="est-v3-history-close",
                                color="secondary",
                            )
                        ),
                    ],
                    id="est-v3-history-modal",
                    is_open=False,
                    size="xl",
                    centered=True,
                ),

                # ---------------------------------------------------------------
                # MODAL EDICIÓN
                # ---------------------------------------------------------------
                dbc.Modal(
                    [
                        dbc.ModalHeader(
                            dbc.ModalTitle(
                                [
                                    html.I(className="bi bi-pencil-square me-2"),
                                    "Editar establecimiento",
                                ]
                            )
                        ),
                        dbc.ModalBody(
                            [
                                dbc.Alert(
                                    (
                                        "RENIPRESS y campos técnicos de historia "
                                        "no se modifican desde esta pantalla."
                                    ),
                                    color="info",
                                ),
                                html.Div(edit_groups),
                                dbc.Label(
                                    "Motivo / observación del cambio",
                                    className="est-v3-edit-label",
                                ),
                                dbc.Textarea(
                                    id="est-v3-edit-observation",
                                    rows=2,
                                    placeholder=(
                                        "Describa brevemente el motivo del cambio..."
                                    ),
                                ),
                                html.Hr(),
                                dbc.Button(
                                    [
                                        html.I(className="bi bi-eye me-2"),
                                        "Revisar cambios",
                                    ],
                                    id="est-v3-edit-review",
                                    color="primary",
                                    outline=True,
                                ),
                                html.Div(
                                    id="est-v3-edit-review-message",
                                    className="mt-3",
                                ),
                                dash_table.DataTable(
                                    id="est-v3-edit-diff-table",
                                    columns=[
                                        {"name": "Campo", "id": "CAMPO"},
                                        {
                                            "name": "Valor anterior",
                                            "id": "VALOR_ANTERIOR",
                                        },
                                        {
                                            "name": "Nuevo valor",
                                            "id": "VALOR_NUEVO",
                                        },
                                    ],
                                    data=[],
                                    style_table={
                                        "overflowX": "auto",
                                        "marginTop": "12px",
                                    },
                                    style_cell={
                                        "fontSize": "12px",
                                        "padding": "8px",
                                        "textAlign": "left",
                                        "whiteSpace": "normal",
                                        "height": "auto",
                                    },
                                    style_header={
                                        "backgroundColor": BRAND_DARK,
                                        "color": "white",
                                        "fontWeight": 700,
                                    },
                                ),
                            ]
                        ),
                        dbc.ModalFooter(
                            [
                                dbc.Button(
                                    "Cancelar",
                                    id="est-v3-edit-cancel",
                                    color="secondary",
                                    outline=True,
                                ),
                                dbc.Button(
                                    [
                                        html.I(className="bi bi-check2-circle me-2"),
                                        "Confirmar cambios",
                                    ],
                                    id="est-v3-edit-confirm",
                                    color="success",
                                    disabled=True,
                                ),
                            ]
                        ),
                    ],
                    id="est-v3-edit-modal",
                    is_open=False,
                    size="xl",
                    centered=True,
                    scrollable=True,
                ),

                # ---------------------------------------------------------------
                # MODAL RENIPRESS
                # ---------------------------------------------------------------
                dbc.Modal(
                    [
                        dbc.ModalHeader(
                            dbc.ModalTitle(
                                [
                                    html.I(className="bi bi-arrow-repeat me-2"),
                                    "Actualizar RENIPRESS",
                                ]
                            )
                        ),
                        dbc.ModalBody(
                            [
                                dbc.Alert(
                                    (
                                        "Este proceso NO sobrescribe la versión actual. "
                                        "Cerrará la versión vigente y creará una nueva, "
                                        "preservando la cadena histórica."
                                    ),
                                    color="warning",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                dbc.Label("RENIPRESS vigente"),
                                                dbc.Input(
                                                    id="est-v3-ren-current",
                                                    disabled=True,
                                                ),
                                            ],
                                            md=6,
                                        ),
                                        dbc.Col(
                                            [
                                                dbc.Label("Nuevo RENIPRESS"),
                                                dbc.Input(
                                                    id="est-v3-ren-new",
                                                    placeholder="Ej. 00012345",
                                                ),
                                            ],
                                            md=6,
                                        ),
                                    ],
                                    className="g-2",
                                ),
                                dbc.Label(
                                    "Motivo del cambio",
                                    className="mt-3",
                                ),
                                dbc.Textarea(
                                    id="est-v3-ren-observation",
                                    rows=3,
                                    placeholder=(
                                        "Indique la fuente o motivo del cambio..."
                                    ),
                                ),
                            ]
                        ),
                        dbc.ModalFooter(
                            [
                                dbc.Button(
                                    "Cancelar",
                                    id="est-v3-ren-cancel",
                                    color="secondary",
                                    outline=True,
                                ),
                                dbc.Button(
                                    "Confirmar nueva versión",
                                    id="est-v3-ren-confirm",
                                    color="warning",
                                ),
                            ]
                        ),
                    ],
                    id="est-v3-ren-modal",
                    is_open=False,
                    centered=True,
                ),
            ],
            style={
                "backgroundColor": BG,
                "minHeight": "100vh",
                "padding": "0",
            },
        )

    def serve_layout():
        from flask import has_request_context
        from flask_login import current_user

        # Sin request (validacion interna de Dash) se usa el layout completo
        # para que todos los IDs de los callbacks existan.
        if public:
            return _build_layout(False)
        if not has_request_context():
            return _build_layout(True)
        return _build_layout(bool(getattr(current_user, "is_admin", False)))

    app.layout = serve_layout

    # =======================================================================
    # RESUMEN EJECUTIVO
    # =======================================================================

    @app.callback(
        Output("est-v3-kpi-oficiales", "children"),
        Output("est-v3-kpi-propios", "children"),
        Output("est-v3-kpi-extras", "children"),
        Output("est-v3-kpi-historicos", "children"),
        Output("est-v3-chart-redes", "figure"),
        Output("est-v3-chart-condicion", "figure"),
        Output("est-v3-chart-nivel", "figure"),
        Output("est-v3-chart-categoria", "figure"),
        Output("est-v3-quality-panel", "children"),
        Output("est-v3-corte", "children"),
        Input("est-v3-init", "n_intervals"),
        Input("est-v3-refresh", "data"),
    )
    def cargar_dashboard(_init, _refresh):
        try:
            resumen = obtener_resumen_ejecutivo()
            calidad = obtener_calidad_maestro()

            redes = obtener_distribucion("RED_ASISTENCIAL", top=12)
            condicion = obtener_distribucion("CONDICION_CENTRO", top=10)
            niveles = obtener_distribucion("NIVEL_ESSALUD", top=20)
            categorias = obtener_distribucion("CATEGORIA", top=12)

            total = int(calidad.get("TOTAL") or 0)

            quality_defs = [
                ("RENIPRESS", "CON_RENIPRESS"),
                ("UBIGEO", "CON_UBIGEO"),
                ("Georreferenciación", "CON_COORDENADAS"),
                ("Categoría", "CON_CATEGORIA"),
                ("Resolución", "CON_RESOLUCION"),
                ("Dirección", "CON_DIRECCION"),
                ("Red asistencial", "CON_RED"),
                ("Nivel EsSalud", "CON_NIVEL"),
            ]

            quality_children = []

            for label, key in quality_defs:
                count = int(calidad.get(key) or 0)
                pct = round(count * 100 / total, 1) if total else 0
                pending = max(total - count, 0)

                quality_children.append(
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(label, className="fw-semibold"),
                                    html.Span(
                                        f"{pct:.1f}% · {pending} pendiente(s)",
                                        className="text-muted small",
                                    ),
                                ],
                                className=(
                                    "d-flex justify-content-between "
                                    "align-items-center mb-1"
                                ),
                            ),
                            dbc.Progress(
                                value=pct,
                                color=(
                                    "success"
                                    if pct >= 95
                                    else (
                                        "warning"
                                        if pct >= 80
                                        else "danger"
                                    )
                                ),
                                style={"height": "8px"},
                                className="mb-3",
                            ),
                        ]
                    )
                )

            return (
                resumen.get("TOTAL_OFICIALES", 0) or 0,
                resumen.get("TOTAL_PROPIOS", 0) or 0,
                resumen.get("TOTAL_EXTRAS", 0) or 0,
                resumen.get("TOTAL_FUERA_OFICIAL", 0) or 0,
                _figure_bar(
                    redes,
                    "Centros oficiales por red asistencial",
                    horizontal=True,
                ),
                _figure_donut(
                    condicion,
                    "Composición del maestro oficial",
                ),
                _figure_bar(
                    niveles,
                    "Distribución por nivel EsSalud",
                    horizontal=False,
                ),
                _figure_bar(
                    categorias,
                    "Principales categorías RENIPRESS",
                    horizontal=True,
                ),
                quality_children,
                "Corte: " + datetime.now().strftime("%d/%m/%Y %H:%M"),
            )

        except Exception as exc:
            print(
                "[ESTABLECIMIENTOS V3] ERROR RESUMEN EJECUTIVO:",
                repr(exc),
                flush=True,
            )
            traceback.print_exc()

            empty = go.Figure()
            empty.update_layout(
                paper_bgcolor="white",
                plot_bgcolor="white",
                annotations=[
                    {
                        "text": "No fue posible consultar SQL Server",
                        "showarrow": False,
                        "font": {"color": DANGER, "size": 14},
                    }
                ],
                xaxis={"visible": False},
                yaxis={"visible": False},
                height=390,
            )

            error_panel = dbc.Alert(
                [
                    html.Div(
                        "No fue posible cargar los indicadores.",
                        className="fw-bold",
                    ),
                    html.Div(str(exc), className="small mt-1"),
                    html.Hr(),
                    html.Div(
                        (
                            "Ejecute diagnostico_establecimientos_v3.py "
                            "desde la raíz del proyecto para identificar "
                            "la causa exacta."
                        ),
                        className="small",
                    ),
                ],
                color="danger",
            )

            return (
                "-",
                "-",
                "-",
                "-",
                empty,
                empty,
                empty,
                empty,
                error_panel,
                "ERROR DE CONEXIÓN / CONSULTA",
            )
    # =======================================================================
    # CARACTERIZACIÓN DE ESTABLECIMIENTOS
    # =======================================================================

    @app.callback(
        Output("est-v3-char-red", "options"),
        Input("est-v3-init", "n_intervals"),
    )
    def cargar_redes_caracterizacion(_):
        try:
            redes = fetch_redes()

            return (
                [
                    {
                        "label": "Todas",
                        "value": "",
                    }
                ]
                + [
                    {
                        "label": red,
                        "value": red,
                    }
                    for red in redes
                ]
            )

        except Exception as exc:
            print(
                "[ESTABLECIMIENTOS V3] ERROR REDES CARACTERIZACION:",
                repr(exc),
                flush=True,
            )
            traceback.print_exc()

            return [
                {
                    "label": "Todas",
                    "value": "",
                }
            ]


    @app.callback(
        Output(
            "est-v3-characterization-content",
            "children",
        ),
        Output(
            "est-v3-char-status",
            "children",
        ),
        Input("est-v3-init", "n_intervals"),
        Input("est-v3-refresh", "data"),
        Input("est-v3-char-condition", "value"),
        Input("est-v3-char-red", "value"),
    )
    def cargar_caracterizacion(
        _init,
        _refresh,
        condition,
        red,
    ):
        try:
            records = fetch_centros_caracterizacion(
                condicion_centro=condition or None,
                red_asistencial=red or None,
            )

            summary = construir_caracterizacion_establecimientos(
                records
            )

            status_parts = [
                f"{summary.get('total', 0)} centro(s) oficial(es)",
            ]

            if condition:
                status_parts.append(
                    (
                        "Oferta propia"
                        if condition == "PROPIO"
                        else "Oferta extrainstitucional"
                    )
                )

            if red:
                status_parts.append(str(red))

            return (
                render_characterization(summary),
                " · ".join(status_parts),
            )

        except Exception as exc:
            print(
                "[ESTABLECIMIENTOS V3] ERROR CARACTERIZACION:",
                repr(exc),
                flush=True,
            )
            traceback.print_exc()

            return (
                dbc.Alert(
                    [
                        html.Div(
                            "No fue posible cargar la caracterización.",
                            className="fw-bold",
                        ),
                        # En modo publico no se expone el detalle (servidor,
                        # tabla, driver) del error de SQL Server.
                        html.Div(
                            "Intente nuevamente en unos minutos." if public else str(exc),
                            className="small mt-1",
                        ),
                    ],
                    color="danger",
                ),
                "Error de consulta",
            )


    # =======================================================================
    # BÚSQUEDA / GESTIÓN
    # =======================================================================

    @app.callback(
        Output("est-v3-search", "value"),
        Output("est-v3-condition", "value"),
        Output("est-v3-vigencia", "value"),
        Input("est-v3-clear", "n_clicks"),
        prevent_initial_call=True,
    )
    def limpiar_filtros(n_clicks):
        if not n_clicks:
            return no_update, no_update, no_update
        return "", "", "ACTIVO"

    @app.callback(
        Output("est-v3-table", "data"),
        Output("est-v3-table", "selected_row_ids"),
        Output("est-v3-search-message", "children"),
        Input("est-v3-init", "n_intervals"),
        Input("est-v3-refresh", "data"),
        Input("est-v3-search", "value"),
        Input("est-v3-condition", "value"),
        Input("est-v3-vigencia", "value"),
    )
    def consultar_centros(
        _init,
        _refresh,
        text,
        condition,
        vigencia,
    ):
        try:
            rows = buscar_establecimientos(
                texto=text,
                condicion_centro=condition or None,
                vigencia=vigencia or "ACTIVO",
                limite=5000,
            )

            data = []

            for row in rows:
                item = _serialize_row(row)
                item["id"] = str(item["ID_REGISTRO"])
                item["ES_VERSION_ACTUAL"] = (
                    1
                    if row.get("ES_VERSION_ACTUAL") in (1, True)
                    else 0
                )
                item["ES_OFICIAL"] = (
                    1
                    if row.get("ES_OFICIAL") in (1, True)
                    else 0
                )
                data.append(item)

            universo = (
                "centros oficiales"
                if (vigencia or "ACTIVO") == "ACTIVO"
                else "histórico completo"
            )

            return (
                data,
                [],
                f"{len(data)} registro(s) · {universo}",
            )

        except Exception as exc:
            print(
                "[ESTABLECIMIENTOS V3] ERROR CONSULTA CENTROS:",
                repr(exc),
                flush=True,
            )
            traceback.print_exc()

            return (
                [],
                [],
                f"Error al consultar SQL Server: {exc}",
            )

    @app.callback(
        Output("est-v3-record-detail", "children"),
        Output("est-v3-selected-record", "data"),
        Input("est-v3-table", "selected_row_ids"),
        prevent_initial_call=False,
    )
    def seleccionar_registro(selected_row_ids):
        if not selected_row_ids:
            return render_ficha(None), None

        try:
            row = obtener_establecimiento_por_id(
                int(selected_row_ids[0])
            )

            return render_ficha(row), _serialize_row(row)

        except Exception as exc:
            return (
                dbc.Alert(
                    f"No fue posible cargar la ficha: {exc}",
                    color="danger",
                ),
                None,
            )

    # =======================================================================
    # HISTORIAL
    # =======================================================================

    @app.callback(
        Output("est-v3-history-modal", "is_open"),
        Output("est-v3-history-title", "children"),
        Output("est-v3-history-table", "data"),
        Output("est-v3-audit-table", "data"),
        Input("est-v3-btn-historial", "n_clicks"),
        Input("est-v3-history-close", "n_clicks"),
        State("est-v3-selected-record", "data"),
        prevent_initial_call=True,
    )
    def gestionar_historial(
        n_open,
        n_close,
        selected,
    ):
        trigger = ctx.triggered_id

        if trigger == "est-v3-history-close":
            return False, no_update, no_update, no_update

        # Cuando el botón se inserta dinámicamente al seleccionar una fila,
        # Dash puede disparar este callback con n_clicks=None/0.
        # Eso NO debe abrir el modal.
        if (
            trigger != "est-v3-btn-historial"
            or not n_open
            or not selected
        ):
            return no_update, no_update, no_update, no_update

        fresh = obtener_establecimiento_por_id(
            int(selected["ID_REGISTRO"])
        )

        if not fresh:
            return (
                False,
                no_update,
                no_update,
                no_update,
            )

        versions = obtener_historial_establecimiento(
            fresh["ID_ESTABLECIMIENTO"]
        )

        audit = obtener_auditoria_establecimiento(
            fresh["ID_ESTABLECIMIENTO"]
        )

        versions_data = []

        for row in versions:
            item = _serialize_row(row)
            item["ES_VERSION_ACTUAL"] = _si_no(
                row.get("ES_VERSION_ACTUAL")
            )
            item["ES_OFICIAL"] = _si_no(row.get("ES_OFICIAL"))
            versions_data.append(item)

        audit_data = [
            _serialize_row(row)
            for row in audit
        ]

        title = (
            "Historial y auditoría · "
            + str(fresh.get("NOMBRE_ESTABLECIMIENTO") or "")
        )

        return True, title, versions_data, audit_data

    # =======================================================================
    # EDICIÓN
    # =======================================================================

    edit_outputs = [
        Output(
            f"est-v3-edit-{definition['field'].lower()}",
            "value",
        )
        for definition in FIELD_DEFINITIONS
    ]

    @app.callback(
        edit_outputs
        + [
            Output("est-v3-edit-observation", "value"),
            Output("est-v3-edit-changes", "data"),
            Output("est-v3-edit-diff-table", "data"),
            Output("est-v3-edit-confirm", "disabled"),
            Output("est-v3-edit-review-message", "children"),
        ],
        Input("est-v3-btn-editar", "n_clicks"),
        State("est-v3-selected-record", "data"),
        prevent_initial_call=True,
    )
    def cargar_formulario_edicion(n_clicks, selected):
        # Un botón recién insertado puede aparecer con n_clicks=None/0.
        # En ese caso no tocar el formulario ni conservar/mezclar estados.
        if not n_clicks or not selected:
            return [no_update] * (len(FIELD_DEFINITIONS) + 5)

        fresh = obtener_establecimiento_por_id(
            int(selected["ID_REGISTRO"])
        )

        if not fresh:
            return [no_update] * (len(FIELD_DEFINITIONS) + 5)

        values = []

        for definition in FIELD_DEFINITIONS:
            value = fresh.get(definition["field"])

            if definition["type"] == "date":
                if value:
                    value = str(value)[:10]

            if definition["type"] == "boolean":
                if value in (True, 1, "1", "SI"):
                    value = 1
                elif value in (False, 0, "0", "NO"):
                    value = 0

            values.append(value)

        return values + [
            "",
            {},
            [],
            True,
            "",
        ]

    @app.callback(
        Output("est-v3-edit-modal", "is_open"),
        Output("est-v3-refresh", "data"),
        Output("est-v3-action-message", "children"),
        Input("est-v3-btn-editar", "n_clicks"),
        Input("est-v3-edit-cancel", "n_clicks"),
        Input("est-v3-edit-confirm", "n_clicks"),
        State("est-v3-selected-record", "data"),
        State("est-v3-edit-changes", "data"),
        State("est-v3-edit-observation", "value"),
        State("est-v3-refresh", "data"),
        prevent_initial_call=True,
    )
    def gestionar_modal_edicion(
        n_open,
        n_cancel,
        n_confirm,
        selected,
        changes,
        observation,
        refresh,
    ):
        trigger = ctx.triggered_id

        if trigger == "est-v3-btn-editar":
            # No abrir cuando Dash solo acaba de insertar el botón
            # en la ficha (n_clicks=None/0).
            if not n_open or not selected:
                return no_update, no_update, no_update

            fresh = obtener_establecimiento_por_id(
                int(selected["ID_REGISTRO"])
            )

            if not fresh:
                return (
                    False,
                    no_update,
                    dbc.Alert(
                        "El registro seleccionado ya no existe.",
                        color="warning",
                        duration=3500,
                    ),
                )

            return True, no_update, no_update

        if trigger == "est-v3-edit-cancel":
            return False, no_update, no_update

        if trigger == "est-v3-edit-confirm":
            if not selected or not changes:
                return (
                    True,
                    no_update,
                    dbc.Alert(
                        "No existen cambios confirmables.",
                        color="warning",
                        duration=3500,
                    ),
                )

            try:
                fresh = obtener_establecimiento_por_id(
                    int(selected["ID_REGISTRO"])
                )

                if not fresh:
                    raise RuntimeError(
                        "El registro seleccionado ya no existe."
                    )

                changed = actualizar_establecimiento(
                    id_registro=fresh["ID_REGISTRO"],
                    cambios=changes,
                    usuario=_usuario_actual(),
                    observacion=observation,
                )

                return (
                    False,
                    int(refresh or 0) + 1,
                    dbc.Alert(
                        (
                            f"Actualización realizada correctamente. "
                            f"{len(changed)} campo(s) modificado(s)."
                        ),
                        color="success",
                        duration=5000,
                    ),
                )

            except Exception as exc:
                return (
                    True,
                    no_update,
                    dbc.Alert(
                        f"No fue posible guardar: {exc}",
                        color="danger",
                    ),
                )

        return no_update, no_update, no_update

    edit_states = [
        State(
            f"est-v3-edit-{definition['field'].lower()}",
            "value",
        )
        for definition in FIELD_DEFINITIONS
    ]

    @app.callback(
        Output("est-v3-edit-changes", "data", allow_duplicate=True),
        Output("est-v3-edit-diff-table", "data", allow_duplicate=True),
        Output("est-v3-edit-confirm", "disabled", allow_duplicate=True),
        Output("est-v3-edit-review-message", "children", allow_duplicate=True),
        Input("est-v3-edit-review", "n_clicks"),
        State("est-v3-selected-record", "data"),
        *edit_states,
        prevent_initial_call=True,
    )
    def revisar_cambios(n_clicks, selected, *values):
        if not n_clicks or not selected:
            return {}, [], True, no_update

        try:
            fresh = obtener_establecimiento_por_id(
                int(selected["ID_REGISTRO"])
            )

            if not fresh:
                return (
                    {},
                    [],
                    True,
                    dbc.Alert(
                        "El registro seleccionado ya no existe.",
                        color="warning",
                    ),
                )

            form_values = {
                definition["field"]: value
                for definition, value in zip(
                    FIELD_DEFINITIONS,
                    values,
                )
            }

            changes, differences = preparar_cambios_edicion(
                fresh,
                form_values,
            )

            if not differences:
                return (
                    {},
                    [],
                    True,
                    dbc.Alert(
                        "No se detectaron cambios.",
                        color="info",
                        duration=3000,
                    ),
                )

            return (
                changes,
                differences,
                False,
                dbc.Alert(
                    (
                        "Revise la comparación antes de confirmar. "
                        f"Se detectaron {len(differences)} cambio(s)."
                    ),
                    color="warning",
                ),
            )

        except Exception as exc:
            return (
                {},
                [],
                True,
                dbc.Alert(
                    f"Revise los datos ingresados: {exc}",
                    color="danger",
                ),
            )

    # =======================================================================
    # RENIPRESS
    # =======================================================================

    @app.callback(
        Output("est-v3-ren-modal", "is_open"),
        Output("est-v3-ren-current", "value"),
        Output("est-v3-ren-new", "value"),
        Output("est-v3-ren-observation", "value"),
        Output("est-v3-refresh", "data", allow_duplicate=True),
        Output("est-v3-action-message", "children", allow_duplicate=True),
        Input("est-v3-btn-renipress", "n_clicks"),
        Input("est-v3-ren-cancel", "n_clicks"),
        Input("est-v3-ren-confirm", "n_clicks"),
        State("est-v3-selected-record", "data"),
        State("est-v3-ren-new", "value"),
        State("est-v3-ren-observation", "value"),
        State("est-v3-refresh", "data"),
        prevent_initial_call=True,
    )
    def gestionar_renipress(
        n_open,
        n_cancel,
        n_confirm,
        selected,
        new_code,
        observation,
        refresh,
    ):
        trigger = ctx.triggered_id

        if trigger == "est-v3-btn-renipress":
            # No abrir cuando el botón acaba de aparecer en una ficha nueva.
            if not n_open or not selected:
                return (
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

            fresh = obtener_establecimiento_por_id(
                int(selected["ID_REGISTRO"])
            )

            if not fresh:
                return (
                    False,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    dbc.Alert(
                        "El registro seleccionado ya no existe.",
                        color="warning",
                        duration=3500,
                    ),
                )

            return (
                True,
                fresh.get("RENIPRESS"),
                "",
                "",
                no_update,
                no_update,
            )

        if trigger == "est-v3-ren-cancel":
            return (
                False,
                no_update,
                "",
                "",
                no_update,
                no_update,
            )

        if trigger == "est-v3-ren-confirm":
            if not selected:
                return (
                    False,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

            try:
                fresh = obtener_establecimiento_por_id(
                    int(selected["ID_REGISTRO"])
                )

                if not fresh:
                    raise RuntimeError(
                        "El registro seleccionado ya no existe."
                    )

                normalized = normalizar_renipress(new_code)

                result = crear_version_renipress(
                    id_registro=fresh["ID_REGISTRO"],
                    nuevo_renipress=normalized,
                    usuario=_usuario_actual(),
                    observacion=observation,
                )

                return (
                    False,
                    no_update,
                    "",
                    "",
                    int(refresh or 0) + 1,
                    dbc.Alert(
                        (
                            "Nueva versión creada correctamente. "
                            f"Registro anterior: "
                            f"{result['ID_REGISTRO_ANTERIOR']} · "
                            f"Nuevo registro: "
                            f"{result['ID_REGISTRO_NUEVO']}."
                        ),
                        color="success",
                        duration=6000,
                    ),
                )

            except Exception as exc:
                return (
                    True,
                    no_update,
                    new_code,
                    observation,
                    no_update,
                    dbc.Alert(
                        f"No fue posible actualizar RENIPRESS: {exc}",
                        color="danger",
                    ),
                )

        return (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
        )

    # =======================================================================
    # REPORTES
    # =======================================================================

    @app.callback(
        Output("est-v3-export-red", "options"),
        Input("est-v3-init", "n_intervals"),
    )
    def cargar_redes(_):
        redes = obtener_redes()

        return (
            [{"label": "Todas", "value": ""}]
            + [
                {"label": red, "value": red}
                for red in redes
            ]
        )

    @app.callback(
        Output("est-v3-export-preview", "children"),
        Input("est-v3-export-universe", "value"),
        Input("est-v3-export-condition", "value"),
        Input("est-v3-export-red", "value"),
    )
    def previsualizar_exportacion(
        universo,
        condition,
        red,
    ):
        try:
            from backend.establecimientos_repository_v3 import (
                obtener_dataset_exportacion,
            )

            rows = obtener_dataset_exportacion(
                universo=universo,
                condicion_centro=condition or None,
                red_asistencial=red or None,
            )

            return html.Div(
                [
                    html.Div(
                        f"{len(rows)}",
                        className="est-v3-export-count",
                    ),
                    html.Div(
                        "registro(s) incluidos en la exportación",
                        className="text-muted small",
                    ),
                ]
            )
        except Exception as exc:
            return dbc.Alert(
                f"No fue posible calcular la exportación: {exc}",
                color="danger",
            )

    @app.callback(
        Output("est-v3-download", "data"),
        Input("est-v3-download-xlsx", "n_clicks"),
        State("est-v3-export-universe", "value"),
        State("est-v3-export-condition", "value"),
        State("est-v3-export-red", "value"),
        prevent_initial_call=True,
    )
    def descargar_excel(
        n_clicks,
        universo,
        condition,
        red,
    ):
        if not n_clicks:
            return no_update

        content, count = generar_excel_maestro(
            universo=universo,
            condicion_centro=condition or None,
            red_asistencial=red or None,
        )

        filename = (
            "MAESTRO_ESTABLECIMIENTOS_"
            + str(universo)
            + "_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".xlsx"
        )

        return dcc.send_bytes(
            lambda buffer: buffer.write(content),
            filename,
        )

    @app.callback(
        Output("est-v3-download", "data", allow_duplicate=True),
        Input("est-v3-download-csv", "n_clicks"),
        State("est-v3-export-universe", "value"),
        State("est-v3-export-condition", "value"),
        State("est-v3-export-red", "value"),
        prevent_initial_call=True,
    )
    def descargar_csv(
        n_clicks,
        universo,
        condition,
        red,
    ):
        if not n_clicks:
            return no_update

        content, count = generar_csv_maestro(
            universo=universo,
            condicion_centro=condition or None,
            red_asistencial=red or None,
        )

        filename = (
            "MAESTRO_ESTABLECIMIENTOS_"
            + str(universo)
            + "_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".csv"
        )

        return dict(
            content=content,
            filename=filename,
            type="text/csv",
        )

    @app.callback(
        Output("est-v3-download", "data", allow_duplicate=True),
        Input("est-v3-download-executive", "n_clicks"),
        prevent_initial_call=True,
    )
    def descargar_resumen_ejecutivo(n_clicks):
        if not n_clicks:
            return no_update

        content = generar_excel_resumen_ejecutivo()

        filename = (
            "RESUMEN_EJECUTIVO_ESTABLECIMIENTOS_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".xlsx"
        )

        return dcc.send_bytes(
            lambda buffer: buffer.write(content),
            filename,
        )

    return app
