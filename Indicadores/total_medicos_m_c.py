from dash import html, dcc, register_page, Input, Output, State, callback
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine
import dash_ag_grid as dag
from urllib.parse import parse_qs

# Paleta similar a dashboard.py
BRAND = "#0064AF"
BRAND_SOFT = "#D7E9FF"
CARD_BG = "#FFFFFF"
TEXT = "#1C1F26"
MUTED = "#6B7280"
BORDER = "#E5E7EB"
FONT_FAMILY = "Inter, Segoe UI, Calibri, sans-serif"
CARD_STYLE = {
    "border": f"1px solid {BORDER}",
    "borderRadius": "16px",
    "backgroundColor": CARD_BG,
    "boxShadow": "0 10px 24px rgba(0,0,0,0.08)",
    "padding": "16px",
    "transition": "transform .12s ease, box-shadow .12s ease",
}
GRAPH_CONFIG = {"responsive": True, "displaylogo": False}
# NUEVOS ESTILOS TABS
TABS_CONTAINER_STYLE = {
    "backgroundColor": CARD_BG,
    "border": f"1px solid {BORDER}",
    "borderRadius": "16px",
    "padding": "8px 12px 4px 12px",
    "boxShadow": "0 4px 12px rgba(0,0,0,0.06)"
}
TAB_STYLE = {
    "padding": "12px 20px",
    "fontFamily": FONT_FAMILY,
    "fontSize": "14px",
    "fontWeight": "600",
    "color": MUTED,
    "borderRadius": "12px",
    "margin": "4px 6px",
    "cursor": "pointer",
    "transition": "all .2s ease",
    "border": "1px solid transparent",
    "letterSpacing": "-0.1px"
}
TAB_SELECTED_STYLE = {
    **TAB_STYLE,
    "color": BRAND,
    "background": "linear-gradient(145deg, #ffffff 0%, #F3F8FC 100%)",
    "boxShadow": "0 3px 8px rgba(0,100,175,0.12)",
    "border": f"1px solid {BRAND}",
    "fontWeight": "700"
}

DEFAULT_TIPO_ASEGURADO = "Todos"
TIPO_ASEGURADO_CLAUSES = {
    "asegurado": "('1')",
    "1": "('1')",
    "no asegurado": "('2')",
    "2": "('2')",
    "todos": "('1','2')"
}


def resolve_tipo_asegurado_clause(value: str | None) -> str:
    key = str(value).strip().lower() if value else ""
    return TIPO_ASEGURADO_CLAUSES.get(key, TIPO_ASEGURADO_CLAUSES["todos"])

# Helpers reutilizables
def empty_fig(title: str | None = None) -> go.Figure:
    fig = go.Figure()
    layout_kwargs = dict(
        template="simple_white",
        plot_bgcolor="#F9FBFD",
        paper_bgcolor="#F9FBFD",
        font=dict(family=FONT_FAMILY, color="#1F2937"),
        margin=dict(l=60, r=32, t=70, b=40),
    )
    if title:
        layout_kwargs["title"] = dict(
            text=title,
            font=dict(size=18, color=BRAND, family=FONT_FAMILY),
            x=0,
            xanchor="left",
        )
    fig.update_layout(**layout_kwargs)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.add_annotation(
        text="Sin datos disponibles",
        font=dict(color=MUTED, size=12),
        showarrow=False,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
    )
    return fig

def _parse_query_param(search: str, key: str) -> str | None:
    if not search:
        return None
    params = parse_qs(search.lstrip("?"))
    values = params.get(key)
    return values[0] if values else None


def _parse_periodo(search: str) -> str | None:
    return _parse_query_param(search, "periodo")


def _parse_anio(search: str) -> str | None:
    return _parse_query_param(search, "anio")


def _parse_codasegu(search: str) -> str | None:
    return _parse_query_param(search, "codasegu")


