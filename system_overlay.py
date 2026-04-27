"""
System Monitor Overlay for Windows 11
- Transparent background, always on top, click-through gaps
- CPU temp via bundled LibreHardwareMonitorLib.dll (no separate app needed)
- Must be run as Administrator for CPU temp to work
- Right-click or system tray for color, snap, and exit controls
"""

import tkinter as tk
from tkinter import colorchooser
import threading
import time
import subprocess
import os
import sys
import ctypes
import traceback
import psutil
import pystray
from PIL import Image, ImageDraw


# ── Refresh intervals ──────────────────────────────────────────────────────────
FAST_MS  = 1000   # CPU%, RAM, HDD, network  (tkinter .after, every 1 s)
TEMP_SEC = 5      # CPU temp                 (background thread, every 5 s)

# ── Transparent key colour ─────────────────────────────────────────────────────
BG = '#010101'    # Any pixel this colour is invisible + click-through on Windows

# ── Default accent & derived dim ──────────────────────────────────────────────
DEFAULT_ACCENT = '#00D4FF'   # Cyan — user can change via right-click / tray

# ── Heat colours (fixed — convey meaning, not theme) ──────────────────────────
GOOD   = '#3fb950'
WARN   = '#d29922'
DANGER = '#f85149'

# ── Menu colours ──────────────────────────────────────────────────────────────
MENU_BG   = '#0D1117'
MENU_FG   = '#C9D1D9'
MENU_SEL  = '#00D4FF'
MENU_SELF = '#000000'

NET_MAX_BPS = 125_000_000   # 1 Gbps cap for bar scaling


# ── Colour helpers ────────────────────────────────────────────────────────────

def _dim(hex_color: str, factor: float = 0.50) -> str:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f'#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}'


def heat_colour(pct: float) -> str:
    if pct < 60: return GOOD
    if pct < 80: return WARN
    return DANGER


def fmt_bytes_per_sec(bps: float) -> str:
    if bps < 1_024:         return f'{bps:.0f} B/s'
    if bps < 1_048_576:     return f'{bps/1_024:.1f} KB/s'
    if bps < 1_073_741_824: return f'{bps/1_048_576:.1f} MB/s'
    return f'{bps/1_073_741_824:.2f} GB/s'


def fmt_gib(n: int) -> str:
    return f'{n/1_073_741_824:.1f}'


# ── LibreHardwareMonitor integration ─────────────────────────────────────────

_DLL_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'LibreHardwareMonitorLib.dll')
_lhm_ready  = False
_lhm_cpu_hw = []


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _init_lhm() -> bool:
    global _lhm_ready, _lhm_cpu_hw
    if not os.path.exists(_DLL_PATH) or not _is_admin():
        return False
    try:
        dll_dir = os.path.dirname(_DLL_PATH)
        if dll_dir not in sys.path:
            sys.path.insert(0, dll_dir)
        import clr
        clr.AddReference('LibreHardwareMonitorLib')
        from LibreHardwareMonitor.Hardware import Computer, HardwareType
        computer = Computer()
        computer.IsCpuEnabled = True
        computer.Open()
        _lhm_cpu_hw = [h for h in computer.Hardware if h.HardwareType == HardwareType.Cpu]
        _lhm_ready = True
        return True
    except Exception:
        return False


def _get_temp_lhm() -> float | None:
    try:
        from LibreHardwareMonitor.Hardware import SensorType
        temps = []
        for hw in _lhm_cpu_hw:
            hw.Update()
            for s in hw.Sensors:
                if s.SensorType == SensorType.Temperature and s.Value is not None:
                    if any(k in s.Name.lower() for k in ('package', 'cpu core', 'core', 'cpu')):
                        temps.append(float(s.Value))
        return max(temps) if temps else None
    except Exception:
        return None


def _get_temp_acpi() -> float | None:
    try:
        r = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command',
             '(Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace root/WMI '
             '-ErrorAction SilentlyContinue | Measure-Object CurrentTemperature -Maximum).Maximum'],
            capture_output=True, text=True, timeout=6, creationflags=0x08000000,
        )
        if r.stdout.strip():
            c = (float(r.stdout.strip()) / 10.0) - 273.15
            if 0 < c < 120:
                return c
    except Exception:
        pass
    return None


def get_cpu_temp() -> float | None:
    return _get_temp_lhm() if _lhm_ready else _get_temp_acpi()


# ── Tray icon ─────────────────────────────────────────────────────────────────

