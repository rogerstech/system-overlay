@echo off
:: Add this widget to Windows startup by dropping a shortcut in the Startup folder.
:: Run this script once; it will register run.bat to launch at login.

set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_DIR%\SystemMonitorOverlay.lnk
set SCRIPT_DIR=%~dp0

powershell -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $sc = $ws.CreateShortcut('%SHORTCUT_PATH%'); ^
   $sc.TargetPath = '%SCRIPT_DIR%run.bat'; ^
   $sc.WorkingDirectory = '%SCRIPT_DIR%'; ^
   $sc.WindowStyle = 7; ^
   $sc.Save()"

echo Startup shortcut created at:
echo   %SHORTCUT_PATH%
echo.
echo The overlay will now launch automatically at login.
pause
