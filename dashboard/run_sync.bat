@echo off
REM Wrapper para sync_csv.py con log de ejecucion.
REM Es el que ejecuta Windows Task Scheduler.

set PYTHON=C:\Users\facun\anaconda3\python.exe
set SCRIPT=C:\Users\facun\OneDrive\Documentos\GitHub\deltix\dashboard\sync_csv.py
set LOGFILE=C:\Users\facun\OneDrive\Documentos\GitHub\deltix\dashboard\sync.log

echo [%DATE% %TIME%] Iniciando sync... >> "%LOGFILE%"
"%PYTHON%" "%SCRIPT%" >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [%DATE% %TIME%] Sync OK >> "%LOGFILE%"
) else (
    echo [%DATE% %TIME%] ERROR en sync (exit code %ERRORLEVEL%) >> "%LOGFILE%"
)
