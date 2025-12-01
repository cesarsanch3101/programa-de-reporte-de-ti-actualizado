from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import sqlite3
import os
import math
from datetime import datetime
import pandas as pd
import io
from flask_weasyprint import HTML, render_pdf
from flask_mail import Mail, Message
from collections import defaultdict

# --- Importaciones Locales ---
from config import config_dict, CATEGORIAS, PRIORIDADES, ESTADOS, PER_PAGE
from database_setup import crear_tablas

# --- Configuración ---
config = config_dict['development']

app = Flask(__name__)
app.config.from_object(config)
app.secret_key = 'clave-secreta-cambiar-en-produccion' # O usa config.SECRET_KEY

# Inicializar Mail
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

# --- FUNCION DE CORREO UNIFICADA (LA QUE SI FUNCIONA) ---
def send_email(to, subject, template, **kwargs):
    if not to: return

    db = get_db()
    # Cargamos configuración de la DB
    config_rows = db.execute("SELECT clave, valor FROM configuracion WHERE clave LIKE 'MAIL_%'").fetchall()
    
    # Actualizamos la app con lo que haya en la DB
    if config_rows:
        config_dict_db = {row['clave']: row['valor'] for row in config_rows}
        # Limpieza básica de espacios
        for key, val in config_dict_db.items():
            if isinstance(val, str):
                config_dict_db[key] = val.strip()
        
        app.config.update(config_dict_db)
        
        # Ajuste de tipos
        if 'MAIL_PORT' in app.config:
            app.config['MAIL_PORT'] = int(app.config['MAIL_PORT'])
        if 'MAIL_USE_TLS' in app.config:
            app.config['MAIL_USE_TLS'] = str(app.config['MAIL_USE_TLS']).lower() == 'true'
            
        # IMPORTANTE: Re-inicializar mail con la nueva config
        mail_instance = Mail(app)
    else:
        mail_instance = mail # Usar config por defecto (.env)

    try:
        msg = Message(subject, sender=app.config.get('MAIL_USERNAME'), recipients=[to])
        # Renderizamos el template aquí mismo
        msg.html = render_template(template, **kwargs)
        mail_instance.send(msg)
        print(f"✅ Correo enviado a {to} | Asunto: {subject}")
    except Exception as e:
        print(f"⚠️ Error enviando correo: {e}")

