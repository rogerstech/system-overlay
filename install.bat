@echo off
echo ============================================
echo  System Monitor Overlay - Installer
echo ============================================
echo.

:: Check Python 3.12 is available via the py launcher
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.12 not found.
    echo Download from: https://www.python.org/downloads/release/python-3129/
    echo Make sure to check "Add Python to PATH" and enable tcl/tk during install.
    pause
    exit /b 1
)

echo Python 3.12 found. Installing dependencies...
py -3.12 -m pip install --upgrade pip --quiet
py -3.12 -m pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Done! Dependencies installed: psutil, pystray, Pillow
echo.

:: Optional: create a desktop shortcut (no console window)
set /p SHORTCUT="Create a desktop shortcut? (y/n): "
if /i "%SHORTCUT%"=="y" (
    for /f "delims=" %%i in ('where pyw') do set "PYWEXE=%%i"
    set "SCRIPT_DIR=%~dp0"
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\System Monitor.lnk'); $sc.TargetPath = '%PYWEXE%'; $sc.Arguments = '-3.12 \"%SCRIPT_DIR%system_overlay.py\"'; $sc.WorkingDirectory = '%SCRIPT_DIR%'; $sc.WindowStyle = 7; $sc.Save()"
    echo Shortcut created on your Desktop.
)

echo.
echo Run the overlay with:  run.bat
echo Or add to startup with: startup.bat
echo.
pause
