@echo off
:: Use Python itself to locate pythonw.exe for the correct version, then launch
py -3.12 -c "import sys,os,subprocess; subprocess.Popen([os.path.join(os.path.dirname(sys.executable),'pythonw.exe'), r'%~dp0system_overlay.py'])"
