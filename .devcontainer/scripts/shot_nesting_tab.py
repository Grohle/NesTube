"""Screenshot: §21.7 nesting tab — SVG icons replacing emojis."""
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

# Navigate to Nesting tab (index 2)
window._tabs.setCurrentIndex(2)
app.processEvents()

pix = window.grab()
out = f"/tmp/nesting_tab_{mode}.png"
pix.save(out)
print(f"Saved {out}")
app.quit()
