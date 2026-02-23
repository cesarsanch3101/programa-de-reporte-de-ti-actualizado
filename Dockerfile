# Usamos una imagen ligera de Python
FROM python:3.11-slim

# Instalamos dependencias del sistema necesarias para WeasyPrint (PDFs), Pandas y SQLite
RUN apt-get update && apt-get install -y \
    python3-dev \
    gcc \
    libpangocairo-1.0-0 \
    libharfbuzz-0b \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    zlib1g-dev \
    shared-mime-info \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Establecemos el directorio de trabajo
WORKDIR /app

# Copiamos los requerimientos primero para aprovechar el cache de Docker
COPY requirements.txt .

# Instalamos las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de la aplicación
COPY . .

# Creamos la carpeta de uploads si no existe y damos permisos
RUN mkdir -p static/uploads && chmod 777 static/uploads

# Exponemos el puerto 5000 (puerto por defecto de Flask)
EXPOSE 5000

# Comando para ejecutar la aplicación con Gunicorn y soporte para WebSockets (eventlet)
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "app:app"]
