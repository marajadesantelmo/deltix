@echo off
REM Registra una tarea en Windows Task Scheduler para sincronizar
REM web_interactions.csv desde PythonAnywhere cada día a las 09:00.
REM
REM Ejecutar como Administrador (click derecho → Ejecutar como administrador).

set PYTHON=C:\Users\facun\anaconda3\python.exe
set SCRIPT=%~dp0sync_csv.py
set TASK_NAME=Deltix_Sync_CSV

echo Registrando tarea: %TASK_NAME%
echo Script: %SCRIPT%
echo Python: %PYTHON%
echo Horario: todos los dias a las 09:00

schtasks /Create /TN "%TASK_NAME%" /TR "\"%PYTHON%\" \"%SCRIPT%\"" /SC DAILY /ST 09:00 /F /RL HIGHEST

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Tarea registrada correctamente.
    echo Podes verla en: Inicio > Task Scheduler > Deltix_Sync_CSV
    echo Para cambiar el horario: schtasks /Change /TN "%TASK_NAME%" /ST HH:MM
) else (
    echo ERROR al registrar la tarea.
    echo Asegurate de ejecutar este .bat como Administrador.
)

pause
