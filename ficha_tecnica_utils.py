"""
Helpers compartidos para mostrar fichas tecnicas (PDF guardados en
dwsge.f_tecnicas) dentro de un modal en los dashboards Dash, en vez de
forzar la descarga del archivo.
"""
import base64

from sqlalchemy import text


def fetch_ficha_row(engine, ficha_id):
    """Devuelve (nombre, pdf_bytes) para el id dado, o None si no existe."""
    if engine is None or ficha_id is None:
        return None
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT nombre, archivo_pdf FROM dwsge.f_tecnicas WHERE id = :id"),
                {"id": ficha_id}
            ).mappings().first()
    except Exception as exc:
        print(f"[ficha_tecnica_utils] fetch_ficha_row error: {exc}")
        return None

    if not row or not row.get('archivo_pdf'):
        return None

    return row.get('nombre') or "Ficha técnica", bytes(row['archivo_pdf'])


def build_pdf_data_uri(pdf_bytes):
    """Codifica el PDF como data: URI para mostrarlo inline en un iframe.

    El fragmento #toolbar=0&navpanes=0 lo reconoce el visor de PDF nativo de
    Chrome/Edge (y en gran medida el pdf.js de Firefox) para ocultar su
    propia barra de herramientas dentro del iframe.
    """
    b64 = base64.b64encode(pdf_bytes).decode('ascii')
    return f"data:application/pdf;base64,{b64}#toolbar=0&navpanes=0"
