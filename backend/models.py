from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db, login_manager
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app

def dashboard_code_for_user(user, request):

    if not getattr(user, 'is_authenticated', False):
        return ''
    role = getattr(user, 'role', None)
    if role in ('admin', 'admin_red', 'consulta'):
        code = request.form.get('codcas', '') or request.args.get('codcas', '')
    else:
        code = getattr(user, 'dashboard_code', lambda: '')()
    if not code:
        return ''
    from backend.models import encode_code
    return encode_code(code)


def get_serializer():
    return URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'],
        salt='dashboard-code'
    )

def encode_code(code: str) -> str:
    s = get_serializer()
    return s.dumps(code)

def decode_code(token: str, max_age=3600):
    s = get_serializer()
    try:
        return s.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


class User(UserMixin, db.Model):
    __tablename__ = 'users' 
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=True)
    name = db.Column(db.String(50), nullable=True)
    lastname = db.Column(db.String(50), nullable=True)
    codcas = db.Column(db.String(50), nullable=True)
    role = db.Column(db.String(20), nullable=True)
    code_red = db.Column(db.String(50), nullable=True)
    flag = db.Column(db.String(1), nullable=False, default='1', server_default='1')

    def is_hashed(self):
        """Verifica si la contraseña está hasheada."""
        return bool(self.password) and isinstance(self.password, str) and (
            self.password.startswith('scrypt:') or 
            self.password.startswith('pbkdf2:')
        )

    def set_password(self, plain_password):
        """
        Establece una nueva contraseña hasheada.
        NO hace commit automático - debe hacerse externamente.
        """
        try:
            self.password = generate_password_hash(plain_password, method='scrypt')
        except (TypeError, ValueError):
            # Fallback si scrypt no está disponible
            self.password = generate_password_hash(plain_password, method='pbkdf2:sha256')

    def verify_password(self, plain_password):
        """
        Verifica si la contraseña proporcionada coincide.
        NO modifica la base de datos.
        """
        if not self.password or not plain_password:
            return False
            
        stored = self.password
        if isinstance(stored, (bytes, bytearray)):
            try:
                stored = stored.decode('utf-8')
            except Exception:
                stored = str(stored)

        # Si está hasheada, verificar con check_password_hash
        if isinstance(stored, str) and (
            stored.startswith('scrypt:') or 
            stored.startswith('pbkdf2:sha256:') or 
            stored.startswith('pbkdf2:')
        ):
            try:
                return check_password_hash(stored, plain_password)
            except Exception as e:
                print(f"Error verificando contraseña hasheada: {e}")
                return False
        
        # Si es texto plano (legacy), comparar directamente
        # NOTA: No actualizar automáticamente aquí para evitar commits inesperados
        return stored == plain_password

    def dashboard_code(self):
        """
        Return a formatted code to use in dashboard URL.
        If codcas is numeric, zero-pad to 3 digits (e.g. 1 -> "001").
        If empty/None, return empty string.
        """
        if not getattr(self, 'codcas', None):
            return ''
        s = str(self.codcas)
        if s.isdigit():
            return s.zfill(3)
        return s

    @property
    def is_active(self):
        # Integrates with Flask-Login to disable access when flag is 0
        return getattr(self, 'flag', '1') == '1'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class SurveyResponse(db.Model):
    """Stores the validation outcome for each survey variable a user reviews."""

    __tablename__ = 'survey_responses'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('public.users.id'), nullable=False)
    user_username = db.Column(db.String(50), nullable=False)
    user_fullname = db.Column(db.String(120), nullable=False)
    user_role = db.Column(db.String(20), nullable=False)
    codcas = db.Column(db.String(50), nullable=True)
    section = db.Column(db.String(40), nullable=False)
    area = db.Column(db.String(40), nullable=False)
    category_id = db.Column(db.String(80), nullable=False)
    category_label = db.Column(db.String(160), nullable=False)
    variable_id = db.Column(db.String(80), nullable=False)
    variable_label = db.Column(db.String(160), nullable=False)
    status = db.Column(db.String(10), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    user = db.relationship('User', backref=db.backref('survey_responses', lazy=True))


class SurveyModule(db.Model):
    __tablename__ = 'modulo'
    __table_args__ = {'schema': 'public'}

    id = db.Column('id_modulo', db.Integer, primary_key=True)
    nombre = db.Column('nombre_modulo', db.String(100), nullable=False)
    active = db.Column(db.Integer, nullable=False, server_default='1', default=1)

    categorias = db.relationship(
        'SurveyCategory',
        back_populates='modulo',
        order_by='SurveyCategory.nombre',
        lazy='selectin'
    )


class SurveyCategory(db.Model):
    __tablename__ = 'categoria'
    __table_args__ = {'schema': 'public'}

    id = db.Column('id_categoria', db.Integer, primary_key=True)
    modulo_id = db.Column('id_modulo', db.Integer, db.ForeignKey('public.modulo.id_modulo'), nullable=False)
    nombre = db.Column('nombre_categoria', db.String(100), nullable=False)
    active = db.Column(db.Integer, nullable=False, server_default='1', default=1)

    modulo = db.relationship('SurveyModule', back_populates='categorias')
    subcategorias = db.relationship(
        'SurveySubcategory',
        back_populates='categoria',
        order_by='SurveySubcategory.nombre',
        lazy='selectin'
    )


class SurveySubcategory(db.Model):
    __tablename__ = 'subcategoria'
    __table_args__ = {'schema': 'public'}

    id = db.Column('id_subcategoria', db.Integer, primary_key=True)
    categoria_id = db.Column('id_categoria', db.Integer, db.ForeignKey('public.categoria.id_categoria'), nullable=False)
    nombre = db.Column('nombre_subcategoria', db.String(150), nullable=True)
    active = db.Column(db.Integer, nullable=False, server_default='1', default=1)

    categoria = db.relationship('SurveyCategory', back_populates='subcategorias')
    variables = db.relationship(
        'SurveyVariable',
        back_populates='subcategoria',
        order_by='SurveyVariable.nombre',
        lazy='selectin'
    )


class SurveyVariable(db.Model):
    __tablename__ = 'variable'
    __table_args__ = {'schema': 'public'}

    id = db.Column('id_variable', db.Integer, primary_key=True)
    subcategoria_id = db.Column('id_subcategoria', db.Integer, db.ForeignKey('public.subcategoria.id_subcategoria'), nullable=False)
    nombre = db.Column('nombre_variable', db.Text, nullable=True)
    active = db.Column(db.Integer, nullable=False, server_default='1', default=1)

    subcategoria = db.relationship('SurveySubcategory', back_populates='variables')


class ClasificacionCamas(db.Model):
    __tablename__ = 'clasificacion_camas'
    __table_args__ = {'schema': 'public'}

    id = db.Column('id', db.Integer, primary_key=True)
    codcas = db.Column('codcas', db.String(50), nullable=False)
    camcod = db.Column('camcod', db.String(50), nullable=False)
    arehoscod = db.Column('arehoscod', db.String(50), nullable=False)
    habcod = db.Column('habcod', db.String(50), nullable=False)
    servhoscod = db.Column('servhoscod', db.String(50), nullable=False)
    descripcion = db.Column('descripcion', db.String(200), nullable=False)
