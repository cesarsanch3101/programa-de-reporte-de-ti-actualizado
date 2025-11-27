import sqlite3
import os
import time
from datetime import datetime
import csv
import pandas as pd # Importamos pandas para la exportación a Excel

# --- CONFIGURACIÓN GLOBAL ---
DB_FILE = 'soportes.db'
CATEGORIAS = ["Hardware", "Software", "Redes", "Cuentas", "Impresoras", "Otro"]
PRIORIDADES = ["Baja", "Media", "Alta", "Urgente"]

# --- FUNCIONES DE INFRAESTRUCTURA ---

def conectar_db():
    """Crea una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DB_FILE)
    return conn

def crear_tabla():
    """Crea la tabla de soportes si no existe."""
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS soportes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_hora TEXT NOT NULL,
        usuario TEXT NOT NULL,
        departamento TEXT,
        problema TEXT NOT NULL,
        estado TEXT NOT NULL,
        tecnico TEXT,
        solucion TEXT,
        prioridad TEXT, 
        categoria TEXT
    )
    """)
    conn.commit()
    conn.close()

def limpiar_pantalla():
    """Limpia la pantalla de la consola."""
    os.system('cls' if os.name == 'nt' else 'clear')

def seleccionar_opcion(titulo, opciones):
    """Muestra un menú de opciones y devuelve la seleccionada por el usuario."""
    print(titulo)
    for i, opcion in enumerate(opciones, 1):
        print(f"{i}. {opcion}")
    
    while True:
        try:
            seleccion = int(input("Elige una opción: "))
            if 1 <= seleccion <= len(opciones):
                return opciones[seleccion - 1]
            else:
                print("❌ Selección fuera de rango. Inténtalo de nuevo.")
        except ValueError:
            print("❌ Por favor, introduce un número válido.")

# --- FUNCIONES PRINCIPALES (CRUD) ---

def registrar_soporte():
    """Registra un nuevo soporte en la base de datos."""
    limpiar_pantalla()
    print("--- ➕ Registrar Nuevo Soporte ---")
    
    usuario = input("Nombre del usuario: ")
    departamento = input("Departamento: ")
    problema = input("Descripción del problema: ")
    
    print("")
    categoria = seleccionar_opcion("Selecciona la categoría:", CATEGORIAS)
    print("")
    prioridad = seleccionar_opcion("Selecciona la prioridad:", PRIORIDADES)

    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    estado = "Abierto"
    
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO soportes (fecha_hora, usuario, departamento, problema, estado, prioridad, categoria)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (fecha_hora, usuario, departamento, problema, estado, prioridad, categoria))
        
        id_ticket = cursor.lastrowid
        conn.commit()
        conn.close()
        print(f"\n✅ ¡Soporte registrado con éxito! ID del Ticket: {id_ticket}")
    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")

    input("\nPresiona Enter para volver al menú...")

def ver_soportes(con_pausa=True):
    """Muestra todos los soportes de la base de datos."""
    limpiar_pantalla()
    print("--- 📋 Lista de Todos los Soportes ---")
    
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, estado, prioridad, categoria, usuario, problema FROM soportes ORDER BY id DESC")
        soportes = cursor.fetchall()
        conn.close()
        
        if not soportes:
            print("\nNo hay soportes registrados todavía.")
        else:
            print(f"\n{'ID':<5} {'Estado':<12} {'Prioridad':<10} {'Categoría':<12} {'Usuario':<15} {'Problema':<30}")
            print("-" * 90)
            for fila in soportes:
                id, estado, prioridad, categoria, usuario, problema = fila
                print(f"{id:<5} {estado:<12} {prioridad:<10} {categoria:<12} {usuario:<15} {problema[:28]:<30}")
    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")

    if con_pausa:
        input("\nPresiona Enter para volver al menú...")

