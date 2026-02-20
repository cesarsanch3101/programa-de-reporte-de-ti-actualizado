from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import sqlite3
import uuid
import os
import math
from datetime import datetime
import pandas as pd
import io
from flask_weasyprint import HTML, render_pdf
from flask_mail import Mail, Message
from flask_socketio import SocketIO, emit
from collections import defaultdict

# --- Importaciones Locales ---
from config import config_dict, CATEGORIAS, PRIORIDADES, ESTADOS, PER_PAGE
from database_setup import crear_tablas

from domain.models import User, Ticket, Equipment, TicketStatus, TicketPriority, UserRole, TicketReadModel
from infrastructure.persistence.repository import SQLiteRepository
from application.services.ticket_service import TicketService
from uuid import UUID

repo = SQLiteRepository('soportes_v2.db')
ticket_service = TicketService(repo)

# --- Configuración ---
config = config_dict['development']

app = Flask(__name__)
app.config.from_object(config)
app.secret_key = 'clave-secreta-cambiar-en-produccion' # O usa config.SECRET_KEY

# Inicializar Mail y SocketIO
mail = Mail(app)
socketio = SocketIO(app, cors_allowed_origins="*")

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
        # Soportar múltiples correos (coma o punto y coma)
        raw_recipients = to.replace(';', ',').split(',')
        recipients = [email.strip() for email in raw_recipients if email.strip()]
        
        if not recipients:
            print("⚠️ No hay destinatarios válidos.")
            return

        print(f"📧 Intentando enviar correo a: {recipients}")
        
        # Enviamos individualmente para mayor robustez y mejor debugging
        for recipient in recipients:
            msg = Message(subject, sender=app.config.get('MAIL_USERNAME'), recipients=[recipient])
            msg.html = render_template(template, **kwargs)
            mail_instance.send(msg)
            print(f"✅ Correo enviado a {recipient} | Asunto: {subject}")
            
    except Exception as e:
        print(f"⚠️ Error crítico en send_email: {e}")
        import traceback
        traceback.print_exc()

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
    
    # Base query for stats
    base_where = ""
    params = []
    
    if session.get('role') == 'user':
        base_where = " AND usuario_id = ?"
        params.append(session['user_id'])
    
    kpis = {
        "total_abiertos": db.execute(f"SELECT COUNT(*) FROM soportes WHERE estado = 'Abierto'{base_where}", params).fetchone()[0],
        "total_en_proceso": db.execute(f"SELECT COUNT(*) FROM soportes WHERE estado = 'En Proceso'{base_where}", params).fetchone()[0],
        "mis_tickets": db.execute("SELECT COUNT(*) FROM soportes WHERE usuario_id = ? AND estado IN ('Abierto', 'En Proceso')", (session['user_id'],)).fetchone()[0],
        "mantenimientos_pendientes": db.execute("SELECT COUNT(*) FROM mantenimientos WHERE estado = 'Pendiente'").fetchone()[0]
    }
    
    estados_raw = db.execute(f"SELECT estado, COUNT(*) as cantidad FROM soportes WHERE 1=1{base_where} GROUP BY estado", params).fetchall()
    grafico_estado = {"labels": [r['estado'] for r in estados_raw], "datos": [r['cantidad'] for r in estados_raw]}
    
    cats_raw = db.execute(f"SELECT categoria, COUNT(*) as cantidad FROM soportes WHERE 1=1{base_where} GROUP BY categoria ORDER BY cantidad DESC", params).fetchall()
    grafico_cat = {"labels": [r['categoria'] for r in cats_raw], "datos": [r['cantidad'] for r in cats_raw]}
    
    return render_template('dashboard.html', kpis=kpis, g_estado=grafico_estado, g_cat=grafico_cat)

