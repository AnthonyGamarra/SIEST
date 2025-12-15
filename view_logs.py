from flask import Blueprint, render_template_string
from flask_login import login_required, current_user
from backend.audit_logging import Logs_User
from sqlalchemy import desc
from extensions import db
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
from flask import Response

# Blueprint para las rutas de logs
logs_bp = Blueprint('logs', __name__, url_prefix='/logs')


def format_datetime(dt_obj):
    """Convierte un objeto datetime a formato dd/MM/yyyy HH:mm"""
    try:
        if isinstance(dt_obj, datetime):
            return dt_obj.strftime('%d/%m/%Y %H:%M')
        elif isinstance(dt_obj, str):
            # Remover microsegundos si existen
            dt_str = dt_obj.split('.')[0] if '.' in dt_obj else dt_obj
            # Reemplazar T por espacio
            dt_str = dt_str.replace('T', ' ')
            
            # Intentar parsear formato ISO: YYYY-MM-DD HH:MM:SS
            try:
                dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                return dt.strftime('%d/%m/%Y %H:%M')
            except ValueError:
                pass
            
            # Intentar otros formatos
            for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M']:
                try:
                    dt = datetime.strptime(dt_obj, fmt)
                    return dt.strftime('%d/%m/%Y %H:%M')
                except ValueError:
                    continue
            
            return dt_obj
        return str(dt_obj)
    except Exception as e:
        print(f"Error formateando fecha: {e} - Valor: {dt_obj}")
        return str(dt_obj)


