"""
Caracterizacion de Establecimientos - acceso publico (solo red interna).

Proceso aparte de SIEST: levanta unicamente el Dash de
mantenimiento_establecimientos_v3.py en modo publico, sin login y en solo
lectura (solo la pestaña Caracterizacion; el resto de callbacks se rechaza en
el servidor). Las lecturas a SQL Server se cachean 5 minutos.

Uso:
    python public_establecimientos.py            # puerto 8090
    set PUBLIC_EST_PORT=8091 & python public_establecimientos.py

No carga la base de usuarios, ni las rutas ni los demas dashboards de SIEST.
"""
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from flask import Flask, redirect

from mantenimiento_establecimientos_v3 import create_dash_app


PORT = int(os.environ.get("PUBLIC_EST_PORT", "8090"))
CACHE_SECONDS = 300

app = Flask(__name__)

create_dash_app(
    app,
    url_base_pathname="/caracterizacion/",
    public=True,
    public_cache_seconds=CACHE_SECONDS,
)


@app.route("/")
def index():
    return redirect("/caracterizacion/")


if __name__ == "__main__":
    from waitress import serve

    print(f"Caracterizacion de Establecimientos (publico) en http://0.0.0.0:{PORT}/caracterizacion/")
    serve(app, host="0.0.0.0", port=PORT, threads=8)
