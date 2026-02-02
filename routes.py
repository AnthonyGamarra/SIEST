from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from backend.models import User
from flask import current_app
from bi import get_bi_url
from backend.models import dashboard_code_for_user
from secure_code import encode_code, decode_code
from backend.centro_asistencial import get_centro_asistencial
from backend.centro_asistencial import get_centro_asistencial_by_code_red
from backend.centro_asistencial import getNombreCentroAsistencial
from backend.centro_asistencial import get_redes_asistenciales


def _format_select_options(df, code_key, label_key):
	if df is None:
		return []

	try:
		records = df.to_dict(orient='records')
	except AttributeError:
		return []

	formatted = []
	for record in records:
		code = record.get(code_key)
		label = record.get(label_key)
		if code is None or label is None:
			continue
		code_str = str(code).strip()
		label_str = str(label).strip()
		if code_str and label_str:
			formatted.append({'code': code_str, 'label': label_str})
	return formatted


def register_routes(app):

	
	bp = Blueprint('main', __name__)
	@bp.app_context_processor
	def inject_flags():
		return {
			'has_reportes_gerenciales': 'main.reportes_gerenciales' in current_app.view_functions,
			'dashboard_code_for_user': lambda: dashboard_code_for_user(current_user, request),
			'getNombreCentroAsistencial': lambda: getNombreCentroAsistencial (request),
		}
	


	@bp.route('/', methods=['GET', 'POST'])
	@login_required
	def index():
		df = get_centro_asistencial()
		code_red=current_user.code_red
		df_by_code_red = (get_centro_asistencial_by_code_red(code_red) if code_red  else df)
		centros_asistenciales = df.to_dict(orient='records')
		centros_asistenciales_by_code_red = df_by_code_red.to_dict(orient='records')
		return render_template('index.html', centros_asistenciales=centros_asistenciales, centros_asistenciales_by_code_red=centros_asistenciales_by_code_red)


	@bp.route('/register', methods=['GET', 'POST'])
	@login_required
	def register():
		if current_user.role != 'admin':
			flash('No tienes permisos para registrar usuarios', 'danger')
			return redirect(url_for('main.index'))
		
		centros_df = get_centro_asistencial()
		redes_df = get_redes_asistenciales()
		centros_options = _format_select_options(centros_df, 'cenasicod', 'cenasides')
		red_options = _format_select_options(redes_df, 'redasiscod', 'redasisdes')
		
		if request.method == 'POST':
			name = request.form.get('nombre', '')
			lastname = request.form.get('apellido', '')
			codcas = request.form.get('codcas', '')
			username = request.form.get('username', '')
			password = request.form.get('password', '')
			role = request.form.get('rol', 'user')
			code_red = request.form.get('code_red', '')

			
			if User.query.filter_by(username=username).first():
				flash('El usuario ya existe', 'danger')
			else:
				new_user = User(username=username)
				new_user.set_password(password)
				new_user.name = name
				new_user.lastname = lastname
				new_user.codcas = codcas
				new_user.code_red = code_red
				new_user.role = role
				db.session.add(new_user)
				db.session.commit()
				flash('Usuario creado exitosamente', 'success')
				return redirect(url_for('main.index'))
		
		return render_template(
			'register.html',
			show_modules=False,
			centros_options=centros_options,
			red_options=red_options,
		)

	@bp.route('/change_password', methods=['GET', 'POST'])
	@login_required
	def change_password():
		if request.method == 'POST':
			current_password = request.form.get('current_password', '').strip()
			new_password = request.form.get('new_password', '').strip()
			confirm_password = request.form.get('confirm_password', '').strip()
			errors = []

			if not current_password or not new_password or not confirm_password:
				errors.append('Todos los campos son obligatorios.')
			if new_password and len(new_password) < 8:
				errors.append('La nueva contraseña debe tener al menos 8 caracteres.')
			if new_password and confirm_password and new_password != confirm_password:
				errors.append('La nueva contraseña y la confirmación no coinciden.')

			for error in errors:
				flash(error, 'danger')

			if not errors:
				if not current_user.verify_password(current_password):
					flash('La contraseña actual no es correcta.', 'danger')
				else:
					current_user.set_password(new_password)
					db.session.add(current_user)
					db.session.commit()
					flash('Contraseña actualizada correctamente.', 'success')
					return redirect(url_for('main.index'))

		return render_template('change_password.html', show_modules=False)

	@bp.route('/api/redes/<code_red>/centros', methods=['GET'])
	@login_required
	def centros_by_red_api(code_red):
		if current_user.role not in ('admin', 'admin_red'):
			return jsonify({'error': 'No autorizado'}), 403

		if not code_red:
			return jsonify({'centers': []})

		df = get_centro_asistencial_by_code_red(code_red)
		centers = _format_select_options(df, 'cenasicod', 'cenasides')
		return jsonify({'centers': centers})

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
		code = ""
		if current_user.role == 'admin':
			code =  request.args.get('codcas', '')
		elif current_user.role == 'user':
			code = getattr(current_user, 'dashboard_code', lambda: '')()

		if code:
			token = encode_code(code)
			return redirect(f'/dashboard/{token}/')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard/')
	@login_required
	def dashboard_index():
		code = ""
		if current_user.role == 'admin':
			code = request.form.get('codcas', '') 
		elif current_user.role == 'user':
			code = getattr(current_user, 'dashboard_code', lambda: '')()
		if code:
			token = encode_code(code)
			return redirect(f'/dashboard/{token}/')
		flash('No hay código asociado al usuario para mostrar el dashboard.', 'warning')
		return redirect(url_for('main.index'))
	
	@bp.route('/dashboard_nm', endpoint='dashboard_nm_redirect')
	@login_required
	def dashboard_nm_redirect():
		code = ""
		if current_user.role == 'admin':
			code =  request.args.get('codcas', '')
		elif current_user.role == 'user':
			code = getattr(current_user, 'dashboard_code', lambda: '')()

		if code:
			token = encode_code(code)
			return redirect(f'/dashboard_nm/{token}/')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard_nm/')
	@login_required
	def dashboard_nm_index():
		code = ""
		if current_user.role == 'admin':
			code = request.form.get('codcas', '') 
		elif current_user.role == 'user':
			code = getattr(current_user, 'dashboard_code', lambda: '')()
		if code:
			token = encode_code(code)
			return redirect(f'/dashboard_nm/{token}/')
		flash('No hay código asociado al usuario para mostrar el dashboard.', 'warning')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard_alt', endpoint='dashboard_alt_redirect')
	@login_required
	def dashboard_alt_redirect():
		code = ""
		if current_user.role == 'admin':
			code = request.form.get('codcas', '') 
		elif current_user.role == 'user':
			code = getattr(current_user, 'dashboard_code', lambda: '')()
		if code:
			return redirect(f'/dashboard_alt/{code}/')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard_alt/')
	@login_required
	def dashboard_alt_index():
		code = ""
		if current_user.role == 'admin':
			code = request.form.get('codcas', '') 
		elif current_user.role == 'user':
			code = getattr(current_user, 'dashboard_code', lambda: '')()
		if code:
			return redirect(f'/dashboard_alt/{code}/')
		flash('No hay código asociado al usuario para mostrar el dashboard alternativo.', 'warning')
		return redirect(url_for('main.index'))
	
	def redirect_with(target_path, warning_msg='No hay código asociado al usuario para mostrar el dashboard.'):
		code = ""
		if current_user.role == 'admin':
			code = request.form.get('codcas', '') or request.args.get('codcas', '')
		elif current_user.role == 'user':
			code = getattr(current_user, 'dashboard_code', lambda: '')()
		if code:
			return redirect(f'/dashboard/dash{target_path}/?codcas={code}')
		flash(warning_msg, 'warning')
		return redirect(url_for('main.index'))

	def get_center_name_by_code(code):
		if not code:
			return ''
		try:
			df = get_centro_asistencial()
			matches = df[df['cenasicod'].astype(str) == str(code)]
			if not matches.empty:
				return matches.iloc[0]['cenasides']
		except Exception as exc:
			current_app.logger.warning('No se pudo obtener el nombre del centro %s: %s', code, exc)
		return ''

	@bp.route('/ce/', methods=['GET'])
	@login_required
	def ce_index():
		token = dashboard_code_for_user(current_user, request)
		if token:
			return redirect(url_for('main.ce_menu', token=token))
		flash('No hay código asociado al usuario para mostrar el menú de Consulta Externa.', 'warning')
		return redirect(url_for('main.index'))

	@bp.route('/ce/<token>', methods=['GET'])
	@bp.route('/ce/<token>/', methods=['GET'])
	@login_required
	def ce_menu(token):
		code = decode_code(token)
		if not code:
			flash('El código seleccionado es inválido o expiró.', 'warning')
			return redirect(url_for('main.index'))
		center_name = get_center_name_by_code(code)
		medical_url = f'/dashboard/{token}/'
		non_medical_url = f'/dashboard_nm/{token}/'
		return render_template(
			'Ce.html',
			show_modules=False,
			dashboard_token=token,
			codcas=code,
			center_name=center_name,
			medical_url=medical_url,
			non_medical_url=non_medical_url,
		)

	@bp.route('/dashboard_eme_prioridad_<prioridad>/<codcas>')
	@login_required
	def dashboard_eme_prioridad_redirect(prioridad, codcas):
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
