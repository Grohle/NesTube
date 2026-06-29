"""Screenshot all tabs in both themes."""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

mode = sys.argv[1] if len(sys.argv) > 1 else "dark"
tab_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 1

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

from nestify.ui_qt.app import NestifyApp
window = NestifyApp()
window._set_theme(mode)
window.resize(1400, 800)
window.show()
app.processEvents()

window._tabs.setCurrentIndex(tab_idx)
app.processEvents()

tab_names = {0: "jobs", 1: "cuts", 2: "nesting", 3: "costs", 4: "stock", 5: "profiles"}
name = tab_names.get(tab_idx, f"tab{tab_idx}")
pix = window.grab()
out = f"/tmp/tab_{name}_{mode}.png"
pix.save(out)
print(f"Saved {out}")
app.quit()
