import os
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

class Config:
    """Configuración base que se usa en producción y desarrollo."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-por-defecto-insegura'
    
    # Base de Datos
    DB_FILE = os.environ.get('DB_NAME', 'soportes.db')
    
    # Paginación
    PER_PAGE = 15
    
    # Configuración de Flask-Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # Constantes del Negocio (Listas maestras)
    CATEGORIAS = ["Hardware", "Software", "Redes", "Cuentas", "Impresoras", "Otro"]
    PRIORIDADES = ["Baja", "Media", "Alta", "Urgente"]
    ESTADOS = ["Abierto", "En Proceso", "Resuelto", "Cerrado"]
    
    # Rutas de Archivos
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
    TEMPLATES_FOLDER = os.path.join(BASE_DIR, 'templates')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # Aquí podrías forzar SSL, logs más estrictos, etc.

# Diccionario para seleccionar configuración fácilmente
config_dict = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}