def actualizar_soporte():
    """Permite actualizar un soporte existente."""
    ver_soportes(con_pausa=False)
    
    try:
        id_a_actualizar = input("\nIntroduce el ID del ticket a actualizar (o '0' para cancelar): ")
        if id_a_actualizar == '0': return

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM soportes WHERE id = ?", (id_a_actualizar,))
        ticket = cursor.fetchone()
        
        if ticket:
            print(f"\n--- Editando Ticket ID: {ticket[0]} | Problema: {ticket[4]} ---")
            
            nuevo_estado = input(f"Nuevo estado (actual: {ticket[5]}) [Abierto/En Proceso/Resuelto/Cerrado]: ")
            nuevo_tecnico = input(f"Técnico asignado (actual: {ticket[6] if ticket[6] else 'N/A'}): ")
            nueva_solucion = input(f"Notas de la solución (actual: {ticket[7] if ticket[7] else 'N/A'}): ")
            
            print(f"\nPrioridad actual: {ticket[8]}")
            cambiar_prioridad = input("¿Cambiar prioridad? (sí/no): ").lower()
            nueva_prioridad = seleccionar_opcion("Selecciona la nueva prioridad:", PRIORIDADES) if cambiar_prioridad == 'sí' else ticket[8]

            print(f"\nCategoría actual: {ticket[9]}")
            cambiar_categoria = input("¿Cambiar categoría? (sí/no): ").lower()
            nueva_categoria = seleccionar_opcion("Selecciona la nueva categoría:", CATEGORIAS) if cambiar_categoria == 'sí' else ticket[9]

            estado_final = nuevo_estado if nuevo_estado else ticket[5]
            tecnico_final = nuevo_tecnico if nuevo_tecnico else ticket[6]
            solucion_final = nueva_solucion if nueva_solucion else ticket[7]

            cursor.execute("""
            UPDATE soportes 
            SET estado = ?, tecnico = ?, solucion = ?, prioridad = ?, categoria = ?
            WHERE id = ?
            """, (estado_final, tecnico_final, solucion_final, nueva_prioridad, nueva_categoria, id_a_actualizar))
            
            conn.commit()
            print("\n✅ ¡Ticket actualizado con éxito!")
        else:
            print("\n❌ ID de ticket no encontrado.")
        
        conn.close()
    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")

    input("\nPresiona Enter para volver al menú...")

def eliminar_soporte():
    """Elimina un soporte de la base de datos previa confirmación."""
    ver_soportes(con_pausa=False)
    
    try:
        id_a_eliminar = input("\nIntroduce el ID del ticket a eliminar (o '0' para cancelar): ")
        if id_a_eliminar == '0': return

        confirmacion = input(f"🚨 ¿Estás seguro de que quieres eliminar el ticket {id_a_eliminar}? Esta acción no se puede deshacer. (sí/no): ").lower()
        
        if confirmacion == 'sí' or confirmacion == 'si':
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM soportes WHERE id = ?", (id_a_eliminar,))
            conn.commit()
            
            if cursor.rowcount > 0:
                print("\n✅ Ticket eliminado correctamente.")
            else:
                print("\n❌ ID de ticket no encontrado.")
            
            conn.close()
        else:
            print("\nOperación cancelada.")

    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")
    
    input("\nPresiona Enter para volver al menú...")

# --- FUNCIONES DE BÚSQUEDA, REPORTE Y EXPORTACIÓN ---