def _make_tray_icon(color: str = DEFAULT_ACCENT) -> Image.Image:
    size = 64
    img  = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy, r = size // 2, size // 2, size // 2 - 4
    cr, cg, cb = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    rgba = (cr, cg, cb, 255)
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=rgba, width=3)
    for i, wf in enumerate([0.55, 0.40, 0.65]):
        y = cy - 10 + i * 10
        bw = int(r * 2 * wf)
        x0 = cx - bw // 2
        draw.rectangle([x0, y-2, x0+bw, y+2], fill=rgba)
    return img


# ── MetricRow ─────────────────────────────────────────────────────────────────

class MetricRow:
    BAR_W = 70
    BAR_H = 5

    def __init__(self, parent: tk.Widget, label: str, row: int, accent: str):
        self._accent = accent

        self._name_lbl = tk.Label(
            parent, text=label, bg=BG, fg=_dim(accent),
            font=('Segoe UI', 8), width=12, anchor='w',
        )
        self._name_lbl.grid(row=row, column=0, padx=(10, 2), pady=5, sticky='w')

        self._val_var = tk.StringVar(value='…')
        self._val_lbl = tk.Label(
            parent, textvariable=self._val_var, bg=BG, fg=accent,
            font=('Segoe UI', 9, 'bold'), width=11, anchor='e',
        )
        self._val_lbl.grid(row=row, column=1, padx=(2, 6), pady=5)

        self._canvas = tk.Canvas(
            parent, width=self.BAR_W, height=self.BAR_H,
            bg=BG, highlightthickness=0,
        )
        self._canvas.grid(row=row, column=2, padx=(0, 10), pady=5)
        self._bar = self._canvas.create_rectangle(0, 0, 0, self.BAR_H, fill=accent, outline='')

        # Right-click passthrough to parent
        for w in (self._name_lbl, self._val_lbl, self._canvas):
            w.bind('<Button-3>', lambda e, p=parent: p.event_generate('<Button-3>', x=e.x_root, y=e.y_root, rootx=e.x_root, rooty=e.y_root))

    def update(self, text: str, pct: float | None = None, colour: str | None = None):
        self._val_var.set(text)
        clr = colour or self._accent
        self._val_lbl.config(fg=clr)
        if pct is not None:
            w = int(self.BAR_W * max(0.0, min(pct, 100.0)) / 100.0)
            self._canvas.coords(self._bar, 0, 0, w, self.BAR_H)
            self._canvas.itemconfig(self._bar, fill=clr)

    def set_label_color(self, accent: str):
        """Update the row label to a dimmed version of the new accent."""
        self._name_lbl.config(fg=_dim(accent))


# ── Main overlay ──────────────────────────────────────────────────────────────

