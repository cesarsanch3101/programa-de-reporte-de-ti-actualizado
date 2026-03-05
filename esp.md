# Especificaciones Técnicas y Desarrollo - Soporte TI Enterprise

Este documento detalla la arquitectura técnica, el modelo de datos y los lineamientos de desarrollo para el **Sistema de Soporte TI Enterprise**.

## 1. Arquitectura del Sistema
El sistema sigue un patrón de arquitectura monolítica basada en el micro-framework **Flask** (Python), diseñado para ser ligero, modular y fácil de desplegar.

- **Backend**: Python 3.x / Flask
- **Frontend**: HTML5, CSS3 (Bootstrap 5), JavaScript (jQuery, Socket.io, DataTables)
- **Base de Datos**: SQLite 3 (Archivo: `soportes.db`)
- **Comunicación en Tiempo Real**: Flask-SocketIO para notificaciones dinámicas.
- **Generación de PDF**: WeasyPrint para reportes y fichas técnicas.
- **Correo Electrónico**: Flask-Mail para notificaciones SMTP.

## 2. Estructura de la Base de Datos
El modelo relacional se define en `database_setup.py`:

- **`usuarios`**: Gestión de accesos y roles (admin, tecnico, user).
- **`equipos`**: Inventario de hardware con especificaciones técnicas detalladas.
- **`soportes`**: Registro de tickets, vinculando usuarios, técnicos y activos.
- **`mantenimientos`**: Programación de tareas preventivas con estados y técnicos asignados.
- **`auditoria_logs`**: Registro histórico de acciones críticas dentro del sistema.

## 3. Requisitos del Entorno
Consulte el archivo `requirements.txt` para la lista completa de dependencias. Las principales son:
- `Flask`: Servidor web.
- `Flask-SocketIO`: Notificaciones en tiempo real.
- `WeasyPrint`: Motor de renderizado PDF.
- `Pandas` / `Openpyxl`: Exportación e importación de datos Excel.
- `Werkzeug`: Seguridad y hashing de contraseñas.

## 4. Configuración y Despliegue
1. **Instalación**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Inicialización de BD**:
   ```bash
   python database_setup.py
   ```
3. **Ejecución (Desarrollo)**:
   ```bash
   python app.py
   ```
   *El sistema corre por defecto en el puerto 5000.*

## 5. Prácticas de Desarrollo
- **Modo Oscuro**: Implementado mediante variables CSS en `style.css` y el atributo `data-theme` en `<html>`.
- **Validación de Formularios**: Se utiliza `needs-validation` de Bootstrap 5 con feedback en tiempo real mediante jQuery.
- **Seguridad**: Todas las rutas críticas están protegidas por decoradores `@login_required` y `@admin_required`. Las contraseñas se almacenan mediante hashing (PBKDF2).

## 6. Endpoints Principales
- `/dashboard`: Resumen de métricas.
- `/soportes`: Listado y gestión de tickets.
- `/equipos`: Inventario y fichas técnicas.
- `/mantenimientos`: Calendario y tareas técnicas.
- `/admin/usuarios`: Administración de cuentas.

---
*Mantenido por el Equipo de Desarrollo de TI.*
