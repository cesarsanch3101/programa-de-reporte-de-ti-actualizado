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

REM --- Obtener IP Local (Metodo Robusto via PowerShell) ---
REM Buscamos la interfaz que tenga un Default Gateway activo (generalmente la de red local)
FOR /F "usebackq tokens=*" %%i IN (`powershell -NoProfile -Command "(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null }).IPv4Address[0].IPAddress"`) DO SET IP=%%i

IF "%IP%"=="" (
    REM Fallback al metodo anterior si PowerShell no devuelve nada
    FOR /F "tokens=2 delims=:" %%a IN ('ipconfig ^| findstr "IPv4" ^| findstr [0-9]') DO (
        SET IP=%%a
        GOTO :found_ip
    )
)

:found_ip
SET IP=%IP: =%

ECHO.
ECHO [+] Iniciando servidor Flask...
ECHO [!] Acceso Local: http://127.0.0.1:5000
ECHO [!] Acceso Red:   http://%IP%:5000
ECHO.
ECHO [i] Presiona CTRL+C para detener el servidor.
ECHO.

python app.py

ECHO.
ECHO ======================================================
ECHO   El servidor se ha detenido.
ECHO ======================================================
PAUSE