class SystemOverlay:
    def __init__(self):
        self.root         = tk.Tk()
        self._dx          = self._dy = 0
        self._cpu_temp    = None
        self._tray        = None
        self._accent      = DEFAULT_ACCENT
        self._prev_net    = psutil.net_io_counters()
        self._prev_t      = time.monotonic()
        self._lhm_ok      = _init_lhm()
        self._admin       = _is_admin()
        self._dll_present = os.path.exists(_DLL_PATH)

        self._setup_window()
        self._build_ui()

        psutil.cpu_percent(interval=None)

        threading.Thread(target=self._temp_loop, daemon=True).start()
        threading.Thread(target=self._run_tray,  daemon=True).start()

        self._fast_update()
        self.root.mainloop()

    # ── Window ────────────────────────────────────────────────────────────────

    def _setup_window(self):
        r = self.root
        r.overrideredirect(True)
        r.attributes('-topmost', True)
        r.configure(bg=BG)
        r.attributes('-transparentcolor', BG)
        r.update_idletasks()
        sw = r.winfo_screenwidth()
        r.geometry(f'+{sw - 280}+20')

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._root_frame = tk.Frame(self.root, bg=BG)
        self._root_frame.pack(padx=2, pady=2)
        self._build_titlebar(self._root_frame)
        self._build_metrics(self._root_frame)
        self._bind_all(self._root_frame)

    def _build_titlebar(self, parent: tk.Widget):
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill='x', pady=(0, 4))

        admin_tag = '  ⚡' if self._admin else '  ⚠'
        self._title_lbl = tk.Label(
            bar,
            text=f'◈  SYS MONITOR{admin_tag}',
            bg=BG,
            fg=self._accent if self._admin else WARN,
            font=('Segoe UI', 9, 'bold'),
        )
        self._title_lbl.pack(side='left')

        self._close_btn = tk.Label(
            bar, text=' × ', bg=BG, fg=_dim(self._accent),
            font=('Segoe UI', 11, 'bold'), cursor='hand2',
        )
        self._close_btn.pack(side='right')
        self._close_btn.bind('<Button-1>', lambda _: self._exit())
        self._close_btn.bind('<Enter>',    lambda _: self._close_btn.config(fg=DANGER))
        self._close_btn.bind('<Leave>',    lambda _: self._close_btn.config(fg=_dim(self._accent)))

        for w in (bar, self._title_lbl):
            w.bind('<ButtonPress-1>', self._drag_start)
            w.bind('<B1-Motion>',     self._drag_motion)

    def _build_metrics(self, parent: tk.Widget):
        frame = tk.Frame(parent, bg=BG)
        frame.pack()

        specs = [
            ('cpu_temp', 'CPU Temp',   DANGER),
            ('cpu_use',  'CPU Usage',  self._accent),
            ('ram',      'RAM',        self._accent),
            ('hdd',      'HDD  (C:)',  self._accent),
            ('net_up',   '↑ Upload',   self._accent),
            ('net_down', '↓ Download', self._accent),
        ]
        self._rows: dict[str, MetricRow] = {}
        self._metrics_frame = frame
        for i, (key, label, colour) in enumerate(specs):
            self._rows[key] = MetricRow(frame, label, i, colour)

    def _bind_all(self, widget: tk.Widget):
        widget.bind('<Button-3>', self._show_menu)
        for child in widget.winfo_children():
            self._bind_all(child)

    # ── Drag ──────────────────────────────────────────────────────────────────

    def _drag_start(self, event: tk.Event):
        self._dx = event.x_root - self.root.winfo_x()
        self._dy = event.y_root - self.root.winfo_y()

    def _drag_motion(self, event: tk.Event):
        self.root.geometry(f'+{event.x_root - self._dx}+{event.y_root - self._dy}')

    # ── Colour ────────────────────────────────────────────────────────────────

    def _apply_color(self, color: str):
        self._accent = color
        self._title_lbl.config(fg=color if self._admin else WARN)
        self._close_btn.config(fg=_dim(color))
        for key, row in self._rows.items():
            if key != 'cpu_temp':   # cpu_temp always uses heat colours
                row._accent = color
                row._val_lbl.config(fg=color)
                row._bar and self._rows[key]._canvas.itemconfig(row._bar, fill=color)
            row.set_label_color(color)
        if self._tray:
            self._tray.icon = _make_tray_icon(color)

    def _pick_color(self):
        result = colorchooser.askcolor(color=self._accent, title='Choose Text Color', parent=self.root)
        if result and result[1]:
            self._apply_color(result[1])

    # ── Fast metrics ──────────────────────────────────────────────────────────

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
            self._rows['cpu_temp'].update(f'{val:.1f} °C', min(val, 100.0), heat_colour(min(val, 100.0)))
        elif not self._dll_present:
            self._rows['cpu_temp'].update('No DLL', 0, WARN)
        elif not self._admin:
            self._rows['cpu_temp'].update('Need admin', 0, WARN)
        else:
            self._rows['cpu_temp'].update('N/A', 0, _dim(self._accent))

    def _update_cpu_usage(self):
        pct = psutil.cpu_percent(interval=None)
        self._rows['cpu_use'].update(f'{pct:.1f} %', pct, heat_colour(pct))

    def _update_ram(self):
        vm = psutil.virtual_memory()
        self._rows['ram'].update(f'{fmt_gib(vm.used)}/{fmt_gib(vm.total)} GB', vm.percent, heat_colour(vm.percent))

    def _update_hdd(self):
        try:
            du = psutil.disk_usage('C:\\')
            self._rows['hdd'].update(f'{fmt_gib(du.used)}/{fmt_gib(du.total)} GB', du.percent, heat_colour(du.percent))
        except Exception:
            self._rows['hdd'].update('N/A', 0, _dim(self._accent))

    def _update_network(self):
        now, net = time.monotonic(), psutil.net_io_counters()
        elapsed  = now - self._prev_t
        if elapsed > 0:
            up   = (net.bytes_sent - self._prev_net.bytes_sent) / elapsed
            down = (net.bytes_recv - self._prev_net.bytes_recv) / elapsed
            self._rows['net_up'].update(fmt_bytes_per_sec(up),   min(up   / NET_MAX_BPS * 100, 100))
            self._rows['net_down'].update(fmt_bytes_per_sec(down), min(down / NET_MAX_BPS * 100, 100))
        self._prev_net, self._prev_t = net, now

    # ── Slow metric: CPU temp ─────────────────────────────────────────────────

    def _temp_loop(self):
        log = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'overlay_error.log')
        try:
            while True:
                self._cpu_temp = get_cpu_temp()
                time.sleep(TEMP_SEC)
        except Exception:
            with open(log, 'a') as f:
                f.write('\n--- _temp_loop ---\n')
                traceback.print_exc(file=f)

    # ── Right-click menu ──────────────────────────────────────────────────────

    def _show_menu(self, event: tk.Event):
        m = tk.Menu(self.root, tearoff=0,
                    bg=MENU_BG, fg=MENU_FG,
                    activebackground=self._accent,
                    activeforeground=MENU_SELF,
                    relief='flat', bd=1)
        m.add_command(label='  Color  ●  Cyan (default)', command=lambda: self._apply_color('#00D4FF'))
        m.add_command(label='  Color  ●  White',          command=lambda: self._apply_color('#FFFFFF'))
        m.add_command(label='  Color  ●  Soft Green',     command=lambda: self._apply_color('#00FF99'))
        m.add_command(label='  Color  ●  Warm Orange',    command=lambda: self._apply_color('#FF8C42'))
        m.add_command(label='  Color  ●  Purple',         command=lambda: self._apply_color('#CC88FF'))
        m.add_command(label='  Color  ●  Pink',           command=lambda: self._apply_color('#FF6EB4'))
        m.add_command(label='  Color  ⊕  Custom...',      command=self._pick_color)
        m.add_separator()
        m.add_command(label='  Snap  ↗  Top Right',    command=lambda: self._snap('tr'))
        m.add_command(label='  Snap  ↖  Top Left',     command=lambda: self._snap('tl'))
        m.add_command(label='  Snap  ↘  Bottom Right', command=lambda: self._snap('br'))
        m.add_command(label='  Snap  ↙  Bottom Left',  command=lambda: self._snap('bl'))
        m.add_separator()
        m.add_command(label='  ✕  Exit', command=self._exit)
        m.tk_popup(event.x_root, event.y_root)

    # ── Snap ──────────────────────────────────────────────────────────────────

    def _snap(self, corner: str):
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w,  h  = self.root.winfo_width(),       self.root.winfo_height()
        pad, taskbar = 20, 52
        x, y = {'tr': (sw-w-pad, pad), 'tl': (pad, pad),
                 'br': (sw-w-pad, sh-h-taskbar), 'bl': (pad, sh-h-taskbar)}[corner]
        self.root.geometry(f'+{x}+{y}')

    # ── System tray ───────────────────────────────────────────────────────────

    def _run_tray(self):
        log = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'overlay_error.log')
        try:
            def _set(c):
                return lambda icon, item: self.root.after(0, lambda: self._apply_color(c))
            def _snap_item(corner):
                return lambda icon, item: self.root.after(0, lambda: self._snap(corner))
            def _custom(icon, item):
                self.root.after(0, self._pick_color)
            def _exit_tray(icon, item):
                icon.stop()
                self.root.after(0, self.root.destroy)

            menu = pystray.Menu(
                pystray.MenuItem('Color', pystray.Menu(
                    pystray.MenuItem('Cyan (default)', _set('#00D4FF')),
                    pystray.MenuItem('White',          _set('#FFFFFF')),
                    pystray.MenuItem('Soft Green',     _set('#00FF99')),
                    pystray.MenuItem('Warm Orange',    _set('#FF8C42')),
                    pystray.MenuItem('Purple',         _set('#CC88FF')),
                    pystray.MenuItem('Pink',           _set('#FF6EB4')),
                    pystray.MenuItem('Custom...',      _custom),
                )),
                pystray.MenuItem('Snap to Corner', pystray.Menu(
                    pystray.MenuItem('Top Right',    _snap_item('tr')),
                    pystray.MenuItem('Top Left',     _snap_item('tl')),
                    pystray.MenuItem('Bottom Right', _snap_item('br')),
                    pystray.MenuItem('Bottom Left',  _snap_item('bl')),
                )),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('Exit', _exit_tray, default=True),
            )
            self._tray = pystray.Icon('system_overlay', _make_tray_icon(self._accent), 'System Monitor', menu)
            self._tray.run()
        except Exception:
            with open(log, 'a') as f:
                f.write('\n--- _run_tray ---\n')
                traceback.print_exc(file=f)

    # ── Exit ──────────────────────────────────────────────────────────────────

    def _exit(self):
        if self._tray:
            self._tray.stop()
        self.root.destroy()


if __name__ == '__main__':
    log = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'overlay_error.log')
    try:
        SystemOverlay()
    except Exception:
        with open(log, 'w') as f:
            traceback.print_exc(file=f)
        raise
