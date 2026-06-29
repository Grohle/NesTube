#!/usr/bin/env python3
"""
Compile all .ui files in nestify/ui_qt/forms/ to Python modules.

Usage:
    python -m nestify.ui_qt.compile_forms

Each  forms/<name>.ui  →  forms/ui_<name>.py
"""
import subprocess
import sys
from pathlib import Path

FORMS_DIR = Path(__file__).parent / "forms"


def compile_all() -> int:
    ui_files = sorted(FORMS_DIR.glob("*.ui"))
    if not ui_files:
        print("No .ui files found in", FORMS_DIR)
        return 0

    errors = 0
    for ui in ui_files:
        out = ui.with_name(f"ui_{ui.stem}.py")
        cmd = ["pyside6-uic", str(ui), "-o", str(out)]
        print(f"  {ui.name}  →  {out.name}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr.strip()}", file=sys.stderr)
            errors += 1
    print(f"\nCompiled {len(ui_files)} file(s), {errors} error(s).")
    return errors


if __name__ == "__main__":
    sys.exit(compile_all())
