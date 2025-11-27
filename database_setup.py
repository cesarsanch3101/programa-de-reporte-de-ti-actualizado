# database_setup.py (Versión Completa y Corregida)

import sqlite3
from config import DB_FILE

def crear_tablas():
    """
    Crea/actualiza las tablas del proyecto de forma segura.
    - Añade la columna 'email_cliente' a 'soportes' si no existe.
    - Crea las tablas 'equipos' y 'mantenimientos' para el cronograma.
    - Crea la tabla 'configuracion' para los ajustes.
    """
    conn = None  # Inicializamos la conexión como None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        print(f"Conectado a la base de datos: {DB_FILE}")
        print("Creando/Verificando tablas...")

        # --- Tabla Soportes (Añadimos la columna de email si no existe) ---
        try:
            cursor.execute("ALTER TABLE soportes ADD COLUMN email_cliente TEXT")
            print("Columna 'email_cliente' añadida a la tabla 'soportes'.")
        except sqlite3.OperationalError:
            pass # La columna ya existe, no hacemos nada.
        
        # Verificamos la tabla principal de soportes
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS soportes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_hora TEXT, usuario TEXT, departamento TEXT, 
            problema TEXT, estado TEXT, tecnico TEXT, solucion TEXT, prioridad TEXT, 
            categoria TEXT, fecha_inicio TEXT, fecha_finalizacion TEXT, comentarios_solucion TEXT,
            email_cliente TEXT 
        )""")
    
        # Tabla Usuarios
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin', 'user'))
        )""")
    
        # Tabla Configuración
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY, valor TEXT
        )""")
        
        # --- NUEVA TABLA para el inventario de equipos ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_asignado TEXT,
            nombre_equipo TEXT UNIQUE NOT NULL,
            tipo TEXT,
            marca_modelo TEXT,
            numero_serie TEXT,
            fecha_adquisicion TEXT,
            notas TEXT
        )""")

        # --- NUEVA TABLA para el cronograma de mantenimientos ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mantenimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER,
            titulo TEXT NOT NULL,
            fecha_programada TEXT NOT NULL,
            estado TEXT NOT NULL,
            fecha_ejecucion TEXT,
            tecnico_asignado TEXT,
            observaciones TEXT,
            FOREIGN KEY (equipo_id) REFERENCES equipos (id)
        )""")

        conn.commit()
        print("✅ Tablas listas y verificadas.")

    # --- BLOQUE 'EXCEPT' AÑADIDO ---
    # Esto captura cualquier error que ocurra durante la conexión o ejecución de SQL
    except sqlite3.Error as e:
        print(f"❌ Ocurrió un error en la base de datos: {e}")

    # --- BLOQUE 'FINALLY' AÑADIDO ---
    # Esto asegura que la conexión a la base de datos siempre se cierre,
    # incluso si ocurre un error.
    finally:
        if conn:
            conn.close()
            print("Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    crear_tablas()