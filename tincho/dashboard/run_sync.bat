@echo off
REM Wrapper de sync_db.py con log de ejecucion (lo usa el Programador de tareas de Windows).

set PYTHON=C:\Users\facun\anaconda3\python.exe
set SCRIPT=%~dp0sync_db.py
set LOGFILE=%~dp0sync.log

echo [%DATE% %TIME%] Iniciando sync... >> "%LOGFILE%"
"%PYTHON%" "%SCRIPT%" >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [%DATE% %TIME%] Sync OK >> "%LOGFILE%"
) else (
    echo [%DATE% %TIME%] ERROR en sync (exit code %ERRORLEVEL%) >> "%LOGFILE%"
)
