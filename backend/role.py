import logging
from extensions import db

logger = logging.getLogger(__name__)

class Role(db.Model):
    """Modelo para almacenar roles de usuarios.

    Campos:
      - id: PK autoincremental
      - name_role: Nombre del rol (admin, user, etc.)
      - description: Descripción del rol
    """
    __tablename__ = 'role'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name_role = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f"<Role {self.name_role}>"


def create_table(app=None):
    """Crea la tabla 'role' en la base de datos si no existe.

    Si se proporciona `app`, ejecuta dentro del contexto de la aplicación.
    """
    if db is None:
        raise RuntimeError("extensions.db no disponible; no se puede crear la tabla")

    def _create():
        try:
            Role.__table__.create(bind=db.engine, checkfirst=True)
            logger.info("Tabla 'role' asegurada en la base de datos")
        except Exception as e:
            logger.exception(f"Error al crear tabla 'role': {e}")

    if app is not None:
        with app.app_context():
            _create()
    else:
        _create()


def init_app(app, ensure_table: bool = False):
    """Inicializa el módulo de roles.

    - Si `ensure_table` es True, intenta crear la tabla usando `create_table(app)`.
    """
    if ensure_table:
        create_table(app)


__all__ = ["Role", "create_table", "init_app"]

