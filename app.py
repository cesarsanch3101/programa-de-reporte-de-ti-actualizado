# --- Importaciones ---
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, Response, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import sqlite3
import math
from datetime import datetime
import pandas as pd
import io
from flask_weasyprint import HTML, render_pdf
from flask_mail import Mail, Message
from collections import defaultdict

# --- Importaciones Locales ---
from config import DB_FILE, CATEGORIAS, PRIORIDADES, ESTADOS, PER_PAGE
from database_setup import crear_tablas

# --- Inicialización y Configuración ---
app = Flask(__name__)
app.secret_key = 'clave-secreta-cambiar-en-produccion'

# --- Gestión de la Base de Datos ---
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_FILE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Decoradores ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: flash('Por favor, inicia sesión.', 'warning'); return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: return redirect(url_for('login'))
        if session.get('role') != 'admin': flash('No tienes permisos de administrador.', 'danger'); return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Lógica de Correo ---
def send_email(to, subject, template, **kwargs):
    db = get_db()
    config_rows = db.execute("SELECT clave, valor FROM configuracion WHERE clave LIKE 'MAIL_%'").fetchall()
    app.config.update({row['clave']: row['valor'] for row in config_rows})

    if not all(k in app.config for k in ['MAIL_SERVER', 'MAIL_USERNAME', 'MAIL_PASSWORD']):
        print("Advertencia: Configuración de correo incompleta. No se enviará el email.")
        return

    app.config['MAIL_PORT'] = int(app.config.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = app.config.get('MAIL_USE_TLS') == 'True'
    app.config['MAIL_USE_SSL'] = False

    try:
        mail = Mail(app)
        msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[to])
        msg.html = render_template(template, **kwargs)
        mail.send(msg)
        print(f"Correo de notificación enviado a {to}")
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        flash(f"La operación se completó, pero falló el envío de notificación por correo: {e}", "warning")

# --- Rutas de Autenticación ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']; password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM usuarios WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.clear(); session['user_id'] = user['id']; session['username'] = user['username']; session['role'] = user['role']
            flash(f'¡Bienvenido de nuevo, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear(); flash('Has cerrado la sesión.', 'info'); return redirect(url_for('login'))

# --- Rutas Principales (Soportes y Dashboard) ---
@app.route('/')
@login_required
def home():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    try:
        stats = {
            "total_abiertos": db.execute("SELECT COUNT(*) FROM soportes WHERE estado = 'Abierto'").fetchone()[0],
            "total_en_proceso": db.execute("SELECT COUNT(*) FROM soportes WHERE estado = 'En Proceso'").fetchone()[0],
        }
        datos_estados = db.execute("SELECT estado, COUNT(*) as cantidad FROM soportes GROUP BY estado").fetchall()
        datos_categorias = db.execute("SELECT categoria, COUNT(*) as cantidad FROM soportes GROUP BY categoria").fetchall()
        
        stats.update({
            "labels_estados": [row['estado'] for row in datos_estados],
            "valores_estados": [row['cantidad'] for row in datos_estados],
            "labels_categorias": [row['categoria'] for row in datos_categorias],
            "valores_categorias": [row['cantidad'] for row in datos_categorias]
        })
    except (sqlite3.OperationalError, TypeError):
        stats = {"total_abiertos": 0, "total_en_proceso": 0, "labels_estados": [], "valores_estados": [], "labels_categorias": [], "valores_categorias": []}
    return render_template('dashboard.html', data=stats)

@app.route('/soportes')
@login_required
def lista_soportes():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '', type=str)
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)
    category = request.args.get('categoria', 'todas', type=str)
    departamento = request.args.get('departamento', 'todos', type=str)

    base_query = "FROM soportes WHERE 1=1"
    params = {}
    
    if q: base_query += " AND (usuario LIKE :q OR problema LIKE :q OR tecnico LIKE :q OR id LIKE :q)"; params['q'] = f"%{q}%"
    if start_date: base_query += " AND fecha_inicio >= :start_date"; params['start_date'] = start_date
    if end_date: base_query += " AND fecha_inicio <= :end_date"; params['end_date'] = end_date
    if category != 'todas': base_query += " AND categoria = :category"; params['category'] = category
    if departamento != 'todos': base_query += " AND departamento = :departamento"; params['departamento'] = departamento

    db = get_db()
    departamentos_db = db.execute("SELECT DISTINCT departamento FROM soportes WHERE departamento IS NOT NULL AND departamento != '' ORDER BY departamento").fetchall()
    total_soportes = db.execute("SELECT COUNT(*) " + base_query, params).fetchone()[0]
    total_pages = math.ceil(total_soportes / PER_PAGE)
    offset = (page - 1) * PER_PAGE
    
    soportes_query = "SELECT * " + base_query + " ORDER BY id DESC LIMIT :limit OFFSET :offset"
    params.update({'limit': PER_PAGE, 'offset': offset})
    soportes_de_la_pagina = db.execute(soportes_query, params).fetchall()
    
    pagination_params = {k: v for k, v in request.args.items() if k != 'page'}

    return render_template('lista_soportes.html', soportes=soportes_de_la_pagina, page=page, total_pages=total_pages, categorias=CATEGORIAS, departamentos=departamentos_db, filters={'q': q, 'start_date': start_date, 'end_date': end_date, 'categoria': category, 'departamento': departamento}, pagination_params=pagination_params)

