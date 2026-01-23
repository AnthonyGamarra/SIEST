from flask import Flask
import sys
from extensions import db, login_manager
from routes import register_routes
from backend.audit_logging import init_app as init_audit

from view_logs import register_logs_blueprint
from sqlalchemy import text
from dashboard import create_dash_app as create_dash_main
from dashboard_eme import create_dash_app as create_dash_eme
from dashboard_nm import create_dash_app as create_dash_nm
import os
from werkzeug.security import generate_password_hash, check_password_hash


def create_app():
    app = Flask(__name__)

    # =============================
    # CONFIGURACIÓN GENERAL
    # =============================
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')

    app.config['SQLALCHEMY_DATABASE_URI'] = (
        'postgresql+psycopg2://postgres:4dm1n@10.0.29.117:5433/Flask_Prueba'
    )

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # =============================
    # CONFIGURACIÓN DEL POOL (CRÍTICO PARA CARGA)
    # =============================
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }

    # =============================
    # INICIALIZAR EXTENSIONES
    # =============================
    db.init_app(app)
    login_manager.init_app(app)

    # =============================
    # REGISTRAR RUTAS
    # =============================
    register_routes(app)
    register_logs_blueprint(app)

    # =============================
    # INICIALIZACIÓN DE BD
    # =============================
    with app.app_context():
        try:
            db.session.execute(text('SELECT 1'))
            init_audit(app, ensure_table=True)
            db.create_all()
            print("Conexión a PostgreSQL exitosa.")
        except Exception as e:
            print("Error al conectar a PostgreSQL:", e)
            raise

    # =============================
    # DASHBOARDS
    # =============================
    create_dash_main(app, url_base_pathname='/dashboard/')
    create_dash_eme(app, url_base_pathname='/dashboard_alt/')
    create_dash_nm(app, url_base_pathname='/dashboard_nm/')

    # =============================
    # HELPER DE PASSWORD
    # =============================
    def verify_and_migrate_password(user, plain_password):
        stored = getattr(user, 'password', '') or ''

        if isinstance(stored, (bytes, bytearray)):
            try:
                stored = stored.decode('utf-8')
            except Exception:
                stored = str(stored)

        try:
            if isinstance(stored, str) and (
                stored.startswith('scrypt:')
                or stored.startswith('pbkdf2:sha256:')
                or stored.startswith('pbkdf2:')
            ):
                return check_password_hash(stored, plain_password)
        except Exception:
            pass

        if stored == plain_password:
            try:
                new_hash = generate_password_hash(plain_password, method='scrypt')
            except TypeError:
                new_hash = generate_password_hash(plain_password, method='pbkdf2:sha256')
            except Exception:
                new_hash = generate_password_hash(plain_password)

            user.password = new_hash
            db.session.add(user)
            db.session.commit()
            return True

        return False

    app.verify_and_migrate_password = verify_and_migrate_password

    return app


# =============================
# INSTANCIA DE APP PARA WAITRESS
# =============================
app = create_app()

# =============================
# SOLO PARA DESARROLLO LOCAL
# =============================
if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    print('⚠️  MODO DESARROLLO (NO USAR EN PRODUCCIÓN)')
    print('http://localhost:8050/')
    app.run(debug=True, host='0.0.0.0', port=8050)
