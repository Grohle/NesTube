"""D1 investigation: place 3 cuts with different bevel combos, capture screenshots
per orientation, report contour_polygons_collide results.

Usage: QT_QPA_PLATFORM=offscreen python scripts/collision_test.py
"""
import sys
import os
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from nestify.bevel_geom import (
    BevelPiece, vertices_local, contour_polygons_collide, max_x_extent,
)

H = 100.0  # section height mm

pieces = [
    ("straight",  BevelPiece(L=500, alpha_L=0.0,  alpha_R=0.0)),
    ("45L",       BevelPiece(L=500, alpha_L=45.0, alpha_R=0.0)),
    ("45L_45R",   BevelPiece(L=500, alpha_L=45.0, alpha_R=45.0)),
]

orientations = [
    ("N",   False, False),
    ("FH",  True,  False),
    ("FV",  False, True),
    ("FHV", True,  True),
]

print("Contour polygon collision matrix (all pairs):")
for name_a, base_a in pieces:
    for name_b, base_b in pieces:
        if name_a >= name_b:
            continue
        x_a = 0.0
        # place b just after a (2mm gap)
        x_b = max_x_extent(base_a, H) + 2.0
        collide = contour_polygons_collide(x_a, base_a, x_b, base_b, H, kerf=2.0)
        print(f"  {name_a} vs {name_b} @ gap 2mm: {'COLLIDE' if collide else 'clear'}")

print("\nBounding boxes per piece per orientation:")
for name, base in pieces:
    for flip_name, fh, fv in orientations:
        piece = base.rotated_180() if fh else base
        piece = BevelPiece(piece.L, piece.alpha_L, piece.alpha_R, flipped_v=fv)
        verts = vertices_local(piece, H)
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        print(f"  {name}/{flip_name}: x=[{min(xs):.1f},{max(xs):.1f}] y=[{min(ys):.1f},{max(ys):.1f}]")

print("\nDone.")
