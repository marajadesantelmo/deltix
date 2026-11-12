@echo off
REM Registra una tarea en el Programador de tareas de Windows que baja la base de
REM conversaciones de Tincho desde PythonAnywhere todos los dias a las 09:05.
REM Ejecutar como Administrador (click derecho > Ejecutar como administrador).

set TASK_NAME=Tincho_Sync_DB
set WRAPPER=%~dp0run_sync.bat

echo Registrando tarea: %TASK_NAME%
echo Script: %WRAPPER%
echo Horario: todos los dias a las 09:05

schtasks /Create /TN "%TASK_NAME%" /TR "\"%WRAPPER%\"" /SC DAILY /ST 09:05 /F /RL HIGHEST

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Tarea registrada correctamente.
    echo Para cambiar el horario: schtasks /Change /TN "%TASK_NAME%" /ST HH:MM
) else (
    echo ERROR al registrar la tarea. Asegurate de ejecutar este .bat como Administrador.
)

pause
