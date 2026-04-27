@echo off
echo ============================================
echo  System Monitor Overlay - Installer
echo ============================================
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Download from https://python.org
    pause
    exit /b 1
)

echo Installing Python dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Done! Run the overlay with:  python system_overlay.py
echo Or use run.bat
echo.

:: Optional: create a desktop shortcut
set /p SHORTCUT="Create a desktop shortcut? (y/n): "
if /i "%SHORTCUT%"=="y" (
    set SCRIPT_DIR=%~dp0
    set SHORTCUT_PATH=%USERPROFILE%\Desktop\System Monitor.lnk
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%SHORTCUT_PATH%'); $sc.TargetPath = 'pythonw.exe'; $sc.Arguments = '\"%SCRIPT_DIR%system_overlay.py\"'; $sc.WorkingDirectory = '%SCRIPT_DIR%'; $sc.IconLocation = 'imageres.dll,109'; $sc.Save()"
    echo Shortcut created on your Desktop.
)

echo.
pause