def get_codcas_periodo(
    pathname: str,
    search: str,
    periodo_dropdown: str,
    anio_dropdown: str,
    tipo_asegurado_dropdown: str | None = None,
):
    if not pathname:
        return None, None, None, DEFAULT_TIPO_ASEGURADO
    import secure_code as sc
    codcas = pathname.rstrip("/").split("/")[-1]
    codcas = sc.decode_code(codcas)
    periodo = _parse_periodo(search) or periodo_dropdown
    anio = _parse_anio(search) or anio_dropdown
    codasegu = _parse_codasegu(search) or tipo_asegurado_dropdown or DEFAULT_TIPO_ASEGURADO
    return codcas, periodo, anio, codasegu

# Conexión DB
def create_connection():
    try:
        engine = create_engine('postgresql+psycopg2://postgres:4dm1n@10.0.29.117:5433/DW_ESTADISTICA')
        with engine.connect():
            pass
        return engine
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        return None

# --- NUEVO: helper para aplicar filtros del grid a los datos de la tabla ---
def _tm_apply_filter(data_records, filter_model):
    if not filter_model:
        return data_records
    df_local = pd.DataFrame(data_records)
    for col, f in (filter_model or {}).items():
        if col not in df_local.columns:
            continue
        ft = f.get("filterType")
        t = f.get("type")
        val = f.get("filter")
        if ft == "text":
            serie = df_local[col].astype(str)
            if t == "contains":
                mask = serie.str.contains(val or "", case=False, na=False)
            elif t == "notContains":
                mask = ~serie.str.contains(val or "", case=False, na=False)
            elif t == "equals":
                mask = serie.str.lower() == str(val or "").lower()
            elif t == "startsWith":
                mask = serie.str.lower().str.startswith(str(val or "").lower())
            elif t == "endsWith":
                mask = serie.str.lower().str.endswith(str(val or "").lower())
            else:
                mask = True
            df_local = df_local[mask]
        elif ft == "number":
            serie = pd.to_numeric(df_local[col], errors="coerce")
            try:
                num = float(val) if val is not None else None
            except:
                num = None
            if t == "equals" and num is not None:
                mask = serie == num
            elif t == "greaterThan" and num is not None:
                mask = serie > num
            elif t == "lessThan" and num is not None:
                mask = serie < num
            elif t == "inRange":
                num_to = f.get("filterTo")
                try:
                    num_to = float(num_to) if num_to is not None else None
                except:
                    num_to = None
                if num is not None and num_to is not None:
                    mask = (serie >= num) & (serie <= num_to)
                elif num is not None:
                    mask = serie >= num
                elif num_to is not None:
                    mask = serie <= num_to
                else:
                    mask = True
            else:
                mask = True
            df_local = df_local[mask]
    return df_local.to_dict("records")


def _tm_format_fecha_atencion(serie: pd.Series) -> pd.Series:
    """Normaliza la fecha al formato AAAA-MM-DD manteniendo valores válidos."""
    if serie.empty:
        return pd.Series([], index=serie.index, dtype=object)
    parsed = pd.to_datetime(serie, errors="coerce", infer_datetime_format=True)
    needs_dayfirst = parsed.isna() & serie.notna()
    if needs_dayfirst.any():
        parsed.loc[needs_dayfirst] = pd.to_datetime(
            serie[needs_dayfirst],
            errors="coerce",
            infer_datetime_format=True,
            dayfirst=True,
        )
    formatted = parsed.dt.strftime("%Y-%m-%d")
    serie_str = serie.astype(str).str.strip()
    mask_missing = serie.isna() | serie_str.eq("") | serie_str.str.lower().isin({"nan", "nat", "none"})
    formatted = formatted.fillna(serie_str.str[:10])
    formatted = formatted.where(~mask_missing, "Sin fecha")
    return formatted.fillna("Sin fecha")

