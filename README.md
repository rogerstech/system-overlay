# Windows 11 System Monitor Overlay

A lightweight always-on-top system monitor for Windows 11. Shows CPU temp, CPU usage, RAM, HDD, and network speed as a floating panel — no external monitoring apps required.

---

## Features

- Always on top, semi-transparent panel
- Draggable title bar
- System tray icon with snap-to-corner and exit controls
- Close button on the panel itself
- Color-coded bars: green → yellow → red as usage climbs
- CPU temp via native Windows ACPI (no OpenHardwareMonitor needed)
- No console window when launched via `run.bat` or shortcut

### Metrics displayed

| Metric | Source |
|---|---|
| CPU Temp | LibreHardwareMonitorLib.dll (bundled, no app needed) |
| CPU Usage | psutil |
| RAM | psutil |
| HDD (C:) | psutil |
| Upload / Download | psutil |

> **CPU Temp note:** Uses the bundled `LibreHardwareMonitorLib.dll` — no separate app needed. The overlay must be **run as Administrator** to access hardware sensors. `install.bat` downloads the DLL automatically and creates an admin shortcut. The title bar shows ⚡ when running as admin, ⚠ when not.

---

## Prerequisites

### Python 3.12

> **Python 3.14+ has a known tkinter bug. Use Python 3.12.**

1. Download: https://www.python.org/downloads/release/python-3129/
   - Choose **Windows installer (64-bit)**
2. During install check:
   - **"Add Python 3.12 to PATH"**
   - **Customize installation → Optional Features → tcl/tk and IDLE**

Verify:
```
py -3.12 --version
```

---

## Installation

1. Download or clone this repository
2. Double-click **`install.bat`**
   - Installs `psutil`, `pystray`, and `Pillow` for Python 3.12
   - Optionally creates a desktop shortcut (no console window)

Or install manually:
```
py -3.12 -m pip install psutil pystray Pillow pythonnet
```

`install.bat` also automatically downloads `LibreHardwareMonitorLib.dll` from the LibreHardwareMonitor GitHub releases into the script folder.

---

## Running

**With console (for troubleshooting):**
```
py -3.12 system_overlay.py
```

**Without console window:**
```
run.bat
```

---

## Auto-start with Windows

Run **`startup.bat`** once to register the overlay in your Windows startup folder. It will launch automatically (no console) every time you log in.

---

## Usage

| Action | Result |
|---|---|
| Drag the title bar | Move the panel anywhere |
| Click **×** on the panel | Close the overlay |
| System tray icon → Snap to Corner | Snap to any screen corner |
| System tray icon → Exit | Close the overlay |
| Double-click tray icon | Close the overlay |

---

## Troubleshooting

**`py -3.12` gives errno 2**
Run `py --list` — if 3.12 is missing, re-run the Python installer.

**Missing module errors**
Run `py -3.12 -m pip install psutil pystray Pillow` and try again.

**CPU Temp shows "No DLL"**
`LibreHardwareMonitorLib.dll` is missing from the script folder. Re-run `install.bat` to download it automatically.

**CPU Temp shows "Need admin"**
The overlay is not running as Administrator. Use `run.bat` or the desktop shortcut created by `install.bat` — both are configured to request admin elevation automatically.

**CPU Temp shows N/A despite admin + DLL**
Your CPU may not be supported by the current version of LibreHardwareMonitor. Check the [LHM supported hardware list](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor).
