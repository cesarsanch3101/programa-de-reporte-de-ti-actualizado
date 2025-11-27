# create_admin.py

import sqlite3
from werkzeug.security import generate_password_hash
from config import DB_FILE
from database_setup import crear_tablas

# --- Configuración del Administrador a Crear ---
# Es mejor pedirlos por consola para no dejar contraseñas en el código
# pero para simplicidad, los dejamos aquí. ¡Cámbialos!
ADMIN_USERNAME = 'admin' 
ADMIN_PASSWORD = 'password' 

def crear_admin_inicial():
    """
    Crea un usuario administrador inicial en la base de datos si no existe.
    Este script debe ejecutarse una vez durante la configuración inicial del sistema.
    """
    print("--- Asistente de Creación de Administrador ---")
    
    # Hashear la contraseña de forma segura
    password_hash = generate_password_hash(ADMIN_PASSWORD)
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Insertar el usuario admin
        cursor.execute(
            "INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)",
            (ADMIN_USERNAME, password_hash, 'admin')
        )
        conn.commit()
        print(f"✅ Usuario administrador '{ADMIN_USERNAME}' creado con éxito.")
        print("¡No olvides cambiar la contraseña por defecto!")

    except sqlite3.IntegrityError:
        print(f"⚠️  El usuario administrador '{ADMIN_USERNAME}' ya existe. No se realizaron cambios.")
    except sqlite3.Error as e:
        print(f"❌ Ocurrió un error en la base de datos: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # 1. Asegurarse de que la estructura de la base de datos exista
    crear_tablas()
    # 2. Intentar crear el usuario administrador
    crear_admin_inicial()