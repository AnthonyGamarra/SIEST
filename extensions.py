import os
import re

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import create_engine

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login'

_dw_engine = None

_VALID_ANIO = re.compile(r'^20(2[0-9]|3[0-9])$')   # 2020–2039
_VALID_PERIODO = re.compile(r'^(0[1-9]|1[0-2])$')   # 01–12


def validate_anio_periodo(anio, periodo):
    """
    Valida que anio y periodo sean valores seguros para usar en nombres de tabla.
    Lanza ValueError si alguno no cumple el formato esperado.
    """
    anio_str = str(anio).strip()
    periodo_str = str(periodo).strip()
    if not _VALID_ANIO.match(anio_str):
        raise ValueError(f"Año inválido: {anio!r}")
    if not _VALID_PERIODO.match(periodo_str):
        raise ValueError(f"Periodo inválido: {periodo!r}")
    return anio_str, periodo_str


def get_dw_engine():
    """Engine compartido para DW_ESTADISTICA. Pool pequeño y único para toda la app."""
    global _dw_engine
    if _dw_engine is None:
        dw_uri = os.environ.get('DW_DATABASE_URI')
        if not dw_uri:
            raise RuntimeError(
                "La variable de entorno DW_DATABASE_URI no está configurada. "
                "Revisa tu archivo .env o la configuración del servidor."
            )
        _dw_engine = create_engine(
            dw_uri,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_timeout=30,
            echo_pool=False,
        )
    return _dw_engine


def is_consulta_user():
    """
    Retorna True si el usuario autenticado tiene role == 'consulta'.
    Seguro para usar tanto en callbacks Dash como en rutas Flask.
    """
    try:
        from flask_login import current_user
        return getattr(current_user, 'role', None) == 'consulta'
    except Exception:
        return False