@app.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar():
    if request.method == 'POST':
        email_cliente = request.form['email_cliente']; usuario = request.form['usuario']; problema = request.form['problema']
        db = get_db()
        cursor = db.execute("INSERT INTO soportes (fecha_hora, usuario, departamento, problema, estado, prioridad, categoria, fecha_inicio, tecnico, email_cliente) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), usuario, request.form['departamento'], problema, 'Abierto', request.form['prioridad'], request.form['categoria'], datetime.now().strftime("%Y-%m-%d"), session['username'], email_cliente))
        db.commit()
        
        ticket_id = cursor.lastrowid
        send_email(to=email_cliente, subject=f"Soporte Registrado [ID: #{ticket_id}]", template='email_nuevo_soporte.html', usuario=usuario, ticket_id=ticket_id, problema=problema)
        flash('Soporte registrado con éxito.', 'success')
        return redirect(url_for('lista_soportes'))
    return render_template('agregar.html', categorias=CATEGORIAS, prioridades=PRIORIDADES)

@app.route('/editar/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def editar(ticket_id):
    db = get_db()
    ticket_actual = db.execute("SELECT * FROM soportes WHERE id = ?", (ticket_id,)).fetchone()
    if not ticket_actual: return "Ticket no encontrado", 404

    if request.method == 'POST':
        estado_anterior = ticket_actual['estado']
        nuevo_estado = request.form.get('estado'); solucion = request.form.get('solucion'); comentarios = request.form.get('comentarios_solucion'); tecnico = request.form.get('tecnico')
        
        fecha_finalizacion = ticket_actual['fecha_finalizacion']
        if estado_anterior not in ['Resuelto', 'Cerrado'] and nuevo_estado in ['Resuelto', 'Cerrado']:
            fecha_finalizacion = datetime.now().strftime("%Y-%m-%d")

        db.execute("UPDATE soportes SET estado = ?, solucion = ?, comentarios_solucion = ?, tecnico = ?, fecha_finalizacion = ? WHERE id = ?", (nuevo_estado, solucion, comentarios, tecnico, fecha_finalizacion, ticket_id))
        db.commit()
        flash(f"Soporte #{ticket_id} actualizado correctamente.", 'success')

        if estado_anterior != nuevo_estado and nuevo_estado in ['En Proceso', 'Resuelto', 'Cerrado']:
            ticket_actualizado = db.execute("SELECT * FROM soportes WHERE id = ?", (ticket_id,)).fetchone()
            if ticket_actualizado and ticket_actualizado['email_cliente']:
                send_email(to=ticket_actualizado['email_cliente'], subject=f"Actualización de Soporte [ID: #{ticket_id}] - {nuevo_estado}", template='email_actualizacion_soporte.html', ticket=ticket_actualizado, nuevo_estado=nuevo_estado)
        return redirect(url_for('lista_soportes'))
    
    return render_template('editar.html', ticket=ticket_actual, estados=ESTADOS)

@app.route('/eliminar/<int:ticket_id>', methods=['POST'])
@login_required
@admin_required
def eliminar(ticket_id):
    db = get_db()
    db.execute("DELETE FROM soportes WHERE id = ?", (ticket_id,))
    db.commit()
    flash(f"Soporte #{ticket_id} ha sido eliminado.", 'success')
    return redirect(url_for('lista_soportes'))
    
# --- Rutas del Cronograma de Mantenimiento ---
@app.route('/cronograma')
@login_required
def cronograma():
    db = get_db()
    equipos = db.execute("SELECT id, nombre_equipo FROM equipos ORDER BY nombre_equipo").fetchall()
    return render_template('cronograma.html', equipos=equipos)

@app.route('/api/mantenimientos')
@login_required
def api_mantenimientos():
    db = get_db()
    try:
        eventos_db = db.execute("""
            SELECT m.id, m.titulo, m.fecha_programada, m.estado, e.nombre_equipo 
            FROM mantenimientos m LEFT JOIN equipos e ON m.equipo_id = e.id
        """).fetchall()
        eventos_calendario = []
        for ev in eventos_db:
            color = '#3498db' if ev['estado'] == 'Pendiente' else '#2ecc71'
            eventos_calendario.append({'id': ev['id'], 'title': f"{ev['nombre_equipo'] or 'General'}: {ev['titulo']}", 'start': ev['fecha_programada'], 'color': color, 'allDay': True})
        return jsonify(eventos_calendario)
    except (sqlite3.OperationalError, TypeError):
        return jsonify([])

@app.route('/cronograma/estadisticas')
@login_required
def cronograma_estadisticas():
    db = get_db()
    current_year = datetime.now().year
    mantenimientos = db.execute("SELECT fecha_programada, estado FROM mantenimientos WHERE strftime('%Y', fecha_programada) = ?", (str(current_year),)).fetchall()
    
    monthly_data = defaultdict(lambda: {'Pendiente': 0, 'Ejecutado': 0})
    quarterly_data = defaultdict(lambda: {'Pendiente': 0, 'Ejecutado': 0})
    
    for mant in mantenimientos:
        try:
            fecha = datetime.strptime(mant['fecha_programada'], '%Y-%m-%d')
            month_name = fecha.strftime('%B').capitalize(); monthly_data[month_name][mant['estado']] += 1
            quarter = f"T{(fecha.month - 1) // 3 + 1}"; quarterly_data[quarter][mant['estado']] += 1
        except (ValueError, TypeError): continue

    meses_es = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    monthly_chart_data = {'labels': meses_es, 'datasets': [{'label': 'Pendiente', 'data': [monthly_data[mes].get('Pendiente', 0) for mes in meses_es], 'backgroundColor': '#3498db'}, {'label': 'Ejecutado', 'data': [monthly_data[mes].get('Ejecutado', 0) for mes in meses_es], 'backgroundColor': '#2ecc71'}]}
    
    trimestres = ['T1', 'T2', 'T3', 'T4']
    quarterly_chart_data = {'labels': trimestres, 'datasets': [{'label': 'Pendiente', 'data': [quarterly_data[q].get('Pendiente', 0) for q in trimestres], 'backgroundColor': '#3498db'}, {'label': 'Ejecutado', 'data': [quarterly_data[q].get('Ejecutado', 0) for q in trimestres], 'backgroundColor': '#2ecc71'}]}

    return render_template('cronograma_estadisticas.html', monthly_data=monthly_chart_data, quarterly_data=quarterly_chart_data, year=current_year)

@app.route('/mantenimiento/agregar', methods=['POST'])
@login_required
def agregar_mantenimiento():
    equipo_id = request.form.get('equipo_id')
    titulo = request.form.get('titulo')
    fecha_programada = request.form.get('fecha_programada')

    if not all([equipo_id, titulo, fecha_programada]):
        return jsonify({'success': False, 'message': 'Faltan datos.'}), 400

    db = get_db()
    db.execute(
        "INSERT INTO mantenimientos (equipo_id, titulo, fecha_programada, estado) VALUES (?, ?, ?, ?)",
        (equipo_id, titulo, fecha_programada, 'Pendiente')
    )
    db.commit()
    return jsonify({'success': True, 'message': 'Mantenimiento agregado con éxito.'})

# --- Rutas de Exportación ---
def get_soportes_filtrados(filters):
    base_query = "SELECT * FROM soportes WHERE 1=1"
    params = {}
    if filters.get('q'): base_query += " AND (usuario LIKE :q OR problema LIKE :q OR tecnico LIKE :q OR id LIKE :q)"; params['q'] = f"%{filters.get('q')}%"
    if filters.get('start_date'): base_query += " AND fecha_inicio >= :start_date"; params['start_date'] = filters.get('start_date')
    if filters.get('end_date'): base_query += " AND fecha_inicio <= :end_date"; params['end_date'] = filters.get('end_date')
    if filters.get('categoria') and filters.get('categoria') != 'todas': base_query += " AND categoria = :category"; params['category'] = filters.get('categoria')
    if filters.get('departamento') and filters.get('departamento') != 'todos': base_query += " AND departamento = :departamento"; params['departamento'] = filters.get('departamento')
    return get_db().execute(base_query + " ORDER BY id DESC", params).fetchall()

@app.route('/exportar/excel')
@login_required
def exportar_excel():
    soportes = get_soportes_filtrados(request.args)
    if not soportes: flash("No hay datos para exportar con los filtros seleccionados.", "warning"); return redirect(url_for('lista_soportes'))
    df = pd.DataFrame([dict(row) for row in soportes])
    output = io.BytesIO()
    df.to_excel(output, index=False, sheet_name='Soportes')
    output.seek(0)
    return Response(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment;filename=reporte_soportes_{datetime.now().strftime('%Y-%m-%d')}.xlsx"})

@app.route('/exportar/pdf')
@login_required
def exportar_pdf():
    soportes = get_soportes_filtrados(request.args)
    if not soportes: flash("No hay datos para exportar con los filtros seleccionados.", "warning"); return redirect(url_for('lista_soportes'))
    html = render_template('reporte_pdf.html', soportes=soportes, start_date=request.args.get('start_date'), end_date=request.args.get('end_date'), selected_category=request.args.get('categoria', 'todas'))
    return render_pdf(HTML(string=html), download_filename=f"reporte_soportes_{datetime.now().strftime('%Y-%m-%d')}.pdf")

# --- Rutas de Administración ---
@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/equipos')
@admin_required
def admin_lista_equipos():
    equipos = get_db().execute("SELECT * FROM equipos ORDER BY nombre_equipo").fetchall()
    return render_template('admin_lista_equipos.html', equipos=equipos)

@app.route('/admin/equipos/agregar', methods=['GET', 'POST'])
@admin_required
def admin_agregar_equipo():
    if request.method == 'POST':
        db = get_db()
        try:
            db.execute("INSERT INTO equipos (nombre_equipo, usuario_asignado, tipo, marca_modelo, numero_serie, fecha_adquisicion, notas) VALUES (?, ?, ?, ?, ?, ?, ?)", (request.form['nombre_equipo'], request.form['usuario_asignado'], request.form['tipo'], request.form['marca_modelo'], request.form['numero_serie'], request.form['fecha_adquisicion'], request.form['notas']))
            db.commit()
            flash('Equipo añadido con éxito.', 'success')
        except sqlite3.IntegrityError: flash('Error: Ya existe un equipo con ese nombre.', 'danger')
        return redirect(url_for('admin_lista_equipos'))
    return render_template('admin_form_equipo.html', equipo=None)

@app.route('/admin/equipos/editar/<int:equipo_id>', methods=['GET', 'POST'])
@admin_required
def admin_editar_equipo(equipo_id):
    db = get_db(); equipo = db.execute("SELECT * FROM equipos WHERE id = ?", (equipo_id,)).fetchone()
    if not equipo: return "Equipo no encontrado", 404
    if request.method == 'POST':
        try:
            db.execute("UPDATE equipos SET nombre_equipo=?, usuario_asignado=?, tipo=?, marca_modelo=?, numero_serie=?, fecha_adquisicion=?, notas=? WHERE id = ?", (request.form['nombre_equipo'], request.form['usuario_asignado'], request.form['tipo'], request.form['marca_modelo'], request.form['numero_serie'], request.form['fecha_adquisicion'], request.form['notas'], equipo_id))
            db.commit()
            flash('Equipo actualizado con éxito.', 'success')
        except sqlite3.IntegrityError: flash('Error: El nombre del equipo ya está en uso.', 'danger')
        return redirect(url_for('admin_lista_equipos'))
    return render_template('admin_form_equipo.html', equipo=equipo)

@app.route('/admin/equipos/eliminar/<int:equipo_id>', methods=['POST'])
@admin_required
def admin_eliminar_equipo(equipo_id):
    db = get_db()
    db.execute("DELETE FROM mantenimientos WHERE equipo_id = ?", (equipo_id,))
    db.execute("DELETE FROM equipos WHERE id = ?", (equipo_id,))
    db.commit()
    flash('Equipo y sus mantenimientos asociados han sido eliminados.', 'success')
    return redirect(url_for('admin_lista_equipos'))

@app.route('/admin/usuarios')
@admin_required
def admin_lista_usuarios():
    usuarios = get_db().execute("SELECT id, username, role FROM usuarios ORDER BY username").fetchall()
    return render_template('admin_usuarios.html', usuarios=usuarios)

@app.route('/admin/usuarios/agregar', methods=['GET', 'POST'])
@admin_required
def admin_agregar_usuario():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        if not username or not password or not role:
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('admin_agregar_usuario'))

        password_hash = generate_password_hash(password)
        db = get_db()
        try:
            db.execute(
                "INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role)
            )
            db.commit()
            flash('Usuario añadido con éxito.', 'success')
            return redirect(url_for('admin_lista_usuarios'))
        except sqlite3.IntegrityError:
            flash('Error: El nombre de usuario ya existe.', 'danger')
            return redirect(url_for('admin_agregar_usuario'))
    
    return render_template('admin_form_usuario.html', usuario=None, title="Agregar Usuario", action_url=url_for('admin_agregar_usuario'))

@app.route('/admin/configuracion/email', methods=['GET', 'POST'])
@admin_required
def admin_config_email():
    db = get_db()
    if request.method == 'POST':
        config_items = [('MAIL_SERVER', request.form.get('mail_server')), ('MAIL_PORT', request.form.get('mail_port')), ('MAIL_USE_TLS', str(request.form.get('mail_use_tls') == 'on')), ('MAIL_USERNAME', request.form.get('mail_username')), ('MAIL_PASSWORD', request.form.get('mail_password'))]
        for clave, valor in config_items:
            db.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (clave, valor))
        db.commit()
        flash('Configuración de correo guardada con éxito.', 'success')
        return redirect(url_for('admin_config_email'))
    config_actual = {row['clave']: row['valor'] for row in db.execute("SELECT clave, valor FROM configuracion WHERE clave LIKE 'MAIL_%'").fetchall()}
    return render_template('admin_config_email.html', config=config_actual)

# --- Bloque de Ejecución ---
if __name__ == '__main__':
    crear_tablas()
    app.run(debug=True)