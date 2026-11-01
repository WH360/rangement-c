@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "rangement_c.py"
    exit /b
)
where py >nul 2>nul
if %errorlevel%==0 (
    start "" pyw "rangement_c.py"
    exit /b
)
echo Python n'est pas installe.
echo Installe-le depuis le Microsoft Store (cherche "Python 3.12"), puis relance ce fichier.
start ms-windows-store://pdp/?productid=9NCVDN91XZQP
pause
