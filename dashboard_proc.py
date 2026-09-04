import os

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, no_update
from flask import has_request_context
from flask_login import current_user

import secure_code as sc



def create_dash_app(flask_app, url_base_pathname='/dashboard_proc_embed/'):
    external_stylesheets = [
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
    ]

    BRAND = "#0064AF"
    BRAND_SOFT = "#D7E9FF"
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

    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    anio_options = [{'label': y, 'value': y} for y in ['2025', '2026']]
    valores = [f"{i:02d}" for i in range(1, 13)]
    df_period = pd.DataFrame({'mes': meses, 'periodo': valores})
    tipo_asegurado_options = [
        {'label': t, 'value': t} for t in ['Asegurado', 'No Asegurado', 'Todos']
    ]

    DEFAULT_TIPO = 'Todos'
    TIPO_SQL = {
        'Asegurado': "('1')",
        'No Asegurado': "('2')",
        'Todos': "('1','2')",
    }

    def resolve_tipo(selection):
        return TIPO_SQL.get(selection, TIPO_SQL[DEFAULT_TIPO])

    # ========== CONFIGURACIÓN DE TARJETAS ==========
    # Para agregar una tarjeta nueva, añade una tupla a esta lista:
    #   ("Título de la tarjeta", ("COD1", "COD2", ...), "bi-icono-bootstrap", "#COLOR_HEX")
    # Para agregar un separador de sección usa un dict: {"section": "Nombre sección"}
    TARJETAS = [
        (
            "Ablación Transcatérer",
            ("93651","93652","93653","93654"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Administración de Oxígeno por Casco Cefálico (OXIHOOD)",
            ("94799.02"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Angiografía Cerebral",
            ("36221","36222","36223","36224","36225","36228","36251",
             "61254","61257","61623","61630","61635","61640","64627"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Angiografía Retinal",
            ("92235","92227","92250","92300"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Angioplastia con Balón",
            ("35456","35474","92981","92982"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Angioplastia Stent Metálico",
            ("37238"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Audiometría",
            ("92552","92553","92556","92583","92551","92555","92557","92560","92561"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Biopsia Endomiocárdica",
            ("93505"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Cardio Holter",
            ("93224","93225","93233"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Cardioversión Eléctrica Electiva",
            ("92960","92961"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Cateterismo + Medición de CIA",
            ("93451"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Cateterismo Cardíaco",
            ("36013","36014","93455","93456","93458",
             "93503","93556","93562","93452","93454","93544"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Colposcopía",
            ("56820","57420","57454","57455","58110","56821","57421","57452","57456","57461"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Cono Frío",
            ("57520"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Cono LEEP",
            ("57522"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Crioterapia",
            ("17340"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Dilatación con Protesis de Coartación de Aorta",
            ("35472"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Ecocardiografía Stress",
            ("93350","93351"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Ecocardiografía Transesofágica",
            ("93312","93313","93314","93315","93317"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Ecocardiografía Transtorácica",
            ("93306","93307","93308","93320","93882.06","93321"),
            "bi-activity",
            "#0064AF",
        ),

        (
            "Ecografía",
            ("76512","76604.02","76700.02","76811","76830","93976.01",
            "76513","76604.04","76705","76812","76856","93976.03",
            "76514","76645","76706","76813","76872","93985",
            "76536","76646","76802","76815","76880","93990",
            "76604","76700","76805","76816","76999.01","76820.01",
            "76700.01","76810",	"76817","93971.01"		 
            ),
            "bi-activity",
            "#0064AF",
        ),

        (
            "Electrocardiografía",
            ("93000","93005","93010"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Electroencefalografía",
            ("95812","95812.02","95813","95816","95819","95822"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Electromiografía y Velocidad de Conducción",
            ("95860","95861","95863","95864","95872","95885","95886","95887","96867","95877",
             "95900","95903","95904","95905","95907","95908","95909","95910","95937"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Endoscopía Diagnóstica no Digestiva",
            ("31231","31505","31575","31622","31623","45338","31624","31625","31627","31628","31632",
             "91010","31633","31641","31645","31646","45334","45337","45379","46614","49082","90901",
             "90911","91038","91111","91122","91212","92511","96366"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Endoscopía Digestiva Diagnóstica",
            ("43234","43239","44388","44391","45358","45359","45378","45380","91200","91202"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Espirometría",
            ("94060","94010","94012.01","94315"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Estimulación Eléctrica Cerebral",
            ("95979","95975","95978","95974","95971"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Estudios Fisiológicos (Electrofisiológicos)",
            ("93613","93618","93619","93623","93609"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Implantación de Cardiovector Desfibrilador Automático",
            ("33215","33225","33263","33240","33244","33249"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Instalación y Mantenimiento de CPAC de burbuja",
            ("94660"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Instalación y Mantenimiento del Cateter Venoso Central de Inserción Periferica (PICC)",
            ("36568","36569"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Laparoscopía Diagnóstica",
            ("49320"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Laserterapia Ocular",
            ("92136","92250","92286","92287","96905"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Marcapaso Definitivo Bicameral",
            ("33208","33213","33214","33228","33230"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Marcapaso Definitivo para Resincronización",
            ("33221","33229"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Marcapaso Definitivo Unicameral",
            ("33206","33207","33212","33227","93612","33233"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Marcapaso Transitorio",
            ("92953","33211"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Oclusión de Defecto Septal Interauricular",
            ("93580"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Oclusión de Defecto Septal Interventricular",
            ("93581"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Perimetría (Campimetría)",
            ("92081","92082","92083"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Procedimiento Corneal Instrumentado",
            ("92025","92100","92137"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Procedimientos Médicos de Rehabilitación",
            ("1983","1984","1985","23929","26011","26989","27427","28001","29220","29240","29260","29280",
             "29530","29540","36513","36514","62271","92020","92548","93015","96008","96009","97784","97785",
             "97786","97125","97003","99187","99193","99194","99199","99207","99210","99214","98889","99489",
             "36516","50590","28890","62311","64418","64445","64450","64470","64475","64612","64613","64722",
             "90287","90885","92015","92506","29799","31299","93668","93750","95851","95852","95860","96001",
             "96004","96110","96111","97010","97014","97034"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Prueba de Esfuerzo",
            ("93015","93016","93017","93018","93464"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Reserva de Flujo Fraccionado",
            ("93571"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Test de Inclinación",
            ("93660"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Test del Aliento",
            ("83013"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Tomografía de Coherencia Óptica (OCT)",
            ("92132","92133","92134"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Tratamiento del Dolor",
            ("1984.01","1984","20553","27299","62310","62311","64483","64510","90780","96365","96367",
             "97785","97786","97810","99187","99193","99194","99489.02"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Trombólisis Sistémica",
            ("37195"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Ultrasonido Endovascular",
            ("92978"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Urodinamia",
            ("51726","51729","51741"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
        (
            "Valvuloplastia Mitral con Balón",
            ("92987"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Valvuloplastía Pulmonar y/o Aórtica",
            ("92998"),
            "bi-activity",
            "#0064AF",
        ),
        (
            "Video/Epilepsia",
            ("95951"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
        ),
    ]

    # ========== CONFIGURACIÓN DE TARJETAS · IMÁGENES (dssge.dw_lab_*) ==========
    # Misma convención que TARJETAS, pero estas se consultan contra la tabla
    # dssge.dw_lab_{anio}_{periodo} (build_lab_query), no dssge.dw_proc_*.
    IMG_COLOR = "#00AEEF"
    TARJETAS_IMAGENES = [
        (
            "Resonancia Simple",
            ("70540.01", "70540.03", "70544", "70551", "71550.02",
             "72141", "72146", "72148", "72195", "72195.01", "73218.01", "73218.02",
             "73218.04", "73218.05", "73718.01", "73718.02", "73718.03", "73718.04",
             "73721.01", "73721.02", "73721.03", "73725", "74181", "74181.01", "74185",
             "74485.01", "77059"),
            "bi-clipboard2-pulse-fill",
            IMG_COLOR,
        ),
        (
            "Resonancia Magnética - Con Contraste",
            ("70336.02", "70542", "70542.01", "70542.02", "70542.03",
             "70545", "70548", "70551.05", "70552", "71551", "71551.01",
             "71551.02", "72142", "72147", "72149", "72196", "73219.01",
             "73219.02", "73219.03", "73219.04", "73219.05", "73222.01",
             "73222.02", "73222.03", "73719.01", "73719.02", "73719.03",
             "73722.01", "73722.02", "73722.03", "74182", "74182.01", "74485.02", "75553"),
            "bi-clipboard2-pulse-fill",
            IMG_COLOR,
        ),
        (
            "Tomografía Con Contraste",
            ("70460", "70481", "70482.01", "70482.02", "70482.03", "70488.01",
             "70491", "70498", "71260", "72126", "72129", "72132", "72132.01",
             "72191", "72193", "73201", "73201.01", "73201.02", "73201.03",
             "73201.05", "73201.06", "73701.01", "73701.02", "73701.03", "73701.04",
             "73701.05", "74160", "74160.01", "74160.02", "75572", "75574"),
            "bi-clipboard2-pulse-fill",
            IMG_COLOR,
        ),
        (
            "Tomografía Sin Contraste",
            ("70450", "70480.01", "70480.02", "70480.03", "70480.04", "70480.05",
             "70486.01", "70490", "71250", "71250.01", "72125", "72128", "72131",
             "72131.01", "72192", "73200.01", "73200.02", "73200.03", "73200.04",
             "73200.05", "73200.06", "73206", "73700.01", "73700.02", "73700.03",
             "73700.04", "73700.05", "73706", "74150.01", "75571"),
            "bi-clipboard2-pulse-fill",
            IMG_COLOR,
        ),
        (
            "Doppler Vascular",
            ("76776", "76831", "93882", "93922", "93926", "93965",
             "93971", "93975", "93976", "93980"),
            "bi-activity",
            IMG_COLOR,
        ),
        (
            "Ecografía",
            ("76536", "76536.01", "76536.03", "76604", "76604.02", "76645", "76700",
             "76700.01", "76700.02", "76770", "76770.01", "76775", "76775.01", "76778",
             "76800", "76801", "76802", "76805", "76813", "76814", "76817", "76830",
             "76856", "76870", "76872", "76873", "76880", "76880.04", "76880.05", "76881",
             "76882", "76885", "76886", "76937", "76970", "76999.01", "78821"),
            "bi-clipboard2-pulse-fill",
            IMG_COLOR,
        ),
        (
            "Rayos X / Radiografía",
            ("70110", "70140", "70150", "70240", "70260", "70300", "70328", "70330",
             "70355", "70360", "70370", "71010", "71010.01", "71022", "71035",
             "71035.01", "71101", "71110", "71130", "72010", "72020", "72040.01",
             "72040.03", "72067", "72068", "72069", "72074", "72081", "72082", "72090",
             "72100", "72170", "72190", "72202", "72220", "73011", "73020", "73030", "73050",
             "73060", "73070", "73080", "73090", "73092", "73100", "73110", "73120", "73130",
             "73131", "73140", "73500", "73520", "73540", "73550", "73560", "73562", "73565",
             "73567", "73590", "73592", "73600", "73610", "73615", "73620", "73630", "73650",
             "73660", "74000", "74000.01", "74010", "74020", "74020.01", "74022", "74210",
             "74210.01", "74220", "74230", "74241", "74246", "74247.01", "74247.02", "74249",
             "74250", "74251", "74270", "74280", "74305", "74320", "74363", "74425", "74430",
             "74450", "74455", "74475", "74740", "74930", "75630", "75671", "75710", "75716",
             "75726", "75743", "75822", "75825", "75827", "75885", "75894", "75894.01", "75940",
             "75962", "75978", "75980", "75982", "75984", "76080", "76096", "76140", "76499",
             "76934", "76942", "77031", "77071", "77075", "77076"),
            "bi-clipboard2-pulse-fill",
            IMG_COLOR,
        ),
        (
            "Mamografía",
            ("77055", "77056"),
            "bi-clipboard2-pulse-fill",
            IMG_COLOR,
        ),
        (
            "Gammagrafía / SPECT",
            ("76390", "78031", "78079", "78320", "78362",
             "78363", "78364", "78451", "78501", "78514",
             "78521", "78528", "78585"),
            "bi-activity",
            IMG_COLOR,
        ),
        (
            "PET / Tomografía por Emisión de Positrones",
            ("78608", "78810", "78811",
             "78812", "78813", "78814", "78815"),
            "bi-activity",
            IMG_COLOR,
        ),
    ]

    # ========== DASH INSTANCE ==========
    app_name = f"dash_{url_base_pathname.strip('/').replace('/', '_') or 'proc'}"
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
    dash_app.title = "SIEST - Procedimientos"

    # ========== HELPERS UI ==========
    def render_card(title, value, border_color, subtitle_text):
        return dbc.Card(
            dbc.CardBody([
                html.H5(title, className="card-title", style={
                    'color': BRAND, 'marginBottom': '6px',
                    'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.1px'
                }),
                html.H2(value, style={
                    'fontWeight': '800', 'color': TEXT, 'fontSize': '34px',
                    'margin': 0, 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.2px'
                }),
                html.P(subtitle_text, style={
                    'fontSize': '12px', 'color': MUTED,
                    'margin': '6px 0 0 0', 'fontFamily': FONT_FAMILY
                })
            ], style=CARD_BODY_STYLE),
            style={**CARD_STYLE, "borderLeft": f"5px solid {border_color}",
                   "height": "100%", "width": "100%"}
        )

    def render_inline_table(dataframe):
        SIDE_COLOR = "#00AEEF"
        heading = html.Div([
            html.H6(
                "Servicio",
                className="fw-semibold",
                style={'fontSize': '11px', 'color': BRAND, 'letterSpacing': '0.6px', 'marginBottom': '0px', 'display': 'inline-block', 'marginRight': '8px'}
            ),
            html.H6(
                "Área Hosp.",
                className="fw-semibold",
                style={'fontSize': '11px', 'color': BRAND, 'letterSpacing': '0.6px', 'marginBottom': '0px', 'display': 'inline-block'}
            )
        ], style={'marginBottom': '8px'})
        if dataframe.empty:
            return dbc.Card(
                dbc.CardBody(
                    [heading, html.P("Sin registros", className="text-muted mb-0",
                                     style={'fontFamily': FONT_FAMILY, 'fontSize': '12px'})],
                    style={**CARD_BODY_STYLE, 'padding': '14px'}
                ),
                style={**CARD_STYLE, "borderLeft": f"5px solid {SIDE_COLOR}", "height": "100%"}
            )
        table_head = html.Thead([
            html.Tr([
                html.Th('Código', style={'padding': '6px 8px', 'fontSize': '11px', 'color': BRAND, 'fontWeight': '600', 'borderBottom': f'2px solid {BORDER}'}),
                html.Th('Procedimiento', style={'padding': '6px 8px', 'fontSize': '11px', 'color': BRAND, 'fontWeight': '600', 'borderBottom': f'2px solid {BORDER}'}),
                html.Th('Servicio', style={'padding': '6px 8px', 'fontSize': '11px', 'color': BRAND, 'fontWeight': '600', 'borderBottom': f'2px solid {BORDER}'}),
                html.Th('Área Hosp.', style={'padding': '6px 8px', 'fontSize': '11px', 'color': BRAND, 'fontWeight': '600', 'borderBottom': f'2px solid {BORDER}'}),
                html.Th('Cantidad', style={'textAlign': 'right', 'padding': '6px 8px', 'fontSize': '11px', 'color': BRAND, 'fontWeight': '600', 'borderBottom': f'2px solid {BORDER}'})
            ])
        ])
        table_body = html.Tbody([
            html.Tr([
                html.Td(str(r.get('codproced') or '-'),
                        style={'padding': '4px 8px', 'lineHeight': '1.1', 'fontSize': '11px', 'fontFamily': 'monospace'}),
                html.Td(str(r.get('cpms') or '-')[:20] + ('...' if len(str(r.get('cpms') or '')) > 20 else ''),
                        title=str(r.get('cpms') or '-'),
                        style={'padding': '4px 8px', 'lineHeight': '1.1', 'fontSize': '11px', 'cursor': 'help'}),
                html.Td(str(r.get('servicio') or 'Sin descripción'),
                        style={'padding': '4px 8px', 'lineHeight': '1.1', 'fontSize': '11px'}),
                html.Td(str(r.get('area_hosp') or '-'),
                        style={'padding': '4px 8px', 'lineHeight': '1.1', 'fontSize': '11px'}),
                html.Td(
                    '-' if pd.isna(r.get('counts')) else f"{r['counts']:,.0f}",
                    style={'textAlign': 'right', 'padding': '4px 8px', 'lineHeight': '1.1', 'fontSize': '11px', 'fontWeight': '600'}
                )
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
            style={**CARD_STYLE, "borderLeft": f"5px solid {SIDE_COLOR}", "height": "100%"}
        )

    def render_area_table(dataframe):
        """Desglose simple Área hospitalaria + Conteo, solo para las
        tarjetas de imágenes (TARJETAS_IMAGENES)."""
        SIDE_COLOR = "#00AEEF"
        heading = html.H6(
            "Área Hosp.",
            className="fw-semibold",
            style={'fontSize': '11px', 'color': BRAND, 'letterSpacing': '0.6px', 'marginBottom': '8px'}
        )
        if dataframe.empty:
            return dbc.Card(
                dbc.CardBody(
                    [heading, html.P("Sin registros", className="text-muted mb-0",
                                     style={'fontFamily': FONT_FAMILY, 'fontSize': '12px'})],
                    style={**CARD_BODY_STYLE, 'padding': '14px'}
                ),
                style={**CARD_STYLE, "borderLeft": f"5px solid {SIDE_COLOR}", "height": "100%"}
            )
        table_head = html.Thead([
            html.Tr([
                html.Th('Área Hosp.', style={'padding': '6px 8px', 'fontSize': '11px', 'color': BRAND, 'fontWeight': '600', 'borderBottom': f'2px solid {BORDER}'}),
                html.Th('Cantidad', style={'textAlign': 'right', 'padding': '6px 8px', 'fontSize': '11px', 'color': BRAND, 'fontWeight': '600', 'borderBottom': f'2px solid {BORDER}'})
            ])
        ])
        table_body = html.Tbody([
            html.Tr([
                html.Td(str(r.get('area_hosp') or 'Sin área'),
                        style={'padding': '4px 8px', 'lineHeight': '1.1', 'fontSize': '11px'}),
                html.Td(
                    '-' if pd.isna(r.get('counts')) else f"{r['counts']:,.0f}",
                    style={'textAlign': 'right', 'padding': '4px 8px', 'lineHeight': '1.1', 'fontSize': '11px', 'fontWeight': '600'}
                )
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
            style={**CARD_STYLE, "borderLeft": f"5px solid {SIDE_COLOR}", "height": "100%"}
        )

    # ========== DB ==========
    def create_connection():
        from extensions import get_dw_engine
        return get_dw_engine()

    def fecha_act(engine):
        if engine is None:
            return None
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                row = conn.execute(
                    text("SELECT TO_CHAR(MIN(fecha_act), 'DD/MM/YYYY HH24:MI:SS') AS fecha_act FROM dwsge.fecha_act;")
                ).mappings().first()
        except Exception as exc:
            print(f"[Dashboard PROC] fecha_act error: {exc}")
            return None
        return (row.get('fecha_act') or row.get('fecha_Act')) if row else None

    # ========== QUERY ==========
    def build_proc_query(anio_str, periodo, codcas, codasegu_clause, codes):
        codes_str = "'" + "','".join(codes) + "'"
        return f"""
            WITH base AS (
                SELECT DISTINCT
                    doc_paciente,
                    cod_cpms,
                    fec_oper
                FROM dssge.dwe_centro_quirurgico_{anio_str}_{periodo}
                WHERE cod_sala IS NOT NULL
                  AND cod_cpms IN ({codes_str})
                  AND cod_centro = '{codcas}'
            ),
            union_proc AS (
                SELECT
                    cod_oricentro, cod_centro, c.cenasides, anio, periodo, cod_servicio, s.servhosdescor as servicio,
                    dni_medico, doc_paciente, tip_doc_paciente, anio_edad, sexo,
                    cod_tipo_seguro, cod_tipo_parentesco, cod_tipo_paciente,
                    fecha_aten, acto_med, codproced, cantproced::numeric, ar.arehosdes as area_hosp,
                    cod_actividad, a.actdes as actividad, cod_subactividad, cp.cpsdes AS cpms
                FROM dssge.dw_proc_{anio_str}_{periodo} as pc
                LEFT JOIN dwsge.sgss_cmsho10 as s ON s.servhoscod = pc.cod_servicio
                LEFT JOIN dwsge.sgss_cmcpp10 as cp ON cp.cpscod = pc.codproced
                LEFT JOIN dwsge.sgss_cmcas10 as c ON c.cenasicod = pc.cod_centro AND c.oricenasicod = pc.cod_oricentro
                LEFT JOIN dwsge.sgss_cmact10 as a ON a.actcod = pc.cod_actividad
                LEFT JOIN dwsge.sgss_cmaho10 as ar ON ar.arehoscod = pc.area_hosp
                WHERE cod_centro = '{codcas}'
                  AND codproced IN ({codes_str})
                  AND cod_actividad in ('96','91')
                  AND pc.grupo_ocupacional ='01'
                  AND (CASE WHEN cod_tipo_paciente = '4' THEN '2' ELSE '1' END) IN {codasegu_clause}

                UNION ALL

                SELECT
                    cod_oricentro, cod_centro, c.cenasides, anio, periodo, cod_servicio,s.servhosdescor as servicio,
                    dni_medico, doc_paciente, tip_doc_paciente, anio_edad, sexo,
                    cod_tipo_seguro, cod_tipo_parentesco, cod_tipo_paciente,
                    fecha_aten, acto_med, codproced, cantproced::numeric, ar.arehosdes as area_hosp,
                    cod_actividad, a.actdes as actividad, cod_subactividad, cp.cpsdes AS cpms
                FROM dssge.dw_proc_eme_{anio_str}_{periodo} as pc
                LEFT JOIN dwsge.sgss_cmsho10 as s ON s.servhoscod = pc.cod_servicio
                LEFT JOIN dwsge.sgss_cmcpp10 as cp ON cp.cpscod = pc.codproced
                LEFT JOIN dwsge.sgss_cmcas10 as c ON c.cenasicod = pc.cod_centro AND c.oricenasicod = pc.cod_oricentro
                LEFT JOIN dwsge.sgss_cmact10 as a ON a.actcod = pc.cod_actividad
                LEFT JOIN dwsge.sgss_cmaho10 as ar ON ar.arehoscod = pc.area_hosp
                WHERE cod_centro = '{codcas}'
                  AND codproced IN ({codes_str})
                  AND cod_actividad in ('96','91')
                  AND pc.grupo_ocupacional ='01'
                  AND (CASE WHEN cod_tipo_paciente = '4' THEN '2' ELSE '1' END) IN {codasegu_clause}

                UNION ALL

                SELECT
                    cod_oricentro, cod_centro, c.cenasides, anio, periodo, cod_servicio,s.servhosdescor as servicio,
                    dni_medico, doc_paciente, tip_doc_paciente, anio_edad, sexo,
                    cod_tipo_seguro, cod_tipo_parentesco, cod_tipo_paciente,
                    fecha_aten, acto_med, codproced, cantproced::numeric, ar.arehosdes as area_hosp,
                    cod_actividad, a.actdes as actividad, cod_subactividad, cp.cpsdes AS cpms
                FROM dssge.dw_proc_hos_{anio_str}_{periodo} as pc
                LEFT JOIN dwsge.sgss_cmsho10 as s ON s.servhoscod = pc.cod_servicio
                LEFT JOIN dwsge.sgss_cmcpp10 as cp ON cp.cpscod = pc.codproced
                LEFT JOIN dwsge.sgss_cmcas10 as c ON c.cenasicod = pc.cod_centro AND c.oricenasicod = pc.cod_oricentro
                LEFT JOIN dwsge.sgss_cmact10 as a ON a.actcod = pc.cod_actividad
                LEFT JOIN dwsge.sgss_cmaho10 as ar ON ar.arehoscod = pc.area_hosp
                WHERE cod_centro = '{codcas}'
                  AND codproced IN ({codes_str})
                  AND cod_actividad in ('96','91')
                  AND pc.grupo_ocupacional ='01'
                  AND (CASE WHEN cod_tipo_paciente = '4' THEN '2' ELSE '1' END) IN {codasegu_clause}
            )
            SELECT *
            FROM union_proc p
            WHERE NOT EXISTS (
                SELECT 1
                FROM base b
                WHERE b.doc_paciente = p.doc_paciente
                  AND b.cod_cpms     = p.codproced
                  AND b.fec_oper     = p.fecha_aten
            )
        """

    def build_lab_query(anio_str, periodo, codcas, codasegu_clause, codes):
        # OJO: cod_cpms se resuelve a descripcion aparte (ver cpms_desc_map en
        # on_search), NO con un JOIN aca. Un JOIN directo contra
        # dwsge.sgss_cmcpp10 (12,906 filas, sin indice util para el planner)
        # fuerza un Nested Loop que reescanea esa tabla completa por cada fila
        # de dw_lab -> con tarjetas de miles de filas (p.ej. Tomografia) eso
        # solo se midio en ~10-14s. Sin el JOIN, la misma tarjeta baja a
        # ~0.6s. No hay permisos de CREATE INDEX sobre esa tabla compartida
        # (ver dw-app-user-sin-create.md), asi que se evita el problema en vez
        # de intentar resolverlo con un indice.
        codes_str = "'" + "','".join(codes) + "'"
        return f"""
            SELECT DISTINCT ON (acto_med, cod_cpms, fecha_examen)
                anio, periodo, cod_cpms,
                c.cenasides, ar.arehosdes AS area_hosp,
                s.servhosdes AS servicio, a.actdes AS actividad,
                areaexades, acto_med
            FROM dssge.dw_lab_{anio_str}_{periodo}
            LEFT JOIN dwsge.sgss_emaea10 ON cod_arealab = areaexacod AND cod_tipoexamen = tipexacod
            LEFT JOIN dwsge.sgss_cmaho10 ar ON ar.arehoscod = cod_area
            LEFT JOIN dwsge.sgss_cmsho10 s ON s.servhoscod = cod_servicio
            LEFT JOIN dwsge.sgss_cmcas10 c ON cod_oricentro = c.oricenasicod AND cod_centro = c.cenasicod
            LEFT JOIN dwsge.sgss_cmact10 a ON a.actcod = cod_actividad
            WHERE cod_cpms IN ({codes_str})
              AND cod_centro = '{codcas}'
              AND cod_tipoexamen = '1'
              AND (CASE WHEN cod_tipo_paciente = '4' THEN '2' ELSE '1' END) IN {codasegu_clause}
        """

    # ========== LAYOUT ==========
    def serve_layout():
        if not has_request_context():
            return html.Div()

        if not getattr(current_user, "is_authenticated", False):
            return html.Div([
                html.H3('No autenticado'),
                html.P('Debes iniciar sesión para ver el dashboard.'),
                dbc.Button('Volver', color='primary',
                           href='javascript:history.back();', external_link=True,
                           style={'marginTop': '12px'})
            ])

        engine = create_connection()
        fecha_act_value = fecha_act(engine) or "Sin información disponible"

        header = html.Div([
            html.Img(
                src=dash_app.get_asset_url('logo.png'),
                style={'width': '120px', 'height': '60px',
                       'objectFit': 'contain', 'marginRight': '20px'}
            ),
            html.Div([
                html.Div([
                    html.I(className="bi bi-heart-pulse-fill",
                           style={'fontSize': '32px', 'color': BRAND, 'marginRight': '12px'}),
                    html.H2(
                        ["Total Procedimientos Realizados ",
                         html.Span("(En proceso de validación)", style={'color': '#dc3545'})],
                        style={'color': BRAND, 'fontFamily': FONT_FAMILY,
                               'fontSize': '26px', 'margin': '0', 'fontWeight': '700'})
                ], style={'display': 'flex', 'alignItems': 'center'}),
                html.Div([
                    html.Span(
                        [html.I(className="bi bi-clock me-1"), f"Actualizado: {fecha_act_value}"],
                        style={
                            'backgroundColor': BRAND_SOFT, 'color': BRAND,
                            'fontFamily': FONT_FAMILY, 'fontSize': '11px', 'fontWeight': '600',
                            'padding': '3px 10px', 'borderRadius': '999px',
                            'display': 'inline-flex', 'alignItems': 'center', 'gap': '4px',
                        }
                    ),
                    html.Span("Sistema de Gestión Estadística",
                              style={'color': MUTED, 'fontFamily': FONT_FAMILY, 'fontSize': '12px'}),
                ], style={'display': 'flex', 'alignItems': 'center', 'gap': '10px', 'marginTop': '6px'})
            ], style={'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center', 'flex': '1'})
        ], style={
            'display': 'flex', 'alignItems': 'center',
            'padding': '16px 20px', 'backgroundColor': CARD_BG,
            'borderRadius': '14px', 'boxShadow': '0 8px 20px rgba(0,0,0,0.08)', 'gap': '20px'
        })

        control_bar = html.Div([
            html.I(className="bi bi-calendar-week dashboard-control-icon",
                   style={'fontSize': '20px', 'color': BRAND, 'marginRight': '10px'}),
            dcc.Dropdown(id='filter-anio-proc', options=anio_options, placeholder='Año',
                         clearable=True, style={'width': '160px', 'fontFamily': FONT_FAMILY,
                                                'position': 'relative', 'zIndex': 4000}),
            dcc.Dropdown(
                id='filter-periodo-proc',
                options=[{'label': row['mes'], 'value': row['periodo']}
                         for _, row in df_period.iterrows()],
                placeholder='Periodo', clearable=True,
                style={'width': '240px', 'fontFamily': FONT_FAMILY,
                       'position': 'relative', 'zIndex': 1200}
            ),
            dcc.Dropdown(id='filter-tipo-proc', options=tipo_asegurado_options,
                         value=DEFAULT_TIPO, clearable=False,
                         style={'width': '200px', 'fontFamily': FONT_FAMILY,
                                'position': 'relative', 'zIndex': 1200}),
            dbc.Button(
                [html.I(className="bi bi-search me-2"), "Buscar"],
                id='search-button-proc', color='primary', className='dashboard-control-btn',
                style={'backgroundColor': BRAND, 'borderColor': BRAND, 'padding': '8px 12px',
                       'boxShadow': '0 4px 10px rgba(0,100,175,0.2)',
                       'fontFamily': FONT_FAMILY, 'fontWeight': '600', 'borderRadius': '8px'}
            ),
            dcc.Loading(
                id='loading-download-proc',
                type='circle',
                color=BRAND,
                children=[
                    dbc.Button(
                        [html.I(className="bi bi-file-earmark-excel me-2"), "Exportar xlsx"],
                        id='download-btn-proc', color='success',
                        className='dashboard-control-btn',
                        style={'padding': '8px 12px', 'fontFamily': FONT_FAMILY,
                               'fontWeight': '600', 'borderRadius': '8px'}
                    ),
                    dcc.Download(id='download-excel-proc'),
                ],
            ),
            dbc.Button(
                [html.I(className="bi bi-arrow-left me-1"), "Volver"],
                id="btn-volver-proc", color='secondary', outline=True,
                className='dashboard-control-btn dashboard-control-btn-back',
                href='javascript:history.back();', external_link=True,
                style={'marginLeft': 'auto', 'padding': '8px 12px'}
            ),
        ], className='dashboard-control-bar', style={**CONTROL_BAR_STYLE})

        return dbc.Container([
            dcc.Location(id='url-proc', refresh=False),
            html.Div([
                header,
                html.Br(),
                control_bar,
                dbc.Tooltip("Volver", target='btn-volver-proc', placement='bottom', style={'zIndex': 9999}),
                dbc.Tooltip("Buscar datos", target='search-button-proc', placement='bottom', style={'zIndex': 9999}),
                dbc.Tooltip("Descargar todos los registros en Excel", target='download-btn-proc', placement='bottom', style={'zIndex': 9999}),
                dbc.Row([
                    dbc.Col(
                        html.Div(
                            dcc.Loading(
                                className='dashboard-loading-inline',
                                parent_className='dashboard-loading-parent',
                                parent_style={'width': '100%'},
                                type='default',
                                style={'width': '100%'},
                                children=html.Div(id='summary-container-proc')
                            ),
                            className='dashboard-loading-shell'
                        ),
                        width=12
                    )
                ]),
            ], id='main-proc-content'),
        ], fluid=True, style={
            'backgroundImage': "url('/static/76824.jpg')",
            'backgroundSize': 'cover',
            'backgroundPosition': 'center center',
            'backgroundRepeat': 'no-repeat',
            'backgroundAttachment': 'fixed',
            'minHeight': '100vh',
            'paddingTop': '20px',
            'paddingBottom': '20px',
        })

    # ========== CALLBACK BÚSQUEDA ==========
    @dash_app.callback(
        Output('summary-container-proc', 'children'),
        Input('search-button-proc', 'n_clicks'),
        State('filter-periodo-proc', 'value'),
        State('filter-anio-proc', 'value'),
        State('filter-tipo-proc', 'value'),
        State('url-proc', 'pathname')
    )
    def on_search(n_clicks, periodo, anio, tipo_asegurado, pathname):
        if not n_clicks:
            return html.Div()

        codcas_url = pathname.rstrip('/').split('/')[-1] if pathname else None
        codcas = sc.decode_code(codcas_url) if codcas_url else None

        if not periodo or not anio or not codcas:
            return html.Div([
                html.I(className="bi bi-exclamation-circle",
                       style={'fontSize': '64px', 'color': '#ffc107', 'marginBottom': '20px'}),
                html.H4("Información requerida",
                        style={'color': TEXT, 'fontFamily': FONT_FAMILY, 'marginBottom': '10px'}),
                html.P("Seleccione un año, un periodo y asegúrese de tener un centro válido.",
                       style={'color': MUTED, 'fontFamily': FONT_FAMILY})
            ], style={'textAlign': 'center', 'padding': '60px', 'backgroundColor': CARD_BG,
                      'borderRadius': '16px', 'boxShadow': '0 10px 30px rgba(0,0,0,0.08)'})

        from extensions import validate_anio_periodo
        try:
            anio_str, periodo = validate_anio_periodo(anio, periodo)
        except ValueError as _ve:
            return html.Div(f"Parámetros inválidos: {_ve}")

        codasegu_clause = resolve_tipo(tipo_asegurado or DEFAULT_TIPO)

        engine = create_connection()
        if engine is None:
            return html.Div("Error de conexión a la base de datos.")

        try:
            from sqlalchemy import text as sa_text
            with engine.connect() as _conn:
                _row = _conn.execute(
                    sa_text("SELECT cenasides FROM dwsge.sgss_cmcas10 WHERE cenasicod = :cod"),
                    {'cod': codcas}
                ).mappings().first()
            center_label = _row['cenasides'] if _row else codcas
        except Exception:
            center_label = codcas
        subtitle = f"Año {anio_str} | Periodo {periodo} | Centro: {center_label}"

        sections = []
        for item in TARJETAS:
            if isinstance(item, dict):
                continue
            titulo, codes, _, color = item
            try:
                df_card = pd.read_sql(
                    build_proc_query(anio_str, periodo, codcas, codasegu_clause, codes),
                    engine
                )
                if 'cantproced' in df_card.columns:
                    df_card['cantproced'] = pd.to_numeric(
                        df_card['cantproced'], errors='coerce'
                    ).fillna(0)
                total = int(df_card['cantproced'].sum()) if 'cantproced' in df_card.columns else len(df_card)

                if not df_card.empty and 'servicio' in df_card.columns:
                    df_breakdown = (
                        df_card.groupby(['codproced', 'cpms', 'servicio', 'area_hosp'], dropna=False)['cantproced']
                        .sum()
                        .reset_index(name='counts')
                        .sort_values('counts', ascending=False)
                    )
                else:
                    df_breakdown = pd.DataFrame(columns=['codproced', 'cpms', 'servicio', 'area_hosp', 'counts'])
            except Exception:
                total = 0
                df_breakdown = pd.DataFrame(columns=['codproced', 'cpms', 'servicio', 'area_hosp', 'counts'])

            if total == 0:
                continue

            sections.append(
                dbc.Row(
                    [
                        dbc.Col(
                            render_card(titulo, f"{total:,.0f}", color, subtitle),
                            width=12, lg=4,
                            style={'display': 'flex'}
                        ),
                        dbc.Col(
                            html.Div(render_inline_table(df_breakdown), style={'width': '100%'}),
                            width=12, lg=4,
                            style={'display': 'flex'}
                        ),
                    ],
                    justify="center",
                    style={'marginBottom': '10px'}
                )
            )

        img_sections = []
        for item in TARJETAS_IMAGENES:
            if isinstance(item, dict):
                continue
            titulo, codes, _, color = item
            try:
                df_card = pd.read_sql(
                    build_lab_query(anio_str, periodo, codcas, codasegu_clause, codes),
                    engine
                )
                total = len(df_card)

                if not df_card.empty and 'area_hosp' in df_card.columns:
                    df_breakdown = (
                        df_card.groupby('area_hosp', dropna=False)
                        .size()
                        .reset_index(name='counts')
                        .sort_values('counts', ascending=False)
                    )
                else:
                    df_breakdown = pd.DataFrame(columns=['area_hosp', 'counts'])
            except Exception:
                total = 0
                df_breakdown = pd.DataFrame(columns=['area_hosp', 'counts'])

            if total == 0:
                continue

            img_sections.append(
                dbc.Row(
                    [
                        dbc.Col(
                            render_card(titulo, f"{total:,.0f}", color, subtitle),
                            width=12, lg=4,
                            style={'display': 'flex'}
                        ),
                        dbc.Col(
                            html.Div(render_area_table(df_breakdown), style={'width': '100%'}),
                            width=12, lg=4,
                            style={'display': 'flex'}
                        ),
                    ],
                    justify="center",
                    style={'marginBottom': '10px'}
                )
            )

        if img_sections:
            sections.append(
                dbc.Row(
                    [
                        dbc.Col(
                            html.H4(
                                "Exámenes de Imágenes",
                                style={'color': '#FFFFFF', 'fontFamily': FONT_FAMILY, 'fontWeight': '700',
                                       'margin': '24px 0 10px 0'}
                            ),
                            width=12, lg=4,
                        ),
                        # Columna vacia con el mismo ancho que la tarjeta de la
                        # derecha: con justify="center" replica exactamente el
                        # mismo offset izquierdo que usan las filas de tarjetas
                        # de abajo, sin tener que calcular el % a mano.
                        dbc.Col(width=12, lg=4),
                    ],
                    justify="center",
                )
            )
            sections.extend(img_sections)

        return html.Div(sections)

    # ========== CALLBACK DESCARGA EXCEL ==========
    @dash_app.callback(
        Output('download-excel-proc', 'data'),
        Input('download-btn-proc', 'n_clicks'),
        State('filter-periodo-proc', 'value'),
        State('filter-anio-proc', 'value'),
        State('filter-tipo-proc', 'value'),
        State('url-proc', 'pathname'),
        prevent_initial_call=True,
    )
    def download_excel(n_clicks, periodo, anio, tipo_asegurado, pathname):
        from extensions import is_consulta_user
        if is_consulta_user():
            return no_update
        if not n_clicks:
            return no_update

        codcas_url = pathname.rstrip('/').split('/')[-1] if pathname else None
        codcas = sc.decode_code(codcas_url) if codcas_url else None

        if not periodo or not anio or not codcas:
            return no_update

        # Build code → titulo mapping from all TARJETAS
        code_to_titulo = {}
        for item in TARJETAS:
            if isinstance(item, dict):
                continue
            titulo, codes, _, _ = item
            for code in codes:
                code_to_titulo[code] = titulo

        all_codes = list(code_to_titulo.keys())
        from extensions import validate_anio_periodo
        try:
            anio_str, periodo = validate_anio_periodo(anio, periodo)
        except ValueError:
            return no_update

        codasegu_clause = resolve_tipo(tipo_asegurado or DEFAULT_TIPO)

        engine = create_connection()
        if engine is None:
            return no_update

        try:
            df = pd.read_sql(
                build_proc_query(anio_str, periodo, codcas, codasegu_clause, all_codes),
                engine,
            )
        except Exception as exc:
            print(f"[Dashboard PROC] download_excel error: {exc}")
            return no_update

        if df.empty:
            return no_update

        if 'cantproced' in df.columns:
            df['cantproced'] = pd.to_numeric(df['cantproced'], errors='coerce').fillna(0)

        df.insert(0, 'Procedimiento', df['codproced'].map(code_to_titulo))

        filename = f"procedimientos_{anio_str}_{periodo}_{codcas}.xlsx"
        return dcc.send_data_frame(df.to_excel, filename, index=False, sheet_name="Procedimientos")

    dash_app.layout = serve_layout
    return dash_app
