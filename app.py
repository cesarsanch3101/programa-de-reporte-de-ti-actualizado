from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import sqlite3
import os
from datetime import datetime
from flask_mail import Mail, Message

# --- Configuración ---
from config import config_dict
config = config_dict['development']

app = Flask(__name__)
app.config.from_object(config)
mail = Mail(app)

# --- RUTA FAVICON ---
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# --- Base de Datos ---
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DB_FILE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- LÓGICA DE CORREO DINÁMICA ---
def get_mail_config_from_db():
    db = get_db()
    try:
        rows = db.execute("SELECT clave, valor FROM configuracion WHERE clave LIKE 'MAIL_%'").fetchall()
        conf = {row['clave']: row['valor'] for row in rows}
        return conf
    except:
        return {}

def enviar_correo_notificacion(destinatario, asunto, template_html):
    if not destinatario: return
    db_config = get_mail_config_from_db()
    
    if db_config.get('MAIL_USERNAME') and db_config.get('MAIL_PASSWORD'):
        app.config.update(
            MAIL_SERVER=db_config.get('MAIL_SERVER', 'smtp.gmail.com'),
            MAIL_PORT=int(db_config.get('MAIL_PORT', 587)),
            MAIL_USE_TLS=db_config.get('MAIL_USE_TLS') == 'True',
            MAIL_USERNAME=db_config.get('MAIL_USERNAME'),
            MAIL_PASSWORD=db_config.get('MAIL_PASSWORD'),
            MAIL_DEFAULT_SENDER=db_config.get('MAIL_USERNAME')
        )
        mail_instance = Mail(app)
    else:
        mail_instance = mail

    try:
        msg = Message(asunto, recipients=[destinatario])
        msg.html = template_html
        mail_instance.send(msg)
    except Exception as e:
        print(f"⚠️ Error enviando correo: {e}")

