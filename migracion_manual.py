# migracion_manual.py (Versión corregida para el error 'local variable df')

import pandas as pd
import sqlite3
from datetime import datetime
import os
import shutil

# --- CONFIGURACIÓN ---
EXCEL_FILE = 'migracion_manual.xlsx'
DB_FILE = 'soportes.db'

def migrar_datos_manuales():
    """
    Crea una copia de seguridad de la base de datos actual, luego la limpia
    e inserta los nuevos datos desde un archivo Excel.
    """
    print(f"Iniciando migración desde '{EXCEL_FILE}'...")

    if os.path.exists(DB_FILE):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        backup_file = f"soportes_backup_{timestamp}.db"
        try:
            shutil.copy(DB_FILE, backup_file)
            print(f"✅ Se ha creado una copia de seguridad de la base de datos en: '{backup_file}'")
        except Exception as e:
            print(f"⚠️ No se pudo crear la copia de seguridad: {e}")

    try:
        # --- CORRECCIÓN AQUÍ ---
        # Paso 1: Leer el archivo Excel y guardarlo en la variable df.
        df = pd.read_excel(EXCEL_FILE, dtype=str)
        
        # Paso 2: Usar la variable df ya creada para reemplazar los valores vacíos.
        df = df.where(pd.notnull(df), None)
        # --- FIN DE LA CORRECCIÓN ---

        print(f"Se encontraron {len(df)} registros en el archivo Excel.")
    except FileNotFoundError:
        print(f"❌ ERROR: No se pudo encontrar el archivo '{EXCEL_FILE}'.")
        return
    except Exception as e:
        print(f"❌ Ocurrió un error al leer el archivo Excel: {e}")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        print("Limpiando la tabla de soportes actual...")
        cursor.execute("DELETE FROM soportes")
        conn.commit()
        
        print("Insertando nuevos registros...")
        for _, row in df.iterrows():
            fecha_creacion_registro = datetime.now().strftime("%Y-%m-%d")

            cursor.execute("""
                INSERT INTO soportes (
                    fecha_hora, usuario, departamento, problema, estado, prioridad, 
                    categoria, tecnico, solucion, fecha_inicio, fecha_finalizacion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fecha_creacion_registro,
                row.get('usuario'), row.get('departamento'), row.get('problema'),
                row.get('estado', 'Cerrado'), row.get('prioridad', 'Media'),
                row.get('categoria', 'Otro'), row.get('tecnico'),
                row.get('solucion'), row.get('fecha_inicio'), row.get('fecha_finalizacion')
            ))
        
        conn.commit()
        print(f"✅ ¡Migración completada con éxito! Se han insertado {len(df)} registros en '{DB_FILE}'.")

    except Exception as e:
        print(f"❌ Ocurrió un error durante la inserción en la base de datos: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrar_datos_manuales()