# --- TICKETS ---
@app.route('/soportes')
@login_required
def lista_soportes():
    db = get_db()
    
    # Filtros de búsqueda
    f_estado = request.args.get('estado')
    
    # Construir filtros para el repositorio
    filters = {}
    if f_estado and f_estado != 'Todos':
        filters['estado'] = f_estado
    
    # RESTRICCIÓN DE VISIBILIDAD: Solo los usuarios estándar ven solo sus propios tickets
    # Administradores y Técnicos ven todo.
    if session.get('role') == 'user':
        filters['usuario_id'] = session['user_id']
    
    # Obtener tickets usando el servicio con los filtros aplicados
    tickets = ticket_service.repository.list_tickets(filters=filters)
    
    # Calcular estadísticas para el banner (también respetando la visibilidad)
    stats_filters = {}
    if session.get('role') == 'user':
        stats_filters['usuario_id'] = session['user_id']
        
    stats = {
        'total': len(ticket_service.repository.list_tickets(stats_filters)),
        'abiertos': len(ticket_service.repository.list_tickets({**stats_filters, 'estado': 'Abierto'})),
        'en_proceso': len(ticket_service.repository.list_tickets({**stats_filters, 'estado': 'En Proceso'})),
        'resueltos': len(ticket_service.repository.list_tickets({**stats_filters, 'estado': 'Resuelto'}))
    }
    
    tecnicos = db.execute("SELECT id, username FROM usuarios WHERE role IN ('admin', 'tecnico')").fetchall()
    
    return render_template('lista_soportes.html', soportes=tickets, tecnicos=tecnicos, stats=stats, categorias=CATEGORIAS, prioridades=PRIORIDADES, estados=ESTADOS)

@app.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar():
    db = get_db()
    if request.method == 'POST':
        usuario_reporta_id = UUID(request.form.get('usuario_id'))
        
        nuevo_ticket = Ticket(
            usuario_id=usuario_reporta_id,
            problema=request.form['problema'],
            categoria=request.form.get('categoria', 'Otro'),
            prioridad=TicketPriority(request.form.get('prioridad', 'Media'))
        )
        
        ticket = repo.create_ticket(nuevo_ticket)
        
        db = get_db()
        usuario_reporta = db.execute("SELECT email, username FROM usuarios WHERE id = ?", (str(usuario_reporta_id),)).fetchone()
        
        if usuario_reporta and usuario_reporta['email']:
            send_email(
                to=usuario_reporta['email'], 
                subject=f"Ticket #{ticket.numero_ticket} Creado", 
                template='email_nuevo_ticket.html', 
                usuario=usuario_reporta['username'], 
                ticket_id=ticket.numero_ticket, # Using sequential ID 
                problema=ticket.problema
            )
            flash(f'✅ Ticket creado y notificación enviada.', 'success')
        else:
            flash(f'✅ Ticket #{ticket.numero_ticket} creado.', 'success')
            
        # Emitir evento en tiempo real (para todos los casos)
        socketio.emit('new_ticket', {
            'id': str(ticket.id),
            'numero': ticket.numero_ticket,
            'titulo': ticket.problema[:50] + '...',
            'prioridad': ticket.prioridad.value
        })
        
        return redirect(url_for('lista_soportes'))
    
    if session['role'] in ['admin', 'tecnico']:
        usuarios = db.execute("SELECT id, username FROM usuarios ORDER BY username").fetchall()
    else:
        usuarios = [{"id": session['user_id'], "username": session['username']}]
    return render_template('agregar.html', categorias=CATEGORIAS, prioridades=PRIORIDADES, usuarios=usuarios)

