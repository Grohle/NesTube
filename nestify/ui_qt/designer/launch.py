"""
nestify/ui_qt/designer/launch.py
Launches pyside6-designer with PYSIDE_DESIGNER_PLUGINS pre-configured.

Usage:
    python -m nestify.ui_qt.designer.launch [designer-args...]
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    plugin_dir = str(Path(__file__).parent.resolve())
    env = os.environ.copy()
    existing = env.get("PYSIDE_DESIGNER_PLUGINS", "")
    env["PYSIDE_DESIGNER_PLUGINS"] = (
        f"{plugin_dir}{os.pathsep}{existing}" if existing else plugin_dir
    )
    designer_args = sys.argv[1:]
    result = subprocess.run(["pyside6-designer", *designer_args], env=env)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
