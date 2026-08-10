from dotenv import load_dotenv
load_dotenv()

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
from dashboard_diag import create_dash_app as create_dash_diag
from dashboard_odo import create_dash_app as create_dash_odo
from dashboard_cq import create_dash_app as create_dash_cq
from dashboard_cq_trans import create_dash_app as create_dash_cq_trans
from dashboard_hosp import create_dash_app as create_dash_hosp
from dashboard_proc import create_dash_app as create_dash_proc
from dashboard_ejec import create_dash_app as create_dash_ejec
from tramas import create_dash_app as create_dash_tramas
from busqueda_paciente import create_dash_app as create_dash_busqueda_paciente
from api_ejec import register_api_ejec
import os
from werkzeug.security import generate_password_hash, check_password_hash


def create_app():
    app = Flask(__name__)

    # =============================
    # CONFIGURACIÓN GENERAL
    # =============================
    secret_key = os.environ.get('SECRET_KEY', '')
    if not secret_key or secret_key == 'dev-secret-key-change-me':
        raise RuntimeError(
            "SECRET_KEY no está configurada o usa el valor por defecto inseguro. "
            "Define SECRET_KEY como variable de entorno antes de iniciar la aplicación."
        )
    app.config['SECRET_KEY'] = secret_key

    app_db_uri = os.environ.get('APP_DATABASE_URI')
    if not app_db_uri:
        raise RuntimeError(
            "La variable de entorno APP_DATABASE_URI no está configurada. "
            "Revisa tu archivo .env o la configuración del servidor."
        )
    app.config['SQLALCHEMY_DATABASE_URI'] = app_db_uri

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # =============================
    # CONFIGURACIÓN DEL POOL (CRÍTICO PARA CARGA)
    # =============================
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_size": 5,
        "max_overflow": 5,
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
    register_api_ejec(app)

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
    create_dash_main(app, url_base_pathname='/dashboard_embed/')
    create_dash_eme(app, url_base_pathname='/dashboard_alt_embed/')
    create_dash_nm(app, url_base_pathname='/dashboard_nm_embed/')
    create_dash_diag(app, url_base_pathname='/diag_cap_embed/')
    create_dash_odo(app, url_base_pathname='/dashboard_odo_embed/')
    create_dash_cq(app, url_base_pathname='/dashboard_cq_embed/')
    create_dash_cq_trans(app, url_base_pathname='/dashboard_cq_trans_embed/')
    create_dash_hosp(app, url_base_pathname='/dashboard_hosp_embed/')
    create_dash_proc(app, url_base_pathname='/dashboard_proc_embed/')
    create_dash_ejec(app, url_base_pathname='/dashboard_ejec_embed/')
    create_dash_tramas(app, url_base_pathname='/tramas_embed/')
    create_dash_busqueda_paciente(app, url_base_pathname='/busqueda_paciente_embed/')

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
    app.run(debug=True, host='0.0.0.0', port=8080)
