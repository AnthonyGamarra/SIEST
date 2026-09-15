import os

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, no_update, MATCH
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
            24,
        ),
        (
            "Administración de Oxígeno por Casco Cefálico (OXIHOOD)",
            ("94799.02","94799.03"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            114,
        ),
        (
            "Angiografía Cerebral",
            ("36221","36222","36223","36224","36225","36228","36251",
             "61254","61257","61623","61624","61630","61635","61640","64627"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            122,
        ),
        (
            "Angiografía Retinal",
            ("92235"), ##cambió
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            86,
        ),
        (
            "Angioplastia con Balón",
            ("37204","37217","37236","37237","37242","37243","61624","61708","61710","62294"), #CAMBIO
            "bi-activity",
            "#0064AF",
            80,
        ),
        (
            "Angioplastia Coronaria con Stent Medicado",
            ("92920","92928"),
            "bi-activity",
            "#0064AF",
            129,
        ),
        (
            "Audiometría",
            ("92552","92553","92556","92583","92551","92552","92553","92555","92556","92557","92560","92561"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            85,
        ),
        (
            "Biopsia Endomiocárdica",
            ("93505"),
            "bi-activity",
            "#0064AF",
            130,
        ),
        (
            "Cardio Holter",
            ("93224","93225","93233","93278"),
            "bi-activity",
            "#0064AF",
            74,
        ),
        (
            "Cardioversión Eléctrica Electiva",
            ("92960"),
            "bi-activity",
            "#0064AF",
            87,
        ),
        (
            "Cateterismo + Medición de CIA",
            ("93451"),
            "bi-activity",
            "#0064AF",
            110,
        ),
        (
            "Cateterismo Cardíaco",
            ("36013","36014","93455","93456","93458",
             "93503","93556","93562","93452","93454","93544"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            72,
        ),

        (
            "Cateterismo con Pruebas de Vasoreactivación",
            ("93501"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            131,
        ),
        (
            "Colposcopía",
            ("56820","57420","57454","57455","58110","56820","56821","57420","57421","57452","57454","57455","57456","57461","58110"), ##cambio
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            88,
        ),
        (
            "Cono Frío",
            ("57520"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            126,
        ),
        (
            "Cono LEEP",
            ("57522"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            117,
        ),
        (
            "Crioterapia",
            ("17340"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            118,
        ),
        (
            "Dilatación con Protesis de Coartación de Aorta",
            ("35472"),
            "bi-activity",
            "#0064AF",
            132,
        ),
        (
            "Ecocardiografía Stress",
            ("93350","93351"),
            "bi-activity",
            "#0064AF",
            78,
        ),
        (
            "Ecocardiografía Transesofágica",
            ("93312","93313","93314","93315","93317"),
            "bi-activity",
            "#0064AF",
            77,
        ),
        (
            "Ecocardiografía Transtorácica",
            ("93306","93307","93308","93318","93320","93882.06","93321","93882"),
            "bi-activity",
            "#0064AF",
            76,
        ),

        (
            "Electrocardiografía",
            ("93000","93005","93010"),
            "bi-activity",
            "#0064AF",
            73,
        ),
        (
            "Electroencefalografía",
            ("95812","95812.02","95813","95816","95819","95822"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            90,
        ),
        (
            "Electromiografía y Velocidad de Conducción",
            ("95860","95861","95863","95864","95872","95885","95886","95887","96867","95877",
             "95900","95903","95904","95905","95907","95908","95909","95910","95937"),
            "bi-activity",
            "#0064AF",
            92,
        ),
        (
            "Ecocardiografía pediatrica",
            ("93303","93308","93318"),
            "bi-activity",
            "#0064AF",
            109,
        ),
        (
            "Endoscopía Diagnóstica no Digestiva",
            ("31231","31505","31575","31622","31623","45338","C7003","31624","31625","31627","31628","31632",
             "91010","31633","31641","31645","31646","45334","45337","45379","46614","49082","76981","90901",
             "90911","91038","91111","91122","91212","92511","96366"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            102,
        ),
        (
            "Endoscopía Digestiva Diagnóstica",
            ("43234","43239","44388","44391","45358","45359","45378","45380","91200","91202"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            91,
        ),
        (
            "Espirometría",
            ("94060","94010","94012.01","94314","94315","94620"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            119,
        ),
        (
            "Estimulación Eléctrica Cerebral",
            ("95979","95975","95978"), ##CAMBIO
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            111,
        ),
        (
            "Estudios Fisiológicos (Electrofisiológicos)",
            ("93613","93618","93619","93623","93609"),
            "bi-activity",
            "#0064AF",
            133,
        ),
        (
            "Evaluación del Marcapaso Cardio Desfibrilador y otros Dispositivos Implantables",
            ("93279","93280","93281","93282","93283","93284","93285","93286","93287","93727","93744"),
            "bi-activity",
            "#0064AF",
            134,
        ),       
        (
            "Holter Implantable",
            ("33282"),
            "bi-activity",
            "#0064AF",
            135,
        ),    
        (
            "Implantación de Cardiovector Desfibrilador Automático",
            ("33215","33225","33263","33240","33244","33249"),
            "bi-activity",
            "#0064AF",
            101,
        ),
        (
            "Instalación y Mantenimiento de CPAC de burbuja",
            ("94660"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            89,
        ),
        (
            "Instalación y Mantenimiento del Cateter Venoso Central de Inserción Periferica (PICC)",
            ("36568","36569"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            115,
        ),
        (
            "Laparoscopía Diagnóstica",
            ("49320"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            None,
        ),
        (
            "Laserterapia Ocular",
            ("92136","92250","92286","92287","96905","U0901"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            121,
        ),
        (
            "Marcapaso Definitivo Bicameral",
            ("33208","33213","33214","33228","33230","33208"), ##cambió
            "bi-activity",
            "#0064AF",
            83,
        ),
        (
            "Marcapaso Definitivo para Resincronización",
            ("33221","33229"),
            "bi-activity",
            "#0064AF",
            99,
        ),
        (
            "Marcapaso Definitivo Unicameral",
            ("33206","33207","33212","33227","93612","33233"),
            "bi-activity",
            "#0064AF",
            82,
        ),
        (
            "Marcapaso Transitorio",
            ("92953","33211"),
            "bi-activity",
            "#0064AF",
            81,
        ),
        (
            "Oclusión de Defecto Septal Interauricular",
            ("93580"),
            "bi-activity",
            "#0064AF",
            137,
        ),
        (
            "Oclusión de Defecto Septal Interventricular",
            ("93581"),
            "bi-activity",
            "#0064AF",
            136,
        ),
        (
            "Perimetría (Campimetría)",
            ("92081","92082","92083"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            120,
        ),

        (
            "Potenciales Evocados",
            ("92288","92585","92586","95930"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            103,
        ),

        (
            "Procedimiento Corneal Instrumentado",
            ("92025","92100","92137"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            106,
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
            107,
        ),
        (
            "Prueba de Esfuerzo",
            ("93015","93016","93017","93018","93464","93233"),
            "bi-activity",
            "#0064AF",
            75,
        ),
        (
            "Reserva de Flujo Fraccionado",
            ("93571"),
            "bi-activity",
            "#0064AF",
            95,
        ),
        (
            "Test de Inclinación",
            ("93660"),
            "bi-activity",
            "#0064AF",
            94,
        ),
        (
            "Test del Aliento",
            ("83013"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            112,
        ),
        (
            "Terapia Endovascular",
            ("37204","37217","37236","37237","37242","37243","61624","61708","61710","62294"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            127,
        ),
        (
            "Tomografía de Coherencia Óptica (OCT)",
            ("92134"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            93,
        ),
        (
            "Tratamiento del Dolor",
            ("1983.02","1984","22510","22511","22512","1984.02","90780","22520","22521","27096","96369","64405","64413","64475","63190","64476","64493","64495","97784"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            105,
        ),
        (
            "Trombólisis Sistémica",
            ("37195"),
            "bi-activity",
            "#0064AF",
            108,
        ),
        (
            "Ultrasonido Endovascular",
            ("92978"),
            "bi-activity",
            "#0064AF",
            98,
        ),
        (
            "Urodinamia",
            ("51726","51729","51741"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            100,
        ),
        (
            "Valvuloplastia Mitral con Balón",
            ("92987"),
            "bi-activity",
            "#0064AF",
            97,
        ),
        (
            "Valvuloplastía Pulmonar y/o Aórtica",
            ("92998"),
            "bi-activity",
            "#0064AF",
            96,
        ),
        (
            "Video/Epilepsia",
            ("95951"),
            "bi-clipboard2-pulse-fill",
            "#0064AF",
            None,
        ),
    ]

    # ========== CONFIGURACIÓN DE TARJETAS · IMÁGENES (dssge.dw_lab_*) ==========
    # Misma convención que TARJETAS, pero estas se consultan contra la tabla
    # dssge.dw_lab_{anio}_{periodo} (build_lab_query), no dssge.dw_proc_*.
    IMG_COLOR = "#00AEEF"
    TARJETAS_IMAGENES = [
        (
            "Tomografía",
            ("70336.02","70542","70542.01","73222.03","70482.03",
            "70542.02","73201.03","73219.01","73719.01","70488.01",
            "70542.03","73201.01","73219.02","73719.02","70491",
            "70545","73201.02","73219.03","73719.03","70498",
            "70548","72142","73219.04","73722.01","72191",
            "70551.05","72147","73219.05","73722.02","72193",
            "70552","72149","73222.01","73722.03","73201",
            "74182.01","72196","73222.02","74182","73201.05",
            "74485.02","75553","73201.06","75574","73701.05",
            "70460","72126","73701.01","74160","71260",
            "70481","72129","73701.02","74160.01",
            "70482.01",	"72132","73701.03",	"74160.02",	
            "70482.02",	"72132.01","73701.04","75572"),
            "bi-clipboard2-pulse-fill",
            IMG_COLOR,
            138,
        ),
        (
            "Mamografía",    
            ("77055","77056"),
            "bi-clipboard2-pulse-fill",
            IMG_COLOR,
            None,
        ),
        (
            "Resonancia Magnética Sin Contraste",
            ("70540.01","70540.03","70544","70551","71550.02","73721.03",
            "72148","72195","72195.01","73218.01","73218.02","77059",
            "73718.01","73718.02","73718.03","73718.04","73721.01",
            "73725","74181","74181.01","74185","74485.01",
            "72141","72146","72146","73218.04","73218.05","73721.02"),
            "bi-clipboard2-pulse-fill",
            IMG_COLOR,
            139,
        ),
        (
            "Resonancia Magnética Con Contraste",
            ("70336.02","70542","70542.01","70542.02","70542.03","70545","70548",
            "71551","71551.01","71551.02","72142","72147","72149","72196",
            "73219.03","73219.04","73219.05","73222.01","73222.02","73222.03","73719.01",
            "73722.01","73722.02","73722.03","74182","74182.01","74485.02","75553",
            "70551.05","70552","73219.01","73219.01","73219.02","73719.02","73719.03"),
            "bi-clipboard2-pulse-fill",
            IMG_COLOR,
            140,
        ),
        (
            "Examen Radiológico por Servicio de Procedencia simple y de contraste",
            ("70110",	"70330",	"71110",	"72068",	"72170",
            "70140",	"70355",	"71130",	"72069",	"72190",
            "70150",	"70360",	"72010",	"72074",	"72202",
            "70240",	"70370",	"72020",	"72081",	"72220",
            "73070",	"71035",	"73050",	"73130",	"73600",	"74020",
            "73080",	"71035.01",	"73060",	"73131",	"73610",	"74020.01",
            "73090",	"71101",	"73562",	"73140",	"73615",	"74022",
            "73092",	"73520",	"73565",	"73500",	"73620",	"74210",
            "73100",	"73540",	"73567",	"74000",	"73630",	"74210.01",
            "73110",	"73550",	"73590",	"74000.01",	"73650",	"74220",
            "73120",	"73560",	"73592",	"74010",	"73660",	"74230",
            "74241",	"74270",	"74740",	"75825",	"75978",	"74450",
            "74246",	"74280",	"74930",	"75827",	"75980",	"74455",
            "74247.01",	"74305",	"75630",	"75885",	"75982",	"744752",
            "74247.02",	"74320",	"75671",	"75894",	"75984",	"75743",
            "74249",	"74363",	"75710",	"75894.01",	"76080",	"75822",
            "74250",	"74425",	"75716",	"75940",	"76096",	"76499",
            "74251",	"74430",	"75726",	"75962",	"76140",	"73020",
            "70260",	"71010",	"72040.01",	"72082",	"73011",	"73030",
            "70300",	"71010.01",	"72040.03",	"72090",    "72067",	"72100",
            "70328",	"71022"),
            "bi-activity",
            IMG_COLOR,
            141,
        ),
    ]

    # ========== TARJETAS QUE SUMAN dw_proc* + dw_lab ==========
    TARJETAS_COMBINADAS = [
        (
            "Ecografía",
            ("76512","76604.02","76700.02","76811","76830","93976.01",
             "76513","76604.04","76705","76812","76856","93976.03",
             "76514","76645","76706","76813","76872","93985",
             "76536","76646","76802","76815","76880","93990",
             "76604","76700","76805","76816","76999.01","76820.01",
             "76700.01","76810","76817","93971.01"),
            ("76536", "76536.01", "76536.03", "76604", "76604.02", "76645", "76700",
             "76700.01", "76700.02", "76770", "76770.01", "76775", "76775.01", "76778",
             "76800", "76801", "76802", "76805", "76813", "76814", "76817", "76830",
             "76856", "76870", "76872", "76873", "76880", "76880.04", "76880.05", "76881",
             "76882", "76885", "76886", "76937", "76970", "76999.01", "78821"),
            "bi-clipboard2-pulse-fill",
            IMG_COLOR,
            142,
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
    def render_card(title, value, border_color, subtitle_text, ficha_id=None):
        title_row_children = [
            html.H5(title, className="card-title", style={
                'color': BRAND, 'marginBottom': '6px',
                'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.1px'
            }),
        ]
        if ficha_id is not None:
            title_row_children.append(
                html.Div([
                    dbc.Button(
                        [html.I(className="bi bi-file-earmark-arrow-down me-1"), "Ficha técnica"],
                        id={'type': 'ficha-btn-proc', 'ficha_id': ficha_id},
                        color='light', outline=True, size='sm',
                        style={
                            'borderColor': BRAND, 'color': BRAND,
                            'backgroundColor': '#F7FBFF', 'fontFamily': FONT_FAMILY,
                            'fontWeight': '600', 'fontSize': '11px', 'borderRadius': '10px',
                            'padding': '4px 10px', 'whiteSpace': 'nowrap', 'flexShrink': 0,
                        }
                    ),
                    dcc.Download(id={'type': 'ficha-download-proc', 'ficha_id': ficha_id}),
                ], style={'marginLeft': '10px'})
            )
        body_children = [
            html.Div(title_row_children, style={
                'display': 'flex', 'alignItems': 'center',
                'justifyContent': 'space-between', 'marginBottom': '6px'
            }),
            html.H2(value, style={
                'fontWeight': '800', 'color': TEXT, 'fontSize': '34px',
                'margin': 0, 'fontFamily': FONT_FAMILY, 'letterSpacing': '-0.2px'
            }),
            html.P(subtitle_text, style={
                'fontSize': '12px', 'color': MUTED,
                'margin': '6px 0 0 0', 'fontFamily': FONT_FAMILY
            }),
        ]
        return dbc.Card(
            dbc.CardBody(body_children, style=CARD_BODY_STYLE),
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

    def _build_safe_pdf_name(raw_name):
        base = (raw_name or "ficha_tecnica").strip()
        safe_chars = [ch if ch.isalnum() or ch in (" ", "-", "_") else "_" for ch in base]
        normalized = ''.join(safe_chars).strip().replace(' ', '_').lower()
        normalized = normalized or "ficha_tecnica"
        return normalized if normalized.endswith('.pdf') else f"{normalized}.pdf"

    def fetch_ficha_tecnica(engine, ficha_id):
        if engine is None or ficha_id is None:
            return None
        try:
            from sqlalchemy import text
            with engine.connect() as connection:
                row = connection.execute(
                    text("SELECT nombre, archivo_pdf FROM dwsge.f_tecnicas WHERE id = :id"),
                    {"id": ficha_id}
                ).mappings().first()
        except Exception as exc:
            print(f"[Dashboard PROC] fetch_ficha_tecnica error: {exc}")
            return None

        if not row or not row.get('archivo_pdf'):
            return None

        filename = _build_safe_pdf_name(row.get('nombre'))
        pdf_bytes = bytes(row['archivo_pdf'])
        return filename, pdf_bytes

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
                  --AND cod_actividad in ('96','91')
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
                  --AND cod_actividad in ('96','91')
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
                  --AND cod_actividad in ('96','91')
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
            titulo, codes, _, color, ficha_id = item
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
                            render_card(titulo, f"{total:,.0f}", color, subtitle, ficha_id),
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
            titulo, codes, _, color, ficha_id = item
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
                            render_card(titulo, f"{total:,.0f}", color, subtitle, ficha_id),
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

        for item in TARJETAS_COMBINADAS:
            if isinstance(item, dict):
                continue
            titulo, codes_proc, codes_lab, _, color, ficha_id = item
            total = 0
            breakdown_parts = []

            try:
                df_proc = pd.read_sql(
                    build_proc_query(anio_str, periodo, codcas, codasegu_clause, codes_proc),
                    engine
                )
                if 'cantproced' in df_proc.columns:
                    df_proc['cantproced'] = pd.to_numeric(
                        df_proc['cantproced'], errors='coerce'
                    ).fillna(0)
                    total += int(df_proc['cantproced'].sum())
                    if not df_proc.empty and 'area_hosp' in df_proc.columns:
                        breakdown_parts.append(
                            df_proc.groupby('area_hosp', dropna=False)['cantproced']
                            .sum()
                            .reset_index(name='counts')
                        )
            except Exception:
                pass

            try:
                df_lab = pd.read_sql(
                    build_lab_query(anio_str, periodo, codcas, codasegu_clause, codes_lab),
                    engine
                )
                total += len(df_lab)
                if not df_lab.empty and 'area_hosp' in df_lab.columns:
                    breakdown_parts.append(
                        df_lab.groupby('area_hosp', dropna=False)
                        .size()
                        .reset_index(name='counts')
                    )
            except Exception:
                pass

            if total == 0:
                continue

            if breakdown_parts:
                df_breakdown = (
                    pd.concat(breakdown_parts, ignore_index=True)
                    .groupby('area_hosp', dropna=False)['counts']
                    .sum()
                    .reset_index()
                    .sort_values('counts', ascending=False)
                )
            else:
                df_breakdown = pd.DataFrame(columns=['area_hosp', 'counts'])

            img_sections.append(
                dbc.Row(
                    [
                        dbc.Col(
                            render_card(titulo, f"{total:,.0f}", color, subtitle, ficha_id),
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

        # Build code → titulo mapping from all TARJETAS (+ el lado dw_proc de
        # las tarjetas combinadas, ej. Ecografia - ver TARJETAS_COMBINADAS)
        code_to_titulo = {}
        for item in TARJETAS:
            if isinstance(item, dict):
                continue
            titulo, codes, _, _, _ = item
            for code in codes:
                code_to_titulo[code] = titulo
        for item in TARJETAS_COMBINADAS:
            if isinstance(item, dict):
                continue
            titulo, codes_proc, _, _, _, _ = item
            for code in codes_proc:
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

    # ========== CALLBACK DESCARGA FICHA TÉCNICA POR TARJETA ==========
    @dash_app.callback(
        Output({'type': 'ficha-download-proc', 'ficha_id': MATCH}, 'data'),
        Input({'type': 'ficha-btn-proc', 'ficha_id': MATCH}, 'n_clicks'),
        State({'type': 'ficha-btn-proc', 'ficha_id': MATCH}, 'id'),
        prevent_initial_call=True,
    )
    def download_ficha_tecnica_proc(n_clicks, btn_id):
        if not n_clicks:
            return no_update

        engine = create_connection()
        ficha = fetch_ficha_tecnica(engine, btn_id['ficha_id'])
        if not ficha:
            return no_update

        filename, pdf_bytes = ficha
        return dcc.send_bytes(lambda buffer: buffer.write(pdf_bytes), filename)

    dash_app.layout = serve_layout
    return dash_app
