"""
Full screenshot pass — all tabs in dark and light themes.
Each tab captured in a separate subprocess call to avoid cross-tab state issues.

Usage: QT_QPA_PLATFORM=offscreen python scripts/full_screenshot.py
"""
import os, sys, subprocess

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
repo = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(repo, "docs", "img")
os.makedirs(OUT, exist_ok=True)

TABS = {0: "jobs", 1: "cuts", 2: "nesting", 3: "costs", 4: "profiles", 5: "stock"}

CAPTURE_PY = """
import os, sys
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, {repo!r})
from PySide6.QtWidgets import QApplication
app = QApplication([])
from nestify.ui_qt.app import NestifyApp
w = NestifyApp()
w._set_theme({theme!r})
w.resize(1440, 860)
w.show()
app.processEvents()
app.processEvents()
w._tabs.setCurrentIndex({idx})
app.processEvents()
app.processEvents()
pix = w.grab()
out = {out!r}
ok = pix.save(out)
print('saved' if ok else 'SAVE_FAILED', out)
"""

for theme in ("dark", "light"):
    suffix = "" if theme == "dark" else "_light"
    print(f"\n=== Theme: {theme} ===")
    for idx, slug in TABS.items():
        out = os.path.join(OUT, f"{slug}{suffix}.png")
        code = CAPTURE_PY.format(repo=os.path.abspath(repo), theme=theme, idx=idx, out=out)
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            print(f"  -> {out}")
        else:
            print(f"  FAIL tab={idx} ({slug}) exit={result.returncode}")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-5:]:
                    print(f"     {line}")

print("\nDone.")
