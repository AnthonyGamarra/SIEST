import os
import csv
import io
import zipfile

import joblib
import pandas as pd
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app, jsonify, Response, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from backend.models import User
from sqlalchemy import func, text
from sqlalchemy.orm import joinedload
from bi import get_bi_url
from backend.models import dashboard_code_for_user
from secure_code import encode_code, decode_code
from backend.centro_asistencial import get_centro_asistencial
from backend.centro_asistencial import get_centro_asistencial_by_code_red
from backend.centro_asistencial import getNombreCentroAsistencial
from backend.centro_asistencial import get_redes_asistenciales
from collections import Counter
from backend.models import (
	SurveyResponse,
	SurveyModule,
	SurveyCategory,
	SurveySubcategory,
	SurveyVariable,
)


DESERCION_MODEL_FILENAME = 'modelo_desercion.pkl'
def _get_dw_engine():
	from extensions import get_dw_engine
	return get_dw_engine()


def _is_valid_pdf(data):
	"""Valida la firma binaria real del archivo (%PDF-), no solo la extensión
	o el mimetype declarados por el navegador (ambos son fácilmente falseables)."""
	return bool(data) and data.lstrip(b'\x00\xef\xbb\xbf')[:5] == b'%PDF-'


def _safe_pdf_filename(raw_name, fallback_id=None):
	base = (raw_name or '').strip() or f"ficha_{fallback_id or 'sin_nombre'}"
	safe_chars = [ch if ch.isalnum() or ch in (' ', '-', '_', '.') else '_' for ch in base]
	normalized = ''.join(safe_chars).strip()
	normalized = normalized or f"ficha_{fallback_id or 'sin_nombre'}"
	return normalized if normalized.lower().endswith('.pdf') else f"{normalized}.pdf"


