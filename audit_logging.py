import logging
import uuid
from datetime import datetime
from flask import request, has_request_context
from flask_login import UserMixin, current_user, user_logged_in, user_logged_out
from extensions import db

logger = logging.getLogger(__name__)


class Logs_User(UserMixin, db.Model):
    """Modelo simple para almacenar eventos de auditoría.

    Campos:
      - id: PK
      - ip_user: dirección IP (clave única en el ejemplo)
      - user: nombre/username
      - log: texto corto del evento
      - tiempo: timestamp o cadena con el tiempo
    """
    __tablename__ = 'Log_users'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    ip_user = db.Column(db.String(50), unique=True, nullable=False)
    user = db.Column(db.String(200), nullable=True)
    log = db.Column(db.String(50), nullable=True)
    tiempo = db.Column(db.String(50), nullable=True)


def create_table(app=None):
    """Create the `Log_users` table in the database if it does not exist.

    If `app` is provided, runs inside the app context. Uses SQLAlchemy
    metadata from `Logs_User` and `extensions.db`.
    """
    if db is None:
        raise RuntimeError("extensions.db is not available; cannot create table")

    def _create():
        try:
            Logs_User.__table__.create(bind=db.engine, checkfirst=True)
            logger.info("Log_users table ensured in the database")
        except Exception as e:
            logger.exception(f"Failed to create Log_users table: {e}")

    if app is not None:
        with app.app_context():
            _create()
    else:
        _create()


def init_app(app, ensure_table: bool = False):
    """Initialize audit helper for the Flask app.

    - If `ensure_table` is True, attempts to create the table using
      `create_table(app)`.
    """
    # Ensure the module is imported and SQLAlchemy knows the model
    if ensure_table:
        create_table(app)
    # Also attach Flask-Login signals so login/logout events are recorded
    try:
        register_audit_signals(app)
    except Exception:
        logger.exception('Failed to register audit signals during init_app')


__all__ = ["Logs_User", "create_table", "init_app"]


def _gather_request_ip():
    if not has_request_context():
        return None
    try:
        return request.headers.get("X-Forwarded-For", request.remote_addr)
    except Exception:
        return None


def record_audit(log_text: str, user=None, ip: str | None = None, tiempo: datetime | None = None, commit: bool = True):
    """Insert a log row into `Log_users`.

    - `log_text`: short textual description of the event
    - `user`: user object or username string (optional)
    - `ip`: optional override for IP address (if omitted will try to gather from request)
    - `tiempo`: optional datetime or string; if datetime provided it'll be converted to ISO string
    - `commit`: if True, commit the DB session after insert
    """
    if db is None:
        logger.warning("DB not available, skipping audit record")
        return None

    uname = None
    if user is None:
        try:
            uname = getattr(current_user, 'username', None) or getattr(current_user, 'name', None)
        except Exception:
            uname = None
    else:
        # if user is an object with username/name attribute
        uname = getattr(user, 'username', None) or getattr(user, 'name', None) if not isinstance(user, str) else user

    if ip is None:
        ip = _gather_request_ip()

    if tiempo is None:
        tiempo_val = datetime.utcnow().isoformat()
    else:
        tiempo_val = tiempo.isoformat() if isinstance(tiempo, datetime) else str(tiempo)

    try:
        # ensure ip_user is unique (the DB currently enforces uniqueness), so
        # append a short uuid suffix to avoid conflicts when multiple records
        # come from the same IP.
        suffix = uuid.uuid4().hex[:8]
        ip_user_val = f"{ip or 'unknown'}-{suffix}"
        rec = Logs_User(ip_user=ip_user_val, user=uname, log=log_text, tiempo=tiempo_val)
        db.session.add(rec)
        if commit:
            db.session.commit()
        return rec
    except Exception as e:
        logger.exception(f"Failed to write audit record: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return None


def _on_user_logged_in(sender, user):
    try:
        record_audit(log_text='login', user=user)
    except Exception:
        logger.exception('Error recording login event')


def _on_user_logged_out(sender, user):
    try:
        record_audit(log_text='logout', user=user)
    except Exception:
        logger.exception('Error recording logout event')


def register_audit_signals(app=None):
    """Connect Flask-Login signals to audit recorders.

    Call this after you have initialized `extensions.db` with the Flask app.
    If `app` is provided, ensures it runs in the app context when connecting.
    """
    if app is not None:
        # ensure the app context is active when we attach handlers
        with app.app_context():
            user_logged_in.connect(_on_user_logged_in)
            user_logged_out.connect(_on_user_logged_out)
    else:
        user_logged_in.connect(_on_user_logged_in)
        user_logged_out.connect(_on_user_logged_out)

__all__.extend(["record_audit", "register_audit_signals"])

