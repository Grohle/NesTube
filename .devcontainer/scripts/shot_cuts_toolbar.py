"""Screenshot: §21.6 — result_lbl beside preview_hdr, accent btn 30px."""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

mode = sys.argv[1] if len(sys.argv) > 1 else "dark"

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

from nestify.ui_qt.app import NestifyApp
window = NestifyApp()
window._set_theme(mode)
window.resize(1400, 800)
window.show()
app.processEvents()

# Navigate to Cuts tab (index 1)
window._tabs.setCurrentIndex(1)
app.processEvents()

pix = window.grab()
out = f"/tmp/cuts_toolbar_{mode}.png"
pix.save(out)
print(f"Saved {out}")
app.quit()
