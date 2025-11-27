@echo off

:: 1. Activar el entorno virtual.
echo Activando entorno virtual de Python 3.12...
call .\.venv\Scripts\activate

:: 2. Verificar la version de Python (opcional, pero util para depurar).
echo.
echo Version de Python activa:
python --version
echo.

:: 3. Ejecutar el servidor con el Python del entorno.
echo Iniciando el servidor de soportes...
python -m waitress --host=0.0.0.0 --port=8080 app:app

:: 4. Pausar para ver errores si el servidor falla.
pause