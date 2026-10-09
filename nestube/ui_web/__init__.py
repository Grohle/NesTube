"""
nestube/ui_web — HTML user interface (nestube/web) hosted in a Qt WebEngine view.

The page talks to Python through a QWebChannel bridge. The application engine is
the regular Qt application (``NesTubeApp``) running headless: every action from
the web UI calls the same tab logic the classic interface uses (nesting
collisions, snapping, auto-nest, persistence, costs…), so behaviour is identical
and nothing is re-implemented in JavaScript.
"""
