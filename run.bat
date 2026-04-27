@echo off
:: Re-launch as Administrator so CPU temp sensors are accessible
net session >nul 2>&1
if errorlevel 1 (
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

:: Now running as admin — launch without console window
py -3.12 -c "import sys,os,subprocess; subprocess.Popen([os.path.join(os.path.dirname(sys.executable),'pythonw.exe'), r'%~dp0system_overlay.py'])"
