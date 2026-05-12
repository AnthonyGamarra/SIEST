import json
import os
import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, dash_table, ALL
from dash.exceptions import PreventUpdate
from flask import has_request_context
from flask_login import current_user
import pandas as pd
import oracledb

# ── Credenciales Oracle ──────────────────────────────────────────────────────
ORACLE_USER = "USR_GCPP_RPILLACA"
ORACLE_PASS = "Qtb8Xp3Ten#J8Wm1"
ORACLE_DSN  = "10.56.1.76:1527/wnet"

COLS_B1 = ['ORIGEN', 'CENTRO', 'PERIODO', 'SEXO', 'GETAREO',
           'PACSECNUM', 'CODSER', 'TIPPROF', 'ORIGEN_TIPO']
COLS_B2 = ['ORIGEN', 'CENTRO', 'PERIODO', 'SEXO', 'GETAREO',
           'PACSECNUM', 'CODDX', 'TIPPROF', 'ORIGEN_TIPO']


# ── Conexión ─────────────────────────────────────────────────────────────────
def _connect():
    return oracledb.connect(user=ORACLE_USER, password=ORACLE_PASS, dsn=ORACLE_DSN)


def _get_options():
    conn = None
    try:
        conn = _connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT CENASICOD,CENASIDES, CENASIRENAESCOD, CENASIRENAESUNIGESCOD "
            "FROM SGSS.CMCAS10 WHERE ESTREGCOD='1' AND ORICENASICOD='1'"
        )
        rows = cursor.fetchall()
        cursor.close()
        opts = sorted(
            [{'label': str(row[1] or '').strip() or str(row[0]), 'value': str(row[0])} for row in rows],
            key=lambda x: x['label']
        )
        codmap = {str(row[0]): (str(row[2] or ''), str(row[3] or '')) for row in rows}
        return opts, codmap
    except Exception as e:
        print(f"[tramas] get_options error: {e}")
        return [], {}
    finally:
        if conn:
            conn.close()


