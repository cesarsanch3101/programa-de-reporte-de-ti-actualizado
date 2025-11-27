# config.py

"""
Archivo de configuración centralizado para el Sistema de Gestión de Soportes.
Contiene todas las constantes globales para mantener el código limpio y fácil de mantener.
"""

# --- Configuración de la Base de Datos ---
DB_FILE = 'soportes.db'

# --- Configuración de la Aplicación Web (Flask) ---
PER_PAGE = 15 # Número de soportes a mostrar por página

# --- Constantes del Negocio ---
# Estas listas definen las opciones disponibles en los formularios de la aplicación.
CATEGORIAS = ["Hardware", "Software", "Redes", "Cuentas", "Impresoras", "Otro"]
PRIORIDADES = ["Baja", "Media", "Alta", "Urgente"]
ESTADOS = ["Abierto", "En Proceso", "Resuelto", "Cerrado"]

# --- Configuración de Scripts de Utilidad ---
# Nombres de archivo para los scripts de migración
MIGRACION_EXCEL_FILE = 'soportes_existentes.xlsx'
MIGRACION_MANUAL_EXCEL_FILE = 'migracion_manual.xlsx'