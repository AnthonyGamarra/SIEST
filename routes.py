from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from backend.models import User

from bi import get_bi_url

def register_routes(app):

	bp = Blueprint('main', __name__)
	@bp.app_context_processor
	def inject_flags():
		return {'has_reportes_gerenciales': 'main.reportes_gerenciales' in current_app.view_functions}

	@bp.route('/')
	def index():
		return render_template('index.html')

	@bp.route('/register', methods=['GET', 'POST'])
	@login_required
	def register():
		if current_user.role != 'admin':
			flash('No tienes permisos para registrar usuarios', 'danger')
			return redirect(url_for('main.index'))
		
		
		
		if request.method == 'POST':
			name = request.form.get('nombre', '')
			lastname = request.form.get('apellido', '')
			codcas = request.form.get('codcas', '')
			username = request.form.get('username', '')
			password = request.form.get('password', '')
			role = request.form.get('rol', 'user')
			
			if User.query.filter_by(username=username).first():
				flash('El usuario ya existe', 'danger')
			else:
				new_user = User(username=username)
				new_user.set_password(password)
				new_user.name = name
				new_user.lastname = lastname
				new_user.codcas = codcas
				new_user.role = role
				db.session.add(new_user)
				db.session.commit()
				flash('Usuario creado exitosamente', 'success')
				return redirect(url_for('main.index'))
		
		return render_template('register.html', show_modules=False)

	@bp.route('/login', methods=['GET', 'POST'])
	def login():
		if request.method == 'POST':
			username = request.form.get('username', '')
			password = request.form.get('password', '')
			user = User.query.filter_by(username=username).first()
			verify = getattr(current_app, 'verify_and_migrate_password', None)
			if user and verify and verify(user, password):
				login_user(user)
				return redirect(url_for('main.index'))
			flash('Credenciales inválidas', 'danger')
		return render_template('login.html')

	@bp.route('/logout')
	@login_required
	def logout():
		logout_user()
		session.clear()
		flash('Cierre de sesión exitoso.', 'success')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard', endpoint='dashboard_redirect')
	@login_required
	def dashboard_redirect():
		code = getattr(current_user, 'dashboard_code', lambda: '')()
		if code:
			return redirect(f'/dashboard/{code}/')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard/')
	@login_required
	def dashboard_index():
		code = getattr(current_user, 'dashboard_code', lambda: '')()
		if code:
			return redirect(f'/dashboard/{code}/')
		flash('No hay código asociado al usuario para mostrar el dashboard.', 'warning')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard_alt', endpoint='dashboard_alt_redirect')
	@login_required
	def dashboard_alt_redirect():
		code = getattr(current_user, 'dashboard_code', lambda: '')()
		if code:
			return redirect(f'/dashboard_alt/{code}/')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard_alt/')
	@login_required
	def dashboard_alt_index():
		code = getattr(current_user, 'dashboard_code', lambda: '')()
		if code:
			return redirect(f'/dashboard_alt/{code}/')
		flash('No hay código asociado al usuario para mostrar el dashboard alternativo.', 'warning')
		return redirect(url_for('main.index'))
	
	def redirect_with(target_path, warning_msg='No hay código asociado al usuario para mostrar el dashboard.'):
		code = getattr(current_user, 'dashboard_code', lambda: '')()
		if code:
			return redirect(f'/dashboard/dash{target_path}/?codcas={code}')
		flash(warning_msg, 'warning')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard_eme_prioridad_<prioridad>/<codcas>')
	@login_required
	def dashboard_eme_prioridad_redirect(prioridad, codcas):
		# Redirecciona a la ruta interna del dashboard de emergencia
		# Ejemplo: /dashboard_alt/prioridad_1/001
		qs = request.query_string.decode()
		return redirect(f"/dashboard_alt/prioridad_{prioridad}/{codcas}?{qs}")

	@bp.route('/total_atenciones/')
	@login_required
	def total_atenciones_redirect():
		return redirect_with('/total_atenciones', 'No hay código asociado al usuario para mostrar total_atenciones.')

	@bp.route('/total_atendidos/')
	@login_required
	def total_atendidos_redirect():
		return redirect_with('/total_atendidos', 'No hay código asociado al usuario para mostrar total_atendidos.')

	@bp.route('/total_citados/')
	@login_required
	def total_citados_redirect():
		return redirect_with('/total_citados', 'No hay código asociado al usuario para mostrar total_citados.')

	@bp.route('/total_desercion/')
	@login_required
	def total_desercion_redirect():
		return redirect_with('/total_desercion', 'No hay código asociado al usuario para mostrar total_desercion.')

	@bp.route('/total_horas_efectivas/')
	@login_required
	def total_horas_efectivas_redirect():
		return redirect_with('/total_horas_efectivas', 'No hay código asociado al usuario para mostrar total_horas_efectivas.')

	@bp.route('/total_horas_programadas/')
	@login_required
	def total_horas_programadas_redirect():
		return redirect_with('/total_horas_programadas', 'No hay código asociado al usuario para mostrar total_horas_programadas.')

	@bp.route('/total_medicos/')
	@login_required
	def total_medicos_redirect():
		return redirect_with('/total_medicos', 'No hay código asociado al usuario para mostrar total_medicos.')
	
	@bp.route('/reportes_gerenciales/', endpoint='reportes_gerenciales')
	@login_required
	def reportes_gerenciales():
		bi_url = get_bi_url()
		back_url = url_for('main.index')
		return render_template('reportes_gerenciales.html', bi_url=bi_url, show_modules=False, back_url=back_url)
	
	app.register_blueprint(bp)