# --- Decoradores ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin': return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rutas de Autenticación ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM usuarios WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session.update({'user_id': user['id'], 'username': user['username'], 'role': user['role']})
            db.execute("INSERT INTO auditoria_logs (usuario_id, accion) VALUES (?, 'LOGIN')", (user['id'],))
            db.commit()
            return redirect(url_for('dashboard'))
        flash('❌ Usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- DASHBOARD ---
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    kpis = {
        "total_abiertos": db.execute("SELECT COUNT(*) FROM soportes WHERE estado = 'Abierto'").fetchone()[0],
        "total_en_proceso": db.execute("SELECT COUNT(*) FROM soportes WHERE estado = 'En Proceso'").fetchone()[0],
        "mis_tickets": db.execute("SELECT COUNT(*) FROM soportes WHERE usuario_id = ?", (session['user_id'],)).fetchone()[0],
        "mantenimientos_pendientes": db.execute("SELECT COUNT(*) FROM mantenimientos WHERE estado = 'Pendiente'").fetchone()[0]
    }
    estados_raw = db.execute("SELECT estado, COUNT(*) as cantidad FROM soportes GROUP BY estado").fetchall()
    grafico_estado = {"labels": [r['estado'] for r in estados_raw], "datos": [r['cantidad'] for r in estados_raw]}
    cats_raw = db.execute("SELECT categoria, COUNT(*) as cantidad FROM soportes GROUP BY categoria ORDER BY cantidad DESC").fetchall()
    grafico_cat = {"labels": [r['categoria'] for r in cats_raw], "datos": [r['cantidad'] for r in cats_raw]}
    return render_template('dashboard.html', kpis=kpis, g_estado=grafico_estado, g_cat=grafico_cat)

# --- TICKETS (CON FILTROS AVANZADOS) ---
@app.route('/soportes')
@login_required
def lista_soportes():
    db = get_db()
    
    # 1. Capturar filtros desde la URL (GET)
    f_inicio = request.args.get('fecha_inicio')
    f_fin = request.args.get('fecha_fin')
    f_categoria = request.args.get('categoria')
    f_prioridad = request.args.get('prioridad')
    f_estado = request.args.get('estado')
    f_tecnico = request.args.get('tecnico_id')

    # 2. Query Base
    query = """
        SELECT s.*, u.username as nombre_usuario, t.username as nombre_tecnico 
        FROM soportes s 
        JOIN usuarios u ON s.usuario_id = u.id 
        LEFT JOIN usuarios t ON s.tecnico_id = t.id 
        WHERE 1=1
    """
    params = []
    
    # 3. Aplicar Filtros Dinámicamente
    if session['role'] == 'user':
        query += " AND s.usuario_id = ?"
        params.append(session['user_id'])
    
    # Filtro de Fechas
    if f_inicio and f_fin:
        # SQLite date() extrae la parte de fecha YYYY-MM-DD
        query += " AND date(s.fecha_creacion) BETWEEN ? AND ?"
        params.extend([f_inicio, f_fin])
    
    # Filtros de Selección (Ignorar si es 'Todos' o vacío)
    if f_categoria and f_categoria != 'Todos':
        query += " AND s.categoria = ?"
        params.append(f_categoria)

    if f_prioridad and f_prioridad != 'Todos':
        query += " AND s.prioridad = ?"
        params.append(f_prioridad)

    if f_estado and f_estado != 'Todos':
        query += " AND s.estado = ?"
        params.append(f_estado)

    if f_tecnico and f_tecnico != 'Todos':
        query += " AND s.tecnico_id = ?"
        params.append(f_tecnico)
    
    # 4. Ordenamiento VIP (Abiertos primero, luego por fecha)
    query += """
        ORDER BY 
            CASE WHEN s.estado IN ('Abierto', 'En Proceso') THEN 0 ELSE 1 END ASC,
            s.fecha_creacion DESC
    """
    
    tickets = db.execute(query, params).fetchall()
    
    # 5. Cargar datos para los dropdowns del filtro
    tecnicos = db.execute("SELECT id, username FROM usuarios WHERE role IN ('admin', 'tecnico')").fetchall()
    
    return render_template('lista_soportes.html', 
                           soportes=tickets, 
                           tecnicos=tecnicos,
                           categorias=config.CATEGORIAS,
                           prioridades=config.PRIORIDADES,
                           estados=config.ESTADOS)

@app.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar():
    db = get_db()
    if request.method == 'POST':
        usuario_reporta_id = request.form.get('usuario_id')
        cursor = db.execute("INSERT INTO soportes (usuario_id, problema, categoria, prioridad, fecha_creacion) VALUES (?, ?, ?, ?, ?)",
                   (usuario_reporta_id, request.form['problema'], request.form['categoria'], request.form['prioridad'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        ticket_id = cursor.lastrowid
        db.commit()
        
        usuario_reporta = db.execute("SELECT email, username FROM usuarios WHERE id = ?", (usuario_reporta_id,)).fetchone()
        if usuario_reporta and usuario_reporta['email']:
            html_body = render_template('email_nuevo_ticket.html', usuario=usuario_reporta['username'], ticket_id=ticket_id, problema=request.form['problema'])
            enviar_correo_notificacion(usuario_reporta['email'], f"Ticket #{ticket_id} Creado", html_body)
            flash(f'✅ Ticket creado y notificación enviada.', 'success')
        else:
            flash('✅ Ticket creado.', 'warning')
        return redirect(url_for('lista_soportes'))
    
    if session['role'] in ['admin', 'tecnico']:
        usuarios = db.execute("SELECT id, username FROM usuarios ORDER BY username").fetchall()
    else:
        usuarios = [{"id": session['user_id'], "username": session['username']}]
    return render_template('agregar.html', categorias=config.CATEGORIAS, prioridades=config.PRIORIDADES, usuarios=usuarios)

@app.route('/editar/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def editar(ticket_id):
    db = get_db()
    ticket = db.execute("SELECT * FROM soportes WHERE id = ?", (ticket_id,)).fetchone()
    if not ticket or (session['role'] == 'user' and ticket['usuario_id'] != session['user_id']):
        return redirect(url_for('lista_soportes'))

    if request.method == 'POST':
        if session['role'] == 'user':
            if ticket['estado'] != 'Abierto': return redirect(url_for('editar', ticket_id=ticket_id))
            db.execute("UPDATE soportes SET problema=?, categoria=?, prioridad=? WHERE id=?",
                       (request.form['problema'], request.form['categoria'], request.form['prioridad'], ticket_id))
        else:
            estado, solucion, tecnico_id = request.form.get('estado'), request.form.get('solucion'), request.form.get('tecnico_id')
            if estado in ['Resuelto', 'Cerrado'] and not solucion:
                flash('⚠️ Documenta la solución.', 'warning')
                return redirect(url_for('editar', ticket_id=ticket_id))
            db.execute("UPDATE soportes SET estado=?, tecnico_id=?, solucion=? WHERE id=?",
                       (estado, tecnico_id if tecnico_id else None, solucion, ticket_id))
        db.commit()
        return redirect(url_for('lista_soportes'))

    tecnicos = db.execute("SELECT id, username FROM usuarios WHERE role IN ('admin', 'tecnico')").fetchall()
    return render_template('editar.html', ticket=ticket, tecnicos=tecnicos, estados=config.ESTADOS, categorias=config.CATEGORIAS, prioridades=config.PRIORIDADES)

@app.route('/soportes/eliminar/<int:ticket_id>', methods=['POST'])
@admin_required
def eliminar_soporte(ticket_id):
    db = get_db()
    db.execute("DELETE FROM soportes WHERE id = ?", (ticket_id,))
    db.commit()
    flash(f'🗑️ Ticket #{ticket_id} eliminado correctamente.', 'success')
    return redirect(url_for('lista_soportes'))

# --- EQUIPOS ---
@app.route('/equipos')
@login_required
def lista_equipos():
    # Obtener equipos con usuario asignado
    equipos = get_db().execute("""
        SELECT e.*, u.username as usuario_asignado 
        FROM equipos e 
        LEFT JOIN usuarios u ON e.usuario_asignado_id = u.id 
        ORDER BY e.nombre_equipo
    """).fetchall()
    
    # Listas para filtros del reporte
    tipos = get_db().execute("SELECT DISTINCT tipo FROM equipos WHERE tipo IS NOT NULL").fetchall()
    
    return render_template('lista_equipos.html', equipos=equipos, tipos=tipos)

# NUEVA RUTA: VER FICHA TÉCNICA
@app.route('/equipos/ver/<int:equipo_id>')
@login_required
def ver_equipo(equipo_id):
    db = get_db()
    equipo = db.execute("""
        SELECT e.*, u.username as usuario_asignado, u.departamento 
        FROM equipos e 
        LEFT JOIN usuarios u ON e.usuario_asignado_id = u.id 
        WHERE e.id = ?
    """, (equipo_id,)).fetchone()
    
    if not equipo:
        flash('Equipo no encontrado.', 'danger')
        return redirect(url_for('lista_equipos'))
        
    # Obtener historial de mantenimiento de este equipo
    historial = db.execute("""
        SELECT * FROM mantenimientos 
        WHERE equipo_id = ? 
        ORDER BY fecha_programada DESC
    """, (equipo_id,)).fetchall()
    
    # Obtener historial de tickets de este equipo (si implementamos la relación en tickets)
    # Por ahora solo mantenimientos
    
    return render_template('ver_equipo.html', equipo=equipo, historial=historial)

@app.route('/equipos/gestion', methods=['GET', 'POST'])
@app.route('/equipos/gestion/<int:equipo_id>', methods=['GET', 'POST'])
@admin_required
def gestion_equipo(equipo_id=None):
    db = get_db()
    equipo = db.execute("SELECT * FROM equipos WHERE id = ?", (equipo_id,)).fetchone() if equipo_id else None
    if request.method == 'POST':
        data = (request.form['nombre_equipo'], request.form['tipo'], request.form['marca_modelo'], request.form['numero_serie'], request.form['procesador'], request.form['memoria_ram'], request.form['tipo_ram'], request.form['disco_duro'], request.form['tipo_disco'], request.form['fecha_compra'], request.form.get('usuario_asignado_id') or None)
        try:
            if equipo_id:
                db.execute("UPDATE equipos SET nombre_equipo=?, tipo=?, marca_modelo=?, numero_serie=?, procesador=?, memoria_ram=?, tipo_ram=?, disco_duro=?, tipo_disco=?, fecha_compra=?, usuario_asignado_id=? WHERE id=?", data + (equipo_id,))
                flash('Equipo actualizado.', 'success')
            else:
                db.execute("INSERT INTO equipos (nombre_equipo, tipo, marca_modelo, numero_serie, procesador, memoria_ram, tipo_ram, disco_duro, tipo_disco, fecha_compra, usuario_asignado_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", data)
                flash('Equipo registrado.', 'success')
            db.commit()
            return redirect(url_for('lista_equipos'))
        except sqlite3.IntegrityError: flash('Error: Duplicado.', 'danger')
    usuarios = db.execute("SELECT id, username FROM usuarios").fetchall()
    return render_template('formulario_equipo.html', equipo=equipo, usuarios=usuarios)

@app.route('/equipos/eliminar/<int:equipo_id>', methods=['POST'])
@admin_required
def eliminar_equipo(equipo_id):
    get_db().execute("DELETE FROM equipos WHERE id = ?", (equipo_id,))
    get_db().commit()
    return redirect(url_for('lista_equipos'))

# --- MANTENIMIENTOS (CON FILTROS DE REPORTE) ---
@app.route('/mantenimientos')
@login_required
def lista_mantenimientos():
    db = get_db()
    
    # 1. Capturar filtros
    f_inicio = request.args.get('fecha_inicio')
    f_fin = request.args.get('fecha_fin')
    f_estado = request.args.get('estado')
    f_equipo = request.args.get('equipo_id')

    # 2. Query Base
    query = """
        SELECT m.*, e.nombre_equipo, u.username as tecnico 
        FROM mantenimientos m 
        JOIN equipos e ON m.equipo_id = e.id
        LEFT JOIN usuarios u ON m.tecnico_asignado_id = u.id 
        WHERE 1=1
    """
    params = []

    # 3. Aplicar Filtros
    if f_inicio and f_fin:
        query += " AND m.fecha_programada BETWEEN ? AND ?"
        params.extend([f_inicio, f_fin])
    
    if f_estado and f_estado != 'Todos':
        query += " AND m.estado = ?"
        params.append(f_estado)

    if f_equipo and f_equipo != 'Todos':
        query += " AND m.equipo_id = ?"
        params.append(f_equipo)

    # Ordenar por fecha
    query += " ORDER BY m.fecha_programada ASC"

    mantenimientos = db.execute(query, params).fetchall()
    
    # Listas para los filtros
    equipos = db.execute("SELECT id, nombre_equipo FROM equipos ORDER BY nombre_equipo").fetchall()
    
    return render_template('mantenimientos.html', 
                           mantenimientos=mantenimientos, 
                           equipos=equipos) 
@app.route('/calendario')
@login_required
def ver_calendario():
    return render_template('calendario.html')

@app.route('/api/eventos')
@login_required
def api_eventos():
    db = get_db()
    eventos_db = db.execute("SELECT m.id, m.titulo, m.fecha_programada, m.estado, e.nombre_equipo FROM mantenimientos m JOIN equipos e ON m.equipo_id = e.id").fetchall()
    eventos = []
    for ev in eventos_db:
        color = '#ffc107' if ev['estado'] == 'Pendiente' else '#198754'
        text_color = '#000000' if ev['estado'] == 'Pendiente' else '#ffffff'
        eventos.append({'id': ev['id'], 'title': f"{ev['nombre_equipo']}: {ev['titulo']}", 'start': ev['fecha_programada'], 'color': color, 'textColor': text_color, 'url': url_for('lista_mantenimientos')})
    return jsonify(eventos)

@app.route('/api/mantenimientos/mover', methods=['POST'])
@admin_required
def mover_mantenimiento():
    data = request.get_json()
    get_db().execute("UPDATE mantenimientos SET fecha_programada = ?, motivo_reprogramacion = ? WHERE id = ?", (data.get('nueva_fecha'), data.get('motivo'), data.get('id')))
    get_db().commit()
    return jsonify({'status': 'success'})

@app.route('/mantenimientos/programar', methods=['GET', 'POST'])
@login_required
def programar_mantenimiento():
    if session['role'] == 'user': return redirect(url_for('dashboard'))
    if request.method == 'POST':
        get_db().execute("INSERT INTO mantenimientos (equipo_id, titulo, fecha_programada, estado) VALUES (?, ?, ?, 'Pendiente')", (request.form['equipo_id'], request.form['titulo'], request.form['fecha_programada']))
        get_db().commit()
        return redirect(url_for('lista_mantenimientos'))
    equipos = get_db().execute("SELECT id, nombre_equipo FROM equipos").fetchall()
    return render_template('formulario_mantenimiento.html', equipos=equipos)

@app.route('/mantenimientos/completar/<int:mant_id>', methods=['POST'])
@login_required
def completar_mantenimiento(mant_id):
    if session['role'] == 'user': return redirect(url_for('dashboard'))
    get_db().execute("UPDATE mantenimientos SET estado = 'Realizado', tecnico_asignado_id = ? WHERE id = ?", (session['user_id'], mant_id))
    get_db().commit()
    return redirect(url_for('lista_mantenimientos'))

@app.route('/mantenimientos/reprogramar/<int:mant_id>', methods=['POST'])
@login_required
def reprogramar_mantenimiento(mant_id):
    if session['role'] == 'user': return redirect(url_for('dashboard'))
    get_db().execute("UPDATE mantenimientos SET fecha_programada = ?, motivo_reprogramacion = ? WHERE id = ?", (request.form['nueva_fecha'], request.form['motivo'], mant_id))
    get_db().commit()
    flash('Reprogramado.', 'success')
    return redirect(url_for('lista_mantenimientos'))

@app.route('/mantenimientos/eliminar/<int:mant_id>', methods=['POST'])
@admin_required
def eliminar_mantenimiento(mant_id):
    get_db().execute("DELETE FROM mantenimientos WHERE id = ?", (mant_id,))
    get_db().commit()
    return redirect(url_for('lista_mantenimientos'))

# --- CONFIGURACIÓN ---
@app.route('/admin/configuracion/email', methods=['GET', 'POST'])
@admin_required
def admin_config_email():
    db = get_db()
    if request.method == 'POST':
        campos = ['MAIL_SERVER', 'MAIL_PORT', 'MAIL_USE_TLS', 'MAIL_USERNAME', 'MAIL_PASSWORD']
        for campo in campos:
            valor = request.form.get(campo)
            if campo == 'MAIL_USE_TLS': valor = 'True' if valor else 'False'
            db.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (campo, valor))
        db.commit()
        flash('⚙️ Configuración guardada.', 'success')
        return redirect(url_for('admin_config_email'))
    rows = db.execute("SELECT clave, valor FROM configuracion WHERE clave LIKE 'MAIL_%'").fetchall()
    config_actual = {row['clave']: row['valor'] for row in rows}
    return render_template('admin_config_email.html', config=config_actual)

@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    return render_template('admin_usuarios.html', usuarios=get_db().execute("SELECT * FROM usuarios").fetchall())

@app.route('/admin/usuarios/crear', methods=['GET', 'POST'])
@admin_required
def admin_crear_usuario():
    if request.method == 'POST':
        try:
            get_db().execute("INSERT INTO usuarios (username, password_hash, role, email) VALUES (?, ?, ?, ?)",
                       (request.form['username'], generate_password_hash(request.form['password']), request.form['role'], request.form['email']))
            get_db().commit()
            return redirect(url_for('admin_usuarios'))
        except: flash('Error al crear.', 'danger')
    return render_template('admin_form_usuario.html')

@app.route('/admin/usuarios/editar/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def admin_editar_usuario(user_id):
    db = get_db()
    if request.method == 'POST':
        if request.form['password']:
            db.execute("UPDATE usuarios SET email=?, role=?, password_hash=? WHERE id=?", (request.form['email'], request.form['role'], generate_password_hash(request.form['password']), user_id))
        else:
            db.execute("UPDATE usuarios SET email=?, role=? WHERE id=?", (request.form['email'], request.form['role'], user_id))
        db.commit()
        return redirect(url_for('admin_usuarios'))
    return render_template('admin_editar_usuario.html', usuario=db.execute("SELECT * FROM usuarios WHERE id=?", (user_id,)).fetchone())

@app.route('/admin/usuarios/eliminar/<int:user_id>', methods=['POST'])
@admin_required
def admin_eliminar_usuario(user_id):
    if user_id != session['user_id']:
        get_db().execute("DELETE FROM usuarios WHERE id=?", (user_id,))
        get_db().commit()
    return redirect(url_for('admin_usuarios'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)