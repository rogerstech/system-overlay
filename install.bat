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

echo Python 3.12 found. Installing Python dependencies...
py -3.12 -m pip install --upgrade pip --quiet
py -3.12 -m pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install Python dependencies.
    pause
    exit /b 1
)

echo.
echo Downloading LibreHardwareMonitorLib.dll for CPU temperature reading...
powershell -NoProfile -Command ^
  "try { ^
     $r = Invoke-RestMethod 'https://api.github.com/repos/LibreHardwareMonitor/LibreHardwareMonitor/releases/latest'; ^
     $url = ($r.assets | Where-Object { $_.name -like '*.zip' } | Select-Object -First 1).browser_download_url; ^
     Invoke-WebRequest -Uri $url -OutFile 'lhm_temp.zip' -UseBasicParsing; ^
     Expand-Archive 'lhm_temp.zip' -DestinationPath 'lhm_temp' -Force; ^
     $dll = Get-ChildItem 'lhm_temp' -Recurse -Filter 'LibreHardwareMonitorLib.dll' | Select-Object -First 1; ^
     Copy-Item $dll.FullName '.' -Force; ^
     Remove-Item 'lhm_temp.zip','lhm_temp' -Recurse -Force; ^
     Write-Host 'DLL downloaded successfully.' ^
   } catch { ^
     Write-Host ('WARNING: Could not download DLL: ' + $_.Exception.Message) ^
   }"

echo.

:: Optional: create a desktop shortcut that runs as admin (needed for CPU temp)
set /p SHORTCUT="Create a desktop shortcut (runs as Administrator for CPU temp)? (y/n): "
if /i "%SHORTCUT%"=="y" (
    for /f "delims=" %%i in ('where pyw') do set "PYWEXE=%%i"
    set "SCRIPT_DIR=%~dp0"
    powershell -NoProfile -Command ^
      "$ws = New-Object -ComObject WScript.Shell; ^
       $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\System Monitor.lnk'); ^
       $sc.TargetPath = '%PYWEXE%'; ^
       $sc.Arguments = '-3.12 \"%SCRIPT_DIR%system_overlay.py\"'; ^
       $sc.WorkingDirectory = '%SCRIPT_DIR%'; ^
       $sc.WindowStyle = 7; ^
       $sc.Save(); ^
       $bytes = [System.IO.File]::ReadAllBytes($sc.FullName); ^
       $bytes[0x15] = $bytes[0x15] -bor 0x20; ^
       [System.IO.File]::WriteAllBytes($sc.FullName, $bytes); ^
       Write-Host 'Shortcut created (set to run as administrator).'"
)

echo.
echo Done! Run the overlay with: run.bat
echo For CPU temp, the overlay must run as Administrator.
echo The title bar shows a lightning bolt when admin rights are active.
echo.
pause
