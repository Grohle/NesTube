#!/usr/bin/env python3
"""Headless GUI smoke test: launch app, exercise Cuts sub-tabs, capture screenshots."""
from __future__ import annotations

import os
import sys
import time

# Project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk

from nestify.models import AppState, MaterialContext
from nestify.ui.tab_cortes import TabCortes


def main() -> int:
    out_dir = "/opt/cursor/artifacts"
    os.makedirs(out_dir, exist_ok=True)

    root = ctk.CTk()
    root.title("Nestify layout verify")
    root.geometry("1024x768")
    state = AppState()
    state.material_contexts.append(MaterialContext(name="Nesting 2", longitud_barra=6000))

    tab = TabCortes(root, state=state)
    tab.pack(fill="both", expand=True)
    root.update_idletasks()
    time.sleep(0.3)

    def rows_of(parent):
        r = {}
        for w in parent.winfo_children():
            info = w.grid_info()
            if info:
                r[int(info["row"])] = w
        return r

    rows = rows_of(tab)
    header = rows[1]
    ctrl = rows[2]
    content = rows[3]

    def metrics() -> tuple[int, int, int]:
        root.update_idletasks()
        top_h = ctrl.winfo_y() + ctrl.winfo_height() - rows[0].winfo_y()
        return header.winfo_y(), top_h, content.winfo_height()

    y0, top0, ch0 = metrics()
    shots = [("initial", y0, top0, ch0)]

    for i in range(5):
        tab._subtabs.set_active_index(i % 2, fire_callback=True)
        root.update_idletasks()
        time.sleep(0.15)
        y, top_h, ch = metrics()
        shots.append((f"switch_{i}", y, top_h, ch))

    disp = os.environ.get("DISPLAY", ":99")
    scrot_path = f"{out_dir}/cuts_layout_verify.png"
    os.system(f"DISPLAY={disp} scrot -o {scrot_path} 2>/dev/null")

    ys = [s[1] for s in shots]
    drift = max(ys) - min(ys)
    tab_h = tab.winfo_height()
    top_pct = 100 * shots[0][2] / max(tab_h, 1)

    print("=== Cuts layout verification ===")
    print(f"Tab height: {tab_h}px")
    print(f"Top section: {shots[0][2]}px ({top_pct:.1f}% of tab)")
    print(f"Content height: {shots[0][3]}px")
    print(f"Header Y drift after 5 switches: {drift}px")
    if scrot_path and os.path.isfile(scrot_path):
        print(f"Screenshot: {scrot_path}")

    ok = drift <= 2 and top_pct < 40 and shots[0][3] > tab_h * 0.45
    print("RESULT:", "PASS" if ok else "FAIL")
    root.destroy()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
