import sqlite3
from config import config_dict

config = config_dict['development']

def crear_tabla_config():
    print("--- ⚙️ Creando tabla de configuraciones ---")
    
    conn = sqlite3.connect(config.DB_FILE)
    cursor = conn.cursor()

    # Tabla Clave-Valor para configuraciones dinámicas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracion (
        clave TEXT PRIMARY KEY,
        valor TEXT
    )
    """)
    
    print("✅ Tabla 'configuracion' lista.")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    crear_tabla_config()