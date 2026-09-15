"""
Carga las fichas tecnicas (PDF) de D:\\f_tec\\fichas_sistema\\proce hacia
dwsge.f_tecnicas, y mapea cada archivo al titulo de tarjeta correspondiente
del primer bloque (TARJETAS) de dashboard_proc.py.

Requiere DW_DATABASE_URI_2 (credencial admin/postgres) en el entorno, ya que
app_user solo tiene permisos de lectura sobre el DW (ver memoria
dw-app-user-sin-create).

Version 2026-09-10: los 66 PDFs de la carpeta fueron renombrados y
renumerados por completo (antes eran ~55 archivos con otra numeracion). Este
mapeo se reconstruyo desde cero cruzando cada archivo contra los titulos
actuales de TARJETAS. Decisiones tomadas con el usuario:
  - "Angioplastia con Balon" tenia 2 PDFs identicos (PRO09.01 y PRO56.01) ->
    se usa PRO09.01; PRO56.01 se sube igual pero sin enlazar a ninguna tarjeta.
  - Las 55 filas viejas en dwsge.f_tecnicas (ids 17-71, con los nombres de
    archivo anteriores) se borran por quedar huerfanas - ver borrar_viejas().

Actualizacion 2026-09-10 (2): el usuario confirmo que PRO57.01 "Angioplastia
Coronaria con Stent Medicado" y la tarjeta "Angioplastia Stent Metalico" son
el MISMO procedimiento -> la tarjeta se renombro a "Angioplastia Coronaria
con Stent Medicado" y ahora usa PRO57.01 (id 129). PRO13.01 "Angioplastia
Stent Metalico.pdf" (id 84) quedo como duplicado sin enlazar - evaluar si
conviene borrarlo de dwsge.f_tecnicas.

Uso:
    python upload_fichas_proc.py
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

ADMIN_URI = os.environ.get('DW_DATABASE_URI_2')
if not ADMIN_URI:
    raise SystemExit("Falta DW_DATABASE_URI_2 (credencial admin) en el entorno (.env).")

FICHAS_DIR = Path(r"D:\f_tec\fichas_sistema\proce")

# Fichas viejas (carga del 2026-09-09, con nombres de archivo que ya no
# existen en la carpeta tras la reorganizacion) - se eliminan antes de
# insertar las nuevas. Confirmado con SELECT id, nombre previo a este cambio.
IDS_VIEJOS_A_BORRAR = list(range(17, 72))  # 17..71 inclusive

# archivo -> titulo de tarjeta EXACTO tal como aparece en TARJETAS dentro de
# dashboard_proc.py. Los archivos que no aparecen aqui igual se suben a la
# tabla, pero no quedan enlazados a ninguna tarjeta.
ARCHIVO_A_TITULO = {
    "PRO01.01 - Cateterismo Cardiaco.pdf": "Cateterismo Cardíaco",
    "PRO02.01 - Electrocardiografia.pdf": "Electrocardiografía",
    "PRO03.01 - Cardio Holter.pdf": "Cardio Holter",
    "PRO04.01 - Prueba de Esfuerzo (Ergometrías).pdf": "Prueba de Esfuerzo",
    "PRO05.01 - Ecocardiografía Transtorácica.pdf": "Ecocardiografía Transtorácica",
    "PRO06.01 - Ecocardiografía Transesofágica.pdf": "Ecocardiografía Transesofágica",
    "PRO07.01 - Ecocardiografía Stress.pdf": "Ecocardiografía Stress",
    "PRO08.01 - Ablación Transcatéter.pdf": "Ablación Transcatérer",
    "PRO09.01 - Angioplastia con Balón.pdf": "Angioplastia con Balón",
    "PRO10.01 - Marcapaso Transitorio.pdf": "Marcapaso Transitorio",
    "PRO11.01 - Marcapaso Definitivo Unicameral.pdf": "Marcapaso Definitivo Unicameral",
    "PRO12.01 - Marcapaso Definitivo Bicameral.pdf": "Marcapaso Definitivo Bicameral",
    # PRO13.01 - Angioplastia Stent Metálico.pdf: duplicado de PRO57.01, sin enlazar.
    "PRO14.01 - Audiometría.pdf": "Audiometría",
    "PRO15.01 - Angiografía Retinal.pdf": "Angiografía Retinal",
    "PRO16.01 - Cardioversión Eléctrica Electiva.pdf": "Cardioversión Eléctrica Electiva",
    "PRO17.01 - Colposcopia.pdf": "Colposcopía",
    "PRO18.01 - Instalación y Mantenimiento de CPAC de burbuja.pdf": "Instalación y Mantenimiento de CPAC de burbuja",
    "PRO19.01 - Electroencefalografía.pdf": "Electroencefalografía",
    "PRO20.01 - Endoscopia Digestiva Diagnostica.pdf": "Endoscopía Digestiva Diagnóstica",
    "PRO21.01 - Electromiografía y Velocidad de Conducción.pdf": "Electromiografía y Velocidad de Conducción",
    "PRO22.01 - Tomografía de Coherencia Óptica ( OCT).pdf": "Tomografía de Coherencia Óptica (OCT)",
    "PRO23.01 - Test de Inclinación ( TILT TEST).pdf": "Test de Inclinación",
    "PRO24.01 - Reserva de Flujo Fraccionado.pdf": "Reserva de Flujo Fraccionado",
    "PRO25.01 - Valvuloplastia Pulmonar Y-O Aorta.pdf": "Valvuloplastía Pulmonar y/o Aórtica",
    "PRO26.01 - Valvuloplastia Mitral con Balón.pdf": "Valvuloplastia Mitral con Balón",
    "PRO27.01 - Ultrasonido Endovascular.pdf": "Ultrasonido Endovascular",
    "PRO28.01 - Marcapaso Definitivo para Resincronización.pdf": "Marcapaso Definitivo para Resincronización",
    "PRO29.01 - Urodinamia.pdf": "Urodinamia",
    "PRO30.01 - Implantación de Cardiovector Desfibrilador Automático.pdf": "Implantación de Cardiovector Desfibrilador Automático",
    "PRO31.01 - Endoscopia Diagnostica no Digestiva.pdf": "Endoscopía Diagnóstica no Digestiva",
    "PRO32.01 - Potenciales Evocados.pdf": "Potenciales Evocados",
    # PRO33.01 - Perfusión Miocárdica con Radioisótopos.pdf: sin tarjeta.
    "PRO33.01 - Tratamiento del Dolor.pdf": "Tratamiento del Dolor",
    "PRO34.01 - Procedimiento Corneal Instrumentado.pdf": "Procedimiento Corneal Instrumentado",
    "PRO35.01 - Procedimientos Médicos de Rehabilitación.pdf": "Procedimientos Médicos de Rehabilitación",
    "PRO36.01 - Trombólisis Sistémica.pdf": "Trombólisis Sistémica",
    "PRO37.01 - Ecocardiografía Pediatrica.pdf": "Ecocardiografía pediatrica",
    "PRO38.01 - Cateterismo + Medición de CIA.pdf": "Cateterismo + Medición de CIA",
    "PRO39.01 - Estimulación Eléctrica Cerebral.pdf": "Estimulación Eléctrica Cerebral",
    "PRO40.01 - Test del Aliento.pdf": "Test del Aliento",
    # PRO41.01 - Implante Cloquear.pdf: sin tarjeta.
    "PRO42.01 - Administración de Oxigeno por Casco Cefálico (OXIHOOD).pdf": "Administración de Oxígeno por Casco Cefálico (OXIHOOD)",
    "PRO43.01 - Instalación y Mantenimiento del Cateter Venoso Central de Inserción Periferica (PICC).pdf": "Instalación y Mantenimiento del Cateter Venoso Central de Inserción Periferica (PICC)",
    # PRO44.01 - Tomografía por emisión Positrones CO.pdf: sin tarjeta (esa
    #   tarjeta vive en TARJETAS_IMAGENES, no en TARJETAS).
    "PRO45.01 - Cono Leep.pdf": "Cono LEEP",
    "PRO46.01 - Crioterapía.pdf": "Crioterapia",
    "PRO47.01 - Espirometría.pdf": "Espirometría",
    "PRO48.01 - Perimetría (Campimetría).pdf": "Perimetría (Campimetría)",
    "PRO49.01 - Laserterapia Ocular.pdf": "Laserterapia Ocular",
    "PRO50.01 - Angiografía Cerebral.pdf": "Angiografía Cerebral",
    # PRO51.01 - Ecografía.pdf: sin tarjeta (vive en TARJETAS_COMBINADAS).
    # PRO52.01 - Uroten con Contraste.pdf: sin tarjeta.
    # PRO53.01 - Angiotem.pdf: sin tarjeta.
    "PRO54.01 - Cono Frio.pdf": "Cono Frío",
    "PRO55.01 - Terapia Endovascular.pdf": "Terapia Endovascular",
    # PRO56.01 - Angioplastia con Balón.pdf: duplicado de PRO09.01, sin enlazar.
    "PRO57.01 - Angioplastia Coronaria con Stent Medicado.pdf": "Angioplastia Coronaria con Stent Medicado",
    "PRO58.01 - Biopsia Endomiocardica.pdf": "Biopsia Endomiocárdica",
    "PRO59.01 - Cateterismo con Pruebas de Vasoreactivación.pdf": "Cateterismo con Pruebas de Vasoreactivación",
    "PRO60.01 - Dilatación con Protesis de Coartación de Aorta.pdf": "Dilatación con Protesis de Coartación de Aorta",
    "PRO61.01 - Estudios Fisiológicos (Electrofisiológicos).pdf": "Estudios Fisiológicos (Electrofisiológicos)",
    "PRO62.01 - Evaluación del Marcapaso Cardio Desfibrilador y otros Dispositivos Implantables.pdf": "Evaluación del Marcapaso Cardio Desfibrilador y otros Dispositivos Implantables",
    "PRO63.01 - Holter Implantable.pdf": "Holter Implantable",
    "PRO64.01 - Oclusión de Defecto Septal Interventricular.pdf": "Oclusión de Defecto Septal Interventricular",
    "PRO65.01 - Oclusión de Defecto Septal Interauricular.pdf": "Oclusión de Defecto Septal Interauricular",
}


def borrar_viejas(conn):
    filas = conn.execute(
        text("SELECT id, nombre FROM dwsge.f_tecnicas WHERE id = ANY(:ids)"),
        {"ids": IDS_VIEJOS_A_BORRAR},
    ).fetchall()
    if not filas:
        print("No hay fichas viejas para borrar (ya se habian limpiado).")
        return
    print(f"Borrando {len(filas)} fichas viejas (nombres de archivo ya reemplazados):")
    for f in filas:
        print(f"  - id={f.id}: {f.nombre}")
    conn.execute(
        text("DELETE FROM dwsge.f_tecnicas WHERE id = ANY(:ids)"),
        {"ids": [f.id for f in filas]},
    )


def main():
    engine = create_engine(ADMIN_URI)
    archivos = sorted(FICHAS_DIR.glob("*.pdf"))
    if not archivos:
        raise SystemExit(f"No se encontraron PDFs en {FICHAS_DIR}")

    mapping = {}
    with engine.begin() as conn:
        borrar_viejas(conn)

        existentes = {
            row.nombre: row.id
            for row in conn.execute(text("SELECT id, nombre FROM dwsge.f_tecnicas"))
        }
        for archivo in archivos:
            nombre = archivo.name
            if nombre in existentes:
                ficha_id = existentes[nombre]
                print(f"Ya existe, se reutiliza id={ficha_id}: {nombre}")
            else:
                data = archivo.read_bytes()
                ficha_id = conn.execute(
                    text(
                        "INSERT INTO dwsge.f_tecnicas (nombre, archivo_pdf, fecha_subida) "
                        "VALUES (:nombre, :data, now()) RETURNING id"
                    ),
                    {"nombre": nombre, "data": data},
                ).scalar_one()
                print(f"Insertado id={ficha_id}: {nombre} ({len(data)} bytes)")

            titulo = ARCHIVO_A_TITULO.get(nombre)
            if titulo:
                mapping[titulo] = ficha_id

    print("\n=== Mapeo titulo -> ficha_id (para TARJETAS en dashboard_proc.py) ===")
    for titulo, ficha_id in mapping.items():
        print(f"{ficha_id}\t{titulo}")

    sin_tarjeta = [a.name for a in archivos if a.name not in ARCHIVO_A_TITULO]
    if sin_tarjeta:
        print("\nArchivos subidos sin tarjeta asociada:")
        for nombre in sin_tarjeta:
            print(f"  - {nombre}")


if __name__ == "__main__":
    main()
