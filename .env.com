# .env
# Configuración de Seguridad
SECRET_KEY=Pablo09**##
FLASK_ENV=development
DEBUG=True

# Configuración de Correo (Cámbialo por tus datos reales)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=admin@stwards.com
MAIL_PASSWORD=Pablo09**##
MAIL_DEFAULT_SENDER=admin@stwards.com

# Configuración de Base de Datos
DB_NAME=soportes.db