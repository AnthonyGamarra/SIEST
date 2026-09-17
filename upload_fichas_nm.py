"""
Carga las fichas tecnicas (PDF) de personal no medico / consulta externa
general (D:\\f_tec\\fichas_sistema, archivos "CE*.pdf") hacia
dwsge.f_tecnicas, y mapea cada archivo al titulo de tarjeta correspondiente
en dashboard_nm.py (pestanas Obstetricia, Preventivo promocional, Nutricion,
Enfermeria, Psicologia, Trabajo social, CRED) y en dashboard.py (pestanas
Medicina ocupacional, Medico de personal).

Requiere DW_DATABASE_URI_2 (credencial admin/postgres) en el entorno, ya que
app_user solo tiene permisos de lectura sobre el DW (ver memoria
dw-app-user-sin-create).

Uso:
    python upload_fichas_nm.py
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

ADMIN_URI = os.environ.get('DW_DATABASE_URI_2')
if not ADMIN_URI:
    raise SystemExit("Falta DW_DATABASE_URI_2 (credencial admin) en el entorno (.env).")

FICHAS_DIR = Path(r"D:\f_tec\fichas_sistema")

# archivo -> (archivo .py destino, titulo EXACTO de la tarjeta).
# Los archivos con destino None se suben a la tabla pero no se enlazan a
# ninguna tarjeta (versiones supersedidas o categorias sin tarjeta todavia).
ARCHIVO_A_TARJETA = {
    "CEC01.01_FT_Obtencion del Dato_At.amb. Enfermeria_CRED.pdf": (
        "dashboard_nm.py", "Total atenciones de control de crecimiento y desarrollo (CRED)"),
    "CEE01.01_FT_Obtencion del Dato_At.amb. Enfermeria.pdf": (
        "dashboard_nm.py", "Total atenciones de enfermería"),
    "CEN01.01_FT_Obtencion del Dato_At.amb.Nutricion.pdf": None,  # superseded by v2
    "CEN01.01_FT_Obtencion del Dato_At.amb.Nutricion_v2.pdf": (
        "dashboard_nm.py", "Total de atenciones de nutrición"),
    "CEOB1.01_FT_Obtencion del Dato_At.amb.Obstetricia.pdf": None,  # superseded by V2
    "CEOB1.01_FT_Obtencion del Dato_At.amb.Obstetricia_V2.pdf": (
        "dashboard_nm.py", "Total de atenciones Obstétricas"),
    "CEP01.01_FT_Atenciones_psicologia.pdf": (
        "dashboard_nm.py", "Total de consultas de psicología"),
    "CEP02.01_FT_Procedimiento Diagnóstico.pdf": (
        "dashboard_nm.py", "Número de procedimiento diagnóstico"),
    "CEP03.01_FT_Procedimiento Terapéutico.pdf": (
        "dashboard_nm.py", "Total procedimiento terapéutico"),
    "CEP04.01_FT_Preventivo Promocional.pdf": (
        "dashboard_nm.py", "Total de atenciones preventivo promocional"),
    "CEP05.01_FT_Atención Psicología Hospitalización.pdf": None,  # sin tarjeta todavia
    "CEP06.01_FT_Procedimiento Diagnóstico Hospitalización.pdf": None,  # sin tarjeta todavia
    "CEP07.01_FT_Procedimiento Terapéutico Hospitalizaciónn.pdf": None,  # sin tarjeta todavia
    "CES01.01_FT_Obtencion del Dato_Salud Ocupacional.pdf": (
        "dashboard.py", "Total de consultantes a medicina ocupacional"),
    "CES02.01_FT_Consulta médico de personal.pdf": (
        "dashboard.py", "Total de consultantes a medico de personal"),
    "CETS1.01_FT_Obtencion del Dato_At.amb.Trabajo Social.pdf": (
        "dashboard_nm.py", "Total atenciones de trabajo social"),
}


def main():
    engine = create_engine(ADMIN_URI)

    mapping = {}
    with engine.begin() as conn:
        existentes = {
            row.nombre: row.id
            for row in conn.execute(text("SELECT id, nombre FROM dwsge.f_tecnicas"))
        }
        for nombre, destino in ARCHIVO_A_TARJETA.items():
            archivo = FICHAS_DIR / nombre
            if not archivo.exists():
                print(f"AVISO: no se encontró el archivo: {archivo}")
                continue

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

            if destino:
                archivo_py, titulo = destino
                mapping[(archivo_py, titulo)] = ficha_id

    print("\n=== Mapeo (archivo.py, titulo tarjeta) -> ficha_id ===")
    for (archivo_py, titulo), ficha_id in mapping.items():
        print(f"{ficha_id}\t{archivo_py}\t{titulo}")

    sin_tarjeta = [n for n, d in ARCHIVO_A_TARJETA.items() if d is None]
    if sin_tarjeta:
        print("\nArchivos subidos sin tarjeta asociada:")
        for nombre in sin_tarjeta:
            print(f"  - {nombre}")


if __name__ == "__main__":
    main()
