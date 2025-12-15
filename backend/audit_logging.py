import logging
import uuid
from datetime import datetime
from flask import request, has_request_context
from flask_login import UserMixin, current_user, user_logged_in, user_logged_out
from extensions import db
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Zona horaria de Lima (UTC-5)
LIMA_TZ = ZoneInfo("America/Lima")


class Logs_User(UserMixin, db.Model):
    """Modelo para almacenar eventos de auditoría de usuarios.

    Campos:
      - id: PK
      - ip_user: dirección IP única con sufijo UUID
      - user: nombre/username del usuario
      - log: descripción del evento (login, logout, etc)
      - peticiones: método HTTP (GET, POST, etc)
      - urls: URL accedida
      - fecha: timestamp del evento
      - status: estado del evento (success, error, denied)
      - user_role: rol del usuario (admin, user, etc)
      - navegador: información del navegador y OS
    """
    __tablename__ = 'Log_users'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    ip_user = db.Column(db.String(100), unique=True, nullable=False)
    user = db.Column(db.String(255), nullable=True)
    log = db.Column(db.String(100), nullable=True)
    peticiones = db.Column(db.String(20), nullable=True)  # GET, POST, PUT, DELETE, etc
    urls = db.Column(db.String(500), nullable=True)
    fecha = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(LIMA_TZ), nullable=False)
    status = db.Column(db.String(50), nullable=True)  # success, error, denied
    user_role = db.Column(db.String(50), nullable=True)  # admin, user, etc
    navegador = db.Column(db.String(255), nullable=True)


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


def _detect_browser(user_agent):
    """Detecta el navegador y sistema operativo del User-Agent de forma precisa."""
    if not user_agent:
        return "Desconocido"
    
    import re
    
    browser_name = "Desconocido"
    browser_version = ""
    
    # IMPORTANTE: El orden importa. Verificar Edge ANTES que Chrome
    # porque los nuevos navegadores Edge contienen "Chrome" en el User-Agent
    
    # Edge (Chromium) - detectar primero
    if re.search(r'Edg(?:e)?/(\d+)', user_agent):
        match = re.search(r'Edg(?:e)?/(\d+)', user_agent)
        if match:
            browser_name = "Microsoft Edge"
            browser_version = match.group(1)
    # Edge (antiguo, basado en EdgeHTML)
    elif "Edge" in user_agent:
        match = re.search(r'Edge/(\d+)', user_agent)
        if match:
            browser_name = "Microsoft Edge (antiguo)"
            browser_version = match.group(1)
    # Chrome
    elif re.search(r'Chrome/(\d+)', user_agent):
        match = re.search(r'Chrome/(\d+)', user_agent)
        if match:
            browser_name = "Google Chrome"
            browser_version = match.group(1)
    # Firefox
    elif re.search(r'Firefox/(\d+)', user_agent):
        match = re.search(r'Firefox/(\d+)', user_agent)
        if match:
            browser_name = "Mozilla Firefox"
            browser_version = match.group(1)
    # Safari
    elif re.search(r'Safari/(\d+)', user_agent):
        match = re.search(r'Version/(\d+)', user_agent)
        if match:
            browser_name = "Apple Safari"
            browser_version = match.group(1)
    # Opera
    elif re.search(r'OPR/(\d+)', user_agent):
        match = re.search(r'OPR/(\d+)', user_agent)
        if match:
            browser_name = "Opera"
            browser_version = match.group(1)
    
    # Detectar OS - más completo
    os_name = "Desconocido"
    
    if re.search(r'Windows NT 11', user_agent):
        os_name = "Windows 11"
    elif re.search(r'Windows NT 10\.0', user_agent):
        os_name = "Windows 10"
    elif re.search(r'Windows NT 6\.3', user_agent):
        os_name = "Windows 8.1"
    elif re.search(r'Windows NT 6\.2', user_agent):
        os_name = "Windows 8"
    elif re.search(r'Windows NT 6\.1', user_agent):
        os_name = "Windows 7"
    elif re.search(r'Windows NT 5\.1', user_agent):
        os_name = "Windows XP"
    elif re.search(r'Mac OS X 10_(\d+)', user_agent):
        match = re.search(r'Mac OS X 10_(\d+)', user_agent)
        version = match.group(1) if match else "?"
        os_name = f"macOS 10.{version}"
    elif re.search(r'Mac OS X', user_agent):
        os_name = "macOS"
    elif re.search(r'Android (\d+)', user_agent):
        match = re.search(r'Android (\d+)', user_agent)
        version = match.group(1) if match else ""
        os_name = f"Android {version}"
    elif "Linux" in user_agent:
        os_name = "Linux"
    elif "iPhone" in user_agent or "iPad" in user_agent:
        os_name = "iOS"
    
    # Formatear resultado
    if browser_version:
        result = f"{browser_name} v{browser_version} ({os_name})"
    else:
        result = f"{browser_name} ({os_name})"
    
    return result


def record_audit(log_text: str, user=None, ip: str | None = None, fecha: datetime | None = None, 
                 peticiones: str | None = None, urls: str | None = None, status: str = "success",
                 user_role: str | None = None, navegador: str | None = None, commit: bool = True):
    """Insert a log row into `Log_users`.

    - `log_text`: short textual description of the event
    - `user`: user object or username string (optional)
    - `ip`: optional override for IP address (if omitted will try to gather from request)
    - `fecha`: optional datetime; if None uses current UTC time
    - `peticiones`: HTTP method (GET, POST, etc)
    - `urls`: URL accessed
    - `status`: event status (success, error, denied)
    - `user_role`: user role (admin, user, etc)
    - `navegador`: browser and OS info
    - `commit`: if True, commit the DB session after insert
    """
    if db is None:
        logger.warning("DB not available, skipping audit record")
        return None

    uname = None
    role = user_role
    if user is None:
        try:
            uname = getattr(current_user, 'username', None) or getattr(current_user, 'name', None)
            if role is None:
                role = getattr(current_user, 'role', None)
        except Exception:
            uname = None
    else:
        # if user is an object with username/name attribute
        if not isinstance(user, str):
            uname = getattr(user, 'username', None) or getattr(user, 'name', None)
            if role is None:
                role = getattr(user, 'role', None)
        else:
            uname = user

    if ip is None:
        ip = _gather_request_ip()

    if fecha is None:
        # Usar UTC Lima (America/Lima)
        fecha_val = datetime.now(LIMA_TZ)
    else:
        fecha_val = fecha if isinstance(fecha, datetime) else datetime.fromisoformat(str(fecha))

    # Auto-detectar método HTTP y URL del request si no se proporcionan
    if has_request_context():
        if peticiones is None:
            peticiones = request.method
        if urls is None:
            urls = request.path
        if navegador is None:
            navegador = _detect_browser(request.headers.get('User-Agent', ''))

    try:
        # ensure ip_user is unique (the DB currently enforces uniqueness), so
        # append a short uuid suffix to avoid conflicts when multiple records
        # come from the same IP.
        suffix = uuid.uuid4().hex[:8]
        ip_user_val = f"{ip or 'unknown'}-{suffix}"
        rec = Logs_User(
            ip_user=ip_user_val, 
            user=uname, 
            log=log_text, 
            peticiones=peticiones,
            urls=urls,
            fecha=fecha_val,
            status=status,
            user_role=role,
            navegador=navegador
        )
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