@app.route('/editar/<ticket_id>', methods=['GET', 'POST'])
@login_required
def editar(ticket_id):
    ticket = repo.get_ticket_by_id(UUID(ticket_id))
    if not ticket or (session['role'] == 'user' and ticket.usuario_id != session['user_id']):
        return redirect(url_for('lista_soportes'))

    db = get_db()
    if request.method == 'POST':
        if session['role'] == 'user':
            if ticket.estado != TicketStatus.ABIERTO:
                return redirect(url_for('editar', ticket_id=ticket_id))
            
            ticket.problema = request.form['problema']
            ticket.categoria = request.form['categoria']
            ticket.prioridad = TicketPriority(request.form['prioridad'])
            
            repo.update_ticket(ticket)
            flash('Ticket actualizado.', 'success')
        else:
            estado_nuevo_str = request.form.get('estado')
            solucion = request.form.get('solucion')
            tecnico_id_str = request.form.get('tecnico_id')
            
            if estado_nuevo_str in ['Resuelto', 'Cerrado'] and not solucion:
                flash('⚠️ Para cerrar el ticket, debes documentar la solución.', 'warning')
                tecnicos = db.execute("SELECT id, username FROM usuarios WHERE role IN ('admin', 'tecnico')").fetchall()
                return render_template('editar.html', ticket=ticket, tecnicos=tecnicos, estados=ESTADOS, categorias=CATEGORIAS, prioridades=PRIORIDADES)
            
            ticket.estado = TicketStatus(estado_nuevo_str)
            ticket.solucion = solucion
            ticket.tecnico_id = UUID(tecnico_id_str) if tecnico_id_str else None
            ticket.fecha_finalizacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if ticket.estado in [TicketStatus.RESUELTO, TicketStatus.CERRADO] else None
            
            repo.update_ticket(ticket)
            
            # Notificación de cierre (comparando con el estado anterior si es posible o simplemente si el nuevo es final)
            if ticket.estado in [TicketStatus.RESUELTO, TicketStatus.CERRADO]:
                usuario_dueno = db.execute("SELECT email, username FROM usuarios WHERE id = ?", (str(ticket.usuario_id),)).fetchone()
                
                if usuario_dueno and usuario_dueno['email']:
                    send_email(
                        to=usuario_dueno['email'], 
                        subject=f"✅ Ticket #{ticket.numero_ticket} Finalizado", 
                        template='email_cierre_ticket.html',
                        usuario=usuario_dueno['username'],
                        ticket_id=ticket.numero_ticket, # Usamos el número secuencial
                        problema=ticket.problema,
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

@app.route('/soportes/eliminar/<ticket_id>', methods=['POST'])
@admin_required
def eliminar_soporte(ticket_id):
    repo.delete_ticket(UUID(ticket_id))
    flash('Ticket eliminado.', 'warning')
    return redirect(url_for('lista_soportes'))

# --- EQUIPOS ---
@app.route('/equipos')
@login_required
def lista_equipos():
    db = get_db() # Still need DB for users list and types
    equipos = repo.list_equipos()
    
    # Adding username manually for now or via a ReadModel if preferred
    # Since we want to display the assigned user name:
    equipos_with_users = []
    for e in equipos:
        user_name = None
        if e.usuario_asignado_id:
            u = db.execute("SELECT username FROM usuarios WHERE id = ?", (str(e.usuario_asignado_id),)).fetchone()
            user_name = u['username'] if u else None
        
        # We can add a temporary attribute or use a ReadModel
        setattr(e, 'usuario_asignado', user_name)
        equipos_with_users.append(e)

    tipos = db.execute("SELECT DISTINCT tipo FROM equipos WHERE tipo IS NOT NULL").fetchall()
    return render_template('lista_equipos.html', equipos=equipos_with_users, tipos=tipos)

@app.route('/equipos/ver/<equipo_id>')
@login_required
def ver_equipo(equipo_id):
    equipo = repo.get_equipment_by_id(UUID(equipo_id))
    if not equipo:
        flash('Equipo no encontrado.', 'danger')
        return redirect(url_for('lista_equipos'))
    
    db = get_db()
    # Add assigned user name for the view
    if equipo.usuario_asignado_id:
        u = db.execute("SELECT username, departamento FROM usuarios WHERE id = ?", (str(equipo.usuario_asignado_id),)).fetchone()
        setattr(equipo, 'usuario_asignado', u['username'] if u else None)
        setattr(equipo, 'departamento', u['departamento'] if u else None)

    historial = db.execute("SELECT * FROM mantenimientos WHERE equipo_id = ? ORDER BY fecha_programada DESC", (str(equipo_id),)).fetchall()
    return render_template('ver_equipo.html', equipo=equipo, historial=historial)

@app.route('/equipos/gestion', methods=['GET', 'POST'])
@app.route('/equipos/gestion/<equipo_id>', methods=['GET', 'POST'])
@admin_required
def gestion_equipo(equipo_id=None):
    equipo = repo.get_equipment_by_id(UUID(equipo_id)) if equipo_id else None
    db = get_db()

    if request.method == 'POST':
        try:
            if equipo:
                equipo.nombre_equipo = request.form['nombre_equipo']
                equipo.tipo = request.form['tipo']
                equipo.marca_modelo = request.form['marca_modelo']
                equipo.numero_serie = request.form['numero_serie']
                equipo.procesador = request.form['procesador']
                equipo.memoria_ram = request.form['memoria_ram']
                equipo.tipo_ram = request.form['tipo_ram']
                equipo.disco_duro = request.form['disco_duro']
                equipo.tipo_disco = request.form['tipo_disco']
                equipo.fecha_compra = request.form['fecha_compra']
                equipo.color = request.form['color']
                equipo.usuario_asignado_id = UUID(request.form.get('usuario_asignado_id')) if request.form.get('usuario_asignado_id') else None
                
                repo.update_equipment(equipo)
                flash('Equipo actualizado correctamente.', 'success')
            else:
                nuevo_equipo = Equipment(
                    nombre_equipo=request.form['nombre_equipo'],
                    tipo=request.form['tipo'],
                    marca_modelo=request.form['marca_modelo'],
                    numero_serie=request.form['numero_serie'],
                    procesador=request.form['procesador'],
                    memoria_ram=request.form['memoria_ram'],
                    tipo_ram=request.form['tipo_ram'],
                    disco_duro=request.form['disco_duro'],
                    tipo_disco=request.form['tipo_disco'],
                    fecha_compra=request.form['fecha_compra'],
                    color=request.form['color'],
                    usuario_asignado_id=UUID(request.form.get('usuario_asignado_id')) if request.form.get('usuario_asignado_id') else None
                )
                repo.create_equipment(nuevo_equipo)
                flash('Equipo registrado correctamente.', 'success')
            
            return redirect(url_for('lista_equipos'))
            
        except sqlite3.IntegrityError:
            flash('Error: El nombre del equipo o serie ya existe.', 'danger')

    usuarios = db.execute("SELECT id, username FROM usuarios").fetchall()
    return render_template('formulario_equipo.html', equipo=equipo, usuarios=usuarios)

@app.route('/equipos/eliminar/<equipo_id>', methods=['POST'])
@admin_required
def eliminar_equipo(equipo_id):
    get_db().execute("DELETE FROM equipos WHERE id = ?", (str(equipo_id),))
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
        # Redirect to maintenance list, but we could eventually point to a detail view
        eventos.append({
            'id': str(ev['id']), 
            'title': f"{ev['nombre_equipo']}: {ev['titulo']}", 
            'start': ev['fecha_programada'], 
            'color': color, 
            'textColor': text_color, 
            'url': url_for('lista_mantenimientos') + f"?id={ev['id']}"
        })
    return jsonify(eventos)

@app.route('/mantenimientos/programar', methods=['GET', 'POST'])
@login_required
def programar_mantenimiento():
    if session['role'] == 'user': return redirect(url_for('dashboard'))
    
    db = get_db()
    # Pre-fill date from calendar if provided
    fecha_predefinida = request.args.get('fecha')
    
    if request.method == 'POST':
        equipo_id = request.form['equipo_id']
        titulo = request.form['titulo']
        fecha = request.form['fecha_programada']
        
        db.execute("INSERT INTO mantenimientos (id, equipo_id, titulo, fecha_programada, estado) VALUES (?, ?, ?, ?, 'Pendiente')",
                   (str(uuid.uuid4()), str(equipo_id), titulo, fecha))
        db.commit()
        
        # Notificar usando send_email
        datos = db.execute("SELECT u.email, u.username, e.nombre_equipo FROM equipos e JOIN usuarios u ON e.usuario_asignado_id = u.id WHERE e.id = ?", (str(equipo_id),)).fetchone()
        
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
    return render_template('formulario_mantenimiento.html', equipos=equipos, fecha_preliminar=fecha_predefinida)

@app.route('/mantenimientos/reprogramar/<mant_id>', methods=['POST'])
@login_required
def reprogramar_mantenimiento(mant_id):
    if session['role'] == 'user': return redirect(url_for('dashboard'))
    
    nueva_fecha = request.form['nueva_fecha']
    motivo = request.form['motivo']
    
    db = get_db()
    db.execute("UPDATE mantenimientos SET fecha_programada = ?, motivo_reprogramacion = ? WHERE id = ?", 
               (nueva_fecha, motivo, str(mant_id)))
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
    """, (str(mant_id),)).fetchone()
    
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

@app.route('/mantenimientos/completar/<mant_id>', methods=['POST'])
@login_required
def completar_mantenimiento(mant_id):
    if session['role'] == 'user': return redirect(url_for('dashboard'))
    
    comentarios = request.form.get('comentarios', '')
    
    db = get_db()
    db.execute("UPDATE mantenimientos SET estado = 'Realizado', tecnico_asignado_id = ?, comentarios = ? WHERE id = ?", 
               (session['user_id'], comentarios, str(mant_id)))
    db.commit()
    
    # Notificar al dueño del equipo
    datos = db.execute("""
        SELECT u.email, u.username, e.nombre_equipo, m.titulo, t.username as tecnico
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        JOIN usuarios u ON e.usuario_asignado_id = u.id
        JOIN usuarios t ON t.id = ?
        WHERE m.id = ?
    """, (session['user_id'], str(mant_id))).fetchone()
    
    if datos and datos['email']:
        send_email(
            to=datos['email'],
            subject="✅ Mantenimiento Finalizado",
            template='email_mantenimiento_completado.html',
            usuario=datos['username'], 
            equipo=datos['nombre_equipo'], 
            tarea=datos['titulo'], 
            tecnico=datos['tecnico'],
            comentarios=comentarios
        )
        flash('Tarea completada y usuario notificado.', 'success')
    else:
        flash('Tarea completada.', 'success')
        
    return redirect(url_for('lista_mantenimientos'))

@app.route('/mantenimientos/eliminar/<mant_id>', methods=['POST'])
@admin_required
def eliminar_mantenimiento(mant_id):
    get_db().execute("DELETE FROM mantenimientos WHERE id = ?", (str(mant_id),))
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
    return render_template('admin_usuarios.html', usuarios=repo.list_users())

@app.route('/admin/usuarios/crear', methods=['GET', 'POST'])
@admin_required
def admin_crear_usuario():
    if request.method == 'POST':
        try:
            nuevo_usuario = User(
                username=request.form['username'],
                email=request.form.get('email'),
                password_hash=generate_password_hash(request.form['password']),
                role=UserRole(request.form.get('role', 'user')),
                departamento=request.form.get('departamento')
            )
            repo.create_user(nuevo_usuario)
            flash('Usuario creado correctamente.', 'success')
            return redirect(url_for('admin_usuarios'))
        except Exception as e:
            flash(f'Error al crear: {str(e)}', 'danger')
    return render_template('admin_form_usuario.html')

@app.route('/admin/usuarios/editar/<user_id>', methods=['GET', 'POST'])
@admin_required
def admin_editar_usuario(user_id):
    usuario = repo.get_user_by_id(UUID(user_id))
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('admin_usuarios'))

    if request.method == 'POST':
        try:
            usuario.email = request.form.get('email')
            usuario.role = UserRole(request.form.get('role', 'user'))
            usuario.departamento = request.form.get('departamento')
            
            if request.form.get('password'):
                usuario.password_hash = generate_password_hash(request.form['password'])
            
            repo.update_user(usuario)
            flash('Usuario actualizado correctamente.', 'success')
            return redirect(url_for('admin_usuarios'))
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'danger')
            
    return render_template('admin_editar_usuario.html', usuario=usuario)

@app.route('/admin/usuarios/eliminar/<user_id>', methods=['POST'])
@admin_required
def admin_eliminar_usuario(user_id):
    try:
        if str(user_id) != str(session['user_id']):
            repo.delete_user(UUID(user_id))
            flash('Usuario eliminado.', 'warning')
        else:
            flash('No puedes eliminarte a ti mismo.', 'danger')
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'danger')
    return redirect(url_for('admin_usuarios'))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)