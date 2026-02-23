# Guía de Implementación en Synology DS1522+

Esta guía detalla cómo desplegar la aplicación en tu Synology NAS usando **Container Manager** (anteriormente Docker), asegurando que no se pierdan datos y que sea accesible desde internet.

## 1. Preparación de Archivos
He creado los siguientes archivos en la raíz de tu proyecto:
- **Dockerfile**: Define el entorno técnico (Python, librerías PDF, etc.).
- **docker-compose.yml**: Configura los volúmenes para no perder datos.
- **.dockerignore**: Optimiza la imagen de la aplicación.
- He añadido `gunicorn` a los requerimientos para un rendimiento profesional.

## 2. Transferencia al NAS
1. Abre **File Station** en tu Synology.
2. Crea una carpeta en `/docker` llamada `it-support`.
3. Copia todo el contenido de tu proyecto local a esa carpeta `/docker/it-support`.
   > [!IMPORTANT]
   > Asegúrate de copiar el archivo `soportes_v2.db` y la carpeta `static/uploads` ya que contienen tus datos actuales.

## 3. Configuración en Container Manager
1. Abre **Container Manager** en tu Synology.
2. Ve a **Proyecto** -> **Crear**.
3. Ponle un nombre (ej: `it-support`).
4. Selecciona la ruta `/docker/it-support`.
5. Selecciona "Utilizar docker-compose.yml existente".
6. Sigue el asistente y dale a **Finalizar**. La aplicación se compilará y se ejecutará en el puerto interno **5000**.

## 4. Acceso desde Internet (Proxy Inverso)
Para que sea accesible y seguro (HTTPS):
1. Ve al **Panel de Control** -> **Portal de inicio de sesión** -> **Avanzado** -> **Proxy inverso**.
2. Haz clic en **Crear**:
   - **Nombre**: `IT Support`
   - **Origen**: HTTPS, Puerto `443`, Nombre de host: `tu-subdominio.synology.me` (o tu dominio).
   - **Destino**: HTTP, Puerto `5000`, Nombre de host: `localhost`.
3. En **Panel de Control** -> **Seguridad** -> **Certificado**, asegúrate de pedir un certificado de **Let's Encrypt** para ese subdominio.

## 5. Acceso Externo (DDNS)
Si no tienes una IP fija:
1. Ve a **Panel de Control** -> **Acceso externo** -> **DDNS**.
2. Añade uno de Synology (ej: `nombre.synology.me`).
3. En tu router, asegúrate de redirigir el puerto **443** (HTTPS) hacia la IP local de tu NAS.

---
### Notas de Persistencia
Los datos se guardan fuera del contenedor en tu carpeta `/docker/it-support`. Si detienes el proyecto, actualizas el código o lo vuelves a crear, los tickets y archivos adjuntos **permanecerán intactos**.
