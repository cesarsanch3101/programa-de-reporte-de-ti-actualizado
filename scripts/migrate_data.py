import sqlite3
import uuid
import os
import sys

# Add the project root to the path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.persistence.db_schema import SCHEMA_SQL

OLD_DB = 'soportes.db'
NEW_DB = 'soportes_v2.db'

def migrate():
    print(f"--- 🚀 Starting Migration: {OLD_DB} -> {NEW_DB} ---")
    
    if os.path.exists(NEW_DB):
        os.remove(NEW_DB)
        print(f"🧹 Removed existing {NEW_DB} for a clean start.")
    
    # Connect to databases
    old_conn = sqlite3.connect(OLD_DB)
    old_conn.row_factory = sqlite3.Row
    new_conn = sqlite3.connect(NEW_DB)
    
    # Init new schema
    new_conn.executescript(SCHEMA_SQL)
    new_conn.commit()

    # Mapping dictionary: table_name -> {old_id: new_uuid}
    id_map = {
        'usuarios': {},
        'equipos': {},
        'soportes': {},
        'mantenimientos': {}
    }

    def save_map(table, old_id, new_uuid):
        id_map[table][old_id] = new_uuid
        new_conn.execute("INSERT INTO legacy_migration_map (old_id, new_uuid, table_name) VALUES (?, ?, ?)", 
                         (old_id, new_uuid, table))

    # 1. Migrate Users
    print("Migrating users...")
    users = old_conn.execute("SELECT * FROM usuarios").fetchall()
    for u in users:
        new_id = str(uuid.uuid4())
        save_map('usuarios', u['id'], new_id)
        new_conn.execute("""
            INSERT INTO usuarios (id, username, email, password_hash, role, departamento, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (new_id, u['username'], u['email'], u['password_hash'], u['role'], u['departamento'], u['fecha_creacion']))

    # 2. Migrate Equipos
    print("Migrating equipment...")
    equipos = old_conn.execute("SELECT * FROM equipos").fetchall()
    for e in equipos:
        new_id = str(uuid.uuid4())
        save_map('equipos', e['id'], new_id)
        
        # Standardizing on fecha_compra
        e_dict = dict(e)
        fecha_val = e_dict.get('fecha_compra') or e_dict.get('fecha_adquisicion')
        
        new_conn.execute("""
            INSERT INTO equipos (id, nombre_equipo, tipo, marca_modelo, numero_serie, fecha_compra, 
                               procesador, memoria_ram, tipo_ram, disco_duro, tipo_disco, color, notas, usuario_asignado_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_id, e['nombre_equipo'], e['tipo'], e['marca_modelo'], e['numero_serie'], fecha_val,
              e_dict.get('procesador'), e_dict.get('memoria_ram'), e_dict.get('tipo_ram'), 
              e_dict.get('disco_duro'), e_dict.get('tipo_disco'), e_dict.get('color'), e_dict.get('notas'),
              id_map['usuarios'].get(e['usuario_asignado_id'])))

    # 3. Migrate Soportes
    print("Migrating tickets (ordered by date)...")
    soportes = old_conn.execute("SELECT * FROM soportes ORDER BY fecha_creacion ASC, id ASC").fetchall()
    for idx, s in enumerate(soportes, 1):
        new_id = str(uuid.uuid4())
        save_map('soportes', s['id'], new_id)
        new_conn.execute("""
            INSERT INTO soportes (id, numero_ticket, usuario_id, tecnico_id, equipo_id, problema, estado, prioridad, categoria, solucion, fecha_creacion, fecha_finalizacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_id, idx,
              id_map['usuarios'].get(s['usuario_id']), 
              id_map['usuarios'].get(s['tecnico_id']), 
              id_map['equipos'].get(s['equipo_id']),
              s['problema'], s['estado'], s['prioridad'], s['categoria'], s['solucion'], s['fecha_creacion'], s['fecha_finalizacion']))

    # 4. Migrate Mantenimientos
    print("Migrating maintenance...")
    mantenimientos = old_conn.execute("SELECT * FROM mantenimientos").fetchall()
    for m in mantenimientos:
        new_id = str(uuid.uuid4())
        save_map('mantenimientos', m['id'], new_id)
        new_conn.execute("""
            INSERT INTO mantenimientos (id, equipo_id, titulo, fecha_programada, estado, tecnico_asignado_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (new_id, id_map['equipos'].get(m['equipo_id']), m['titulo'], m['fecha_programada'], m['estado'], id_map['usuarios'].get(m['tecnico_asignado_id'])))

    # 5. Migrate Auditoria Logs
    print("Migrating logs...")
    logs = old_conn.execute("SELECT * FROM auditoria_logs").fetchall()
    for l in logs:
        new_conn.execute("""
            INSERT INTO auditoria_logs (usuario_id, accion, detalles, fecha)
            VALUES (?, ?, ?, ?)
        """, (id_map['usuarios'].get(l['usuario_id']), l['accion'], l['detalles'], l['fecha']))

    new_conn.commit()
    old_conn.close()
    new_conn.close()
    print("--- ✅ Migration Completed Successfully! ---")
    print(f"New database created: {NEW_DB}")

if __name__ == "__main__":
    migrate()
