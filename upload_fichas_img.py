"""
Carga las fichas tecnicas (PDF) del segundo bloque (imagenologia /
TARJETAS_IMAGENES + TARJETAS_COMBINADAS) hacia dwsge.f_tecnicas, y mapea
cada archivo al titulo de tarjeta correspondiente en dashboard_proc.py.

Requiere DW_DATABASE_URI_2 (credencial admin/postgres) en el entorno, ya que
app_user solo tiene permisos de lectura sobre el DW (ver memoria
dw-app-user-sin-create).

Uso:
    python upload_fichas_img.py
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

# archivo -> titulo de tarjeta EXACTO tal como aparece en TARJETAS_IMAGENES /
# TARJETAS_COMBINADAS dentro de dashboard_proc.py.
ARCHIVO_A_TITULO = {
    "PRO03.01 - Tomografia.pdf": "Tomografía",
    "PRO03.02 - Resonancia Magnética sin Contraste.pdf": "Resonancia Magnética Sin Contraste",
    "PRO03.03 - Resonancia Magnética con Contraste.pdf": "Resonancia Magnética Con Contraste",
    "PRO03.04 - Examen Radiológico por Servicio de Procedencia simple y de contraste.pdf": "Examen Radiológico por Servicio de Procedencia simple y de contraste",
    "PRO03.05 - Ecografia.pdf": "Ecografía",
}


def main():
    engine = create_engine(ADMIN_URI)

    mapping = {}
    with engine.begin() as conn:
        existentes = {
            row.nombre: row.id
            for row in conn.execute(text("SELECT id, nombre FROM dwsge.f_tecnicas"))
        }
        for nombre, titulo in ARCHIVO_A_TITULO.items():
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

            mapping[titulo] = ficha_id

    print("\n=== Mapeo titulo -> ficha_id (para TARJETAS_IMAGENES / TARJETAS_COMBINADAS) ===")
    for titulo, ficha_id in mapping.items():
        print(f"{ficha_id}\t{titulo}")


if __name__ == "__main__":
    main()
