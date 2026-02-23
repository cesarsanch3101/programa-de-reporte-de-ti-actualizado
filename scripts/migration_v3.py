import sqlite3
import os

def migrate():
    db_path = 'soportes_v2.db'
    if not os.path.exists(db_path):
        print(f"Error: {db_path} no encontrado.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Creando tabla de adjuntos en {db_path}...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS adjuntos (
            id TEXT PRIMARY KEY,
            ticket_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            mimetype TEXT,
            fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES soportes(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()
    print("Migración completada con éxito.")

if __name__ == "__main__":
    migrate()
