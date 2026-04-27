@echo off
:: Launch with pythonw.exe (Python 3.12) so no console window appears
for /f "delims=" %%i in ('py -3.12 -c "import sys,os; print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"') do set PYTHONW=%%i
start "" "%PYTHONW%" "%~dp0system_overlay.py"
