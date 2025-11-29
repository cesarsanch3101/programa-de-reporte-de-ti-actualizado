import pandas as pd
import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime
from config import config_dict

# --- CONFIGURACIÓN ---
ARCHIVO_EXCEL = 'plantilla_soportes_historicos.xlsx'
config = config_dict['development']
DB_FILE = config.DB_FILE
PASSWORD_POR_DEFECTO = '123456'  # Contraseña para usuarios nuevos creados automáticamente

def conectar_db():
    return sqlite3.connect(DB_FILE)

def obtener_o_crear_usuario(cursor, username, role='user'):
    """
    Busca si el usuario existe. Si no, lo crea automáticamente.
    Retorna el ID del usuario.
    """
    if not username or pd.isna(username):
        return None

    username = str(username).strip()
    
    # 1. Buscar si ya existe
    cursor.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
    resultado = cursor.fetchone()
    
    if resultado:
        return resultado[0] # Retorna el ID existente
    
    # 2. Si no existe, crearlo
    print(f"   ↳ 👤 Usuario '{username}' no existía. Creándolo como {role}...")
    password_hash = generate_password_hash(PASSWORD_POR_DEFECTO)
    try:
        cursor.execute("INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)", 
                       (username, password_hash, role))
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # Por seguridad, si falla por concurrencia, volvemos a buscar
        cursor.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
        return cursor.fetchone()[0]

def migrar_datos():
    print(f"--- 🚀 INICIANDO MIGRACIÓN DESDE {ARCHIVO_EXCEL} ---")
    
    try:
        # Leer Excel (asegurando que los vacíos sean None)
        df = pd.read_excel(ARCHIVO_EXCEL)
        df = df.where(pd.notnull(df), None)
    except FileNotFoundError:
        print(f"❌ ERROR: No encuentro el archivo '{ARCHIVO_EXCEL}'.")
        print("   Por favor crea el archivo y asegúrate de que esté en la misma carpeta.")
        return

    conn = conectar_db()
    cursor = conn.cursor()
    
    tickets_creados = 0
    usuarios_nuevos = 0 # Contador simple (aprox)

    print(f"📂 Se encontraron {len(df)} registros para procesar.")

    for index, row in df.iterrows():
        try:
            # 1. Resolver ID del Usuario (Reportador)
            usuario_id = obtener_o_crear_usuario(cursor, row['usuario_reporta'], 'user')
            
            # 2. Resolver ID del Técnico (Opcional)
            tecnico_id = obtener_o_crear_usuario(cursor, row['tecnico_asignado'], 'tecnico')

            # 3. Preparar datos del Ticket
            fecha_creacion = row['fecha'] if row['fecha'] else datetime.now().strftime('%Y-%m-%d')
            # Si es fecha de Excel (timestamp), convertir a string
            if isinstance(fecha_creacion, datetime):
                fecha_creacion = fecha_creacion.strftime('%Y-%m-%d %H:%M:%S')

            problema = row['problema'] or "Sin descripción importada"
            categoria = row['categoria'] or "Otro"
            prioridad = row['prioridad'] or "Media"
            estado = row['estado'] or "Cerrado"
            solucion = row['solucion']
            fecha_finalizacion = row['fecha_cierre']

            # 4. Insertar Ticket
            cursor.execute("""
                INSERT INTO soportes (
                    usuario_id, tecnico_id, problema, categoria, prioridad, estado, 
                    solucion, fecha_creacion, fecha_finalizacion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (usuario_id, tecnico_id, problema, categoria, prioridad, estado, solucion, fecha_creacion, fecha_finalizacion))
            
            tickets_creados += 1
            if tickets_creados % 10 == 0:
                print(f"   ... Procesados {tickets_creados} tickets.")

        except Exception as e:
            print(f"❌ Error en fila {index + 2}: {e}")
            continue

    conn.commit()
    conn.close()
    
    print("\n" + "="*40)
    print(f"✅ MIGRACIÓN COMPLETADA")
    print(f"📊 Total Tickets Importados: {tickets_creados}")
    print(f"🔑 Nota: Los usuarios nuevos tienen la contraseña: '{PASSWORD_POR_DEFECTO}'")
    print("="*40)

if __name__ == '__main__':
    migrar_datos()