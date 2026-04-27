#!/usr/bin/env python3
"""
System Monitor Overlay Widget for Windows 11
Displays CPU Temp, CPU Usage, RAM, HDD, and Network as a desktop overlay.

Requirements:
    pip install psutil wmi

CPU Temperature Notes:
    Requires OpenHardwareMonitor OR LibreHardwareMonitor running as Administrator.
    Download: https://openhardwaremonitor.org  or  https://github.com/LibreHardwareMonitor
    After launching one of those as admin, this widget will show live CPU temps.
"""

import tkinter as tk
import psutil
import time
import sys
import platform

# ─── Colour palette ───────────────────────────────────────────────────────────
C = {
    "bg":       "#0d1117",
    "card":     "#161b22",
    "border":   "#30363d",
    "header":   "#1f2937",
    "text":     "#e6edf3",
    "dim":      "#7d8590",
    "good":     "#3fb950",
    "warn":     "#d29922",
    "danger":   "#f85149",
    "blue":     "#58a6ff",
    "purple":   "#bc8cff",
    "teal":     "#39d353",
    "close_h":  "#f85149",
}

UPDATE_MS = 1000        # refresh interval in milliseconds
NET_MAX_BPS = 125_000_000  # 1 Gbps cap for bar scaling


# ─── CPU temperature (Windows only via OHM / LHM WMI) ────────────────────────

def _get_temp_from_namespace(namespace: str):
    import wmi  # noqa: import-outside-toplevel
    w = wmi.WMI(namespace=namespace)
    sensors = w.Sensor()
    cpu_temps = [
        s.Value for s in sensors
        if s.SensorType == "Temperature"
        and any(k in s.Name for k in ("CPU", "Core", "Package"))
    ]
    return max(cpu_temps) if cpu_temps else None


def get_cpu_temp():
    """Return (celsius: float | None, source: str)."""
    for ns in ("root\\OpenHardwareMonitor", "root\\LibreHardwareMonitor"):
        try:
            val = _get_temp_from_namespace(ns)
            if val is not None:
                return val, ns.split("\\")[-1]
        except Exception:
            continue
    return None, ""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def heat_colour(pct: float) -> str:
    if pct < 60:
        return C["good"]
    if pct < 80:
        return C["warn"]
    return C["danger"]


def fmt_bytes_per_sec(bps: float) -> str:
    if bps < 1_024:
        return f"{bps:.0f} B/s"
    if bps < 1_048_576:
        return f"{bps / 1_024:.1f} KB/s"
    if bps < 1_073_741_824:
        return f"{bps / 1_048_576:.1f} MB/s"
    return f"{bps / 1_073_741_824:.2f} GB/s"


def fmt_gib(n_bytes: int) -> str:
    return f"{n_bytes / 1_073_741_824:.1f}"


# ─── Reusable metric row ──────────────────────────────────────────────────────

class MetricRow:
    BAR_W = 72
    BAR_H = 5

    def __init__(self, parent: tk.Widget, label: str, row: int, accent: str):
        self._accent = accent

        tk.Label(
            parent, text=label, bg=C["card"], fg=C["dim"],
            font=("Segoe UI", 8), width=13, anchor="w",
        ).grid(row=row, column=0, padx=(10, 2), pady=3, sticky="w")

        self._val_var = tk.StringVar(value="…")
        self._val_lbl = tk.Label(
            parent, textvariable=self._val_var,
            bg=C["card"], fg=accent,
            font=("Segoe UI", 9, "bold"), width=10, anchor="e",
        )
        self._val_lbl.grid(row=row, column=1, padx=(2, 6), pady=3)

        self._canvas = tk.Canvas(
            parent, width=self.BAR_W, height=self.BAR_H,
            bg=C["border"], highlightthickness=0,
        )
        self._canvas.grid(row=row, column=2, padx=(0, 10), pady=3)
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


# ─── Main overlay ─────────────────────────────────────────────────────────────

class SystemOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self._prev_net = psutil.net_io_counters()
        self._prev_t = time.monotonic()
        self._temp_source: str = ""
        self._drag_ox = self._drag_oy = 0

        self._build_window()
        self._build_ui()
        # Kick off the first non-blocking CPU sample
        psutil.cpu_percent(interval=None)
        self._schedule_update()

    # ── Window setup ──────────────────────────────────────────────────────────

    def _build_window(self):
        r = self.root
        r.title("SysMonitor")
        r.overrideredirect(True)       # frameless
        r.attributes("-topmost", True) # always on top
        r.attributes("-alpha", 0.90)   # slight transparency
        r.configure(bg=C["bg"])

        if platform.system() == "Windows":
            r.attributes("-toolwindow", True)

        sw = r.winfo_screenwidth()
        r.geometry(f"+{sw - 260}+20")  # top-right corner

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # Thin outer border frame
        outer = tk.Frame(self.root, bg=C["border"], padx=1, pady=1)
        outer.pack(fill="both", expand=True)

        card = tk.Frame(outer, bg=C["card"])
        card.pack(fill="both", expand=True)

        self._build_titlebar(card)
        self._build_metrics(card)
        self._build_footer(card)

    def _build_titlebar(self, parent: tk.Widget):
        bar = tk.Frame(parent, bg=C["header"], height=26)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # Drag on the title bar
        bar.bind("<Button-1>", self._drag_start)
        bar.bind("<B1-Motion>", self._drag_motion)

        tk.Label(
            bar, text="  ⬡  SYS MONITOR", bg=C["header"], fg=C["blue"],
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=2)

        close = tk.Label(
            bar, text=" × ", bg=C["header"], fg=C["dim"],
            font=("Segoe UI", 11, "bold"), cursor="hand2",
        )
        close.pack(side="right", padx=2)
        close.bind("<Button-1>", lambda _e: self.root.destroy())
        close.bind("<Enter>", lambda _e: close.config(fg=C["close_h"]))
        close.bind("<Leave>", lambda _e: close.config(fg=C["dim"]))

    def _build_metrics(self, parent: tk.Widget):
        frame = tk.Frame(parent, bg=C["card"])
        frame.pack(fill="both", expand=True, pady=(6, 2))

        rows = [
            ("cpu_temp",  "CPU Temp",      C["danger"]),
            ("cpu_use",   "CPU Usage",     C["blue"]),
            ("ram",       "RAM",           C["purple"]),
            ("hdd",       "HDD  (C:)",     C["warn"]),
            ("net_up",    "↑ Upload",      C["teal"]),
            ("net_down",  "↓ Download",    C["good"]),
        ]
        self._rows: dict[str, MetricRow] = {}
        for i, (key, label, colour) in enumerate(rows):
            self._rows[key] = MetricRow(frame, label, i, colour)

            # Hairline separator (skip after last row)
            if i < len(rows) - 1:
                sep = tk.Frame(frame, bg=C["border"], height=1)
                sep.grid(row=i, column=3, padx=(0, 0))  # invisible spacer col

    def _build_footer(self, parent: tk.Widget):
        self._footer_var = tk.StringVar(value="")
        tk.Label(
            parent, textvariable=self._footer_var,
            bg=C["card"], fg=C["dim"],
            font=("Segoe UI", 7), wraplength=230, justify="left",
        ).pack(pady=(0, 5), padx=10, anchor="w")

    # ── Drag logic ────────────────────────────────────────────────────────────

    def _drag_start(self, event: tk.Event):
        self._drag_ox = event.x_root - self.root.winfo_x()
        self._drag_oy = event.y_root - self.root.winfo_y()

    def _drag_motion(self, event: tk.Event):
        self.root.geometry(f"+{event.x_root - self._drag_ox}+{event.y_root - self._drag_oy}")

    # ── Metrics update ────────────────────────────────────────────────────────

    def _schedule_update(self):
        self._update_metrics()
        self.root.after(UPDATE_MS, self._schedule_update)

    def _update_metrics(self):
        self._update_cpu_temp()
        self._update_cpu_usage()
        self._update_ram()
        self._update_hdd()
        self._update_network()

    def _update_cpu_temp(self):
        val, src = get_cpu_temp()
        if val is not None:
            pct = min(val, 100.0)
            clr = heat_colour(pct)
            self._rows["cpu_temp"].update(f"{val:.1f} °C", pct, clr)
            if not self._temp_source:
                self._temp_source = src
                self._footer_var.set(f"Temp source: {src}")
        else:
            self._rows["cpu_temp"].update("N/A", 0)
            if not self._temp_source:
                self._footer_var.set(
                    "CPU temp unavailable – run OpenHardwareMonitor or "
                    "LibreHardwareMonitor as Administrator."
                )

    def _update_cpu_usage(self):
        pct = psutil.cpu_percent(interval=None)
        clr = heat_colour(pct)
        self._rows["cpu_use"].update(f"{pct:.1f} %", pct, clr)

    def _update_ram(self):
        vm = psutil.virtual_memory()
        used_g = fmt_gib(vm.used)
        total_g = fmt_gib(vm.total)
        clr = heat_colour(vm.percent)
        self._rows["ram"].update(f"{used_g}/{total_g} GB", vm.percent, clr)

    def _update_hdd(self):
        try:
            du = psutil.disk_usage("C:\\")
            used_g = fmt_gib(du.used)
            total_g = fmt_gib(du.total)
            clr = heat_colour(du.percent)
            self._rows["hdd"].update(f"{used_g}/{total_g} GB", du.percent, clr)
        except Exception:
            self._rows["hdd"].update("N/A", 0)

    def _update_network(self):
        now = time.monotonic()
        net = psutil.net_io_counters()
        elapsed = now - self._prev_t

        if elapsed > 0:
            up_bps   = (net.bytes_sent - self._prev_net.bytes_sent) / elapsed
            down_bps = (net.bytes_recv - self._prev_net.bytes_recv) / elapsed
            up_pct   = min(up_bps   / NET_MAX_BPS * 100, 100)
            down_pct = min(down_bps / NET_MAX_BPS * 100, 100)
            self._rows["net_up"].update(fmt_bytes_per_sec(up_bps),   up_pct)
            self._rows["net_down"].update(fmt_bytes_per_sec(down_bps), down_pct)

        self._prev_net = net
        self._prev_t = now

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if platform.system() != "Windows":
        print("Warning: this widget is designed for Windows 11.")
        print("CPU temp and HDD drive-letter detection may not work on other platforms.")

    app = SystemOverlay()
    app.run()
