from flask import Flask
import sys
from extensions import db, login_manager
from routes import register_routes
from backend.audit_logging import init_app as init_audit

from view_logs import register_logs_blueprint
from sqlalchemy import text
from dashboard import create_dash_app as create_dash_main
from dashboard_eme import create_dash_app as create_dash_eme
import os
from werkzeug.security import generate_password_hash, check_password_hash
import dash_bootstrap_components as dbc

def create_app():
    app = Flask(__name__)

    # CONFIGURACIÓN GENERAL
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:4dm1n@10.0.29.117:5433/Flask_Prueba'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # INICIALIZAR EXTENSIONES
    db.init_app(app)
    login_manager.init_app(app)

    # REGISTRAR RUTAS FLASK
    register_routes(app)
    
    # REGISTRAR BLUEPRINT DE LOGS
    register_logs_blueprint(app)

    # CONECTAR A BD EXISTENTE
    with app.app_context():
        try:
            # Probar conexión
            db.session.execute(text('SELECT 1'))
            # Inicializar el módulo de auditoría y crear la tabla si falta
            init_audit(app, ensure_table=True)
            db.create_all()
            print("Conexión a PostgreSQL exitosa.")
        except Exception as e:
            print("Error al conectar a PostgreSQL:", e)

    # CREAR APP DASH (posibles múltiples instancias)

    # Dashboard principal
    create_dash_main(app, url_base_pathname='/dashboard/')

    # Dashboard alternativo (Emergencia) — usa el módulo dashboard_eme
    create_dash_eme(app, url_base_pathname='/dashboard_alt/')

    # Helper: verificar contraseña y migrar si estaba en texto plano
    def verify_and_migrate_password(user, plain_password):
        """
        Verifica la contraseña del usuario.
        - Si la contraseña en BD ya está hasheada (ej. 'scrypt:' o 'pbkdf2:sha256:'), usa check_password_hash.
        - Si la contraseña en BD está en texto plano y coincide -> la hashea (scrypt o pbkdf2) y actualiza la BD.
        Devuelve True si la contraseña es correcta.
        """
        stored = getattr(user, 'password', '') or ''

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


if __name__ == '__main__':
    # Forzar que los prints se vean en consola inmediatamente
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    app = create_app()
    print('Servidor Flask/Dash corriendo en todas las interfaces')
    print('Abre desde este PC: http://localhost:8050/')
    print('Abre desde otra PC:  http://<tu-IP-local>:8050/')
    app.run(debug=True, host='0.0.0.0', port=8050)