#!/usr/bin/env python3
"""Launch Nestify nesting tab to visually verify snap, spacing, and dark sidebar."""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk

from nestify.models import AppState, Corte
from nestify.theme import apply_theme_palette, SUCCESS_BG
from nestify.ui.tab_nesting import TabNesting


def main() -> None:
    apply_theme_palette("dark")
    ctk.set_appearance_mode("dark")

    root = ctk.CTk()
    root.title("Nestify — Nesting fixes demo")
    root.geometry("1100x720")

    state = AppState(longitud_barra=6000, perdida_corte=2, margen_tubo=0)
    state.cortes = [Corte("Corte 1", 500, 21)]

    tab = TabNesting(root, state)
    tab.pack(fill="both", expand=True)
    root.update_idletasks()

    # Add two bars via API (same as + Añadir barra)
    tab._bars = [[], []]
    tab._rebuild_pieces()
    tab._auto_nest()
    root.update_idletasks()

    print("SUCCESS_BG (dark):", SUCCESS_BG)
    print("Bars:", len(tab._bars))
    print("Snap enabled:", tab._snap_enabled)

    # Simulate picking remaining piece and snap preview near bar 2 gap
    if tab._pieces and tab._pieces[0].remaining > 0:
        tab._select_piece(tab._pieces[0])
        bar_top, bar_bot = tab._bar_pixel_range(1)
        cy = int((bar_top + bar_bot) / 2)
        snap = tab._find_best_snap(tab.MARGIN + 40, cy, 500)
        print("Snap preview near bar 2:", snap)
        tab._snap_preview = snap
        tab._schedule_draw()

    print("Demo running — inspect nesting UI (dark sidebar cards, snap preview on bar).")
    print("Close window to exit.")
    root.mainloop()


if __name__ == "__main__":
    main()
