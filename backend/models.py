from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db, login_manager
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app

def dashboard_code_for_user(user, request):

    if not getattr(user, 'is_authenticated', False):
        return ''
    if getattr(user, 'role', None) == 'admin' or getattr(user, 'role', None) == 'admin_red':
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

    def is_hashed(self):
        return bool(self.password) and isinstance(self.password, str) and self.password.startswith('pbkdf2:')

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        if not self.password:
            return False
        if self.is_hashed():
            return check_password_hash(self.password, raw_password)
        return self.password == raw_password

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

    def set_password(self, plain_password):
        try:
            self.password = generate_password_hash(plain_password, method='scrypt')
        except TypeError:
            self.password = generate_password_hash(plain_password, method='pbkdf2:sha256')

    def verify_password(self, plain_password):
        stored = self.password or ''
        if isinstance(stored, (bytes, bytearray)):
            try:
                stored = stored.decode('utf-8')
            except Exception:
                stored = str(stored)

        try:
            if isinstance(stored, str) and (stored.startswith('scrypt:') or stored.startswith('pbkdf2:sha256:') or stored.startswith('pbkdf2:')):
                return check_password_hash(stored, plain_password)
        except Exception:
            pass

        if stored == plain_password:
            try:
                self.password = generate_password_hash(plain_password, method='scrypt')
            except TypeError:
                self.password = generate_password_hash(plain_password, method='pbkdf2:sha256')
            db.session.add(self)
            db.session.commit()
            return True

        return False

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))