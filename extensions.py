from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import create_engine

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login'

_dw_engine = None

def get_dw_engine():
    """Engine compartido para DW_ESTADISTICA. Pool pequeño y único para toda la app."""
    global _dw_engine
    if _dw_engine is None:
        _dw_engine = create_engine(
            'postgresql+psycopg2://app_user:sge02@10.0.29.117:5433/DW_ESTADISTICA',
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_timeout=30,
            echo_pool=False,
        )
    return _dw_engine