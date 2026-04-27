"""Generates instructinosToInstall.pdf in the same directory."""

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUTPUT = "/home/arogers/system-overlay/instructinosToInstall.pdf"

# ── Colour palette ────────────────────────────────────────────────────────────
DARK_BG    = colors.HexColor("#0d1117")
CARD_BG    = colors.HexColor("#161b22")
BORDER     = colors.HexColor("#30363d")
BLUE       = colors.HexColor("#58a6ff")
GREEN      = colors.HexColor("#3fb950")
YELLOW     = colors.HexColor("#d29922")
RED        = colors.HexColor("#f85149")
TEXT       = colors.HexColor("#e6edf3")
DIM        = colors.HexColor("#7d8590")
WHITE      = colors.white

def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=LETTER,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.85 * inch,
    )

    base = getSampleStyleSheet()

    # ── Custom styles ─────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "Title", parent=base["Title"],
        fontSize=22, textColor=BLUE,
        fontName="Helvetica-Bold",
        spaceAfter=4, alignment=TA_LEFT,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=base["Normal"],
        fontSize=11, textColor=DIM,
        fontName="Helvetica",
        spaceAfter=16,
    )
    h2_style = ParagraphStyle(
        "H2", parent=base["Heading2"],
        fontSize=13, textColor=BLUE,
        fontName="Helvetica-Bold",
        spaceBefore=18, spaceAfter=6,
        borderPad=0,
    )
    h3_style = ParagraphStyle(
        "H3", parent=base["Heading3"],
        fontSize=11, textColor=TEXT,
        fontName="Helvetica-Bold",
        spaceBefore=10, spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body", parent=base["Normal"],
        fontSize=10, textColor=colors.black,
        fontName="Helvetica",
        spaceAfter=4, leading=15,
    )
    note_style = ParagraphStyle(
        "Note", parent=base["Normal"],
        fontSize=9, textColor=colors.HexColor("#555555"),
        fontName="Helvetica-Oblique",
        spaceAfter=4, leading=13,
        leftIndent=12,
    )
    code_style = ParagraphStyle(
        "Code", parent=base["Code"],
        fontSize=9, textColor=colors.HexColor("#2d6a4f"),
        fontName="Courier",
        backColor=colors.HexColor("#f0faf4"),
        borderColor=colors.HexColor("#b7e4c7"),
        borderWidth=0.5, borderPad=5,
        spaceAfter=6, leading=14,
    )
    bullet_style = ParagraphStyle(
        "Bullet", parent=base["Normal"],
        fontSize=10, textColor=colors.black,
        fontName="Helvetica",
        leftIndent=20, spaceAfter=3, leading=15,
        bulletIndent=8,
    )

    # ── Table helpers ─────────────────────────────────────────────────────────
    def kv_table(rows, col_widths=(1.8 * inch, 4.0 * inch)):
        data = []
        for label, value in rows:
            data.append([
                Paragraph(f"<b>{label}</b>", body_style),
                Paragraph(value, body_style),
            ])
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
            ("BACKGROUND",  (1, 0), (1, -1), colors.white),
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("VALIGN",      (0, 0), (-1, -1), "TOP"),
            ("PADDING",     (0, 0), (-1, -1), 6),
        ]))
        return t

    def step_table(steps):
        data = []
        for i, (step, detail) in enumerate(steps, 1):
            data.append([
                Paragraph(f"<b>{i}</b>", ParagraphStyle(
                    "StepNum", parent=body_style,
                    fontSize=12, textColor=BLUE, alignment=TA_CENTER,
                )),
                Paragraph(f"<b>{step}</b>", body_style),
                Paragraph(detail, body_style),
            ])
        t = Table(data, colWidths=[0.35 * inch, 1.6 * inch, 3.85 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (0, -1), colors.HexColor("#e8f4fd")),
            ("BACKGROUND",  (1, 0), (-1, -1), colors.white),
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("VALIGN",      (0, 0), (-1, -1), "TOP"),
            ("PADDING",     (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1),
             [colors.white, colors.HexColor("#fafafa")]),
        ]))
        return t

    # ── Content ───────────────────────────────────────────────────────────────
    story = []

    # Title block
    story.append(Paragraph("System Monitor Overlay", title_style))
    story.append(Paragraph("Installation &amp; Setup Guide — Windows 11", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=14))

    # Overview
    story.append(Paragraph("Overview", h2_style))
    story.append(Paragraph(
        "This widget is a lightweight, always-on-top Python overlay that displays "
        "live system metrics on your Windows 11 desktop. It requires no installation "
        "beyond Python and two small packages.",
        body_style,
    ))
    story.append(Spacer(1, 8))

    story.append(kv_table([
        ("CPU Temp",     "Maximum core temperature (°C), colour-coded green / yellow / red"),
        ("CPU Usage",    "Aggregate usage across all cores (%)"),
        ("RAM",          "Used vs. total physical memory (GB)"),
        ("HDD (C:)",     "Used vs. total capacity on the C: drive (GB)"),
        ("↑ Upload",     "Live outbound network throughput (B/s – GB/s)"),
        ("↓ Download",   "Live inbound network throughput (B/s – GB/s)"),
    ]))

    # Prerequisites
    story.append(Paragraph("Prerequisites", h2_style))
    story.append(Paragraph(
        "Before running the widget you need the following software installed on "
        "your Windows 11 machine:", body_style,
    ))
    story.append(Spacer(1, 6))

    story.append(kv_table([
        ("Python 3.10+",
         'Download from <a href="https://python.org"><u>python.org</u></a>. '
         'During install, tick <b>"Add Python to PATH"</b>.'),
        ("psutil",  "Reads CPU, RAM, disk, and network stats. Installed by install.bat."),
        ("wmi",     "Windows Management Instrumentation bridge. Installed by install.bat."),
    ]))

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "For CPU temperature readings you also need one of the following "
        "sensor tools running as Administrator (see Step 5 below):",
        body_style,
    ))
    story.append(Paragraph(
        "• <b>OpenHardwareMonitor</b> — openhardwaremonitor.org",
        bullet_style,
    ))
    story.append(Paragraph(
        "• <b>LibreHardwareMonitor</b> — github.com/LibreHardwareMonitor",
        bullet_style,
    ))

    # Files included
    story.append(Paragraph("Files Included", h2_style))
    story.append(kv_table([
        ("system_overlay.py", "Main widget application — the Python script that draws the overlay."),
        ("requirements.txt",  "Lists Python package dependencies (psutil, wmi)."),
        ("install.bat",       "One-time setup: installs dependencies and optionally creates a desktop shortcut."),
        ("run.bat",           "Launches the widget without showing a console window. Double-click to start."),
        ("startup.bat",       "Registers the widget to launch automatically every time you log into Windows."),
    ], col_widths=(1.9 * inch, 3.9 * inch)))

    # Installation steps
    story.append(Paragraph("Installation Steps", h2_style))
    story.append(step_table([
        ("Copy the folder",
         "Transfer the entire <b>system-overlay</b> folder to your Windows 11 PC "
         "(USB drive, network share, or cloud storage)."),
        ("Install Python",
         'If Python is not already installed, download the latest 3.x release from '
         '<b>python.org</b> and run the installer. <i>Check "Add Python to PATH" '
         'before clicking Install.</i>'),
        ("Run install.bat",
         "Double-click <b>install.bat</b>. It will install psutil and wmi via pip. "
         "When prompted, you can choose to create a Desktop shortcut."),
        ("Launch the widget",
         "Double-click <b>run.bat</b>. The overlay appears in the top-right corner "
         "of your screen. Drag the title bar to reposition it. Click <b>×</b> to close."),
        ("Enable CPU temp (optional)",
         "Download <b>OpenHardwareMonitor</b> or <b>LibreHardwareMonitor</b>, "
         "right-click the .exe and choose <i>Run as Administrator</i>. "
         "Leave it running — the widget will detect it and show live temperatures."),
        ("Auto-start at login (optional)",
         "Run <b>startup.bat</b> once. It places a shortcut in your Windows Startup "
         "folder so the overlay launches automatically every time you sign in."),
    ]))

    # Usage tips
    story.append(Paragraph("Usage Tips", h2_style))

    tips = [
        ("Move the widget",
         "Click and drag anywhere on the dark title bar."),
        ("Close the widget",
         'Click the <b>×</b> button in the top-right of the overlay. '
         'To reopen it, double-click run.bat.'),
        ("Change transparency",
         "Open system_overlay.py in a text editor and change the <b>-alpha</b> "
         "value on the line <code>r.attributes(\"-alpha\", 0.90)</code>. "
         "0.0 = fully transparent, 1.0 = fully opaque."),
        ("Change position",
         "Edit the <b>geometry</b> line near the bottom of setup_window() to "
         "pin the overlay to a different corner, e.g. <code>\"+10+20\"</code> "
         "for top-left."),
        ("Monitor a different drive",
         'Change <code>psutil.disk_usage("C:\\\\")</code> to any drive letter, '
         'e.g. <code>"D:\\\\"</code>.'),
        ("Update speed",
         "The default refresh rate is 1 second. Change <b>UPDATE_MS = 1000</b> "
         "at the top of the script (value is in milliseconds)."),
    ]

    t_data = [[
        Paragraph(f"<b>{tip}</b>", body_style),
        Paragraph(detail, body_style),
    ] for tip, detail in tips]

    tips_table = Table(t_data, colWidths=[1.8 * inch, 4.0 * inch])
    tips_table.setStyle(TableStyle([
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("PADDING",    (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
         [colors.white, colors.HexColor("#fafafa")]),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
    ]))
    story.append(tips_table)

    # Troubleshooting
    story.append(Paragraph("Troubleshooting", h2_style))

    issues = [
        ('"python" is not recognized',
         "Python is not on your PATH. Re-run the Python installer and tick "
         '"Add Python to PATH", or manually add Python to your system environment variables.'),
        ("CPU Temp shows N/A",
         "OpenHardwareMonitor or LibreHardwareMonitor is not running, or was not "
         "started as Administrator. Ensure the sensor tool is open before launching the widget."),
        ("Widget not visible",
         "It may be behind a full-screen application. Press Win + D to show the "
         "desktop, then look for the overlay in the top-right corner."),
        ("HDD shows N/A",
         'The C: drive was not found (e.g. on a non-standard partition layout). '
         'Edit system_overlay.py and change "C:\\\\" to the correct drive letter.'),
        ("High CPU usage by the widget",
         "Reduce refresh frequency by increasing UPDATE_MS (e.g. to 2000 for 2-second updates)."),
    ]

    issue_data = [[
        Paragraph(f"<b>{issue}</b>", body_style),
        Paragraph(fix, body_style),
    ] for issue, fix in issues]

    issue_table = Table(issue_data, colWidths=[2.0 * inch, 3.8 * inch])
    issue_table.setStyle(TableStyle([
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("PADDING",    (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
         [colors.white, colors.HexColor("#fafafa")]),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fff8f0")),
    ]))
    story.append(issue_table)

    # Footer note
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=DIM, spaceAfter=8))
    story.append(Paragraph(
        "The widget uses only standard Windows APIs and open-source Python libraries. "
        "No data is sent off-device. CPU temperature reading relies on a third-party "
        "hardware monitor because Windows does not expose raw sensor data natively.",
        note_style,
    ))

    doc.build(story)
    print(f"PDF saved to: {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
