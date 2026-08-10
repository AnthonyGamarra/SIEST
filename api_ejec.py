"""
API JSON del Modulo Ejecutivo de Patologias (Tab 1 - Analitica), consumida
por el frontend React/Nivo (frontend_ejec/). Mismo control de acceso que la
version Dash: solo usuarios autenticados con role == 'admin'.
"""
from flask import Blueprint, jsonify, request
from flask_login import current_user

import ejec_data as data

bp = Blueprint("api_ejec", __name__, url_prefix="/api/ejec")


@bp.before_request
def _require_admin():
    if not getattr(current_user, "is_authenticated", False):
        return jsonify({"error": "Sesion no iniciada."}), 401
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Solo los administradores pueden acceder al Modulo Ejecutivo de Patologias."}), 403


def _anio_list():
    anios = request.args.getlist("anio")
    return anios or ["TODOS"]


def _safe(fn, *args, **kwargs):
    try:
        return jsonify(fn(*args, **kwargs))
    except data.EjecDataError as exc:
        return jsonify({"error": str(exc)}), 502


@bp.get("/meta")
def meta():
    return _safe(lambda: {"anios": data.get_anio_options()})


@bp.get("/tab1/historic")
def tab1_historic():
    def payload():
        return {
            "pacientes_totales": data.get_pacientes_totales(),
            "evolucion_anual": data.get_evolucion_anual(),
            "comorbilidad_oncologico": data.get_comorbilidad_grupo("Oncologico", "Coomorbilidad Oncología"),
            "comorbilidad_renal": data.get_comorbilidad_grupo("Renal", "Coomorbilidad Renal"),
            "burbujas": data.get_comorbilidad_burbujas(),
        }
    return _safe(payload)


@bp.get("/tab1/comparativa")
def tab1_comparativa():
    anio_list = _anio_list()
    return _safe(data.get_comparativa, anio_list)


@bp.get("/tab1/flujo-area")
def tab1_flujo_area():
    anio_list = _anio_list()
    return _safe(data.get_flujo_area, anio_list)


@bp.get("/tab1/diag-treemap")
def tab1_diag_treemap():
    anio_list = _anio_list()
    return _safe(lambda: {"rows": data.get_diag_treemap(anio_list)})


def register_api_ejec(app):
    app.register_blueprint(bp)
