from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import sqlite3
import os
from datetime import datetime
from flask_mail import Mail

# --- Configuración ---
from config import config_dict
config = config_dict['development']

app = Flask(__name__)
app.config.from_object(config)
mail = Mail(app)

# --- RUTA FAVICON (NUEVO) ---
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

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

# --- Decoradores ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('🔒 Inicia sesión para continuar.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('⛔ Acceso restringido a administradores.', 'danger')
            return redirect(url_for('dashboard'))
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

# --- DASHBOARD (Con corrección .datos para JSON) ---
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    
    # 1. Contadores Tarjetas (KPIs)
    kpis = {
        "total_abiertos": db.execute("SELECT COUNT(*) FROM soportes WHERE estado = 'Abierto'").fetchone()[0],
        "total_en_proceso": db.execute("SELECT COUNT(*) FROM soportes WHERE estado = 'En Proceso'").fetchone()[0],
        "mis_tickets": db.execute("SELECT COUNT(*) FROM soportes WHERE usuario_id = ?", (session['user_id'],)).fetchone()[0],
        "mantenimientos_pendientes": db.execute("SELECT COUNT(*) FROM mantenimientos WHERE estado = 'Pendiente'").fetchone()[0]
    }

    # 2. Gráfico de ESTADO
    estados_raw = db.execute("SELECT estado, COUNT(*) as cantidad FROM soportes GROUP BY estado").fetchall()
    grafico_estado = {
        "labels": [row['estado'] for row in estados_raw],
        "datos": [row['cantidad'] for row in estados_raw] # Clave corregida a 'datos'
    }

    # 3. Gráfico de CATEGORÍAS
    cats_raw = db.execute("SELECT categoria, COUNT(*) as cantidad FROM soportes GROUP BY categoria ORDER BY cantidad DESC").fetchall()
    grafico_cat = {
        "labels": [row['categoria'] for row in cats_raw],
        "datos": [row['cantidad'] for row in cats_raw]   # Clave corregida a 'datos'
    }

    return render_template('dashboard.html', kpis=kpis, g_estado=grafico_estado, g_cat=grafico_cat)

# --- Tickets ---
@app.route('/soportes')
@login_required
def lista_soportes():
    db = get_db()
    query = """
        SELECT s.*, u.username as nombre_usuario, t.username as nombre_tecnico 
        FROM soportes s JOIN usuarios u ON s.usuario_id = u.id LEFT JOIN usuarios t ON s.tecnico_id = t.id 
        WHERE 1=1
    """
    params = []
    if session['role'] == 'user':
        query += " AND s.usuario_id = ?"
        params.append(session['user_id'])
    tickets = db.execute(query + " ORDER BY s.fecha_creacion DESC", params).fetchall()
    return render_template('lista_soportes.html', soportes=tickets)

@app.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar():
    if request.method == 'POST':
        get_db().execute("INSERT INTO soportes (usuario_id, problema, categoria, prioridad) VALUES (?, ?, ?, ?)",
                   (session['user_id'], request.form['problema'], request.form['categoria'], request.form['prioridad']))
        get_db().commit()
        return redirect(url_for('lista_soportes'))
    return render_template('agregar.html', categorias=config.CATEGORIAS, prioridades=config.PRIORIDADES)

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

# --- EQUIPOS ---
@app.route('/equipos')
@login_required
def lista_equipos():
    equipos = get_db().execute("""
        SELECT e.*, u.username as usuario_asignado FROM equipos e 
        LEFT JOIN usuarios u ON e.usuario_asignado_id = u.id ORDER BY e.nombre_equipo
    """).fetchall()
    return render_template('lista_equipos.html', equipos=equipos)

