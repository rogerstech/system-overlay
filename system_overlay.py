"""
System Monitor Overlay for Windows 11
- CPU temp via bundled LibreHardwareMonitorLib.dll (no separate app needed)
- Falls back to ACPI WMI if DLL is not present
- Must be run as Administrator for CPU temp to work
- System tray icon for all controls
- Always on top, semi-transparent, draggable
"""

import tkinter as tk
import threading
import time
import subprocess
import os
import sys
import ctypes
import psutil
import pystray
from PIL import Image, ImageDraw


# ── Refresh intervals ──────────────────────────────────────────────────────────
FAST_MS   = 1000    # CPU%, RAM, HDD, network  (every 1 s via tkinter .after)
TEMP_SEC  = 5       # CPU temp                 (background thread, every 5 s)

# ── Colour palette ─────────────────────────────────────────────────────────────
C = {
    "bg":      "#0d1117",
    "card":    "#161b22",
    "border":  "#21262d",
    "header":  "#1a1f27",
    "text":    "#e6edf3",
    "dim":     "#7d8590",
    "good":    "#3fb950",
    "warn":    "#d29922",
    "danger":  "#f85149",
    "blue":    "#58a6ff",
    "purple":  "#bc8cff",
    "teal":    "#39d353",
    "cyan":    "#00D4FF",
}

NET_MAX_BPS = 125_000_000   # 1 Gbps cap for bar scaling


# ── Helpers ───────────────────────────────────────────────────────────────────

def heat_colour(pct: float) -> str:
    if pct < 60:  return C["good"]
    if pct < 80:  return C["warn"]
    return C["danger"]


def fmt_bytes_per_sec(bps: float) -> str:
    if bps < 1_024:         return f"{bps:.0f} B/s"
    if bps < 1_048_576:     return f"{bps / 1_024:.1f} KB/s"
    if bps < 1_073_741_824: return f"{bps / 1_048_576:.1f} MB/s"
    return f"{bps / 1_073_741_824:.2f} GB/s"


def fmt_gib(n_bytes: int) -> str:
    return f"{n_bytes / 1_073_741_824:.1f}"


# ── LibreHardwareMonitor integration ─────────────────────────────────────────

_DLL_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LibreHardwareMonitorLib.dll")
_lhm_ready   = False   # True once the .NET Computer object is open
_lhm_cpu_hw  = []      # list of CPU Hardware objects to update each tick


def _is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def _init_lhm() -> bool:
    """
    Load LibreHardwareMonitorLib.dll via pythonnet and open a Computer object
    with CPU monitoring enabled.  Returns True on success.
    Requires admin rights and the DLL present next to the script.
    """
    global _lhm_ready, _lhm_cpu_hw

    if not os.path.exists(_DLL_PATH):
        return False
    if not _is_admin():
        return False

    try:
        dll_dir = os.path.dirname(_DLL_PATH)
        if dll_dir not in sys.path:
            sys.path.insert(0, dll_dir)

        import clr  # pythonnet
        clr.AddReference("LibreHardwareMonitorLib")

        from LibreHardwareMonitor.Hardware import Computer, HardwareType

        computer = Computer()
        computer.IsCpuEnabled = True
        computer.Open()

        _lhm_cpu_hw = [h for h in computer.Hardware
                       if h.HardwareType == HardwareType.Cpu]
        _lhm_ready = True
        return True
    except Exception:
        return False


def _get_temp_lhm() -> float | None:
    """Poll the already-open LHM Computer object for the highest CPU temp."""
    try:
        from LibreHardwareMonitor.Hardware import SensorType
        temps = []
        for hw in _lhm_cpu_hw:
            hw.Update()
            for sensor in hw.Sensors:
                if sensor.SensorType == SensorType.Temperature and sensor.Value is not None:
                    name = sensor.Name.lower()
                    if any(k in name for k in ("package", "cpu core", "core", "cpu")):
                        temps.append(float(sensor.Value))
        return max(temps) if temps else None
    except Exception:
        return None


