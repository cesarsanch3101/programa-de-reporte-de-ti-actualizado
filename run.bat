@echo off
TITLE Soporte TI Enterprise - Launcher
COLOR 0B
CLS

ECHO ======================================================
ECHO         SOPORTE TI - GESTION ENTERPRISE
ECHO ======================================================
ECHO.

REM --- Verificación de Entorno Virtual ---
IF EXIST venv\Scripts\activate (
    ECHO [+] Activando Entorno Virtual (venv)...
    CALL venv\Scripts\activate
) ELSE (
    ECHO [!] ADVERTENCIA: No se detecto Carpeta 'venv'. 
    ECHO [i] Se intentará ejecutar usando el Python global...
)
ECHO.

REM --- Verificación de Dependencias ---
ECHO [+] Verificando modulos necesarios...
pip install -r requirements.txt --quiet
IF %ERRORLEVEL% NEQ 0 (
    ECHO [X] ERROR: No se pudieron instalar las dependencias.
    PAUSE
    EXIT /B
)
ECHO.

REM --- Ejecución ---
ECHO [+] Iniciando servidor Flask...
ECHO [!] La aplicacion abrira en: http://127.0.0.1:5000
ECHO.
python app.py

REM --- Cierre Seguro ---
IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    ECHO [X] El sistema se detuvo con un error.
    PAUSE
)