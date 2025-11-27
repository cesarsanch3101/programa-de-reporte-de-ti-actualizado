# Copilot Instructions for AI Agents

## Arquitectura General
- El proyecto es una aplicación de gestión de soportes de TI basada en Flask, con persistencia en SQLite (`soportes.db`).
- El frontend utiliza plantillas HTML en `templates/` y archivos estáticos en `static/`.
- El backend principal está en `app.py`, que gestiona rutas, autenticación, y lógica de negocio.
- El archivo `gestor_soportes_db.py` contiene utilidades y lógica CRUD para la base de datos, usado para scripts y operaciones fuera de Flask.
- `create_admin.py` permite crear un usuario administrador en la base de datos.
- `migracion.py` importa datos desde un archivo Excel (`soportes_existentes.xlsx`) a la base de datos, vaciando la tabla antes de migrar para evitar duplicados.

## Flujos de Desarrollo
- **Ejecución local:** Usar `run.bat` para iniciar el servidor con Waitress en el puerto 8080 (`python -m waitress --host=0.0.0.0 --port=8080 app:app`).
- **Migración de datos:** Ejecutar `migracion.py` para poblar la base de datos desde Excel. El script elimina los datos previos antes de migrar.
- **Creación de admin:** Ejecutar `create_admin.py` para crear el usuario administrador. Asegura que la tabla `usuarios` exista antes de insertar.
- **Gestión de base de datos:** Usar funciones de `gestor_soportes_db.py` para operaciones directas sobre la base de datos fuera de Flask.

## Convenciones y Patrones
- Las rutas protegidas usan los decoradores `login_required` y `admin_required` definidos en `app.py`.
- Las constantes globales (`DB_FILE`, `CATEGORIAS`, `PRIORIDADES`, etc.) se definen al inicio de los archivos principales.
- La conexión a la base de datos se gestiona centralizadamente con `get_db()` en Flask y `conectar_db()` en scripts.
- Las tablas principales son `soportes` y `usuarios`. La estructura puede variar ligeramente entre scripts, pero `app.py` define el modelo más completo.
- Los scripts de migración y creación de admin importan funciones de `app.py` para asegurar la consistencia de las tablas.

## Integraciones y Dependencias
- Flask, pandas, waitress, werkzeug, flask-weasyprint.
- El frontend depende de los archivos en `static/` y las plantillas en `templates/`.
- El sistema de autenticación usa hashes de contraseña con Werkzeug.

## Ejemplo de flujo típico
1. Migrar datos con `migracion.py` si es necesario.
2. Crear usuario admin con `create_admin.py`.
3. Iniciar el servidor con `run.bat`.
4. Acceder a la app vía navegador en `http://localhost:8080`.

## Recomendaciones para agentes AI
- Mantener la consistencia de la estructura de las tablas entre scripts y Flask.
- Usar los decoradores de autenticación para proteger rutas sensibles.
- Validar la existencia de archivos clave (`soportes.db`, `soportes_existentes.xlsx`) antes de ejecutar scripts.
- Referenciar y reutilizar funciones utilitarias en vez de duplicar lógica.
- Documentar cambios relevantes en este archivo para futuras mejoras de agentes.