def _get_temp_acpi() -> float | None:
    """Fallback: native Windows ACPI thermal zone via PowerShell (no admin needed)."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-WmiObject MSAcpi_ThermalZoneTemperature "
             "-Namespace root/WMI -ErrorAction SilentlyContinue "
             "| Measure-Object CurrentTemperature -Maximum).Maximum"],
            capture_output=True, text=True, timeout=6,
            creationflags=0x08000000,
        )
        out = result.stdout.strip()
        if out:
            celsius = (float(out) / 10.0) - 273.15
            if 0 < celsius < 120:
                return celsius
    except Exception:
        pass
    return None


def get_cpu_temp() -> float | None:
    """Return CPU temp in °C using LHM if available, ACPI as fallback."""
    if _lhm_ready:
        return _get_temp_lhm()
    return _get_temp_acpi()


# ── Tray icon image ───────────────────────────────────────────────────────────

def _make_tray_icon() -> Image.Image:
    size  = 64
    img   = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(img)
    cx, cy, r = size // 2, size // 2, size // 2 - 4
    color = (0, 212, 255, 255)

    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=3)

    # Three horizontal bars (monitor / chart icon)
    for i, w_frac in enumerate([0.55, 0.40, 0.65]):
        y     = cy - 10 + i * 10
        bar_w = int(r * 2 * w_frac)
        x0    = cx - bar_w // 2
        draw.rectangle([x0, y - 2, x0 + bar_w, y + 2], fill=color)

    return img


# ── Metric row widget ─────────────────────────────────────────────────────────

class MetricRow:
    BAR_W = 70
    BAR_H = 5

    def __init__(self, parent: tk.Widget, label: str, row: int, accent: str):
        self._accent = accent

        tk.Label(
            parent, text=label,
            bg=C["card"], fg=C["dim"],
            font=("Segoe UI", 8), width=12, anchor="w",
        ).grid(row=row, column=0, padx=(10, 2), pady=4, sticky="w")

        self._val_var = tk.StringVar(value="…")
        self._val_lbl = tk.Label(
            parent, textvariable=self._val_var,
            bg=C["card"], fg=accent,
            font=("Segoe UI", 9, "bold"), width=11, anchor="e",
        )
        self._val_lbl.grid(row=row, column=1, padx=(2, 6), pady=4)

        self._canvas = tk.Canvas(
            parent, width=self.BAR_W, height=self.BAR_H,
            bg=C["border"], highlightthickness=0,
        )
        self._canvas.grid(row=row, column=2, padx=(0, 10), pady=4)
        self._bar = self._canvas.create_rectangle(
            0, 0, 0, self.BAR_H, fill=accent, outline="",
        )

    def update(self, text: str, pct: float | None = None, colour: str | None = None):
        self._val_var.set(text)
        clr = colour or self._accent
        self._val_lbl.config(fg=clr)
        if pct is not None:
            w = int(self.BAR_W * max(0.0, min(pct, 100.0)) / 100.0)
            self._canvas.coords(self._bar, 0, 0, w, self.BAR_H)
            self._canvas.itemconfig(self._bar, fill=clr)


# ── Main overlay ──────────────────────────────────────────────────────────────

class SystemOverlay:
    def __init__(self):
        self.root      = tk.Tk()
        self._dx       = self._dy = 0
        self._cpu_temp = None       # written by background thread, read by main thread
        self._tray     = None
        self._prev_net = psutil.net_io_counters()
        self._prev_t   = time.monotonic()

        # Attempt to initialise LibreHardwareMonitor (needs admin + DLL present)
        self._lhm_ok      = _init_lhm()
        self._admin       = _is_admin()
        self._dll_present = os.path.exists(_DLL_PATH)

        self._setup_window()
        self._build_ui()

        psutil.cpu_percent(interval=None)   # prime the non-blocking sampler

        threading.Thread(target=self._temp_loop, daemon=True).start()
        threading.Thread(target=self._run_tray,  daemon=True).start()

        self._fast_update()
        self.root.mainloop()

    # ── Window ────────────────────────────────────────────────────────────────

    def _setup_window(self):
        r = self.root
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        r.attributes("-alpha", 0.93)
        r.configure(bg=C["bg"])
        r.update_idletasks()
        sw = r.winfo_screenwidth()
        r.geometry(f"+{sw - 270}+20")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = tk.Frame(self.root, bg=C["border"], padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        card = tk.Frame(outer, bg=C["card"])
        card.pack(fill="both", expand=True)
        self._build_titlebar(card)
        self._build_metrics(card)

    def _build_titlebar(self, parent: tk.Widget):
        bar = tk.Frame(parent, bg=C["header"], height=28)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        bar.bind("<ButtonPress-1>", self._drag_start)
        bar.bind("<B1-Motion>",     self._drag_motion)

        admin_tag = "  ⚡" if self._admin else "  ⚠"
        tk.Label(
            bar, text=f"  ◈  SYS MONITOR{admin_tag}",
            bg=C["header"], fg=C["cyan"] if self._admin else C["warn"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=4)

        close = tk.Label(
            bar, text=" × ",
            bg=C["header"], fg=C["dim"],
            font=("Segoe UI", 11, "bold"), cursor="hand2",
        )
        close.pack(side="right", padx=4)
        close.bind("<Button-1>", lambda _: self._exit())
        close.bind("<Enter>",    lambda _: close.config(fg=C["danger"]))
        close.bind("<Leave>",    lambda _: close.config(fg=C["dim"]))

    def _build_metrics(self, parent: tk.Widget):
        frame = tk.Frame(parent, bg=C["card"])
        frame.pack(fill="both", expand=True, pady=(4, 6))

        specs = [
            ("cpu_temp", "CPU Temp",   C["danger"]),
            ("cpu_use",  "CPU Usage",  C["blue"]),
            ("ram",      "RAM",        C["purple"]),
            ("hdd",      "HDD  (C:)",  C["warn"]),
            ("net_up",   "↑ Upload",   C["teal"]),
            ("net_down", "↓ Download", C["good"]),
        ]
        self._rows: dict[str, MetricRow] = {}
        for i, (key, label, colour) in enumerate(specs):
            self._rows[key] = MetricRow(frame, label, i, colour)

    # ── Drag ──────────────────────────────────────────────────────────────────

    def _drag_start(self, event: tk.Event):
        self._dx = event.x_root - self.root.winfo_x()
        self._dy = event.y_root - self.root.winfo_y()

    def _drag_motion(self, event: tk.Event):
        self.root.geometry(f"+{event.x_root - self._dx}+{event.y_root - self._dy}")

    # ── Fast metrics (tkinter .after, every 1 s) ──────────────────────────────

    def _fast_update(self):
        self._update_cpu_temp_display()
        self._update_cpu_usage()
        self._update_ram()
        self._update_hdd()
        self._update_network()
        self.root.after(FAST_MS, self._fast_update)

    def _update_cpu_temp_display(self):
        val = self._cpu_temp
        if val is not None:
            pct = min(val, 100.0)
            self._rows["cpu_temp"].update(f"{val:.1f} °C", pct, heat_colour(pct))
        elif not self._dll_present:
            self._rows["cpu_temp"].update("No DLL", 0, C["warn"])
        elif not self._admin:
            self._rows["cpu_temp"].update("Need admin", 0, C["warn"])
        else:
            self._rows["cpu_temp"].update("N/A", 0, C["dim"])

    def _update_cpu_usage(self):
        pct = psutil.cpu_percent(interval=None)
        self._rows["cpu_use"].update(f"{pct:.1f} %", pct, heat_colour(pct))

    def _update_ram(self):
        vm   = psutil.virtual_memory()
        text = f"{fmt_gib(vm.used)}/{fmt_gib(vm.total)} GB"
        self._rows["ram"].update(text, vm.percent, heat_colour(vm.percent))

    def _update_hdd(self):
        try:
            du   = psutil.disk_usage("C:\\")
            text = f"{fmt_gib(du.used)}/{fmt_gib(du.total)} GB"
            self._rows["hdd"].update(text, du.percent, heat_colour(du.percent))
        except Exception:
            self._rows["hdd"].update("N/A", 0, C["dim"])

    def _update_network(self):
        now     = time.monotonic()
        net     = psutil.net_io_counters()
        elapsed = now - self._prev_t
        if elapsed > 0:
            up   = (net.bytes_sent - self._prev_net.bytes_sent) / elapsed
            down = (net.bytes_recv - self._prev_net.bytes_recv) / elapsed
            self._rows["net_up"].update(fmt_bytes_per_sec(up),   min(up   / NET_MAX_BPS * 100, 100))
            self._rows["net_down"].update(fmt_bytes_per_sec(down), min(down / NET_MAX_BPS * 100, 100))
        self._prev_net = net
        self._prev_t   = now

    # ── Slow metric: CPU temp (background thread) ─────────────────────────────

    def _temp_loop(self):
        import traceback, os
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "overlay_error.log")
        try:
            while True:
                self._cpu_temp = get_cpu_temp()
                time.sleep(TEMP_SEC)
        except Exception:
            with open(log_path, "a") as f:
                f.write("\n--- _temp_loop crash ---\n")
                traceback.print_exc(file=f)

    # ── Snap ──────────────────────────────────────────────────────────────────

    def _snap(self, corner: str):
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w,  h  = self.root.winfo_width(),       self.root.winfo_height()
        pad, taskbar = 20, 52
        positions = {
            "tr": (sw - w - pad,  pad),
            "tl": (pad,           pad),
            "br": (sw - w - pad,  sh - h - taskbar),
            "bl": (pad,           sh - h - taskbar),
        }
        x, y = positions[corner]
        self.root.geometry(f"+{x}+{y}")

    # ── System tray ───────────────────────────────────────────────────────────

    def _run_tray(self):
        import traceback, os
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "overlay_error.log")
        try:
            self._run_tray_inner()
        except Exception:
            with open(log_path, "a") as f:
                f.write("\n--- _run_tray crash ---\n")
                traceback.print_exc(file=f)

    def _run_tray_inner(self):
        def _snap_item(corner):
            return lambda icon, item: self.root.after(0, lambda: self._snap(corner))

        def _exit_tray(icon, item):
            icon.stop()
            self.root.after(0, self.root.destroy)

        menu = pystray.Menu(
            pystray.MenuItem("Snap to Corner", pystray.Menu(
                pystray.MenuItem("Top Right",    _snap_item("tr")),
                pystray.MenuItem("Top Left",     _snap_item("tl")),
                pystray.MenuItem("Bottom Right", _snap_item("br")),
                pystray.MenuItem("Bottom Left",  _snap_item("bl")),
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", _exit_tray, default=True),
        )

        self._tray = pystray.Icon(
            "system_overlay",
            _make_tray_icon(),
            "System Monitor",
            menu,
        )
        self._tray.run()

    # ── Exit ──────────────────────────────────────────────────────────────────

    def _exit(self):
        if self._tray:
            self._tray.stop()
        self.root.destroy()


if __name__ == "__main__":
    import traceback, os
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "overlay_error.log")
    try:
        SystemOverlay()
    except Exception:
        with open(log_path, "w") as f:
            traceback.print_exc(file=f)
        raise