def _zip_response(rows, zip_filename):
	buffer = io.BytesIO()
	used_names = set()
	with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
		for row in rows:
			if not row.get('archivo_pdf'):
				continue
			filename = _safe_pdf_filename(row.get('nombre'), row['id'])
			if filename in used_names:
				stem = filename[:-4] if filename.lower().endswith('.pdf') else filename
				filename = f"{stem}_{row['id']}.pdf"
			used_names.add(filename)
			zf.writestr(filename, bytes(row['archivo_pdf']))
	buffer.seek(0)

	response = Response(buffer.read(), mimetype='application/zip')
	response.headers['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
	return response


FICHA_SECTION_ORDER = [
	'Procedimientos',
	'Consulta Externa / Personal No Médico',
	'Odontología',
	'Emergencia',
	'Centro Quirúrgico',
	'Otras / Generales',
]


def _resolve_section_options(engine):
	"""Lista de secciones seleccionables: las fijas de FICHA_SECTION_ORDER
	mas cualquier seccion "libre" (creada a mano desde la UI) que ya este en
	uso en la tabla, para que quede disponible para elegir en adelante. El
	catch-all ('Otras / Generales') siempre queda al final."""
	catch_all = FICHA_SECTION_ORDER[-1]
	fijas = FICHA_SECTION_ORDER[:-1]
	extras = []
	try:
		with engine.connect() as conn:
			rows = conn.execute(
				text("SELECT DISTINCT seccion FROM dwsge.f_tecnicas WHERE seccion IS NOT NULL ORDER BY seccion")
			).scalars().all()
		extras = [s for s in rows if s and s not in FICHA_SECTION_ORDER]
	except Exception as exc:
		current_app.logger.exception('Error al listar secciones de fichas técnicas: %s', exc)
	return fijas + extras + [catch_all]


def _resolve_seccion_from_form(form, known_sections):
	"""El input de texto 'seccion_nueva' tiene prioridad sobre el <select>
	'seccion', para permitir crear una seccion/grupo nuevo desde la UI.

	Si lo escrito coincide (sin distinguir mayusculas/espacios) con una
	seccion que ya existe, se reutiliza tal cual esta guardada esa seccion
	en vez de crear una "nueva" que en realidad es un duplicado por typo
	(ej. "Emergencia " o "emergencia" en vez de "Emergencia")."""
	nueva = form.get('seccion_nueva', '').strip()
	if nueva:
		for existing in known_sections:
			if existing.strip().lower() == nueva.lower():
				return existing
		return nueva
	return form.get('seccion', '').strip() or known_sections[-1]


def _guess_section_from_nombre(nombre):
	"""Solo como respaldo para filas sin 'seccion' asignada todavia."""
	n = (nombre or '').strip().upper()
	if n.startswith('PRO'):
		return 'Procedimientos'
	if n.startswith('SOD'):
		return 'Odontología'
	if n.startswith('EME'):
		return 'Emergencia'
	if n.startswith('CQX'):
		return 'Centro Quirúrgico'
	if n.startswith('CE'):
		return 'Consulta Externa / Personal No Médico'
	return 'Otras / Generales'


def _group_fichas_by_section(fichas):
	buckets = {label: [] for label in FICHA_SECTION_ORDER}
	for ficha in fichas:
		label = ficha.get('seccion') or _guess_section_from_nombre(ficha.get('nombre'))
		if label not in buckets:
			buckets[label] = []
		buckets[label].append(ficha)
	ordered = [
		(label, buckets.pop(label))
		for label in FICHA_SECTION_ORDER
		if buckets.get(label)
	]
	# Por si alguna fila quedo con una seccion "libre" no listada en
	# FICHA_SECTION_ORDER (ej. cargada a mano), se muestra igual al final.
	ordered.extend((label, rows) for label, rows in buckets.items() if rows)
	return ordered


def _fetch_tabla_homologada_rows(codcas):
	query = text(
		"""
		SELECT
			h.cod_centro,
			c.cenasides,
			h.cod_topico,
			t.topemedes,
			h.cod_emergencia,
			e.desc_emergencia,
			h.cod_estandar,
			s.des_estandar
		FROM dssge.dw_homologacion_enlaces_emergencia h
		LEFT OUTER JOIN dwsge.sgss_cmcas10 c
			ON c.cenasicod = h.cod_centro
		LEFT OUTER JOIN dssge.sgss_mbtoe10 t
			ON h.cod_topico = t.topemecod
		LEFT OUTER JOIN dwsge.dim_emergencia e
			ON e.cod_emergencia = h.cod_emergencia
		LEFT OUTER JOIN dwsge.dim_estandar s
			ON s.id_estandar = h.cod_estandar
		WHERE h.cod_estado = '1'
			AND h.cod_centro = :codcas
		ORDER BY h.cod_topico, h.cod_emergencia, h.cod_estandar
		"""
	)

	engine = _get_dw_engine()
	with engine.connect() as conn:
		result = conn.execute(query, {'codcas': codcas})
		return [dict(row._mapping) for row in result]


def _fetch_tabla_homologada_ce_rows():
	query = text(
		"""
		SELECT
			desc_gpo_ocup,
			cod_area,
			desc_area,
			cod_actividad,
			desc_actividad,
			cod_subactividad,
			desc_subactividad,
			cod_servicio,
			desc_servicio,
			cod_especialidad,
			especialidad,
			cod_subespecialidad,
			subespecialidad,
			cod_agrupador,
			agrupador,
			cod_variable,
			variable,
			anio,
			anio_uso
		FROM dssge.dw_homologacion_enlaces
		ORDER BY desc_gpo_ocup, cod_area, cod_actividad, cod_subactividad, cod_servicio
		"""
	)

	engine = _get_dw_engine()
	with engine.connect() as conn:
		result = conn.execute(query)
		return [dict(row._mapping) for row in result]


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


def _get_center_name_by_code(code):
	if not code:
		return ''
	try:
		df = get_centro_asistencial()
		matches = df[df['cenasicod'].astype(str) == str(code)]
		if not matches.empty:
			return str(matches.iloc[0]['cenasides'])
	except Exception as exc:
		current_app.logger.warning('No se pudo obtener el nombre del centro %s: %s', code, exc)
	return ''


def _load_survey_structure():
	modules = (
		SurveyModule.query.options(
			joinedload(SurveyModule.categorias)
			.joinedload(SurveyCategory.subcategorias)
			.joinedload(SurveySubcategory.variables)
		)
		.order_by(SurveyModule.nombre.asc())
		.all()
	)
	structure = {}
	for module in modules:
		module_key = str(module.id)
		module_entry = {
			'id': module.id,
			'label': (module.nombre or f'Módulo {module.id}').strip(),
			'areas': {}
		}
		for category in module.categorias or []:
			if getattr(category, 'active', 1) != 1:
				# Skip inactive categories so they don't appear in the survey
				continue
			area_key = str(category.id)
			area_entry = {
				'id': category.id,
				'label': (category.nombre or f'Categoría {category.id}').strip(),
				'description': 'Complete la encuesta para esta categoría.',
				'categories': []
			}
			for subcat in category.subcategorias or []:
				if not subcat:
					continue
				if getattr(subcat, 'active', 1) != 1:
					# Skip inactive subcategories
					continue
				subcat_key = str(subcat.id)
				variables = []
				for variable in subcat.variables or []:
					if getattr(variable, 'active', 1) != 1:
						# Skip inactive variables
						continue
					variables.append({
						'id': str(variable.id),
						'label': (variable.nombre or f'Variable {variable.id}').strip() or f'Variable {variable.id}'
					})
				if variables:
					area_entry['categories'].append({
						'id': subcat_key,
						'label': (subcat.nombre or f'Subcategoría {subcat.id}').strip(),
						'variables': variables,
					})
			if area_entry['categories']:
				module_entry['areas'][area_key] = area_entry
		if module_entry['areas']:
			structure[module_key] = module_entry
	return structure


def _build_survey_defaults(structure):
	section_defaults = {}
	area_defaults = {}
	for section_key, section in structure.items():
		areas = section.get('areas', {}) or {}
		if areas:
			first_area = next(iter(areas.keys()))
			section_defaults[section_key] = first_area
			area_defaults[section_key] = {}
			for area_key, area in areas.items():
				categories = area.get('categories', []) or []
				area_defaults[section_key][area_key] = categories[0]['id'] if categories else ''
	return section_defaults, area_defaults


def _load_desercion_model():
	model = current_app.config.get('_desercion_model')
	model_path = current_app.config.get('_desercion_model_path')
	if model is None:
		model_path = os.path.join(current_app.root_path, DESERCION_MODEL_FILENAME)
		if not os.path.exists(model_path):
			raise FileNotFoundError(f"No se encontró el archivo del modelo en {model_path}.")
		model = joblib.load(model_path)
		current_app.config['_desercion_model'] = model
		current_app.config['_desercion_model_path'] = model_path
	return model, model_path


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
		code_red = getattr(current_user, 'code_red', None)
		role = getattr(current_user, 'role', None)
		limit_to_red = bool(code_red) and role == 'admin_red'
		df_by_code_red = get_centro_asistencial_by_code_red(code_red) if limit_to_red else df
		centros_asistenciales = df.to_dict(orient='records')
		centros_asistenciales_by_code_red = df_by_code_red.to_dict(orient='records')
		redes_df = get_redes_asistenciales()
		red_options = _format_select_options(redes_df, 'redasiscod', 'redasisdes')
		selected_codcas = ''
		selected_code_red = ''
		if request.method == 'POST':
			selected_codcas = (request.form.get('codcas', '') or '').strip()
			selected_code_red = (request.form.get('code_red_filter', '') or '').strip()
		else:
			selected_codcas = (request.args.get('codcas', '') or '').strip()
			selected_code_red = (request.args.get('code_red_filter', '') or '').strip()
		return render_template(
			'index.html',
			centros_asistenciales=centros_asistenciales,
			centros_asistenciales_by_code_red=centros_asistenciales_by_code_red,
			red_options=red_options,
			selected_codcas=selected_codcas,
			selected_code_red=selected_code_red,
		)

	@bp.route('/encuestas/', methods=['GET', 'POST'])
	@login_required
	def survey_module():
		survey_structure = _load_survey_structure()
		if not survey_structure:
			flash('No hay módulos configurados para la encuesta.', 'warning')
			return redirect(url_for('main.index'))

		section_defaults, area_defaults = _build_survey_defaults(survey_structure)
		selected_section = request.values.get('section') or next(iter(survey_structure.keys()))
		if selected_section not in survey_structure:
			selected_section = next(iter(survey_structure.keys()))
		section_data = survey_structure[selected_section]

		areas = section_data.get('areas', {})
		if not areas:
			flash('El módulo seleccionado no tiene categorías configuradas.', 'warning')
			return redirect(url_for('main.index'))
		section_default_area = section_defaults.get(selected_section, next(iter(areas)))
		selected_area = request.values.get('area') or section_default_area
		if selected_area not in areas:
			selected_area = section_default_area
		area_data = areas[selected_area]

		categories = area_data.get('categories', [])
		if not categories:
			flash('No hay subcategorías configuradas para esta categoría.', 'warning')
			return redirect(url_for('main.index'))

		default_category = area_defaults.get(selected_section, {}).get(selected_area, categories[0]['id'])
		selected_category = request.values.get('category') or default_category
		category_data = next((c for c in categories if c['id'] == selected_category), None)
		if not category_data:
			category_data = categories[0]
			selected_category = category_data['id']

		center_code = (request.values.get('codcas') or getattr(current_user, 'codcas', '') or '').strip()
		center_label = _get_center_name_by_code(center_code)

		def _build_response_entries():
			entries = []
			for variable in category_data.get('variables', []):
				status_field = f"status__{variable['id']}"
				status_value = request.form.get(status_field)
				if status_value not in ('valid', 'invalid'):
					continue
				comment = (request.form.get(f"comment__{variable['id']}") or '').strip()
				entry = SurveyResponse(
					user_id=current_user.id,
					user_username=current_user.username,
					user_fullname=f"{current_user.name or ''} {current_user.lastname or ''}".strip() or current_user.username,
					user_role=current_user.role or 'user',
					codcas=center_code or current_user.codcas,
					section=selected_section,
					area=selected_area,
					category_id=category_data['id'],
					category_label=category_data['label'],
					variable_id=variable['id'],
					variable_label=variable['label'],
					status=status_value,
					comment=comment,
				)
				entries.append(entry)
			return entries

		if request.method == 'POST':
			entries = _build_response_entries()
			if not entries:
				flash('Selecciona al menos una variable y marca Válido o No válido.', 'warning')
			else:
				db.session.add_all(entries)
				db.session.commit()
				flash('Respuestas registradas correctamente.', 'success')
				return redirect(url_for(
					'main.survey_module',
					section=selected_section,
					area=selected_area,
					category=selected_category,
					codcas=center_code,
				))

		return render_template(
			'survey_module.html',
			survey_structure=survey_structure,
			section_defaults=section_defaults,
			area_defaults=area_defaults,
			selected_section=selected_section,
			selected_area=selected_area,
			selected_category=selected_category,
			section_data=section_data,
			area_data=area_data,
			category_data=category_data,
			center_code=center_code,
			center_label=center_label,
			show_modules=False,
		)

	@bp.route('/prediccion_desercion', methods=['GET', 'POST'])
	@login_required
	def prediccion_desercion():
		if current_user.role != 'admin':
			flash('Solo los administradores pueden ejecutar la predicción de deserción.', 'danger')
			return redirect(url_for('main.index'))

		default_payload = {
			'anio_edad': '25',
			'sexo': 'M',
			'cod_area': '01',
			'cod_servicio': 'AM13',
			'dia_semana': '6',
			'mes': '7',
			'es_fin_semana': '1',
			'cod_subactividad': '001',
		}
		form_values = default_payload.copy()
		probability = None
		probability_percent = None
		model_path = current_app.config.get('_desercion_model_path')

		if request.method == 'POST':
			for field in form_values:
				incoming = (request.form.get(field) or '').strip()
				if incoming:
					form_values[field] = incoming

			form_values['sexo'] = (form_values.get('sexo') or 'M').upper()
			numeric_fields = ('anio_edad', 'dia_semana', 'mes', 'es_fin_semana')
			try:
				numeric_values = {name: int(form_values[name]) for name in numeric_fields}
			except ValueError:
				flash('Revisa los campos numéricos (edad, día, mes y fin de semana). Deben ser enteros.', 'warning')
			else:
				payload = {
					'anio_edad': [numeric_values['anio_edad']],
					'sexo': [form_values['sexo']],
					'cod_area': [form_values['cod_area']],
					'cod_servicio': [form_values['cod_servicio']],
					'dia_semana': [numeric_values['dia_semana']],
					'mes': [numeric_values['mes']],
					'es_fin_semana': [numeric_values['es_fin_semana']],
					'cod_subactividad': [form_values['cod_subactividad']],
				}
				try:
					model, model_path = _load_desercion_model()
					model_input = pd.DataFrame(payload)
					if hasattr(model, 'predict_proba'):
						raw_probability = model.predict_proba(model_input)[:, 1][0]
					else:
						raw_probability = model.predict(model_input)[0]
					probability = float(raw_probability)
					probability_percent = round(probability * 100, 2)
				except FileNotFoundError as missing:
					flash(str(missing), 'danger')
				except Exception as exc:
					current_app.logger.exception('Error al calcular la predicción de deserción: %s', exc)
					flash('No fue posible calcular la probabilidad. Revisa el archivo del modelo.', 'danger')

		return render_template(
			'prediccion_desercion.html',
			show_modules=False,
			form_values=form_values,
			probability=probability,
			probability_percent=probability_percent,
			model_filename=DESERCION_MODEL_FILENAME,
			model_path=model_path,
		)

	@bp.route('/tabla_homologada/', methods=['GET'], endpoint='tabla_homologada_eme')
	@bp.route('/tabla_homologada/', methods=['GET'])
	@login_required
	def tabla_homologada():
		selected_codcas = (request.args.get('codcas') or '').strip()
		fallback_codcas = (getattr(current_user, 'codcas', '') or '').strip()
		codcas = selected_codcas or fallback_codcas

		if not codcas:
			flash('Selecciona un centro asistencial para visualizar la tabla homologada.', 'warning')
			return redirect(url_for('main.index'))

		try:
			rows = _fetch_tabla_homologada_rows(codcas)
		except Exception as exc:
			current_app.logger.exception('Error al consultar la tabla homologada para codcas=%s: %s', codcas, exc)
			flash('No se pudo cargar la tabla homologada en este momento.', 'danger')
			return redirect(url_for('main.index'))

		return render_template(
			'tabla_homologada_eme.html',
			show_modules=False,
			rows=rows,
			codcas=codcas,
			center_name=_get_center_name_by_code(codcas),
		)

	@bp.route('/tablas_homologadas/', methods=['GET'])
	@login_required
	def tablas_homologadas():
		selected_codcas = (request.args.get('codcas') or '').strip()
		fallback_codcas = (getattr(current_user, 'codcas', '') or '').strip()
		codcas = selected_codcas or fallback_codcas
		return render_template(
			'tablas_homologadas.html',
			show_modules=False,
			codcas=codcas,
			center_name=_get_center_name_by_code(codcas),
		)

	@bp.route('/tabla_homologada/consulta-externa/', methods=['GET'])
	@login_required
	def tabla_homologada_ce():
		try:
			rows = _fetch_tabla_homologada_ce_rows()
		except Exception as exc:
			current_app.logger.exception('Error al consultar la tabla homologada de consulta externa: %s', exc)
			flash('No se pudo cargar la tabla homologada de consulta externa en este momento.', 'danger')
			return redirect(url_for('main.tablas_homologadas'))

		selected_codcas = (request.args.get('codcas') or '').strip()
		fallback_codcas = (getattr(current_user, 'codcas', '') or '').strip()
		codcas = selected_codcas or fallback_codcas
		return render_template(
			'tabla_homologada_ce.html',
			show_modules=False,
			rows=rows,
			codcas=codcas,
		)

	@bp.route('/tabla_homologada/consulta-externa/csv', methods=['GET'])
	@login_required
	def tabla_homologada_ce_csv():
		if getattr(current_user, 'role', None) == 'consulta':
			flash('No tienes permisos para descargar archivos.', 'warning')
			return redirect(url_for('main.tabla_homologada_ce'))
		try:
			rows = _fetch_tabla_homologada_ce_rows()
		except Exception as exc:
			current_app.logger.exception('Error al exportar tabla homologada de consulta externa: %s', exc)
			flash('No se pudo generar el CSV de consulta externa en este momento.', 'danger')
			return redirect(url_for('main.tabla_homologada_ce'))

		output = io.StringIO()
		fieldnames = [
			'desc_gpo_ocup',
			'cod_area',
			'desc_area',
			'cod_actividad',
			'desc_actividad',
			'cod_subactividad',
			'desc_subactividad',
			'cod_servicio',
			'desc_servicio',
			'cod_especialidad',
			'especialidad',
			'cod_subespecialidad',
			'subespecialidad',
			'cod_agrupador',
			'agrupador',
			'cod_variable',
			'variable',
			'anio',
			'anio_uso',
		]
		writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
		writer.writeheader()
		if rows:
			writer.writerows(rows)

		filename = 'tabla_homologada_consulta_externa.csv'
		csv_content = '\ufeff' + output.getvalue()
		response = Response(csv_content, mimetype='text/csv; charset=utf-8')
		response.headers['Content-Disposition'] = f'attachment; filename={filename}'
		return response

	@bp.route('/tabla_homologada/csv', methods=['GET'])
	@login_required
	def tabla_homologada_csv():
		if getattr(current_user, 'role', None) == 'consulta':
			flash('No tienes permisos para descargar archivos.', 'warning')
			return redirect(url_for('main.index'))
		selected_codcas = (request.args.get('codcas') or '').strip()
		fallback_codcas = (getattr(current_user, 'codcas', '') or '').strip()
		codcas = selected_codcas or fallback_codcas

		if not codcas:
			flash('Selecciona un centro asistencial para descargar la tabla homologada.', 'warning')
			return redirect(url_for('main.index'))

		try:
			rows = _fetch_tabla_homologada_rows(codcas)
		except Exception as exc:
			current_app.logger.exception('Error al exportar tabla homologada para codcas=%s: %s', codcas, exc)
			flash('No se pudo generar el archivo CSV en este momento.', 'danger')
			return redirect(url_for('main.tabla_homologada', codcas=codcas))

		output = io.StringIO()
		fieldnames = [
			'cod_centro',
			'cenasides',
			'cod_topico',
			'topemedes',
			'cod_emergencia',
			'desc_emergencia',
			'cod_estandar',
			'des_estandar',
		]
		writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
		writer.writeheader()
		if rows:
			writer.writerows(rows)

		filename = f'tabla_homologada_emergencia_{codcas}.csv'
		csv_content = '\ufeff' + output.getvalue()
		response = Response(csv_content, mimetype='text/csv; charset=utf-8')
		response.headers['Content-Disposition'] = f'attachment; filename={filename}'
		return response


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
			flag = (request.form.get('flag', '1') or '1').strip()
			flag = '0' if flag == '0' else '1'

			
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
				new_user.flag = flag
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

	@bp.route('/manage_users', methods=['GET', 'POST'])
	@login_required
	def manage_users():
		if current_user.role != 'admin':
			flash('No tienes permisos para gestionar usuarios', 'danger')
			return redirect(url_for('main.index'))

		centros_df = get_centro_asistencial()
		redes_df = get_redes_asistenciales()
		centros_options = _format_select_options(centros_df, 'cenasicod', 'cenasides')
		red_options = _format_select_options(redes_df, 'redasiscod', 'redasisdes')

		if request.method == 'POST':
			user_id = request.form.get('user_id')
			usuario = User.query.get(user_id)
			if not usuario:
				flash('El usuario seleccionado no existe.', 'danger')
				return redirect(url_for('main.manage_users'))

			nombre = request.form.get('nombre', '').strip()
			apellido = request.form.get('apellido', '').strip()
			username = request.form.get('username', '').strip()
			codcas = request.form.get('codcas', '').strip()
			rol = request.form.get('rol', '').strip() or 'user'
			code_red = request.form.get('code_red', '').strip()
			nuevo_password = request.form.get('password', '').strip()
			flag = (request.form.get('flag', '1') or '1').strip()
			flag = '0' if flag == '0' else '1'
			search_field_post = request.form.get('field', 'nombre')
			search_query_post = request.form.get('q', '').strip()

			if not username:
				flash('El nombre de usuario es obligatorio.', 'warning')
				return redirect(url_for('main.manage_users', field=search_field_post, q=search_query_post))

			usuario_existente = User.query.filter(User.username == username, User.id != usuario.id).first()
			if usuario_existente:
				flash('Ya existe otro usuario con el mismo nombre.', 'danger')
				return redirect(url_for('main.manage_users', field=search_field_post, q=search_query_post))

			usuario.name = nombre
			usuario.lastname = apellido
			usuario.username = username
			usuario.codcas = codcas
			usuario.role = rol
			usuario.code_red = code_red
			usuario.flag = flag
			if nuevo_password:
				usuario.set_password(nuevo_password)

			db.session.add(usuario)
			db.session.commit()
			flash('Usuario actualizado correctamente.', 'success')
			return redirect(url_for('main.manage_users', field=search_field_post, q=search_query_post))

		search_field = request.args.get('field', 'usuario')
		search_query = request.args.get('q', '').strip()
		field_map = {
			'nombre': User.name,
			'apellido': User.lastname,
			'usuario': User.username,
		}
		column = field_map.get(search_field, User.username)
		usuarios = []
		if search_query:
			usuarios = (
				User.query.filter(func.lower(column).like(f"%{search_query.lower()}%"))
				.order_by(User.id.asc())
				.all()
			)
		return render_template(
			'manage_users.html',
			show_modules=False,
			usuarios=usuarios,
			centros_options=centros_options,
			red_options=red_options,
			search_field=search_field,
			search_query=search_query,
		)

	@bp.route('/manage_fichas', methods=['GET', 'POST'])
	@login_required
	def manage_fichas():
		if current_user.role != 'admin':
			flash('No tienes permisos para gestionar fichas técnicas', 'danger')
			return redirect(url_for('main.index'))

		engine = _get_dw_engine()

		if request.method == 'POST':
			nombre = request.form.get('nombre', '').strip()
			seccion = _resolve_seccion_from_form(request.form, _resolve_section_options(engine))
			archivo = request.files.get('archivo_pdf')

			if not archivo or not archivo.filename:
				flash('Selecciona un archivo PDF para subir.', 'warning')
				return redirect(url_for('main.manage_fichas'))

			if not archivo.filename.lower().endswith('.pdf') or archivo.mimetype not in (
				'application/pdf', 'application/octet-stream'
			):
				flash('El archivo debe ser un PDF.', 'danger')
				return redirect(url_for('main.manage_fichas'))

			data = archivo.read()
			if not data:
				flash('El archivo está vacío.', 'danger')
				return redirect(url_for('main.manage_fichas'))
			if len(data) > 20 * 1024 * 1024:
				flash('El archivo supera el límite de 20 MB.', 'danger')
				return redirect(url_for('main.manage_fichas'))
			if not _is_valid_pdf(data):
				flash('El archivo no es un PDF válido (la firma del contenido no coincide).', 'danger')
				return redirect(url_for('main.manage_fichas'))

			nombre_final = nombre or archivo.filename

			try:
				with engine.begin() as conn:
					conn.execute(
						text(
							"INSERT INTO dwsge.f_tecnicas (nombre, seccion, archivo_pdf, fecha_subida) "
							"VALUES (:nombre, :seccion, :data, now())"
						),
						{'nombre': nombre_final, 'seccion': seccion, 'data': data},
					)
				flash(f'Ficha "{nombre_final}" subida correctamente en "{seccion}".', 'success')
			except Exception as exc:
				current_app.logger.exception('Error al subir ficha técnica: %s', exc)
				flash('No se pudo subir la ficha técnica.', 'danger')

			return redirect(url_for('main.manage_fichas', open=seccion))

		search_query = request.args.get('q', '').strip()
		seccion_filter = request.args.get('seccion', '').strip()
		open_section = request.args.get('open', '').strip()
		sql = "SELECT id, nombre, seccion, length(archivo_pdf) AS size_bytes, fecha_subida FROM dwsge.f_tecnicas"
		conditions = []
		params = {}
		if search_query:
			conditions.append("nombre ILIKE :q")
			params['q'] = f"%{search_query}%"
		if seccion_filter:
			conditions.append("seccion = :seccion")
			params['seccion'] = seccion_filter
		if conditions:
			sql += " WHERE " + " AND ".join(conditions)
		sql += " ORDER BY id"

		try:
			with engine.connect() as conn:
				fichas = conn.execute(text(sql), params).mappings().all()
		except Exception as exc:
			current_app.logger.exception('Error al listar fichas técnicas: %s', exc)
			flash('No se pudieron cargar las fichas técnicas.', 'danger')
			fichas = []

		secciones = _group_fichas_by_section(fichas)

		return render_template(
			'manage_fichas.html',
			show_modules=False,
			secciones=secciones,
			total_fichas=len(fichas),
			search_query=search_query,
			seccion_filter=seccion_filter,
			open_section=open_section,
			section_options=_resolve_section_options(engine),
		)

	@bp.route('/manage_fichas/<int:ficha_id>/update', methods=['POST'])
	@login_required
	def update_ficha(ficha_id):
		if current_user.role != 'admin':
			flash('No tienes permisos para gestionar fichas técnicas', 'danger')
			return redirect(url_for('main.index'))

		engine = _get_dw_engine()
		nombre = request.form.get('nombre', '').strip()
		seccion = _resolve_seccion_from_form(request.form, _resolve_section_options(engine))
		archivo = request.files.get('archivo_pdf')
		search_query = request.form.get('q', '').strip()
		seccion_filter = request.form.get('seccion_filter', '').strip()

		if not nombre:
			flash('El nombre no puede quedar vacío.', 'warning')
			return redirect(url_for('main.manage_fichas', q=search_query, seccion=seccion_filter, open=seccion))

		data = None
		if archivo and archivo.filename:
			if not archivo.filename.lower().endswith('.pdf') or archivo.mimetype not in (
				'application/pdf', 'application/octet-stream'
			):
				flash('El archivo de reemplazo debe ser un PDF.', 'danger')
				return redirect(url_for('main.manage_fichas', q=search_query, seccion=seccion_filter, open=seccion))
			data = archivo.read()
			if not data:
				flash('El archivo de reemplazo está vacío.', 'danger')
				return redirect(url_for('main.manage_fichas', q=search_query, seccion=seccion_filter, open=seccion))
			if len(data) > 20 * 1024 * 1024:
				flash('El archivo supera el límite de 20 MB.', 'danger')
				return redirect(url_for('main.manage_fichas', q=search_query, seccion=seccion_filter, open=seccion))
			if not _is_valid_pdf(data):
				flash('El archivo no es un PDF válido (la firma del contenido no coincide).', 'danger')
				return redirect(url_for('main.manage_fichas', q=search_query, seccion=seccion_filter, open=seccion))

		try:
			with engine.begin() as conn:
				if data is not None:
					conn.execute(
						text(
							"UPDATE dwsge.f_tecnicas SET nombre = :nombre, seccion = :seccion, "
							"archivo_pdf = :data, fecha_subida = now() WHERE id = :id"
						),
						{'nombre': nombre, 'seccion': seccion, 'data': data, 'id': ficha_id},
					)
					flash(f'Ficha #{ficha_id} actualizada (nombre, sección y archivo).', 'success')
				else:
					conn.execute(
						text(
							"UPDATE dwsge.f_tecnicas SET nombre = :nombre, seccion = :seccion "
							"WHERE id = :id"
						),
						{'nombre': nombre, 'seccion': seccion, 'id': ficha_id},
					)
					flash(f'Ficha #{ficha_id} renombrada.', 'success')
		except Exception as exc:
			current_app.logger.exception('Error al actualizar ficha técnica %s: %s', ficha_id, exc)
			flash('No se pudo actualizar la ficha técnica.', 'danger')

		return redirect(url_for('main.manage_fichas', q=search_query, open=seccion))

	@bp.route('/manage_fichas/<int:ficha_id>/delete', methods=['POST'])
	@login_required
	def delete_ficha(ficha_id):
		if current_user.role != 'admin':
			flash('No tienes permisos para gestionar fichas técnicas', 'danger')
			return redirect(url_for('main.index'))

		engine = _get_dw_engine()
		search_query = request.form.get('q', '').strip()
		seccion_filter = request.form.get('seccion_filter', '').strip()
		open_section = ''

		try:
			with engine.begin() as conn:
				deleted = conn.execute(
					text("DELETE FROM dwsge.f_tecnicas WHERE id = :id RETURNING seccion"),
					{'id': ficha_id},
				).first()
			if deleted:
				open_section = deleted[0] or ''
				flash(
					f'Ficha #{ficha_id} eliminada. Si alguna tarjeta de los dashboards '
					'todavía la referencia, su botón de "Ficha técnica" dejará de funcionar '
					'hasta que actualices ese ficha_id en el código.',
					'success'
				)
			else:
				flash(f'No se encontró la ficha #{ficha_id}.', 'warning')
		except Exception as exc:
			current_app.logger.exception('Error al eliminar ficha técnica %s: %s', ficha_id, exc)
			flash('No se pudo eliminar la ficha técnica.', 'danger')

		return redirect(url_for('main.manage_fichas', q=search_query, seccion=seccion_filter, open=open_section))

	@bp.route('/manage_fichas/<int:ficha_id>/pdf')
	@login_required
	def preview_ficha(ficha_id):
		if current_user.role != 'admin':
			flash('No tienes permisos para gestionar fichas técnicas', 'danger')
			return redirect(url_for('main.index'))

		engine = _get_dw_engine()
		try:
			with engine.connect() as conn:
				row = conn.execute(
					text("SELECT nombre, archivo_pdf FROM dwsge.f_tecnicas WHERE id = :id"),
					{'id': ficha_id},
				).mappings().first()
		except Exception as exc:
			current_app.logger.exception('Error al previsualizar ficha técnica %s: %s', ficha_id, exc)
			return 'Error al cargar la ficha', 500

		if not row or not row.get('archivo_pdf'):
			return 'Ficha no encontrada', 404

		response = Response(bytes(row['archivo_pdf']), mimetype='application/pdf')
		response.headers['Content-Disposition'] = 'inline; filename="ficha.pdf"'
		return response

	@bp.route('/manage_fichas/<int:ficha_id>/download')
	@login_required
	def download_ficha(ficha_id):
		if current_user.role != 'admin':
			flash('No tienes permisos para gestionar fichas técnicas', 'danger')
			return redirect(url_for('main.index'))

		engine = _get_dw_engine()
		try:
			with engine.connect() as conn:
				row = conn.execute(
					text("SELECT nombre, archivo_pdf FROM dwsge.f_tecnicas WHERE id = :id"),
					{'id': ficha_id},
				).mappings().first()
		except Exception as exc:
			current_app.logger.exception('Error al descargar ficha técnica %s: %s', ficha_id, exc)
			return 'Error al cargar la ficha', 500

		if not row or not row.get('archivo_pdf'):
			return 'Ficha no encontrada', 404

		filename = _safe_pdf_filename(row.get('nombre'), ficha_id)
		response = Response(bytes(row['archivo_pdf']), mimetype='application/pdf')
		response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
		return response

	@bp.route('/manage_fichas/download_all')
	@login_required
	def download_all_fichas():
		if current_user.role != 'admin':
			flash('No tienes permisos para gestionar fichas técnicas', 'danger')
			return redirect(url_for('main.index'))

		engine = _get_dw_engine()
		try:
			with engine.connect() as conn:
				rows = conn.execute(
					text("SELECT id, nombre, archivo_pdf FROM dwsge.f_tecnicas ORDER BY id")
				).mappings().all()
		except Exception as exc:
			current_app.logger.exception('Error al descargar todas las fichas técnicas: %s', exc)
			flash('No se pudieron descargar las fichas técnicas.', 'danger')
			return redirect(url_for('main.manage_fichas'))

		if not rows:
			flash('No hay fichas técnicas para descargar.', 'warning')
			return redirect(url_for('main.manage_fichas'))

		return _zip_response(rows, 'fichas_tecnicas.zip')

	@bp.route('/manage_fichas/download_section')
	@login_required
	def download_section_fichas():
		if current_user.role != 'admin':
			flash('No tienes permisos para gestionar fichas técnicas', 'danger')
			return redirect(url_for('main.index'))

		seccion = request.args.get('seccion', '').strip()
		if not seccion:
			flash('Sección no especificada.', 'warning')
			return redirect(url_for('main.manage_fichas'))

		engine = _get_dw_engine()
		try:
			with engine.connect() as conn:
				# Filtrado en SQL: para una seccion puntual no hace falta traer
				# el archivo_pdf (bytea) de las demas ~100+ fichas de la tabla
				# para descartarlas despues en Python.
				rows = conn.execute(
					text("SELECT id, nombre, archivo_pdf FROM dwsge.f_tecnicas WHERE seccion = :seccion"),
					{'seccion': seccion},
				).mappings().all()
				# Filas legacy sin 'seccion' asignada (no deberian quedar, ya
				# se hizo un backfill, pero por si acaso): se resuelven con el
				# mismo criterio de respaldo que usa el agrupamiento de la UI.
				sin_seccion = conn.execute(
					text("SELECT id, nombre, archivo_pdf FROM dwsge.f_tecnicas WHERE seccion IS NULL OR seccion = ''")
				).mappings().all()
		except Exception as exc:
			current_app.logger.exception('Error al descargar fichas técnicas de la sección %s: %s', seccion, exc)
			flash('No se pudieron descargar las fichas técnicas.', 'danger')
			return redirect(url_for('main.manage_fichas'))

		rows = list(rows) + [
			row for row in sin_seccion
			if _guess_section_from_nombre(row.get('nombre')) == seccion
		]

		if not rows:
			flash(f'No hay fichas técnicas en la sección "{seccion}".', 'warning')
			return redirect(url_for('main.manage_fichas'))

		safe_section = _safe_pdf_filename(seccion, 'seccion')[:-4]
		return _zip_response(rows, f"fichas_{safe_section}.zip")

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
		if current_user.role not in ('admin', 'admin_red', 'consulta'):
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
			if user and getattr(user, 'flag', '1') != '1':
				flash('Tu usuario está inactivo. Solicita la activación al administrador.', 'warning')
			elif user and verify and verify(user, password):
				login_user(user)
				return redirect(url_for('main.index'))
			else:
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

	@bp.route('/dashboard/<token>', methods=['GET'])
	@bp.route('/dashboard/<token>/', methods=['GET'])
	@login_required
	def dashboard_wrapper(token):
		code = decode_code(token)
		if not code:
			flash('El código seleccionado es inválido o expiró.', 'warning')
			return redirect(url_for('main.index'))
		dashboard_url = f'/dashboard_embed/{token}/'
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url=dashboard_url,
			codcas=code,
		)
	
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

	@bp.route('/dashboard_nm/<token>', methods=['GET'])
	@bp.route('/dashboard_nm/<token>/', methods=['GET'])
	@login_required
	def dashboard_nm_wrapper(token):
		code = decode_code(token)
		if not code:
			flash('El código seleccionado es inválido o expiró.', 'warning')
			return redirect(url_for('main.index'))
		dashboard_url = f'/dashboard_nm_embed/{token}/'
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url=dashboard_url,
			codcas=code,
		)
	

	@bp.route('/dashboard_odo', endpoint='dashboard_odo_redirect')
	@login_required
	def dashboard_odo_redirect():
		code = ""
		if current_user.role == 'admin':
			code =  request.args.get('codcas', '')
		elif current_user.role == 'user':
			code = getattr(current_user, 'dashboard_code', lambda: '')()

		if code:
			token = encode_code(code)
			return redirect(f'/dashboard_odo/{token}/')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard_odo/')
	@login_required
	def dashboard_odo_index():
		code = ""
		if current_user.role == 'admin':
			code = request.form.get('codcas', '') 
		elif current_user.role == 'user':
			code = getattr(current_user, 'dashboard_code', lambda: '')()
		if code:
			token = encode_code(code)
			return redirect(f'/dashboard_odo/{token}/')
		flash('No hay código asociado al usuario para mostrar el dashboard.', 'warning')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard_odo/<token>', methods=['GET'])
	@bp.route('/dashboard_odo/<token>/', methods=['GET'])
	@login_required
	def dashboard_odo_wrapper(token):
		code = decode_code(token)
		if not code:
			flash('El código seleccionado es inválido o expiró.', 'warning')
			return redirect(url_for('main.index'))
		dashboard_url = f'/dashboard_odo_embed/{token}/'
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url=dashboard_url,
			codcas=code,
		)

	@bp.route('/dashboard_cq', endpoint='dashboard_cq_redirect')
	@login_required
	def dashboard_cq_redirect():
		code = request.args.get('codcas', '')
		if code:
			token = encode_code(code)
			return redirect(f'/dashboard_cq/{token}/')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard_cq/')
	@login_required
	def dashboard_cq_index():
		code = request.form.get('codcas', '')
		if code:
			token = encode_code(code)
			return redirect(f'/dashboard_cq/{token}/')
		flash('No hay código asociado al usuario para mostrar el dashboard.', 'warning')
		return redirect(url_for('main.index'))

	@bp.route('/cq/')
	@login_required
	def cq_index():
		token = dashboard_code_for_user(current_user, request)
		if token:
			return redirect(url_for('main.cq_menu', token=token))
		flash('No hay código asociado al usuario para mostrar el menú de Centro Quirúrgico.', 'warning')
		return redirect(url_for('main.index'))

	@bp.route('/cq/<token>', methods=['GET'])
	@bp.route('/cq/<token>/', methods=['GET'])
	@login_required
	def cq_menu(token):
		code = decode_code(token)
		if not code:
			flash('El código seleccionado es inválido o expiró.', 'warning')
			return redirect(url_for('main.index'))
		center_name = _get_center_name_by_code(code)
		intervenciones_url = f'/dashboard_cq/{token}/'
		transplantes_url = f'/dashboard_cq_trans/{token}/'
		return render_template(
			'cq.html',
			show_modules=False,
			dashboard_token=token,
			codcas=code,
			center_name=center_name,
			intervenciones_url=intervenciones_url,
			transplantes_url=transplantes_url,
		)

	@bp.route('/dashboard_cq/<token>', methods=['GET'])
	@bp.route('/dashboard_cq/<token>/', methods=['GET'])
	@login_required
	def dashboard_cq_wrapper(token):
		code = decode_code(token)
		if not code:
			flash('El código seleccionado es inválido o expiró.', 'warning')
			return redirect(url_for('main.index'))
		dashboard_url = f'/dashboard_cq_embed/{token}/'
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url=dashboard_url,
			codcas=code,
		)

	@bp.route('/dashboard_cq/complejidad_<complejidad>/<token>', methods=['GET'])
	@bp.route('/dashboard_cq/complejidad_<complejidad>/<token>/', methods=['GET'])
	@login_required
	def dashboard_cq_complejidad_wrapper(complejidad, token):
		code = decode_code(token)
		if not code:
			flash('El código seleccionado es inválido o expiró.', 'warning')
			return redirect(url_for('main.index'))
		qs = request.query_string.decode()
		dashboard_url = f'/dashboard_cq_embed/complejidad_{complejidad}/{token}/'
		if qs:
			dashboard_url = f'{dashboard_url}?{qs}'
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url=dashboard_url,
			codcas=code,
		)

	@bp.route('/dashboard_cq_trans', endpoint='dashboard_cq_trans_redirect')
	@login_required
	def dashboard_cq_trans_redirect():
		code = request.args.get('codcas', '')
		if code:
			token = encode_code(code)
			return redirect(f'/dashboard_cq_trans/{token}/')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard_cq_trans/')
	@login_required
	def dashboard_cq_trans_index():
		code = request.form.get('codcas', '')
		if code:
			token = encode_code(code)
			return redirect(f'/dashboard_cq_trans/{token}/')
		flash('No hay código asociado al usuario para mostrar el dashboard.', 'warning')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard_cq_trans/<token>', methods=['GET'])
	@bp.route('/dashboard_cq_trans/<token>/', methods=['GET'])
	@login_required
	def dashboard_cq_trans_wrapper(token):
		code = decode_code(token)
		if not code:
			flash('El código seleccionado es inválido o expiró.', 'warning')
			return redirect(url_for('main.index'))
		dashboard_url = f'/dashboard_cq_trans_embed/{token}/'
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url=dashboard_url,
			codcas=code,
		)


	@bp.route('/diag_cap_admin')
	@login_required
	def dashboard_diag_admin():
		if current_user.role != 'admin':
			flash('Solo los administradores pueden acceder al reporte diagnóstico.', 'danger')
			return redirect(url_for('main.index'))
		return redirect('/diag_cap/')

	@bp.route('/diag_cap/')
	@login_required
	def diag_cap_wrapper():
		dashboard_url = '/diag_cap_embed/'
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url=dashboard_url,
		)

	@bp.route('/dashboard_alt', endpoint='dashboard_alt_redirect')
	@login_required
	def dashboard_alt_redirect():
		code = ""
		if current_user.role == 'admin':
			code = request.form.get('codcas', '') or request.args.get('codcas', '')
		elif current_user.role == 'user':
			code = getattr(current_user, 'dashboard_code', lambda: '')()
		if code:
			token = encode_code(code)
			return redirect(f'/dashboard_alt/{token}/')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard_alt/')
	@login_required
	def dashboard_alt_index():
		code = ""
		if current_user.role == 'admin':
			code = request.form.get('codcas', '') or request.args.get('codcas', '')
		elif current_user.role == 'user':
			code = getattr(current_user, 'dashboard_code', lambda: '')()
		if code:
			token = encode_code(code)
			return redirect(f'/dashboard_alt/{token}/')
		flash('No hay código asociado al usuario para mostrar el dashboard alternativo.', 'warning')
		return redirect(url_for('main.index'))

	@bp.route('/dashboard_alt/<token>', methods=['GET'])
	@bp.route('/dashboard_alt/<token>/', methods=['GET'])
	@login_required
	def dashboard_alt_wrapper(token):
		code = decode_code(token)
		if not code:
			flash('El código seleccionado es inválido o expiró.', 'warning')
			return redirect(url_for('main.index'))
		dashboard_url = f'/dashboard_alt_embed/{token}/'
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url=dashboard_url,
			codcas=code,
		)
	
	HOSP_ALLOWED_USERS = {'42991109', '76262790'}

	def _hosp_allowed():
		return (
			getattr(current_user, 'role', '') == 'admin'
			or str(getattr(current_user, 'username', '')).strip() in HOSP_ALLOWED_USERS
		)

	@bp.route('/hosp/')
	@login_required
	def hosp_index():
		if not _hosp_allowed():
			flash('No tiene acceso al módulo de Hospitalización.', 'warning')
			return redirect(url_for('main.index'))
		token = dashboard_code_for_user(current_user, request)
		if token:
			return redirect(url_for('main.hosp_wrapper', token=token))
		flash('No hay código asociado al usuario para mostrar el dashboard de Hospitalización.', 'warning')
		return redirect(url_for('main.index'))

	@bp.route('/hosp/<token>', methods=['GET'])
	@bp.route('/hosp/<token>/', methods=['GET'])
	@login_required
	def hosp_wrapper(token):
		if not _hosp_allowed():
			flash('No tiene acceso al módulo de Hospitalización.', 'warning')
			return redirect(url_for('main.index'))
		code = decode_code(token)
		if not code:
			flash('El código seleccionado es inválido o expiró.', 'warning')
			return redirect(url_for('main.index'))
		dashboard_url = f'/dashboard_hosp_embed/{token}/'
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url=dashboard_url,
			codcas=code,
		)

	@bp.route('/proc/')
	@login_required
	def proc_index():
		token = dashboard_code_for_user(current_user, request)
		if token:
			return redirect(url_for('main.proc_wrapper', token=token))
		flash('No hay código asociado al usuario para mostrar el dashboard de Procedimientos.', 'warning')
		return redirect(url_for('main.index'))

	@bp.route('/proc/<token>', methods=['GET'])
	@bp.route('/proc/<token>/', methods=['GET'])
	@login_required
	def proc_wrapper(token):
		code = decode_code(token)
		if not code:
			flash('El código seleccionado es inválido o expiró.', 'warning')
			return redirect(url_for('main.index'))
		dashboard_url = f'/dashboard_proc_embed/{token}/'
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url=dashboard_url,
			codcas=code,
		)

	@bp.route('/farm/')
	@login_required
	def farm_index():
		token = dashboard_code_for_user(current_user, request)
		if token:
			return redirect(url_for('main.farm_wrapper', token=token))
		flash('No hay código asociado al usuario para mostrar el dashboard de Farmacia.', 'warning')
		return redirect(url_for('main.index'))

	@bp.route('/farm/<token>', methods=['GET'])
	@bp.route('/farm/<token>/', methods=['GET'])
	@login_required
	def farm_wrapper(token):
		code = decode_code(token)
		if not code:
			flash('El código seleccionado es inválido o expiró.', 'warning')
			return redirect(url_for('main.index'))
		dashboard_url = f'/dashboard_farm_embed/{token}/'
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url=dashboard_url,
			codcas=code,
		)

	@bp.route('/variables_ses/')
	@login_required
	def variables_ses_index():
		token = dashboard_code_for_user(current_user, request)
		if token:
			return redirect(url_for('main.variables_ses_menu', token=token))
		flash('No hay código asociado al usuario.', 'warning')
		return redirect(url_for('main.index'))

	@bp.route('/variables_ses/<token>', methods=['GET'])
	@bp.route('/variables_ses/<token>/', methods=['GET'])
	@login_required
	def variables_ses_menu(token):
		code = decode_code(token)
		if not code:
			flash('El código seleccionado es inválido o expiró.', 'warning')
			return redirect(url_for('main.index'))
		return render_template(
			'variables_ses.html',
			show_modules=False,
			dashboard_token=token,
			codcas=code,
			center_name=_get_center_name_by_code(code),
			ce_url=f'/ce/{token}/',
			emergencia_url=f'/dashboard_alt/{token}/',
			cq_url=f'/cq/{token}/',
			hosp_url=f'/hosp/{token}/',
			proc_url=f'/proc/{token}/',
			farm_url=f'/farm/{token}/',
		)

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
		center_name = _get_center_name_by_code(code)
		medical_url = f'/dashboard/{token}/'
		non_medical_url = f'/dashboard_nm/{token}/'
		odo_medical_url = f'/dashboard_odo/{token}/'
		return render_template(
			'Ce.html',
			show_modules=False,
			dashboard_token=token,
			codcas=code,
			center_name=center_name,
			medical_url=medical_url,
			non_medical_url=non_medical_url,
			odo_medical_url=odo_medical_url,
		)

	@bp.route('/dashboard_eme_prioridad_<prioridad>/<codcas>')
	@login_required
	def dashboard_eme_prioridad_redirect(prioridad, codcas):
		qs = request.query_string.decode()
		resolved_code = decode_code(codcas) or codcas
		token = encode_code(resolved_code)
		dashboard_url = f'/dashboard_alt_embed/prioridad_{prioridad}/{token}/'
		if qs:
			dashboard_url = f'{dashboard_url}?{qs}'
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url=dashboard_url,
			codcas=resolved_code,
		)

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

	@bp.route('/reportes_gerenciales/historico/', endpoint='historico_ce')
	@login_required
	def historico_ce():
		back_url = url_for('main.reportes_gerenciales')
		return render_template(
			'historico_ce.html',
			back_url=back_url,
			show_modules=False,
		)

	@bp.route('/tramas/')
	@login_required
	def tramas():
		if current_user.role != 'admin':
			flash('Solo los administradores pueden acceder a las Tramas B1-B2.', 'danger')
			return redirect(url_for('main.index'))
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url='/tramas_embed/',
		)

	@bp.route('/patologias/')
	@login_required
	def modulo_patologias():
		if current_user.role != 'admin':
			flash('Solo los administradores pueden acceder al Modulo Ejecutivo de Patologias.', 'danger')
			return redirect(url_for('main.index'))
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url='/dashboard_ejec_embed/',
		)

	@bp.route('/busqueda-paciente/')
	@login_required
	def busqueda_paciente():
		if current_user.role != 'admin':
			flash('Solo los administradores pueden acceder a la Busqueda de Paciente.', 'danger')
			return redirect(url_for('main.index'))
		return render_template(
			'wrappers/dashboard_wrapper.html',
			show_modules=False,
			dashboard_url='/busqueda_paciente_embed/',
		)

	# Version beta (React + Nivo) de la pestaña "Analitica por patologia de
	# alto costo". Ruta nueva e independiente: /patologias/ sigue sirviendo
	# la version Dash completa (3 pestañas) sin cambios.
	FRONTEND_EJEC_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend_ejec', 'dist')

	@bp.route('/patologias-beta/')
	@bp.route('/patologias-beta/<path:filename>')
	@login_required
	def modulo_patologias_beta(filename='index.html'):
		if current_user.role != 'admin':
			flash('Solo los administradores pueden acceder al Modulo Ejecutivo de Patologias.', 'danger')
			return redirect(url_for('main.index'))
		target = filename
		if not os.path.isfile(os.path.join(FRONTEND_EJEC_DIST, target)):
			target = 'index.html'
		return send_from_directory(FRONTEND_EJEC_DIST, target)

	app.register_blueprint(bp)
