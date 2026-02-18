# Guía de Traspaso y Configuración - Soporte TI Enterprise

Esta guía detalla los pasos necesarios para instalar y ejecutar la aplicación en un nuevo equipo, asegurando la integridad de los datos y la configuración profesional.

## 📋 Requisitos Previos

1. **Python 3.10+**: Asegúrate de tener instalada una versión reciente de Python.
2. **Git**: Para clonar el repositorio (si aplica).
3. **Navegador Moderno**: Chrome, Edge o Firefox.

## 🚀 Instalación Paso a Paso

1. **Clonar/Copiar el Proyecto**:
   Copia la carpeta completa del proyecto al nuevo equipo.

2. **Crear Entorno Virtual**:
   Abre una terminal en la carpeta del proyecto y ejecuta:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Instalar Dependencias**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Base de Datos**:
   *   El sistema utiliza la base de datos **`soportes_v2.db`**. Asegúrate de que este archivo esté en la raíz.
   *   Si necesitas reiniciar la base de datos desde cero conservando los modelos, puedes usar el script `database_setup.py`.

## ⚙️ Configuración Inicial

1. **Usuario Administrador**:
   Si necesitas crear un nuevo administrador inicial, ejecuta:
   ```powershell
   python create_admin.py
   ```

2. **Servidor de Correo (SMTP)**:
   *   Inicia la aplicación.
   *   Entra con la cuenta de administrador.
   *   Ve a la sección **"Email Config"** en la barra lateral.
   *   Configura los datos del servidor (Host, Puerto, Usuario, Contraseña).

## 🛠️ Ejecución y Mantenimiento

*   **Iniciar Servidor**: 
    ```powershell
    python app.py
    ```
    La app estará disponible en `http://127.0.0.1:5000`.

*   **Verificación de Salud**:
    He incluido un script de validación profesional. Antes de subir a producción o tras hacer cambios, ejecuta:
    ```powershell
    python scripts/verify_project.py
    ```
    Este script verifica la integridad de los archivos y busca vulnerabilidades críticas.

## 🎨 Guía de Diseño y UX (Continuidad)

Para mantener la estética **"Enterprise Modern"** en futuras páginas, sigue estos patrones definidos en `static/css/style.css`:

### 1. Sistema de Diseño (CSS Variables)
Usa siempre las variables definidas en `:root` para mantener la coherencia:
- `--primary-color`: Azul institucional (#3699ff).
- `--sidebar-bg`: Color oscuro profesional (#1e1e2d).
- `--card-shadow`: Sombra suave para elevación profesional.

### 2. Componentes Premium
*   **Glassmorphism**: Usa la clase `.glass-card` con `.glass-card-primary` etc., para crear paneles translúcidos con bordes de color.
*   **Glow Badges**: Usa `.badge-glow-success`, `.badge-glow-danger`, etc., para etiquetas de estado que llamen la atención sin saturar.
*   **FAB (Floating Action Button)**: El botón "+" está en el `layout.html`. Puedes cambiar su icono o destino según la página.

## 🚀 Próximas Mejoras Sugeridas

Si deseas llevar la interfaz al siguiente nivel, te sugiero estos pasos:

1.  **Modo Oscuro (Dark Mode)**: Implementar un switch en la `top-bar` que cambie las variables CSS a tonos oscuros (Gris carbón/Negro).
2.  **Notificaciones en Tiempo Real**: Usar Flask-SocketIO para que el Dashboard se actualice solo cuando un usuario cree un ticket, sin refrescar la página.
3.  **Skeleton Screens**: Añadir efectos de carga (shimmer) en las tablas de DataTables mientras los datos se cargan desde el servidor.
4.  **Formularios con Validación Viva**: Usar librerías como *Parsley.js* o validaciones nativas de HTML5 mejoradas con CSS para que los errores aparezcan mientras el usuario escribe.
5.  **Optimización Móvil**: Aunque es responsive, se puede añadir un "Bottom Navigation" para móviles, simulando una app nativa.

---
*Guía generada por Antigravity para el equipo de TI.*
