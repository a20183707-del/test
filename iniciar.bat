@echo off
setlocal
cd /d "%~dp0extractor-documental"
call iniciar.bat
exit /b %errorlevel%
