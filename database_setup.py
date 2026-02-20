import sqlite3
import os
from werkzeug.security import generate_password_hash
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DB_FILE)
    conn.row_factory = sqlite3.Row
    # Activar Foreign Keys (SQLite lo tiene desactivado por defecto)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def crear_tablas():
    print(f"--- 🛠️ Iniciando configuración de Base de Datos: {Config.DB_FILE} ---")
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Tabla de USUARIOS (Añadimos email y departamento para normalizar)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('admin', 'user', 'tecnico')),
            departamento TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 2. Tabla de EQUIPOS (Inventario)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_equipo TEXT UNIQUE NOT NULL,
            tipo TEXT,
            marca_modelo TEXT,
            numero_serie TEXT UNIQUE,
            fecha_adquisicion DATE,
            usuario_asignado_id INTEGER,
            notas TEXT,
            FOREIGN KEY (usuario_asignado_id) REFERENCES usuarios (id) ON DELETE SET NULL
        )
        """)

        # 3. Tabla de SOPORTES (Tickets) - La Joya de la Corona
        # Usamos IDs para vincular usuario y técnico.
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS soportes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            usuario_id INTEGER NOT NULL,  -- Quién reporta
            tecnico_id INTEGER,           -- Quién atiende
            equipo_id INTEGER,            -- Equipo afectado (opcional)
            
            problema TEXT NOT NULL,
            descripcion_detallada TEXT,
            
            estado TEXT NOT NULL DEFAULT 'Abierto',
            prioridad TEXT NOT NULL DEFAULT 'Media',
            categoria TEXT NOT NULL DEFAULT 'Otro',
            
            solucion TEXT,
            fecha_inicio DATE,
            fecha_finalizacion DATE,
            
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE,
            FOREIGN KEY (tecnico_id) REFERENCES usuarios (id) ON DELETE SET NULL,
            FOREIGN KEY (equipo_id) REFERENCES equipos (id) ON DELETE SET NULL
        )
        """)

        # 4. Tabla de MANTENIMIENTOS (Cronograma)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mantenimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            fecha_programada DATE NOT NULL,
            estado TEXT DEFAULT 'Pendiente',
            tecnico_asignado_id INTEGER,
            motivo_reprogramacion TEXT,
            comentarios TEXT,
            FOREIGN KEY (equipo_id) REFERENCES equipos (id) ON DELETE CASCADE,
            FOREIGN KEY (tecnico_asignado_id) REFERENCES usuarios (id) ON DELETE SET NULL
        )
        """)

        # 5. Tabla de AUDITORÍA (Logs) - ¡Nuevo! Para ser robustos
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS auditoria_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            accion TEXT NOT NULL,
            detalles TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
        )
        """)

        # Crear Admin por defecto si no existe
        admin_user = 'admin'
        cursor.execute("SELECT * FROM usuarios WHERE username = ?", (admin_user,))
        if not cursor.fetchone():
            hashed_pw = generate_password_hash('admin123')
            cursor.execute("""
                INSERT INTO usuarios (username, password_hash, role, email) 
                VALUES (?, ?, ?, ?)
            """, (admin_user, hashed_pw, 'admin', 'admin@empresa.com'))
            print("✅ Usuario 'admin' creado (Pass: admin123). ¡Cámbialo pronto!")

        conn.commit()
        print("✅ Tablas verificadas y estructura robusta aplicada.")

    except sqlite3.Error as e:
        print(f"❌ Error en base de datos: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    crear_tablas()