def buscar_soportes():
    """Busca soportes por un término en múltiples campos."""
    limpiar_pantalla()
    print("--- 🔍 Buscar Soportes ---")
    termino = input("Introduce el término de búsqueda (usuario, categoría, prioridad, etc.): ")
    
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        termino_busqueda = f"%{termino}%"
        cursor.execute("""
        SELECT id, estado, prioridad, categoria, usuario, problema 
        FROM soportes 
        WHERE usuario LIKE ? OR problema LIKE ? OR solucion LIKE ? OR prioridad LIKE ? OR categoria LIKE ?
        ORDER BY id DESC
        """, (termino_busqueda, termino_busqueda, termino_busqueda, termino_busqueda, termino_busqueda))
        
        resultados = cursor.fetchall()
        conn.close()

        if not resultados:
            print(f"\nNo se encontraron soportes que coincidan con '{termino}'.")
        else:
            print(f"\n--- Resultados de la Búsqueda para '{termino}' ---")
            print(f"\n{'ID':<5} {'Estado':<12} {'Prioridad':<10} {'Categoría':<12} {'Usuario':<15} {'Problema':<30}")
            print("-" * 90)
            for fila in resultados:
                 id, estado, prioridad, categoria, usuario, problema = fila
                 print(f"{id:<5} {estado:<12} {prioridad:<10} {categoria:<12} {usuario:<15} {problema[:28]:<30}")

    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")

    input("\nPresiona Enter para volver al menú...")

def ver_reporte():
    """Muestra un reporte de soportes agrupados por estado."""
    limpiar_pantalla()
    print("--- 📊 Reporte de Soportes por Estado ---")

    try:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT estado, COUNT(*) FROM soportes GROUP BY estado")
        reporte = cursor.fetchall()
        conn.close()

        if not reporte:
            print("\nNo hay datos para generar un reporte.")
        else:
            print("\nEstado              | Cantidad")
            print("--------------------|----------")
            total = 0
            for estado, cantidad in reporte:
                print(f"{estado:<19} | {cantidad}")
                total += cantidad
            print("--------------------|----------")
            print(f"TOTAL               | {total}")

    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")
    
    input("\nPresiona Enter para volver al menú...")

def exportar_a_excel():
    """Exporta todos los soportes de la base de datos a un archivo Excel (.xlsx)."""
    limpiar_pantalla()
    print("--- ექს Exportar Soportes a Excel ---")
    
    try:
        conn = conectar_db()
        df = pd.read_sql_query("SELECT * FROM soportes ORDER BY id", conn)
        conn.close()

        if df.empty:
            print("\nNo hay soportes para exportar.")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            nombre_archivo = f"reporte_soportes_{timestamp}.xlsx"
            
            df.to_excel(nombre_archivo, index=False)
            
            print(f"\n✅ ¡Exportación a Excel completada con éxito!")
            print(f"Se han guardado {len(df)} soportes en el archivo: {nombre_archivo}")

    except Exception as e:
        print(f"❌ Ocurrió un error durante la exportación: {e}")
    
    input("\nPresiona Enter para volver al menú...")

# --- MENÚ PRINCIPAL ---

def menu_principal():
    """Muestra el menú principal y maneja la selección del usuario."""
    crear_tabla()
    while True:
        limpiar_pantalla()
        print("===========================================")
        print("    SISTEMA DE GESTIÓN DE SOPORTES (DB)")
        print("===========================================")
        print("1. ➕ Registrar Soporte")
        print("2. 📋 Ver Todos los Soportes")
        print("3. 🔄 Actualizar Soporte")
        print("-------------------------------------------")
        print("4. 🔍 Buscar Soportes")
        print("5. 📊 Ver Reporte por Estado")
        print("6. 🗑️ Eliminar Soporte")
        print("-------------------------------------------")
        print("7. ექს Exportar a Excel")
        print("8. ❌ Salir")
        print("===========================================")
        
        opcion = input("Elige una opción: ")
        
        if opcion == '1': registrar_soporte()
        elif opcion == '2': ver_soportes()
        elif opcion == '3': actualizar_soporte()
        elif opcion == '4': buscar_soportes()
        elif opcion == '5': ver_reporte()
        elif opcion == '6': eliminar_soporte()
        elif opcion == '7': exportar_a_excel()
        elif opcion == '8':
            print("\n¡Hasta luego! 👋")
            break
        else:
            print("\n❌ Opción no válida. Inténtalo de nuevo.")
            time.sleep(2)

# --- Punto de entrada del programa ---
if __name__ == "__main__":
    menu_principal()