@app.route('/equipos/gestion', methods=['GET', 'POST'])
@app.route('/equipos/gestion/<int:equipo_id>', methods=['GET', 'POST'])
@admin_required
def gestion_equipo(equipo_id=None):
    db = get_db()
    equipo = db.execute("SELECT * FROM equipos WHERE id = ?", (equipo_id,)).fetchone() if equipo_id else None

    if request.method == 'POST':
        data = (
            request.form['nombre_equipo'], request.form['tipo'], request.form['marca_modelo'],
            request.form['numero_serie'], request.form['procesador'], request.form['memoria_ram'],
            request.form['tipo_ram'], request.form['disco_duro'], request.form['tipo_disco'],
            request.form['fecha_compra'], request.form.get('usuario_asignado_id') or None
        )
        try:
            if equipo_id:
                db.execute("""
                    UPDATE equipos SET nombre_equipo=?, tipo=?, marca_modelo=?, numero_serie=?,
                    procesador=?, memoria_ram=?, tipo_ram=?, disco_duro=?, tipo_disco=?, fecha_compra=?,
                    usuario_asignado_id=? WHERE id=?
                """, data + (equipo_id,))
                flash('Equipo actualizado.', 'success')
            else:
                db.execute("""
                    INSERT INTO equipos (nombre_equipo, tipo, marca_modelo, numero_serie,
                    procesador, memoria_ram, tipo_ram, disco_duro, tipo_disco, fecha_compra, usuario_asignado_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
                flash('Equipo registrado.', 'success')
            db.commit()
            return redirect(url_for('lista_equipos'))
        except sqlite3.IntegrityError:
            flash('Error: Duplicado.', 'danger')

    usuarios = db.execute("SELECT id, username FROM usuarios").fetchall()
    return render_template('formulario_equipo.html', equipo=equipo, usuarios=usuarios)

@app.route('/equipos/eliminar/<int:equipo_id>', methods=['POST'])
@admin_required
def eliminar_equipo(equipo_id):
    get_db().execute("DELETE FROM equipos WHERE id = ?", (equipo_id,))
    get_db().commit()
    return redirect(url_for('lista_equipos'))

# --- MANTENIMIENTOS Y CALENDARIO API ---
@app.route('/mantenimientos')
@login_required
def lista_mantenimientos():
    mantenimientos = get_db().execute("""
        SELECT m.*, e.nombre_equipo, u.username as tecnico 
        FROM mantenimientos m JOIN equipos e ON m.equipo_id = e.id
        LEFT JOIN usuarios u ON m.tecnico_asignado_id = u.id ORDER BY m.fecha_programada ASC
    """).fetchall()
    return render_template('mantenimientos.html', mantenimientos=mantenimientos)

@app.route('/calendario')
@login_required
def ver_calendario():
    return render_template('calendario.html')

@app.route('/api/eventos')
@login_required
def api_eventos():
    db = get_db()
    eventos_db = db.execute("""
        SELECT m.id, m.titulo, m.fecha_programada, m.estado, e.nombre_equipo 
        FROM mantenimientos m JOIN equipos e ON m.equipo_id = e.id
    """).fetchall()
    
    eventos = []
    for ev in eventos_db:
        color = '#ffc107' if ev['estado'] == 'Pendiente' else '#198754'
        texto_color = '#000000' if ev['estado'] == 'Pendiente' else '#ffffff'
        eventos.append({
            'title': f"{ev['nombre_equipo']}: {ev['titulo']}",
            'start': ev['fecha_programada'],
            'color': color,
            'textColor': texto_color,
            'url': url_for('lista_mantenimientos')
        })
    return jsonify(eventos)

@app.route('/mantenimientos/programar', methods=['GET', 'POST'])
@login_required
def programar_mantenimiento():
    if session['role'] == 'user': return redirect(url_for('dashboard'))
    if request.method == 'POST':
        get_db().execute("INSERT INTO mantenimientos (equipo_id, titulo, fecha_programada, estado) VALUES (?, ?, ?, 'Pendiente')",
                   (request.form['equipo_id'], request.form['titulo'], request.form['fecha_programada']))
        get_db().commit()
        return redirect(url_for('lista_mantenimientos'))
    equipos = get_db().execute("SELECT id, nombre_equipo FROM equipos").fetchall()
    return render_template('formulario_mantenimiento.html', equipos=equipos)

@app.route('/mantenimientos/completar/<int:mant_id>', methods=['POST'])
@login_required
def completar_mantenimiento(mant_id):
    if session['role'] == 'user': return redirect(url_for('dashboard'))
    get_db().execute("UPDATE mantenimientos SET estado = 'Realizado', tecnico_asignado_id = ? WHERE id = ?", 
               (session['user_id'], mant_id))
    get_db().commit()
    return redirect(url_for('lista_mantenimientos'))

@app.route('/mantenimientos/reprogramar/<int:mant_id>', methods=['POST'])
@login_required
def reprogramar_mantenimiento(mant_id):
    if session['role'] == 'user': return redirect(url_for('dashboard'))
    get_db().execute("UPDATE mantenimientos SET fecha_programada = ?, motivo_reprogramacion = ? WHERE id = ?", 
               (request.form['nueva_fecha'], request.form['motivo'], mant_id))
    get_db().commit()
    flash('Reprogramado.', 'success')
    return redirect(url_for('lista_mantenimientos'))

# --- Admin Usuarios ---
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