# Layout sin verificador de query
layout = html.Div([
    dcc.Location(id="tm-location_m_c", refresh=False),
    html.Div([
        # Header con icono
        html.Div([
            html.Div([
                html.I(className="bi bi-clipboard2-heart", style={'fontSize': '26px', 'color': BRAND, 'marginRight': '12px'}),
                html.Div([
                    html.H4("Detalle de producción médica",
                            style={"margin": 0, "color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700, "letterSpacing": "-0.3px"}),
                          html.P("📊 Tabla de atenciones por médico para el periodo seleccionado",
                           style={"color": MUTED, "fontSize": "13px", "marginTop": "6px", "fontFamily": FONT_FAMILY})
                ])
            ], style={'display': 'flex', 'alignItems': 'center', 'flex': 1})
        ], style={'flex': 1}),
        # Lado derecho: botón descargar
        html.Div([
            html.Button(
                [html.I(className="bi bi-download me-2"), "Descargar CSV"],
                id="tm-download-btn_m_c",
                n_clicks=0,
                style={
                    "backgroundColor": BRAND,
                    "color": "#fff",
                    "border": "none",
                    "borderRadius": "10px",
                    "padding": "10px 16px",
                    "fontFamily": FONT_FAMILY,
                    "fontSize": "14px",
                    "fontWeight": "600",
                    "cursor": "pointer",
                    "boxShadow": "0 4px 12px rgba(0,100,175,0.2)",
                    "transition": "all .2s ease",
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "6px"
                }
            ),
            dcc.Download(id="tm-download_m_c")
        ])
    ], style={
        "padding": "16px 20px",
        "background": "linear-gradient(120deg, #ffffff 0%, #EEF5FF 70%, #E4F0FF 100%)",
        "border": f"1px solid {BORDER}",
        "borderRadius": "16px",
        "boxShadow": "0 6px 18px rgba(0,0,0,0.08)",
        "marginBottom": "16px",
        "display": "flex",
        "justifyContent": "space-between",
        "alignItems": "center",
        "gap": "16px"
    }),
    # PESTAÑAS
    dcc.Tabs(
        id="tm-tabs_m_c",
        value="tm-tab-prod",
        style={"border": "none"},
        parent_style={"marginTop": "12px"},
        className="custom-tabs",
        children=[
            dcc.Tab(
                label="Producción",
                value="tm-tab-prod",
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=html.Div([
                    html.Div([
                        html.Div([
                            html.I(
                                className="bi bi-calendar-week",
                                style={'fontSize': '20px', 'color': BRAND, 'marginRight': '10px'}
                            ),
                            html.H5(
                                "Matriz de Atenciones por Día",
                                style={"margin": 0, "color": BRAND, "fontFamily": FONT_FAMILY, "fontWeight": 700}
                            )
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
                        html.Div(id="tm-matriz-wrapper_m_c", style={"marginTop": "12px"})
                    ], style={**CARD_STYLE}),
                    html.Div([
                        dcc.Loading(
                            html.Div([
                                # Gráfico agrupador + especialidad (lado a lado)
                            ], style={"display": "flex", "gap": "8px", "flexWrap": "wrap"}),
                            type="dot"
                        ),
                        html.Div(
                            id="tm-msg_m_c",
                            style={"marginTop": "6px", "color": MUTED, "fontFamily": FONT_FAMILY, "fontSize": "12px", "fontWeight": "bold"}
                        ),
                        html.Div(id="tm-table-wrapper_m_c", style={"marginTop": "12px"})
                    ], style={**CARD_STYLE})
                ], style={"padding": "8px", "display": "flex", "flexDirection": "column", "gap": "12px"})
            )
        ],
        content_style=TABS_CONTAINER_STYLE
    ),
    # Stores
    dcc.Store(id="tm-store_m_c")
], style={
    "width": "100%",
    "maxWidth": "1600px",
    "margin": "0 auto",
    "padding": "8px 16px 24px 16px",
    "fontFamily": FONT_FAMILY
})

# Registrar la página con el layout explícito para evitar NoLayoutException
register_page(
    __name__,
    path_template="/dash/total_medicos_m_c/<codcas>",
    name="total_medicos_m_c",
    layout=layout
)


@callback(
    Output("tm-table-wrapper_m_c", "children"),
    Input("tm-location_m_c", "pathname"),
    Input("tm-location_m_c", "search"),
    State("filter-periodo", "value"),
    State("filter-anio", "value"),
    State("filter-tipo-asegurado", "value"),
)
def update_tabla_medicos(pathname, search, periodo_dropdown, anio_dropdown, tipo_dropdown):
    codcas, periodo, anio, tipo_asegurado = get_codcas_periodo(
        pathname,
        search,
        periodo_dropdown,
        anio_dropdown,
        tipo_dropdown,
    )
    codasegu_clause = resolve_tipo_asegurado_clause(tipo_asegurado)
    if not codcas:
        return html.Div("Sin ruta.", style={"color": "#b00"})
    if not periodo or not anio:
        return html.Div("Faltan filtros (periodo/año).", style={"color": "#b00"})
    engine = create_connection()
    if engine is None:
        return html.Div("Error de conexión a la base de datos.", style={"color": "#b00"})
    query = f"""
         SELECT c.servhosdes AS descripcion_servicio,
             ce.dni_medico,
             ce.fecha_atencion
        FROM dwsge.dw_consulta_externa_homologacion_{anio}_{periodo} AS ce
        LEFT JOIN dwsge.sgss_cmsho10 AS c ON ce.cod_servicio = c.servhoscod
        WHERE ce.cod_centro = '{codcas}'
          AND ce.clasificacion in (2,4,6)
          AND ce.cod_servicio= 'A91'
          AND (
                            CASE 
                                WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                ELSE '1'
                            END
                            ) IN {codasegu_clause}
    """
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        return html.Div(f"Error consulta: {e}", style={"color": "#b00"})
    if df.empty:
        return html.Div("Sin datos producción por médico.", style={"color": "#b00"})
    fechas = _tm_format_fecha_atencion(df["fecha_atencion"])
    prod_med_df = (
        df.assign(
            descripcion_servicio=df["descripcion_servicio"].fillna("Sin servicio"),
            dni_medico=df["dni_medico"].fillna("Sin DNI"),
            fecha_atencion=fechas
        )
        .groupby(["descripcion_servicio", "dni_medico", "fecha_atencion"])
        .size().reset_index(name="Atenciones")
        .sort_values("Atenciones", ascending=False)
    )
    total_att = int(prod_med_df["Atenciones"].sum())
    col_defs = [
        {"headerName": "DNI Médico", "field": "dni_medico", "minWidth": 120},
        {"headerName": "Fecha atención", "field": "fecha_atencion", "minWidth": 140},
        {"headerName": "Servicio", "field": "descripcion_servicio", "minWidth": 350, "flex": 2},
        {"headerName": "Atenciones", "field": "Atenciones", "filter": "agNumberColumnFilter", "minWidth": 130}
    ]
    return dag.AgGrid(
        id="tm-table-grid_m_c",
        columnDefs=col_defs,
        rowData=prod_med_df.to_dict("records"),
        defaultColDef={
            "sortable": True,
            "resizable": True,
            "filter": "agTextColumnFilter",
            "floatingFilter": True,
            "flex": 1
        },
        dashGridOptions={
            "pinnedBottomRowData": [{
                "descripcion_servicio": f"Total atenciones: {total_att:,}",
                "fecha_atencion": "",
                "Atenciones": total_att
            }],
            "onFirstDataRendered": {"function": "params.api.autoSizeAllColumns();"}
        },
        className="ag-theme-alpine",
        style={"height": "750px", "width": "100%"}
    )

# --- NUEVO: total dinámico para la tabla (suma Atenciones filtradas) ---
@callback(
    Output("tm-table-grid_m_c", "dashGridOptions"),
    Input("tm-table-grid_m_c", "filterModel"),
    State("tm-table-grid_m_c", "rowData")
)
def tm_actualizar_total_grid(filter_model, row_data):
    if not row_data:
        return {"pinnedBottomRowData": [{"descripcion_servicio": "Total atenciones: 0", "fecha_atencion": "", "Atenciones": 0}]}
    filtrados = _tm_apply_filter(row_data, filter_model)
    df_f = pd.DataFrame(filtrados) if filtrados else pd.DataFrame(columns=["Atenciones"])
    total_att = int(pd.to_numeric(df_f.get("Atenciones", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    return {
        "pinnedBottomRowData": [{
            "descripcion_servicio": f"Total atenciones: {total_att:,}",
            "fecha_atencion": "",
            "Atenciones": total_att
        }],
        "statusBar": {
            "statusPanels": [
                {"statusPanel": "agAggregationComponent", "align": "right"}
            ]
        }
    }


@callback(
    Output("tm-matriz-wrapper_m_c", "children"),
    Input("tm-location_m_c", "pathname"),
    Input("tm-location_m_c", "search"),
    State("filter-periodo", "value"),
    State("filter-anio", "value"),
    State("filter-tipo-asegurado", "value"),
)
def update_matriz_medicos(pathname, search, periodo_dropdown, anio_dropdown, tipo_dropdown):
    codcas, periodo, anio, tipo_asegurado = get_codcas_periodo(
        pathname,
        search,
        periodo_dropdown,
        anio_dropdown,
        tipo_dropdown,
    )
    codasegu_clause = resolve_tipo_asegurado_clause(tipo_asegurado)
    if not codcas:
        return html.Div("Sin ruta.", style={"color": "#b00"})
    if not periodo or not anio:
        return html.Div("Faltan filtros (periodo/año).", style={"color": "#b00"})
    engine = create_connection()
    if engine is None:
        return html.Div("Error de conexión a la base de datos.", style={"color": "#b00"})
    
    query = f"""
         SELECT ce.dni_medico,
             ce.fecha_atencion
        FROM dwsge.dw_consulta_externa_homologacion_{anio}_{periodo} AS ce
        WHERE ce.cod_centro = '{codcas}'
          AND ce.clasificacion in (2,4,6)
          AND ce.cod_servicio= 'A91'
          AND (
                            CASE 
                                WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                ELSE '1'
                            END
                            ) IN {codasegu_clause}
    """
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        return html.Div(f"Error consulta: {e}", style={"color": "#b00"})
    
    if df.empty:
        return html.Div("Sin datos de atenciones.", style={"color": "#b00"})
    
    # Formatear fechas y limpiar datos
    fechas = _tm_format_fecha_atencion(df["fecha_atencion"])
    df = df.assign(
        dni_medico=df["dni_medico"].fillna("Sin DNI"),
        fecha_atencion=fechas
    )
    
    # Filtrar fechas válidas (excluir "Sin fecha")
    df_valid = df[df["fecha_atencion"] != "Sin fecha"].copy()
    
    if df_valid.empty:
        return html.Div("No hay fechas válidas en los datos.", style={"color": "#b00"})
    
    # Crear tabla pivotada: DNI en filas, fechas en columnas, conteo de atenciones
    pivot_df = df_valid.groupby(["dni_medico", "fecha_atencion"]).size().unstack(fill_value=0)
    
    # Ordenar columnas por fecha
    pivot_df = pivot_df.reindex(sorted(pivot_df.columns), axis=1)
    
    # Agregar columna de total por médico
    pivot_df["Total"] = pivot_df.sum(axis=1)
    
    # Ordenar filas por total descendente
    pivot_df = pivot_df.sort_values("Total", ascending=False)
    
    # Resetear índice para tener dni_medico como columna
    pivot_df = pivot_df.reset_index()
    
    # Preparar columnas para AG Grid
    col_defs = [
        {
            "headerName": "DNI Médico", 
            "field": "dni_medico", 
            "pinned": "left",
            "minWidth": 120,
            "cellStyle": {"fontWeight": "bold", "backgroundColor": "#f8f9fa"}
        }
    ]
    
    # Agregar columnas para cada fecha
    for fecha in sorted([col for col in pivot_df.columns if col not in ["dni_medico", "Total"]]):
        col_defs.append({
            "headerName": fecha,
            "field": fecha,
            "filter": "agNumberColumnFilter",
            "minWidth": 100,
            "cellStyle": {
                "function": "params.value > 0 ? {'backgroundColor': '#ECF5FB', 'fontWeight': '600'} : {}"
            }
        })
    
    # Agregar columna Total
    col_defs.append({
        "headerName": "Total",
        "field": "Total",
        "pinned": "right",
        "filter": "agNumberColumnFilter",
        "minWidth": 100,
        "cellStyle": {"fontWeight": "bold", "backgroundColor": "#7FB9DE"}
    })
    
    # Calcular fila de totales por columna
    total_row = {"dni_medico": "TOTAL"}
    for col in pivot_df.columns:
        if col != "dni_medico":
            total_row[col] = int(pivot_df[col].sum())
    
    return dag.AgGrid(
        id="tm-matriz-grid_m_c",
        columnDefs=col_defs,
        rowData=pivot_df.to_dict("records"),
        defaultColDef={
            "sortable": True,
            "resizable": True,
            "filter": True,
            "floatingFilter": False,
            "flex": 0
        },
        dashGridOptions={
            "pinnedBottomRowData": [total_row],
            "onFirstDataRendered": {"function": "params.api.autoSizeAllColumns();"}
        },
        className="ag-theme-alpine",
        style={"height": "700px", "width": "100%"}
    )


@callback(
    Output("tm-download_m_c", "data"),
    Input("tm-download-btn_m_c", "n_clicks"),
    State("tm-location_m_c", "pathname"),
    State("tm-location_m_c", "search"),
    State("filter-periodo", "value"),
    State("filter-anio", "value"),
    State("filter-tipo-asegurado", "value"),
    prevent_initial_call=True
)
def tm_descargar_csv(n_clicks, pathname, search, periodo_dropdown, anio_dropdown, tipo_dropdown):
    if not n_clicks:
        return None
    codcas, periodo, anio, tipo_asegurado = get_codcas_periodo(
        pathname,
        search,
        periodo_dropdown,
        anio_dropdown,
        tipo_dropdown,
    )
    codasegu_clause = resolve_tipo_asegurado_clause(tipo_asegurado)
    if not codcas or not periodo or not anio:
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
            ag.agrupador AS agrupador,
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
        FROM dwsge.dw_consulta_externa_homologacion_{anio}_{periodo} AS ce
        LEFT JOIN dwsge.sgss_cmsho10 AS c ON ce.cod_servicio = c.servhoscod
        LEFT JOIN dwsge.dim_especialidad AS e ON ce.cod_especialidad = e.cod_especialidad
        LEFT JOIN dwsge.sgss_cmtco10 AS t ON ce.cod_tipo_consulta = t.tipconcod
        LEFT JOIN dwsge.sgss_cmdia10 AS d ON ce.cod_diag = d.diagcod
        LEFT JOIN dwsge.sgss_cmace10 AS a ON ce.cod_actividad = a.actcod AND ce.cod_subactividad = a.actespcod
        LEFT JOIN dwsge.sgss_cmact10 AS am ON ce.cod_actividad = am.actcod
        LEFT JOIN dwsge.sgss_cmcas10 AS ca ON ce.cod_oricentro = ca.oricenasicod AND ce.cod_centro = ca.cenasicod
        LEFT JOIN dwsge.dim_agrupador as ag ON ce.cod_agrupador = ag.cod_agrupador
        WHERE ce.cod_centro = '{codcas}'
          AND cod_servicio= 'A91'
          AND ce.clasificacion in (2,4,6)
          AND (
                            CASE 
                                WHEN ce.cod_tipo_paciente = '4' THEN '2'
                                ELSE '1'
                            END
                            ) IN {codasegu_clause}
    """
    try:
        df = pd.read_sql(query, engine)
    except Exception:
        return None
    filename = f"total_atenciones_{codcas}_{anio}_{periodo}.csv"
    return dcc.send_data_frame(df.to_csv, filename, index=False, encoding="utf-8-sig", sep="|")