# ── Consultas dinámicas ───────────────────────────────────────────────────────
def _query_b1(fec_ini: str, fec_fin: str, cas: str) -> pd.DataFrame:
    fi = pd.to_datetime(fec_ini).strftime('%d/%m/%Y')
    ff = pd.to_datetime(fec_fin).strftime('%d/%m/%Y')
    sql = f"""
SELECT A.ATENAMBORICENASICOD        AS ORIGEN,
       A.ATENAMBCENASICOD           AS CENTRO,
       TO_CHAR(A.ATENAMBATENFEC,'yyyymm') AS PERIODO,
       DECODE(Y.PERSEXOCOD,'0','2','1','1') AS SEXO,
       CB.GRPETA1COD                AS GETAREO,
       Y.PERSECNUM                  AS PACSECNUM,
       SR.SERVHOSCOD                AS CODSER,
       SR.SERVHOSTIPPROCOD          AS TIPPROF,
       'ATENME'                     AS ORIGEN_TIPO
  FROM SGSS.CTAAM10 A
  LEFT JOIN SGSS.CMAME10 X
    ON X.ORICENASICOD = A.ATENAMBORICENASICOD
   AND X.CENASICOD    = A.ATENAMBCENASICOD
   AND X.ACTMEDNUM    = A.ATENAMBNUM
  LEFT JOIN SGSS.CMPER10 Y     ON X.ACTMEDPACSECNUM = Y.PERSECNUM
  LEFT JOIN SGSS.CBGPE10 CB    ON CB.GRPETAEDADCOD = X.ACTMEDEDADATEN
  LEFT JOIN SGSS.CMSHO10 SR    ON SR.SERVHOSCOD = X.ACTMEDSERVHOSCOD
 WHERE TRUNC(A.ATENAMBATENFEC) BETWEEN TO_DATE('{fi}','DD/MM/YYYY')
                                   AND TO_DATE('{ff}','DD/MM/YYYY')
   AND A.ATENAMBESTREGCOD = '1'
   AND Y.PERSECNUM IS NOT NULL
   AND A.ATENAMBCENASICOD = '{cas}'
UNION ALL
SELECT B.ATENOMORICENASICOD         AS ORIGEN,
       B.ATENOMCENASICOD            AS CENTRO,
       TO_CHAR(B.ATENOMFEC,'yyyymm') AS PERIODO,
       DECODE(Y1.PERSEXOCOD,'0','2','1','1') AS SEXO,
       CB1.GRPETA1COD               AS GETAREO,
       Y1.PERSECNUM                 AS PACSECNUM,
       SR1.SERVHOSCOD               AS CODSER,
       SR1.SERVHOSTIPPROCOD         AS TIPPROF,
       'ATENOME'                    AS ORIGEN_TIPO
  FROM SGSS.CTANM10 B
  LEFT JOIN SGSS.CMAME10 X1
    ON X1.ORICENASICOD = B.ATENOMORICENASICOD
   AND X1.CENASICOD    = B.ATENOMCENASICOD
   AND X1.ACTMEDNUM    = B.ATENOMACTMEDNUM
  LEFT JOIN SGSS.CMPER10 Y1    ON X1.ACTMEDPACSECNUM = Y1.PERSECNUM
  LEFT JOIN SGSS.CBGPE10 CB1   ON CB1.GRPETAEDADCOD = X1.ACTMEDEDADATEN
  LEFT JOIN SGSS.CMSHO10 SR1   ON SR1.SERVHOSCOD = X1.ACTMEDSERVHOSCOD
 WHERE B.ATENOMFEC BETWEEN TO_DATE('{fi}','DD/MM/YYYY')
                       AND TO_DATE('{ff}','DD/MM/YYYY')
   AND B.ATENOMESTREGCOD = '1'
   AND Y1.PERSECNUM IS NOT NULL
   AND B.ATENOMCENASICOD = '{cas}'
UNION ALL
SELECT CT.CITAMBORICENASICOD        AS ORIGEN,
       CT.CITAMBCENASICOD           AS CENTRO,
       TO_CHAR(CT.CITAMBPROCONFEC,'YYYYMM') AS PERIODO,
       DECODE(Y2.PERSEXOCOD,'0','2','1','1') AS SEXO,
       CB2.GRPETA1COD               AS GETAREO,
       Y2.PERSECNUM                 AS PACSECNUM,
       SR2.SERVHOSCOD               AS CODSER,
       SR2.SERVHOSTIPPROCOD         AS TIPPROF,
       'ATEODON'                    AS ORIGEN_TIPO
  FROM SGSS.CTCAM10 CT
  LEFT JOIN SGSS.CMAME10 X2
    ON CT.CITAMBORICENASICOD = X2.ORICENASICOD
   AND CT.CITAMBCENASICOD    = X2.CENASICOD
   AND CT.CITAMBNUM          = X2.ACTMEDNUM
  LEFT JOIN SGSS.CMPER10 Y2    ON X2.ACTMEDPACSECNUM = Y2.PERSECNUM
  LEFT JOIN SGSS.CBGPE10 CB2   ON CB2.GRPETAEDADCOD = X2.ACTMEDEDADATEN
  LEFT JOIN SGSS.CMSHO10 SR2   ON SR2.SERVHOSCOD = X2.ACTMEDSERVHOSCOD
 WHERE CT.CITAMBPROCONFEC BETWEEN TO_DATE('{fi}','DD/MM/YYYY')
                              AND TO_DATE('{ff}','DD/MM/YYYY')
   AND CT.CITAMBSERVHOSCOD IN ('E11','E12','E19')
   AND CT.ESTCITCOD = '4'
   AND Y2.PERSECNUM IS NOT NULL
   AND CT.CITAMBCENASICOD = '{cas}'
"""
    conn = None
    try:
        conn = _connect()
        return pd.read_sql(sql, conn)
    except Exception as e:
        print(f"[tramas] query_b1 error: {e}")
        return pd.DataFrame(columns=COLS_B1)
    finally:
        if conn:
            conn.close()


