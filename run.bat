@echo off
TITLE Sistema de Soportes TI
ECHO Iniciando el Sistema de Soportes...
ECHO.

REM --- Instalar dependencias si faltan ---
ECHO Verificando e instalando dependencias necesarias...
pip install -r requirements.txt
ECHO.

REM --- Ejecutar la aplicación ---
python app.py

REM --- Mantener ventana abierta si hay error ---
PAUSE