@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3.11 -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        py -3.11 src\bsg_extractor\launcher.py
        goto completed
    )
)
where python >nul 2>nul
if errorlevel 1 (
    echo Falta Python 3.11 o posterior. Instala Python y vuelve a ejecutar este archivo.
    pause
    exit /b 1
)
python src\bsg_extractor\launcher.py
:completed
set "bsg_exit_code=%errorlevel%"
if not "%bsg_exit_code%"=="0" pause
exit /b %bsg_exit_code%