def _query_b2(fec_ini: str, fec_fin: str, cas: str) -> pd.DataFrame:
    fi = pd.to_datetime(fec_ini).strftime('%d/%m/%Y')
    ff = pd.to_datetime(fec_fin).strftime('%d/%m/%Y')
    sql = f"""
SELECT A.ATENAMBORICENASICOD        AS ORIGEN,
       A.ATENAMBCENASICOD           AS CENTRO,
       TO_CHAR(A.ATENAMBATENFEC,'yyyymm') AS PERIODO,
       DECODE(Y.PERSEXOCOD,'0','2','1','1') AS SEXO,
       CB.GRPETA1COD                AS GETAREO,
       Y.PERSECNUM                  AS PACSECNUM,
       DECODE(INSTR(DX.DIAGCOD,'.'),0,DX.DIAGCOD||'.X',DX.DIAGCOD) AS CODDX,
       SR.SERVHOSTIPPROCOD          AS TIPPROF,
       'ATENME'                     AS ORIGEN_TIPO
  FROM SGSS.CTAAM10 A
  LEFT JOIN SGSS.CMAME10 X
    ON X.ORICENASICOD = A.ATENAMBORICENASICOD
   AND X.CENASICOD    = A.ATENAMBCENASICOD
   AND X.ACTMEDNUM    = A.ATENAMBNUM
  LEFT JOIN SGSS.CMPER10 Y     ON X.ACTMEDPACSECNUM = Y.PERSECNUM
  LEFT JOIN SGSS.CBGPE10 CB    ON CB.GRPETAEDADCOD = X.ACTMEDEDADATEN
  LEFT JOIN SGSS.CMSHO10 SR    ON SR.SERVHOSCOD = X.ACTMEDSERVHOSCOD
  LEFT JOIN SGSS.CTDAA10 DX
    ON A.ATENAMBORICENASICOD = DX.ATENAMBORICENASICOD
   AND A.ATENAMBCENASICOD    = DX.ATENAMBCENASICOD
   AND A.ATENAMBNUM          = DX.ATENAMBNUM
 WHERE TRUNC(A.ATENAMBATENFEC) BETWEEN TO_DATE('{fi}','DD/MM/YYYY')
                                   AND TO_DATE('{ff}','DD/MM/YYYY')
   AND A.ATENAMBESTREGCOD = '1'
   AND Y.PERSECNUM IS NOT NULL
   AND '2' = DX.ATENAMBTIPODIAGCOD
   AND A.ATENAMBCENASICOD = '{cas}'
UNION ALL
SELECT B.ATENOMORICENASICOD         AS ORIGEN,
       B.ATENOMCENASICOD            AS CENTRO,
       TO_CHAR(B.ATENOMFEC,'yyyymm') AS PERIODO,
       DECODE(Y1.PERSEXOCOD,'0','2','1','1') AS SEXO,
       CB1.GRPETA1COD               AS GETAREO,
       Y1.PERSECNUM                 AS PACSECNUM,
       DECODE(INSTR(DX.ATENMDDIAGCOD,'.'),0,DX.ATENMDDIAGCOD||'.X',DX.ATENMDDIAGCOD) AS CODDX,
       SR1.SERVHOSTIPPROCOD         AS TIPPROF,
       'ATENOME'                    AS ORIGEN_TIPO
  FROM SGSS.CTANM10 B
  LEFT JOIN SGSS.CMAME10 X1
    ON X1.ORICENASICOD = B.ATENOMORICENASICOD
   AND X1.CENASICOD    = B.ATENOMCENASICOD
   AND X1.ACTMEDNUM    = B.ATENOMACTMEDNUM
  LEFT JOIN SGSS.CMPER10 Y1    ON X1.ACTMEDPACSECNUM = Y1.PERSECNUM
  LEFT JOIN SGSS.CBGPE10 CB1   ON CB1.GRPETAEDADCOD = X1.ACTMEDEDADATEN
  LEFT JOIN SGSS.CMSHO10 SR1   ON SR1.SERVHOSCOD = X1.ACTMEDSERVHOSCOD
  LEFT JOIN SGSS.CTDAN10 DX
    ON B.ATENOMORICENASICOD = DX.ATENOMORICENASICOD
   AND B.ATENOMCENASICOD    = DX.ATENOMCENASICOD
   AND B.ATENOMACTMEDNUM    = DX.ATENOMACTMEDNUM
 WHERE B.ATENOMFEC BETWEEN TO_DATE('{fi}','DD/MM/YYYY')
                       AND TO_DATE('{ff}','DD/MM/YYYY')
   AND B.ATENOMESTREGCOD = '1'
   AND Y1.PERSECNUM IS NOT NULL
   AND '2' = DX.ATENMDTIPODIAGCOD
   AND B.ATENOMCENASICOD = '{cas}'
UNION ALL
SELECT CT.CITAMBORICENASICOD        AS ORIGEN,
       CT.CITAMBCENASICOD           AS CENTRO,
       TO_CHAR(CT.CITAMBPROCONFEC,'YYYYMM') AS PERIODO,
       DECODE(Y1.PERSEXOCOD,'0','2','1','1') AS SEXO,
       CB1.GRPETA1COD               AS GETAREO,
       Y1.PERSECNUM                 AS PACSECNUM,
       DECODE(INSTR(DX1.DIAGCOD,'.'),0,DX1.DIAGCOD||'.X',DX1.DIAGCOD) AS CODDX,
       SR1.SERVHOSTIPPROCOD         AS TIPPROF,
       'ATEODO'                     AS ORIGEN_TIPO
  FROM SGSS.CTCAM10 CT
  LEFT JOIN SGSS.CMAME10 X1
    ON CT.CITAMBORICENASICOD = X1.ORICENASICOD
   AND CT.CITAMBCENASICOD    = X1.CENASICOD
   AND CT.CITAMBNUM          = X1.ACTMEDNUM
  LEFT JOIN SGSS.CMPER10 Y1    ON X1.ACTMEDPACSECNUM = Y1.PERSECNUM
  LEFT JOIN SGSS.CBGPE10 CB1   ON CB1.GRPETAEDADCOD = X1.ACTMEDEDADATEN
  LEFT JOIN SGSS.CMSHO10 SR1   ON SR1.SERVHOSCOD = X1.ACTMEDSERVHOSCOD
  LEFT JOIN SGSS.CTDAO10 DX1
    ON CT.CITAMBORICENASICOD = DX1.ATENODOORICENASICOD
   AND CT.CITAMBCENASICOD    = DX1.ATENODOCENASICOD
   AND CT.CITAMBNUM          = DX1.ATENODONUM
 WHERE CT.CITAMBPROCONFEC BETWEEN TO_DATE('{fi}','DD/MM/YYYY')
                              AND TO_DATE('{ff}','DD/MM/YYYY')
   AND CT.CITAMBSERVHOSCOD IN ('E11','E12','E19')
   AND CT.ESTCITCOD = '4'
   AND Y1.PERSECNUM IS NOT NULL
   AND '2' = DX1.TIPODIAGCOD
   AND CT.CITAMBCENASICOD = '{cas}'
"""
    conn = None
    try:
        conn = _connect()
        return pd.read_sql(sql, conn)
    except Exception as e:
        print(f"[tramas] query_b2 error: {e}")
        return pd.DataFrame(columns=COLS_B2)
    finally:
        if conn:
            conn.close()