def generate_logs_html(logs, total, graphs=None):
    """Genera el HTML completo con estilos inline para mostrar los logs y gráficos."""
    
    if graphs is None:
        graphs = {'graph1': None, 'graph2': None}
    # Generar scripts para los gráficos
    graphs_script = ""
    if graphs['graph1']:
        graphs_script += f"""
        document.addEventListener('DOMContentLoaded', function() {{
            var graph1Data = {graphs['graph1']};
            
            function updateGraph1() {{
                var newLayout = JSON.parse(JSON.stringify(graph1Data.layout));
                if (window.innerWidth > 1200) {{
                    newLayout.margin = {{l: 60, r: 40, t: 60, b: 50}};
                    newLayout.height = 500;
                }} else if (window.innerWidth > 768) {{
                    newLayout.margin = {{l: 50, r: 30, t: 50, b: 40}};
                    newLayout.height = 450;
                }} else {{
                    newLayout.margin = {{l: 40, r: 20, t: 40, b: 40}};
                    newLayout.height = 380;
                }}
                newLayout.autosize = true;
                return newLayout;
            }}
            
            var layout1 = updateGraph1();
            Plotly.newPlot('graph1', graph1Data.data, layout1, {{responsive: true, maintainAspectRatio: false}});
            
            // Listener mejorado
            var resizeTimer;
            window.addEventListener('resize', function() {{
                clearTimeout(resizeTimer);
                resizeTimer = setTimeout(function() {{
                    var newLayout = updateGraph1();
                    Plotly.relayout('graph1', newLayout);
                }}, 300);
            }});
            
            // Escuchar cambios de orientación
            window.addEventListener('orientationchange', function() {{
                setTimeout(function() {{
                    var newLayout = updateGraph1();
                    Plotly.relayout('graph1', newLayout);
                }}, 100);
            }});
        }});
        """
    else:
        graphs_script += """
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('graph1').innerHTML = '<p style="text-align:center;padding:20px;color:#999;">No hay datos para gráfico</p>';
        });
        """
    
    if graphs.get('graph2'):
        graphs_script += f"""
        document.addEventListener('DOMContentLoaded', function() {{
            var graph2Data = {graphs['graph2']};
            
            function updateGraph2() {{
                var newLayout = JSON.parse(JSON.stringify(graph2Data.layout));
                if (window.innerWidth > 1200) {{
                    newLayout.margin = {{l: 60, r: 40, t: 60, b: 50}};
                    newLayout.height = 500;
                }} else if (window.innerWidth > 768) {{
                    newLayout.margin = {{l: 50, r: 30, t: 50, b: 40}};
                    newLayout.height = 450;
                }} else {{
                    newLayout.margin = {{l: 40, r: 20, t: 40, b: 40}};
                    newLayout.height = 380;
                }}
                newLayout.autosize = true;
                return newLayout;
            }}
            
            var layout2 = updateGraph2();
            Plotly.newPlot('graph2', graph2Data.data, layout2, {{responsive: true, maintainAspectRatio: false}});
            
            // Listener mejorado
            var resizeTimer;
            window.addEventListener('resize', function() {{
                clearTimeout(resizeTimer);
                resizeTimer = setTimeout(function() {{
                    var newLayout = updateGraph2();
                    Plotly.relayout('graph2', newLayout);
                }}, 300);
            }});
            
            // Escuchar cambios de orientación
            window.addEventListener('orientationchange', function() {{
                setTimeout(function() {{
                    var newLayout = updateGraph2();
                    Plotly.relayout('graph2', newLayout);
                }}, 100);
            }});
        }});
        """
    else:
        graphs_script += """
        document.addEventListener('DOMContentLoaded', function() {
            var graph2Elem = document.getElementById('graph2');
            if (graph2Elem) {
                graph2Elem.innerHTML = '<p style="text-align:center;padding:20px;color:#999;">No hay datos para gráfico</p>';
            }
        });
        """
    # Generar filas de la tabla
    rows_html = ""
    if logs:
        for log in logs:
            # Extraer solo la IP sin el UUID
            ip_display = log.ip_user.split('-')[0] if log.ip_user and '-' in log.ip_user else (log.ip_user or 'N/A')
            # Formatear la fecha
            fecha_formateada = format_datetime(log.fecha)
            
            # Badge de método HTTP
            metodo = log.peticiones or 'N/A'
            metodo_color = {
                'GET': '#0d6efd', 'POST': '#198754', 'PUT': '#fd7e14', 
                'DELETE': '#dc3545', 'PATCH': '#6c757d'
            }.get(metodo, '#6c757d')
            
            # Badge de estado
            estado = log.status or 'success'
            estado_color = {
                'success': '#28a745', 'error': '#dc3545', 'denied': '#ffc107'
            }.get(estado, '#6c757d')
            
            rows_html += f"""
            <tr>
                <td>{log.id}</td>
                <td>{ip_display}</td>
                <td>{log.user or 'Anónimo'}</td>
                <td><span class="log-event">{log.log}</span></td>
                <td><span class="badge" style="background-color: {metodo_color};">{metodo}</span></td>
                <td style="font-size: 11px; max-width: 200px; overflow: hidden; text-overflow: ellipsis;">{log.urls or 'N/A'}</td>
                <td style="font-size: 11px;">{log.navegador or 'N/A'}</td>
                <td><span class="badge" style="background-color: {estado_color};">{estado}</span></td>
                <td>{log.user_role or 'N/A'}</td>
                <td>{fecha_formateada}</td>
            </tr>
            """
    else:
        rows_html = '<tr><td colspan="10" style="text-align: center; padding: 2rem;">No hay registros de logs</td></tr>'
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Logs de Auditoría</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                
            }}
            body {{
                font-family: 'Calibri', Arial, sans-serif;
                background: #F5F7FB;
                margin: 0;
                padding: 20px;
                min-height: 100vh;
                
            }}
            .logs-container {{
                width: 100%;
                max-width: 1600px;
                margin: 0 auto;
                display: flex;
                flex-direction: column;
                gap: 20px;
            }}
            h1 {{
                margin: 0;
                font-size: 32px;
                color: #003b72;
                font-weight: 700;
            }}
            .logs-subtitle {{
                color: #6b6b6b;
                font-size: 15px;
                margin-top: 4px;
            }}
            .header-card {{
                background: white;
                padding: 24px;
                border-radius: 14px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.08);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
                margin-bottom: 20px;
            }}
            .stat-card {{
                background: white;
                padding: 20px;
                border-radius: 14px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.08);
                text-align: center;
            }}
            .stat-number {{
                font-size: 36px;
                font-weight: 700;
                color: #0064AF;
                line-height: 1;
            }}
            .stat-label {{
                font-size: 13px;
                margin-top: 8px;
                color: #6b6b6b;
            }}
            .content-card {{
                background: white;
                padding: 24px;
                border-radius: 14px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.08);
            }}
            .section-title {{
                font-size: 18px;
                font-weight: 600;
                color: #0064AF;
                margin-bottom: 16px;
                padding-bottom: 12px;
                border-bottom: 2px solid #e9ecef;
            }}
            .logs-table-wrapper {{
                overflow-x: auto;
                max-height: 500px;
                overflow-y: auto;
            }}
            .logs-table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 8px;
                overflow: hidden;
            }}
            .logs-table thead {{
                background: linear-gradient(135deg, #0076d6 0%, #0064AF 100%);
                color: white;
                position: sticky;
                top: 0;
                z-index: 10;
            }}
            .logs-table th {{
                padding: 12px 16px;
                text-align: left;
                font-weight: 600;
                font-size: 14px;
            }}
            .logs-table td {{
                padding: 12px 16px;
                border-bottom: 1px solid #e2e6ea;
                font-size: 13px;
                color: #2f2f2f;
            }}
            .logs-table tbody tr:hover {{
                background-color: rgba(0,100,175,0.05);
            }}
            .log-event {{
                display: inline-block;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                background-color: #e8f4ff;
                color: #0064AF;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                color: white;
            }}
            .logs-actions {{
                text-align: center;
                margin-top: 16px;
            }}
            .header-actions {{
                display: flex;
                gap: 10px;
                align-items: center;
            }}
            .btn-export, .btn-back {{
                display: inline-block;
                padding: 10px 20px;
                min-width: 150px;
                text-align: center;
                color: white;
                border-radius: 8px;
                text-decoration: none;
                font-size: 14px;
                font-weight: 600;
                transition: transform 0.15s ease, background 0.15s ease;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            }}
            .btn-export {{
                background: #198754;
                box-shadow: 0 4px 10px rgba(25,135,84,0.15);
            }}
            .btn-export:hover {{
                background: #146c43;
                transform: translateY(-2px);
            }}
            .btn-back {{
                background: #0064AF;
                box-shadow: 0 4px 12px rgba(0,100,175,0.2);
            }}
            .btn-back:hover {{
                background: #004d8c;
                transform: translateY(-2px);
            }}
            
            /* Gráficos - Responsive */
            .graphs-container {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                width: 100%;
            }}
            
            .graph-card {{
                background: transparent;
                border-radius: 14px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.08);
                padding: 20px;
                min-height: 500px;
                width: 100%;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                animation: fadeInGraph 0.6s ease-out;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }}
            
            .graph-card:hover {{
                box-shadow: 0 12px 28px rgba(0,0,0,0.12);
            }}
            
            @keyframes fadeInGraph {{
                from {{
                    opacity: 0;
                    transform: translateY(20px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            
            /* Media queries para responsive */
            @media (max-width: 1400px) {{
                .graph-card {{
                    min-height: 480px;
                }}
            }}
            
            @media (max-width: 1200px) {{
                .graphs-container {{
                    grid-template-columns: 1fr;
                }}
                .graph-card {{
                    min-height: 450px;
                }}
            }}
            
            @media (max-width: 768px) {{
                .logs-container {{
                    padding: 16px;
                    overflow-y: auto;
                }}
                h1 {{
                    font-size: 22px;
                }}
                .logs-stats {{
                    flex-direction: column;
                }}
                .logs-table {{
                    font-size: 12px;
                }}
                .logs-table th,
                .logs-table td {{
                    padding: 8px 10px;
                }}
                .graphs-container {{
                    grid-template-columns: 1fr;
                    gap: 16px;
                }}
                .graph-card {{
                    min-height: 380px;
                    padding: 12px;
                }}
                .header-card {{
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 12px;
                }}
                .header-actions {{
                    flex-wrap: wrap;
                    width: 100%;
                }}
                .btn-export, .btn-back {{
                    flex: 1;
                    min-width: 120px;
                }}
            }}
            
            @media (max-width: 480px) {{
                .logs-container {{
                    padding: 10px;
                }}
                h1 {{
                    font-size: 18px;
                }}
                .graphs-container {{
                    grid-template-columns: 1fr;
                    gap: 10px;
                }}
                .graph-card {{
                    min-height: 320px;
                    padding: 8px;
                    border-radius: 10px;
                }}
                .logs-table {{
                    font-size: 11px;
                }}
                .logs-table th,
                .logs-table td {{
                    padding: 6px 8px;
                }}
                .header-actions {{
                    flex-direction: column;
                    gap: 8px;
                }}
                .btn-export, .btn-back {{
                    width: 100%;
                    padding: 8px 12px;
                    font-size: 13px;
                }}
            }}
        </style>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    </head>
    <body>
        <div class="logs-container">
            <!-- Header -->
            <div class="header-card">
                <div style="flex:1">
                    <h1>📊 Dashboard de Auditoría</h1>
                    <p class="logs-subtitle">Análisis completo de logs y actividad del sistema</p>
                </div>
                <div class="header-actions">
                    <a href="/" class="btn-back">← Volver al inicio</a>
                    <a href="/logs/export_csv" class="btn-export" role="button">Exportar CSV</a>
                </div>
            </div>
            <!-- Estadísticas -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{total}</div>
                    <div class="stat-label">Total de Logs</div>
                </div>
            </div>
            <!-- Gráficos -->
            <div class="graphs-container">
                <div class="graph-card" id="graph1"></div>
                <div class="graph-card" id="graph2"></div>
            </div>
            <!-- Tabla de Logs -->
            <div class="content-card">
                <div class="section-title">📋 Registro Detallado de Logs</div>
                <div class="logs-table-wrapper">
                    <table class="logs-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>IP</th>
                                <th>Usuario</th>
                                <th>Evento</th>
                                <th>Método</th>
                                <th>URL</th>
                                <th>Navegador</th>
                                <th>Estado</th>
                                <th>Rol</th>
                                <th>Fecha/Hora</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
            </div>
            <!-- (Botón movido al header) -->
        </div>
        <script>
            {graphs_script}
        </script>
    </body>
    </html>
    """
    
    return html_content


def generate_graphs(logs):
    """Genera gráficos Plotly basados en los logs.
    
    Retorna un diccionario con los gráficos serializados.
    """
    if not logs or len(logs) == 0:
        print("DEBUG: No hay logs para generar gráficos")
        return {'graph1': None, 'graph2': None}
    
    # Convertir a DataFrame
    df = pd.DataFrame([{
        'user': log.user or 'Anónimo',
        'log': log.log or 'evento',
        'status': getattr(log, 'status', 'success') or 'success',
        'peticiones': getattr(log, 'peticiones', 'N/A') or 'N/A',
        'user_role': getattr(log, 'user_role', 'sin_rol') or 'sin_rol',
        'urls': getattr(log, 'urls', '') or '',
    } for log in logs])
    
  
    
    try:
        # GRÁFICO 1: Cantidad de logs por rol (solo URL = /login)
        df_login = df[df['urls'] == '/login']
        
        if len(df_login) == 0:
            print("DEBUG: No hay logs de login para el gráfico 1")
            graph1_json = None
        else:
            eventos_por_rol = df_login['user_role'].value_counts().sort_values(ascending=False)
            
            
            # Convertir a listas para asegurar compatibilidad
            import numpy as np
            roles_list = eventos_por_rol.index.tolist()
            valores_list = eventos_por_rol.values.tolist()
            
            
            # Crear colores según el rol
            colors_list = ['#0064AF' if str(r).strip() == 'admin' else '#4C78A8' if str(r).strip() == 'user' else '#9D755D' 
                           for r in roles_list]
            
            
            # Usar graph_objects para gráfico de barras vertical
            fig1 = go.Figure()
            fig1.add_trace(go.Bar(
                x=roles_list,
                y=valores_list,
                text=valores_list,
                textposition='outside',
                marker=dict(color=colors_list),
                hovertemplate='<b>%{x}</b><br>Logs: %{y}<extra></extra>'
            ))
            
            fig1.update_layout(
                title='Cantidad de Ingresos de Usuarios por Rol',
                xaxis_title='Rol',
                yaxis_title='Número de Ingresos',
                showlegend=False,
                margin=dict(l=60, r=60, t=80, b=60),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Calibri, Arial, sans-serif', size=13, color='#2f2f2f'),
                height=400,
                xaxis=dict(gridcolor='#e9ecef'),
                yaxis=dict(gridcolor='#e9ecef', zeroline=True)
            )
            
            # Serializar gráfico 1 usando to_json()
            graph1_json = fig1.to_json()
        
        # GRÁFICO 2: Cantidad de logs por fecha (línea)
        try:
            from sqlalchemy import text
            query_str = """SELECT 
                           TO_CHAR(fecha, 'DD/MM/YYYY') AS fecha,
                           COUNT(*) AS cantidad_logs
                           FROM public."Log_users"
                           GROUP BY TO_CHAR(fecha, 'DD/MM/YYYY')
                           ORDER BY TO_CHAR(fecha, 'DD/MM/YYYY');
                        """
            
            result = db.session.execute(text(query_str))
            rows = result.fetchall()
            
            if rows and len(rows) > 0:
                fechas = [str(row[0]) for row in rows]
                cantidades = [row[1] for row in rows]
                
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=fechas,
                    y=cantidades,
                    mode='lines+markers',
                    name='Cantidad de logs',
                    line=dict(color='#0064AF', width=3),
                    marker=dict(size=8, color='#0064AF'),
                    hovertemplate='<b>%{x}</b><br>Logs: %{y}<extra></extra>'
                ))
                
                fig2.update_layout(
                    title='Cantidad de Logs por Fecha',
                    xaxis_title='Fecha',
                    yaxis_title='Número de logs',
                    showlegend=False,
                    margin=dict(l=60, r=60, t=80, b=60),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Calibri, Arial, sans-serif', size=13, color='#2f2f2f'),
                    height=400,
                    xaxis=dict(gridcolor='#e9ecef'),
                    yaxis=dict(gridcolor='#e9ecef', zeroline=True),
                    hovermode='x unified'
                )
                
                graph2_json = fig2.to_json()
            else:
                graph2_json = None
        except Exception as e:
            print(f"ERROR al generar gráfico 2 (línea de fechas): {e}")
            graph2_json = None
        
        return {'graph1': graph1_json, 'graph2': graph2_json}
    
    except Exception as e:
        print(f"ERROR al generar gráficos: {e}")
        import traceback
        traceback.print_exc()
        return {'graph1': None, 'graph2': None}


@logs_bp.route('/')
@login_required
def view_logs():
    """Vista principal para mostrar logs de auditoría.
    
    Solo accesible para administradores.
    Muestra todos los registros de la tabla Log_users en una sola página
    junto con 2 gráficos de análisis.
    """
    # Verificar que el usuario sea admin
    if current_user.role != 'admin':
        return "Acceso denegado. Solo administradores pueden ver los logs.", 403
    
    # Consultar TODOS los logs ordenados por ID descendente (más recientes primero)
    logs = Logs_User.query.order_by(desc(Logs_User.id)).all()
    
    # Generar gráficos
    graphs = generate_graphs(logs)
    
    # Generar HTML con tabla y gráficos
    return generate_logs_html(logs, len(logs), graphs)


def register_logs_blueprint(app):
    """Registra el blueprint de logs en la aplicación Flask.
    
    Llamar esta función desde app.py después de crear la app:
        from view_logs import register_logs_blueprint
        register_logs_blueprint(app)
    """
    app.register_blueprint(logs_bp)


@logs_bp.route('/export_csv')
@login_required
def export_logs_csv():
    """Exporta todos los logs como CSV (solo admin)."""
    if current_user.role != 'admin':
        return "Acceso denegado.", 403

    logs = Logs_User.query.order_by(desc(Logs_User.id)).all()

    # Construir lista de dicts con todas las columnas de la tabla mostrada
    rows = []
    for log in logs:
        rows.append({
            'id': getattr(log, 'id', None),
            'ip_user': getattr(log, 'ip_user', None),
            'user': getattr(log, 'user', None),
            'log': getattr(log, 'log', None),
            'peticiones': getattr(log, 'peticiones', None),
            'urls': getattr(log, 'urls', None),
            'navegador': getattr(log, 'navegador', None),
            'status': getattr(log, 'status', None),
            'user_role': getattr(log, 'user_role', None),
            'fecha': format_datetime(getattr(log, 'fecha', None)),
        })

    # Crear DataFrame y generar CSV
    try:
        df_export = pd.DataFrame(rows)
        csv_data = df_export.to_csv(index=False)
        # Responder con attachment
        return Response(
            csv_data,
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': 'attachment; filename=logs_export.csv'}
        )
    except Exception as e:
        print(f"ERROR export CSV: {e}")
        return "Error generando CSV", 500

