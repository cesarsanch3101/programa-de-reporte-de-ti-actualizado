@echo off
TITLE Soporte TI Enterprise - Launcher
COLOR 0B
CLS

ECHO ======================================================
ECHO         SOPORTE TI - GESTION ENTERPRISE
ECHO ======================================================
ECHO.

REM --- Diagnostico inicial ---
ECHO [+] Directorio actual: %CD%
ECHO [+] Verificando instalacion de Python...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO [X] ERROR: Python no esta instalado o no esta en el PATH.
    PAUSE
    EXIT /B
)

REM --- Activacion de Entorno Virtual ---
IF EXIST "venv\Scripts\activate.bat" (
    ECHO [+] Activando Entorno Virtual...
    CALL "venv\Scripts\activate.bat"
) ELSE IF EXIST "venv\Scripts\activate" (
    ECHO [+] Activando Entorno Virtual...
    CALL "venv\Scripts\activate"
) ELSE (
    ECHO [!] ADVERTENCIA: No se detecto Carpeta 'venv'.
)

ECHO.
SET /P choice="¿Deseas verificar dependencias? (S/N, Enter para saltar): "
IF /I "%choice%"=="S" (
    ECHO [+] Verificando dependencias...
    python -m pip install -r requirements.txt
) ELSE (
    ECHO [+] Saltando verificacion de dependencias.
)

REM --- Obtención de IP Local (Método Ultra-Robusto) ---
ECHO [+] Detectando IP de red para acceso remoto...
FOR /F "usebackq tokens=*" %%i IN (`python -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()"`) DO SET LOCAL_IP=%%i

IF "%LOCAL_IP%"=="" (
    FOR /F "tokens=*" %%i IN ('python -c "import socket; print(socket.gethostbyname(socket.gethostname()))"') DO SET LOCAL_IP=%%i
)

ECHO.
ECHO [+] Iniciando servidor Flask...
ECHO [!] Acceso Local:  http://127.0.0.1:5000
ECHO [!] Acceso Red:    http://%LOCAL_IP%:5000
ECHO.
ECHO [i] Otros equipos pueden entrar usando: http://%LOCAL_IP%:5000
ECHO [i] Presiona CTRL+C para detener el servidor.
ECHO.

python app.py

ECHO.
ECHO ======================================================
ECHO   El servidor se ha detenido.
ECHO ======================================================
PAUSE