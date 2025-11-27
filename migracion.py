# migracion.py (versión corregida para no duplicar)

import pandas as pd
import sqlite3
import os
from datetime import datetime
from config import DB_FILE, MIGRACION_EXCEL_FILE
from database_setup import crear_tablas

def migrar_datos():
    """
    Limpia la tabla de soportes y la repuebla con datos de un archivo Excel.
    Valida la existencia del archivo Excel antes de proceder.
    """
    print(f"--- Script de Migración desde Excel ---")
    print(f"Archivo de origen: '{MIGRACION_EXCEL_FILE}'")
    print(f"Base de datos destino: '{DB_FILE}'")
    
    # --- Paso 1: Validar que el archivo Excel exista ---
    if not os.path.exists(MIGRACION_EXCEL_FILE):
        print(f"\n❌ ERROR: No se pudo encontrar el archivo de migración '{MIGRACION_EXCEL_FILE}'.")
        print("Por favor, asegúrate de que el archivo esté en el mismo directorio que este script.")
        return

    try:
        # --- Paso 2: Leer el archivo Excel ---
        df = pd.read_excel(MIGRACION_EXCEL_FILE)
        print(f"\nSe encontraron {len(df)} registros en el archivo Excel.")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # --- Paso 3: Limpiar la tabla existente para evitar duplicados ---
        print("Limpiando la tabla de soportes existente...")
        cursor.execute("DELETE FROM soportes")
        conn.commit()
        print("Tabla 'soportes' limpiada.")
        
        # --- Paso 4: Insertar los nuevos registros ---
        print("Insertando nuevos registros en la base de datos...")
        for _, row in df.iterrows():
            fecha_ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
            INSERT INTO soportes (
                fecha_hora, usuario, departamento, problema, estado, prioridad, categoria, tecnico, solucion,
                fecha_inicio, fecha_finalizacion, comentarios_solucion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fecha_ahora,
                row.get('Usuario'), row.get('Departamento'), row.get('Problema'),
                row.get('Estado', 'Abierto'), row.get('Prioridad', 'Media'), row.get('Categoria', 'Otro'),
                row.get('Tecnico'), row.get('Solucion'),
                fecha_ahora, None, None # Valores por defecto para nuevos tickets
            ))
        
        conn.commit()
        print(f"✅ ¡Migración completada! Se han insertado {len(df)} registros.")

    except FileNotFoundError: # Doble chequeo, aunque el 'os.path.exists' ya lo cubre
        print(f"❌ ERROR: No se encontró el archivo '{MIGRACION_EXCEL_FILE}'.")
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado durante la migración: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    # Asegurarse de que las tablas existan antes de intentar migrar datos
    crear_tablas()
    migrar_datos()