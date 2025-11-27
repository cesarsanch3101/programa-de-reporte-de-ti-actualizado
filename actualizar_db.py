import sqlite3
from config import config_dict

config = config_dict['development']

def actualizar_tablas():
    print("--- 🛠️ Iniciando actualización de estructura de Base de Datos ---")
    
    conn = sqlite3.connect(config.DB_FILE)
    cursor = conn.cursor()

    # 1. Nuevas columnas para EQUIPOS
    columnas_equipos = [
        ("procesador", "TEXT"),
        ("memoria_ram", "TEXT"),      # Ej: 16GB
        ("tipo_ram", "TEXT"),         # Ej: DDR4
        ("disco_duro", "TEXT"),       # Ej: 512GB
        ("tipo_disco", "TEXT"),       # Ej: SSD NVMe
        ("fecha_compra", "DATE")
    ]

    print("Actualizando tabla 'equipos'...")
    for col, tipo in columnas_equipos:
        try:
            cursor.execute(f"ALTER TABLE equipos ADD COLUMN {col} {tipo}")
            print(f"✅ Columna '{col}' añadida.")
        except sqlite3.OperationalError:
            print(f"ℹ️ La columna '{col}' ya existía.")

    # 2. Nuevas columnas para MANTENIMIENTOS
    print("\nActualizando tabla 'mantenimientos'...")
    try:
        cursor.execute("ALTER TABLE mantenimientos ADD COLUMN motivo_reprogramacion TEXT")
        print("✅ Columna 'motivo_reprogramacion' añadida.")
    except sqlite3.OperationalError:
        print("ℹ️ La columna 'motivo_reprogramacion' ya existía.")

    conn.commit()
    conn.close()
    print("\n✅ ¡Base de datos actualizada con éxito! Ya puedes correr la app.")

if __name__ == '__main__':
    actualizar_tablas()