# --- Decoradores ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: 
            flash('Por favor, inicia sesión.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin': 
            flash('Acceso denegado.', 'danger')
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
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            db.execute("INSERT INTO auditoria_logs (usuario_id, accion) VALUES (?, 'LOGIN')", (user['id'],))
            db.commit()
            return redirect(url_for('dashboard'))
        flash('Usuario o contraseña incorrectos.', 'danger')
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

# --- TICKETS ---
@app.route('/soportes')
@login_required
def lista_soportes():
    db = get_db()
    
    # Filtros
    f_inicio = request.args.get('fecha_inicio')
    f_fin = request.args.get('fecha_fin')
    f_categoria = request.args.get('categoria')
    f_prioridad = request.args.get('prioridad')
    f_estado = request.args.get('estado')
    f_tecnico = request.args.get('tecnico_id')

    query = """
        SELECT s.*, u.username as nombre_usuario, t.username as nombre_tecnico 
        FROM soportes s 
        JOIN usuarios u ON s.usuario_id = u.id 
        LEFT JOIN usuarios t ON s.tecnico_id = t.id 
        WHERE 1=1
    """
    params = []
    
    if session['role'] == 'user':
        query += " AND s.usuario_id = ?"
        params.append(session['user_id'])
    
    if f_inicio and f_fin:
        query += " AND date(s.fecha_creacion) BETWEEN ? AND ?"
        params.extend([f_inicio, f_fin])
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
    
    query += """ ORDER BY CASE WHEN s.estado IN ('Abierto', 'En Proceso') THEN 0 ELSE 1 END ASC, s.fecha_creacion DESC """
    
    tickets = db.execute(query, params).fetchall()
    tecnicos = db.execute("SELECT id, username FROM usuarios WHERE role IN ('admin', 'tecnico')").fetchall()
    
    return render_template('lista_soportes.html', soportes=tickets, tecnicos=tecnicos, categorias=CATEGORIAS, prioridades=PRIORIDADES, estados=ESTADOS)

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
        
        # Usamos la función UNIFICADA send_email
        if usuario_reporta and usuario_reporta['email']:
            send_email(
                to=usuario_reporta['email'], 
                subject=f"Ticket #{ticket_id} Creado", 
                template='email_nuevo_ticket.html', 
                usuario=usuario_reporta['username'], 
                ticket_id=ticket_id, 
                problema=request.form['problema']
            )
            flash(f'✅ Ticket creado y notificación enviada.', 'success')
        else:
            flash('✅ Ticket creado.', 'warning')
        return redirect(url_for('lista_soportes'))
    
    if session['role'] in ['admin', 'tecnico']:
        usuarios = db.execute("SELECT id, username FROM usuarios ORDER BY username").fetchall()
    else:
        usuarios = [{"id": session['user_id'], "username": session['username']}]
    return render_template('agregar.html', categorias=CATEGORIAS, prioridades=PRIORIDADES, usuarios=usuarios)

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
            db.commit()
            flash('Ticket actualizado.', 'success')
        else:
            estado_nuevo = request.form.get('estado')
            solucion = request.form.get('solucion')
            tecnico_id = request.form.get('tecnico_id')
            
            if estado_nuevo in ['Resuelto', 'Cerrado'] and not solucion:
                flash('⚠️ Para cerrar el ticket, debes documentar la solución.', 'warning')
                tecnicos = db.execute("SELECT id, username FROM usuarios WHERE role IN ('admin', 'tecnico')").fetchall()
                return render_template('editar.html', ticket=ticket, tecnicos=tecnicos, estados=ESTADOS, categorias=CATEGORIAS, prioridades=PRIORIDADES)
            
            fecha_finalizacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if estado_nuevo in ['Resuelto', 'Cerrado'] else None
            
            db.execute("UPDATE soportes SET estado=?, tecnico_id=?, solucion=?, fecha_finalizacion=? WHERE id=?",
                       (estado_nuevo, tecnico_id if tecnico_id else None, solucion, fecha_finalizacion, ticket_id))
            db.commit()
            
            # Notificación de cierre
            if estado_nuevo in ['Resuelto', 'Cerrado'] and ticket['estado'] not in ['Resuelto', 'Cerrado']:
                usuario_dueno = db.execute("SELECT email, username FROM usuarios WHERE id = ?", (ticket['usuario_id'],)).fetchone()
                
                if usuario_dueno and usuario_dueno['email']:
                    send_email(
                        to=usuario_dueno['email'], 
                        subject=f"✅ Ticket #{ticket_id} Finalizado", 
                        template='email_cierre_ticket.html',
                        usuario=usuario_dueno['username'],
                        ticket_id=ticket_id,
                        problema=ticket['problema'],
                        solucion=solucion,
                        tecnico=session['username']
                    )
                    flash(f'Ticket cerrado y notificación enviada.', 'success')
                else:
                    flash('Ticket cerrado.', 'success')
            else:
                flash('Gestión actualizada.', 'success')

        return redirect(url_for('lista_soportes'))

    tecnicos = db.execute("SELECT id, username FROM usuarios WHERE role IN ('admin', 'tecnico')").fetchall()
    return render_template('editar.html', ticket=ticket, tecnicos=tecnicos, estados=ESTADOS, categorias=CATEGORIAS, prioridades=PRIORIDADES)

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
    equipos = get_db().execute("""
        SELECT e.*, u.username as usuario_asignado 
        FROM equipos e 
        LEFT JOIN usuarios u ON e.usuario_asignado_id = u.id 
        ORDER BY e.nombre_equipo
    """).fetchall()
    tipos = get_db().execute("SELECT DISTINCT tipo FROM equipos WHERE tipo IS NOT NULL").fetchall()
    return render_template('lista_equipos.html', equipos=equipos, tipos=tipos)

@app.route('/equipos/ver/<int:equipo_id>')
@login_required
def ver_equipo(equipo_id):
    db = get_db()
    equipo = db.execute("SELECT e.*, u.username as usuario_asignado, u.departamento FROM equipos e LEFT JOIN usuarios u ON e.usuario_asignado_id = u.id WHERE e.id = ?", (equipo_id,)).fetchone()
    if not equipo:
        flash('Equipo no encontrado.', 'danger')
        return redirect(url_for('lista_equipos'))
    historial = db.execute("SELECT * FROM mantenimientos WHERE equipo_id = ? ORDER BY fecha_programada DESC", (equipo_id,)).fetchall()
    return render_template('ver_equipo.html', equipo=equipo, historial=historial)

@app.route('/equipos/gestion', methods=['GET', 'POST'])
@app.route('/equipos/gestion/<int:equipo_id>', methods=['GET', 'POST'])
@admin_required
def gestion_equipo(equipo_id=None):
    db = get_db()
    equipo = db.execute("SELECT * FROM equipos WHERE id = ?", (equipo_id,)).fetchone() if equipo_id else None

    if request.method == 'POST':
        data = (
            request.form['nombre_equipo'], 
            request.form['tipo'], 
            request.form['marca_modelo'], 
            request.form['numero_serie'], 
            request.form['procesador'], 
            request.form['memoria_ram'], 
            request.form['tipo_ram'], 
            request.form['disco_duro'], 
            request.form['tipo_disco'], 
            request.form['fecha_compra'], 
            request.form['color'],        
            request.form.get('usuario_asignado_id') or None
        )
        
        try:
            if equipo_id:
                db.execute("""
                    UPDATE equipos SET 
                        nombre_equipo=?, tipo=?, marca_modelo=?, numero_serie=?,
                        procesador=?, memoria_ram=?, tipo_ram=?, disco_duro=?, tipo_disco=?, fecha_compra=?,
                        color=?, usuario_asignado_id=? 
                    WHERE id=?
                """, data + (equipo_id,))
                flash('Equipo actualizado correctamente.', 'success')
            else:
                db.execute("""
                    INSERT INTO equipos (
                        nombre_equipo, tipo, marca_modelo, numero_serie,
                        procesador, memoria_ram, tipo_ram, disco_duro, tipo_disco, fecha_compra,
                        color, usuario_asignado_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
                flash('Equipo registrado correctamente.', 'success')
            
            db.commit()
            return redirect(url_for('lista_equipos'))
            
        except sqlite3.IntegrityError:
            flash('Error: El nombre del equipo o serie ya existe.', 'danger')

    usuarios = db.execute("SELECT id, username FROM usuarios").fetchall()
    return render_template('formulario_equipo.html', equipo=equipo, usuarios=usuarios)

@app.route('/equipos/eliminar/<int:equipo_id>', methods=['POST'])
@admin_required
def eliminar_equipo(equipo_id):
    get_db().execute("DELETE FROM equipos WHERE id = ?", (equipo_id,))
    get_db().commit()
    return redirect(url_for('lista_equipos'))

# --- MANTENIMIENTOS (USANDO SEND_EMAIL UNIFICADO) ---
@app.route('/mantenimientos')
@login_required
def lista_mantenimientos():
    db = get_db()
    f_inicio = request.args.get('fecha_inicio')
    f_fin = request.args.get('fecha_fin')
    f_estado = request.args.get('estado')
    f_equipo = request.args.get('equipo_id')

    query = """
        SELECT m.*, e.nombre_equipo, u.username as tecnico 
        FROM mantenimientos m 
        JOIN equipos e ON m.equipo_id = e.id
        LEFT JOIN usuarios u ON m.tecnico_asignado_id = u.id 
        WHERE 1=1
    """
    params = []
    if f_inicio and f_fin:
        query += " AND m.fecha_programada BETWEEN ? AND ?"
        params.extend([f_inicio, f_fin])
    if f_estado and f_estado != 'Todos':
        query += " AND m.estado = ?"
        params.append(f_estado)
    if f_equipo and f_equipo != 'Todos':
        query += " AND m.equipo_id = ?"
        params.append(f_equipo)
    query += " ORDER BY m.fecha_programada ASC"

    mantenimientos = db.execute(query, params).fetchall()
    equipos = db.execute("SELECT id, nombre_equipo FROM equipos ORDER BY nombre_equipo").fetchall()
    return render_template('mantenimientos.html', mantenimientos=mantenimientos, equipos=equipos)

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

@app.route('/mantenimientos/programar', methods=['GET', 'POST'])
@login_required
def programar_mantenimiento():
    if session['role'] == 'user': return redirect(url_for('dashboard'))
    
    db = get_db()
    if request.method == 'POST':
        equipo_id = request.form['equipo_id']
        titulo = request.form['titulo']
        fecha = request.form['fecha_programada']
        
        db.execute("INSERT INTO mantenimientos (equipo_id, titulo, fecha_programada, estado) VALUES (?, ?, ?, 'Pendiente')",
                   (equipo_id, titulo, fecha))
        db.commit()
        
        # Notificar usando send_email
        datos = db.execute("SELECT u.email, u.username, e.nombre_equipo FROM equipos e JOIN usuarios u ON e.usuario_asignado_id = u.id WHERE e.id = ?", (equipo_id,)).fetchone()
        
        if datos and datos['email']:
            send_email(
                to=datos['email'],
                subject="🔧 Mantenimiento Programado",
                template='email_mantenimiento_nuevo.html', 
                usuario=datos['username'], 
                equipo=datos['nombre_equipo'], 
                tarea=titulo, 
                fecha=fecha
            )
            flash('Mantenimiento programado y notificación enviada.', 'success')
        else:
            flash('Mantenimiento programado.', 'success')
            
        return redirect(url_for('lista_mantenimientos'))
    
    equipos = db.execute("SELECT id, nombre_equipo FROM equipos").fetchall()
    return render_template('formulario_mantenimiento.html', equipos=equipos)

@app.route('/mantenimientos/reprogramar/<int:mant_id>', methods=['POST'])
@login_required
def reprogramar_mantenimiento(mant_id):
    if session['role'] == 'user': return redirect(url_for('dashboard'))
    
    nueva_fecha = request.form['nueva_fecha']
    motivo = request.form['motivo']
    
    db = get_db()
    db.execute("UPDATE mantenimientos SET fecha_programada = ?, motivo_reprogramacion = ? WHERE id = ?", 
               (nueva_fecha, motivo, mant_id))
    db.commit()
    
    # Notificar usando send_email
    datos = db.execute("""
        SELECT u.email, u.username, e.nombre_equipo, m.titulo 
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        JOIN usuarios u ON e.usuario_asignado_id = u.id
        WHERE m.id = ?
    """, (mant_id,)).fetchone()
    
    if datos and datos['email']:
        send_email(
            to=datos['email'],
            subject="📅 Cambio en Mantenimiento",
            template='email_mantenimiento_cambio.html',
            usuario=datos['username'], 
            equipo=datos['nombre_equipo'], 
            tarea=datos['titulo'], 
            nueva_fecha=nueva_fecha,
            motivo=motivo
        )
        flash('Reprogramado y notificado.', 'success')
    else:
        flash('Reprogramado.', 'success')
        
    return redirect(url_for('lista_mantenimientos'))

@app.route('/api/mantenimientos/mover', methods=['POST'])
@admin_required
def mover_mantenimiento():
    data = request.get_json()
    mant_id = data.get('id')
    nueva_fecha = data.get('nueva_fecha')
    motivo = data.get('motivo')
    
    db = get_db()
    db.execute("UPDATE mantenimientos SET fecha_programada = ?, motivo_reprogramacion = ? WHERE id = ?", 
               (nueva_fecha, motivo, mant_id))
    db.commit()
    
    # Notificar usando send_email (sin flash porque es API)
    datos = db.execute("""
        SELECT u.email, u.username, e.nombre_equipo, m.titulo 
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        JOIN usuarios u ON e.usuario_asignado_id = u.id
        WHERE m.id = ?
    """, (mant_id,)).fetchone()
    
    if datos and datos['email']:
        send_email(
            to=datos['email'],
            subject="📅 Cambio en Mantenimiento",
            template='email_mantenimiento_cambio.html',
            usuario=datos['username'], 
            equipo=datos['nombre_equipo'], 
            tarea=datos['titulo'], 
            nueva_fecha=nueva_fecha,
            motivo=motivo
        )
    
    return jsonify({'status': 'success'})

@app.route('/mantenimientos/completar/<int:mant_id>', methods=['POST'])
@login_required
def completar_mantenimiento(mant_id):
    if session['role'] == 'user': return redirect(url_for('dashboard'))
    get_db().execute("UPDATE mantenimientos SET estado = 'Realizado', tecnico_asignado_id = ? WHERE id = ?", (session['user_id'], mant_id))
    get_db().commit()
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
            if valor: valor = valor.strip() # Limpieza obligatoria
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