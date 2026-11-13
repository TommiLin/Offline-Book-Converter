@echo off
cd /d "%~dp0"
if exist "%~dp0OfflineBookConverter.exe" (
    start "" "%~dp0OfflineBookConverter.exe"
    exit /b
)
where pythonw.exe >nul 2>nul
if errorlevel 1 goto missing
start "" pythonw.exe "%~dp0app.pyw"
exit /b
:missing
echo Python 3 with Tkinter is required. See README.txt.
pause