# ── Validación ────────────────────────────────────────────────────────────────
def _validar(ini, fin, cas):
    if not ini or not fin or not cas:
        return 'Complete todos los campos: fecha inicio, fecha fin y centro asistencial.'
    if pd.to_datetime(fin) < pd.to_datetime(ini):
        return 'La fecha fin no puede ser anterior a la fecha inicio.'
    if (pd.to_datetime(fin) - pd.to_datetime(ini)).days > 31:
        return 'El rango de fechas no puede ser mayor a 31 días.'
    return None


# ── App principal ─────────────────────────────────────────────────────────────
def create_dash_app(flask_app, url_base_pathname='/tramas_embed/'):

    # ── Paleta de colores (igual que el resto de dashboards) ─────────────────
    BRAND       = "#0064AF"
    BRAND_SOFT  = "#D7E9FF"
    CARD_BG     = "#FFFFFF"
    TEXT        = "#1C1F26"
    MUTED       = "#6B7280"
    BORDER      = "#E5E7EB"
    FONT        = "Inter, Segoe UI, Calibri, sans-serif"

    CARD_STYLE = {
        "border": f"1px solid {BORDER}",
        "borderRadius": "14px",
        "backgroundColor": CARD_BG,
        "boxShadow": "0 10px 24px rgba(0,0,0,0.08)",
        "padding": "6px",
    }
    CARD_BODY_STYLE = {
        "padding": "18px",
        "background": "linear-gradient(180deg, #ffffff 0%, #f9fbff 100%)",
        "borderRadius": "12px",
    }
    CONTROL_BAR_STYLE = {
        "display": "flex",
        "alignItems": "center",
        "flexWrap": "wrap",
        "gap": "12px",
        "marginBottom": "18px",
        "backgroundColor": CARD_BG,
        "border": f"1px solid {BORDER}",
        "padding": "14px 16px",
        "borderRadius": "14px",
        "boxShadow": "0 4px 10px rgba(0,0,0,0.05)",
        "position": "relative",
        "zIndex": 1100,
        "width": "100%",
    }
    BTN_SEARCH = {
        "backgroundColor": BRAND, "borderColor": BRAND,
        "padding": "8px 16px", "fontFamily": FONT, "fontWeight": "600",
        "borderRadius": "8px", "boxShadow": "0 4px 10px rgba(0,100,175,0.2)",
    }
    BTN_DOWNLOAD = {
        "backgroundColor": "#28a745", "borderColor": "#28a745",
        "padding": "8px 16px", "fontFamily": FONT, "fontWeight": "600",
        "borderRadius": "8px", "boxShadow": "0 4px 10px rgba(40,167,69,0.18)",
    }
    TABLE_CELL = {
        "textAlign": "left", "fontFamily": FONT, "padding": "6px 10px",
        "height": "auto", "maxWidth": "160px", "whiteSpace": "normal",
        "color": TEXT, "fontSize": "13px",
    }
    TABLE_HEADER = {
        "backgroundColor": BRAND, "fontWeight": "700",
        "color": "white", "fontFamily": FONT, "fontSize": "13px",
    }
    TABLE_STRIPE = [{"if": {"row_index": "odd"}, "backgroundColor": "#F4FAFD"}]

    external_stylesheets = [
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
    ]

    assets_path = os.path.join(os.path.dirname(__file__), "assets")
    assets_url_path = f"{url_base_pathname.rstrip('/')}/assets"
    app_name = f"dash_{url_base_pathname.strip('/').replace('/', '_') or 'tramas'}"

    dash_app = Dash(
        name=app_name,
        server=flask_app,
        url_base_pathname=url_base_pathname,
        assets_folder=assets_path,
        assets_url_path=assets_url_path,
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
    )
    dash_app.title = "SIEST - Tramas B1-B2"

    options, codmap = _get_options()

    TABS = [
        {'label': 'TABLA B1', 'value': 'b1', 'key': 'b1'},
        {'label': 'TABLA B2', 'value': 'b2', 'key': 'b2'},
    ]
    TAB_SECTION_STYLE = {'width': '100%', 'transition': 'opacity 0.2s ease'}

    # ── Agregación para exportación ──────────────────────────────────────────
    def _agregar(df, tipos_no_medicas):
        _COLS_OUT = ['PERIODO', 'COD_IPRESS', 'COD_UGIPRESS', 'SEXO', 'GETAREO',
                     'ATEMEDICAS', 'ATENNOMEDICAS', 'ATENDIDOS']
        if df.empty:
            return pd.DataFrame(columns=_COLS_OUT)
        agg = (
            df.groupby(['PERIODO', 'CENTRO', 'SEXO', 'GETAREO'])
            .agg(
                ATEMEDICAS   =('ORIGEN_TIPO', lambda x: (x == 'ATENME').sum()),
                ATENNOMEDICAS=('ORIGEN_TIPO', lambda x: x.isin(tipos_no_medicas).sum()),
                ATENDIDOS    =('PACSECNUM',   'nunique'),
            )
            .reset_index()
        )
        agg['COD_IPRESS']  = agg['CENTRO'].astype(str).map(lambda c: codmap.get(c, ('', ''))[0])
        agg['COD_UGIPRESS'] = agg['CENTRO'].astype(str).map(lambda c: codmap.get(c, ('', ''))[1])
        return agg[_COLS_OUT]

    def _agregar_b2(df):
        _COLS_OUT = ['PERIODO', 'COD_IPRESS', 'COD_UGIPRESS', 'SEXO', 'GETAREO',
                     'DIAGNOSTICO', 'ATENDIDOS']
        if df.empty:
            return pd.DataFrame(columns=_COLS_OUT)
        agg = (
            df.groupby(['PERIODO', 'CENTRO', 'SEXO', 'GETAREO', 'CODDX'])
            .agg(ATENDIDOS=('PACSECNUM', 'count'))
            .reset_index()
            .rename(columns={'CODDX': 'DIAGNOSTICO'})
        )
        agg['COD_IPRESS']  = agg['CENTRO'].astype(str).map(lambda c: codmap.get(c, ('', ''))[0])
        agg['COD_UGIPRESS'] = agg['CENTRO'].astype(str).map(lambda c: codmap.get(c, ('', ''))[1])
        return agg[_COLS_OUT]

    # ── Helpers de renderizado ────────────────────────────────────────────────
    def _empty_msg(msg, icon="bi-table"):
        return html.Div([
            html.I(className=f"bi {icon}",
                   style={"fontSize": "52px", "color": MUTED, "marginBottom": "14px"}),
            html.H5(msg, style={"color": TEXT, "fontFamily": FONT}),
        ], style={
            "textAlign": "center", "padding": "50px",
            "backgroundColor": CARD_BG, "borderRadius": "14px",
            "boxShadow": "0 10px 24px rgba(0,0,0,0.06)",
        })

    def _render_table(table_id, cols, df):
        if df.empty:
            return _empty_msg("No se encontraron datos para los criterios seleccionados.",
                              "bi-inbox")
        return dbc.Card(
            dbc.CardBody([
                html.Div([
                    html.I(className="bi bi-grid-3x3-gap-fill me-2",
                           style={"color": BRAND, "fontSize": "16px"}),
                    html.Span(f"Muestra de datos — {len(df):,} filas totales · mostrando primeras 20",
                              style={"fontFamily": FONT, "fontSize": "13px",
                                     "color": MUTED, "fontWeight": "500"}),
                ], style={"display": "flex", "alignItems": "center", "marginBottom": "12px"}),
                dash_table.DataTable(
                    id=table_id,
                    columns=[{"name": c, "id": c} for c in cols],
                    data=df.head(20).to_dict("records"),
                    style_table={"overflowX": "auto"},
                    page_size=20,
                    style_cell=TABLE_CELL,
                    style_header=TABLE_HEADER,
                    style_cell_conditional=[
                        {"if": {"column_id": c},
                         "minWidth": "90px", "width": "110px",
                         "maxWidth": "180px", "textAlign": "center"}
                        for c in cols
                    ],
                    style_data_conditional=TABLE_STRIPE,
                ),
            ], style=CARD_BODY_STYLE),
            style=CARD_STYLE,
        )

    def _control_bar(pfx):
        return html.Div([
            html.I(className="bi bi-calendar-range",
                   style={"fontSize": "20px", "color": BRAND, "marginRight": "4px"}),
            dcc.DatePickerSingle(
                id=f"{pfx}-ini", display_format="DD/MM/YYYY",
                placeholder="Fecha inicio",
                className="date-picker-custom",
                style={"zIndex": 2000},
            ),
            dcc.DatePickerSingle(
                id=f"{pfx}-fin", display_format="DD/MM/YYYY",
                placeholder="Fecha fin",
                className="date-picker-custom",
                style={"zIndex": 2000},
            ),
            html.I(className="bi bi-hospital ms-2",
                   style={"fontSize": "20px", "color": BRAND}),
            dcc.Dropdown(
                id=f"{pfx}-cas", options=options,
                placeholder="Centro asistencial",
                optionHeight=48,
                style={"minWidth": "280px", "fontFamily": FONT,
                       "position": "relative", "zIndex": 1500},
            ),
            dbc.Button(
                [html.I(className="bi bi-search me-2"), "Buscar"],
                id=f"{pfx}-btn", color="primary",
                style=BTN_SEARCH,
            ),
            dcc.Loading(
                id=f"{pfx}-loading-dl",
                type="default",
                children=html.Div([
                    dbc.Button(
                        [html.I(className="bi bi-download me-2"), "Exportar Excel"],
                        id=f"{pfx}-dl-btn", n_clicks=0, color="success",
                        style=BTN_DOWNLOAD,
                    ),
                    dcc.Download(id=f"{pfx}-dl"),
                ]),
            ),
            dbc.Button(
                [html.I(className="bi bi-arrow-left me-1"), "Volver"],
                id=f"{pfx}-back", color="secondary", outline=True,
                href="javascript:history.back();", external_link=True,
                style={"marginLeft": "auto", "padding": "8px 14px",
                       "fontFamily": FONT, "borderRadius": "8px"},
            ),
        ], style=CONTROL_BAR_STYLE)

    def _tab_content(pfx):
        return dbc.Container([
            _control_bar(pfx),
            dbc.Alert(id=f"{pfx}-alert", is_open=False, dismissable=True,
                      color="danger", style={"fontFamily": FONT, "borderRadius": "10px"}),
            dcc.Loading(
                id=f"{pfx}-loading", type="default",
                children=html.Div(
                    id=f"{pfx}-output",
                    children=_empty_msg(
                        "Seleccione un rango de fechas, un centro asistencial y haga clic en Buscar.",
                        "bi-search"
                    ),
                ),
            ),
        ], fluid=True, className="px-0")

    # ── Layout con serve_layout (autentica) ───────────────────────────────────
    def serve_layout():
        if not has_request_context():
            return html.Div()

        if not getattr(current_user, "is_authenticated", False):
            return html.Div([
                html.H3("No autenticado", style={"fontFamily": FONT}),
                html.P("Debes iniciar sesión para ver este módulo.",
                       style={"fontFamily": FONT, "color": MUTED}),
                dbc.Button("Volver", color="primary",
                           href="javascript:history.back();", external_link=True,
                           style={"marginTop": "12px", "borderRadius": "8px"}),
            ], style={"textAlign": "center", "padding": "80px"})

        header = html.Div([
            html.Img(
                src=dash_app.get_asset_url("logo.png"),
                style={"width": "110px", "height": "55px",
                       "objectFit": "contain", "marginRight": "20px"},
            ),
            html.Div([
                html.Div([
                    html.I(className="bi bi-file-earmark-spreadsheet-fill",
                           style={"fontSize": "30px", "color": BRAND, "marginRight": "12px"}),
                    html.H2("Tramas B1 y B2 — SUSALUD",
                            style={"color": BRAND, "fontFamily": FONT,
                                   "fontSize": "24px", "margin": "0", "fontWeight": "700"}),
                ], style={"display": "flex", "alignItems": "center"}),
                html.Div([
                    html.Span(
                        [html.I(className="bi bi-database-check me-1"),
                         "Tablas agregadas ESSI"],
                        style={
                            "backgroundColor": BRAND_SOFT, "color": BRAND,
                            "fontFamily": FONT, "fontSize": "11px", "fontWeight": "600",
                            "padding": "3px 10px", "borderRadius": "999px",
                            "display": "inline-flex", "alignItems": "center", "gap": "4px",
                        },
                    ),
                    html.Span("Sistema de Gestión Estadística",
                              style={"color": MUTED, "fontFamily": FONT, "fontSize": "12px"}),
                ], style={"display": "flex", "alignItems": "center",
                          "gap": "10px", "marginTop": "6px"}),
            ], style={"display": "flex", "flexDirection": "column", "justifyContent": "center"}),
        ], style={
            "display": "flex", "alignItems": "center",
            "padding": "16px 20px", "backgroundColor": CARD_BG,
            "borderRadius": "14px", "boxShadow": "0 8px 20px rgba(0,0,0,0.08)",
            "gap": "20px", "marginBottom": "20px",
        })

        tabs = html.Div([
            dcc.Store(id='active-tab-tramas', data='b1'),
            html.Div([
                dbc.Button(
                    html.Span(t['label'], className='dashboard-nav-btn-label'),
                    id={'type': 'tab-nav-tramas', 'value': t['value']},
                    color='light',
                    className='dashboard-nav-btn dashboard-nav-btn--active' if i == 0 else 'dashboard-nav-btn',
                    n_clicks=0,
                    style={'minWidth': '160px'},
                )
                for i, t in enumerate(TABS)
            ], className='dashboard-nav-bar'),
            html.Div([
                html.Div(
                    _tab_content(t['key']),
                    id=f"tab-{t['key']}-content",
                    className='dashboard-tab-section',
                    style={**TAB_SECTION_STYLE, 'display': 'block' if i == 0 else 'none'},
                )
                for i, t in enumerate(TABS)
            ], className='dashboard-tab-content-area'),
        ], className='dashboard-tab-wrapper')

        return dbc.Container([
            html.Div(style={"height": "16px"}),
            header,
            tabs,
            html.Div(style={"height": "32px"}),
        ], fluid=True, style={
            "backgroundImage": "url('/static/76824.jpg')",
            "backgroundSize": "cover",
            "backgroundPosition": "center center",
            "backgroundRepeat": "no-repeat",
            "backgroundAttachment": "fixed",
            "minHeight": "100vh",
            "paddingTop": "16px",
            "paddingBottom": "32px",
        })

    dash_app.layout = serve_layout

    # ── Callbacks B1 ─────────────────────────────────────────────────────────
    @dash_app.callback(
        Output("b1-output", "children"),
        Output("b1-alert", "children"),
        Output("b1-alert", "is_open"),
        Input("b1-btn", "n_clicks"),
        State("b1-ini", "date"),
        State("b1-fin", "date"),
        State("b1-cas", "value"),
        prevent_initial_call=True,
    )
    def buscar_b1(n, ini, fin, cas):
        if not n:
            raise PreventUpdate
        err = _validar(ini, fin, cas)
        if err:
            return _empty_msg("Corrija los parámetros de búsqueda.",
                              "bi-exclamation-circle"), err, True
        df = _query_b1(ini, fin, cas)
        return _render_table("b1-table", COLS_B1, df), None, False

    @dash_app.callback(
        Output("b1-dl", "data"),
        Output("b1-alert", "children", allow_duplicate=True),
        Output("b1-alert", "is_open", allow_duplicate=True),
        Input("b1-dl-btn", "n_clicks"),
        State("b1-ini", "date"),
        State("b1-fin", "date"),
        State("b1-cas", "value"),
        prevent_initial_call=True,
    )
    def descargar_b1(n, ini, fin, cas):
        if not n:
            raise PreventUpdate
        err = _validar(ini, fin, cas)
        if err:
            return None, err, True
        df = _query_b1(ini, fin, cas)
        return dcc.send_data_frame(_agregar(df, ['ATENOME', 'ATEODON']).to_excel, filename="DATA_B1.xlsx", index=False, engine='openpyxl'), None, False

    # ── Callbacks B2 ─────────────────────────────────────────────────────────
    @dash_app.callback(
        Output("b2-output", "children"),
        Output("b2-alert", "children"),
        Output("b2-alert", "is_open"),
        Input("b2-btn", "n_clicks"),
        State("b2-ini", "date"),
        State("b2-fin", "date"),
        State("b2-cas", "value"),
        prevent_initial_call=True,
    )
    def buscar_b2(n, ini, fin, cas):
        if not n:
            raise PreventUpdate
        err = _validar(ini, fin, cas)
        if err:
            return _empty_msg("Corrija los parámetros de búsqueda.",
                              "bi-exclamation-circle"), err, True
        df = _query_b2(ini, fin, cas)
        return _render_table("b2-table", COLS_B2, df), None, False

    @dash_app.callback(
        Output("b2-dl", "data"),
        Output("b2-alert", "children", allow_duplicate=True),
        Output("b2-alert", "is_open", allow_duplicate=True),
        Input("b2-dl-btn", "n_clicks"),
        State("b2-ini", "date"),
        State("b2-fin", "date"),
        State("b2-cas", "value"),
        prevent_initial_call=True,
    )
    def descargar_b2(n, ini, fin, cas):
        if not n:
            raise PreventUpdate
        err = _validar(ini, fin, cas)
        if err:
            return None, err, True
        df = _query_b2(ini, fin, cas)
        return dcc.send_data_frame(_agregar_b2(df).to_excel, filename="DATA_B2.xlsx", index=False, engine='openpyxl'), None, False

    # ── Callbacks de navegación por tabs ─────────────────────────────────────
    @dash_app.callback(
        Output('active-tab-tramas', 'data'),
        Input({'type': 'tab-nav-tramas', 'value': ALL}, 'n_clicks'),
        State('active-tab-tramas', 'data'),
        prevent_initial_call=True,
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
        Output({'type': 'tab-nav-tramas', 'value': ALL}, 'className'),
        Input('active-tab-tramas', 'data'),
    )
    def highlight_active_button(active_value):
        return [
            'dashboard-nav-btn dashboard-nav-btn--active' if t['value'] == active_value else 'dashboard-nav-btn'
            for t in TABS
        ]

    @dash_app.callback(
        [Output(f"tab-{t['key']}-content", 'style') for t in TABS],
        Input('active-tab-tramas', 'data'),
    )
    def toggle_tab_visibility(active_value):
        return [
            {**TAB_SECTION_STYLE, 'display': 'block' if t['value'] == active_value else 'none'}
            for t in TABS
        ]

    return dash_app
