import sqlite3
from config import config_dict

config = config_dict['development']

def actualizar_tabla():
    print("--- 🎨 Agregando campo Color al inventario ---")
    
    conn = sqlite3.connect(config.DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE equipos ADD COLUMN color TEXT")
        print("✅ Columna 'color' añadida correctamente.")
    except sqlite3.OperationalError:
        print("ℹ️ La columna 'color' ya existía.")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    actualizar_tabla()