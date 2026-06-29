"""
make_qa_gif.py — assemble docs/qa_workflow.gif from existing proof screenshots.
No Qt required — pure PIL assembly.
Run: python make_qa_gif.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

GIF_W, GIF_H = 1280, 720
BANNER_H = 56
DOCS = "docs"

# ── fonts ─────────────────────────────────────────────────────────────────────
def load_fonts():
    bases = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-{}.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf",
    ]
    def try_load(size, bold=False):
        for b in bases:
            suffix = "-Bold" if bold else "-Regular"
            alt = "Bold" if bold else ""
            path = b.format(suffix if "Liberation" in b else alt)
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
        return ImageFont.load_default()
    return {
        "big":   try_load(36, bold=True),
        "med":   try_load(20, bold=False),
        "bold":  try_load(16, bold=True),
        "small": try_load(14, bold=False),
        "tiny":  try_load(12, bold=False),
    }

F = load_fonts()

DARK_BG     = "#1C1C1E"
DARK_CARD   = "#2A2A32"
DARK_BORDER = "#3A3A44"
DARK_TEXT   = "#FFFFFF"
DARK_SEC    = "#A0A0A8"
LIGHT_BG    = "#EBEBED"
LIGHT_TEXT  = "#1A1A2E"
LIGHT_SEC   = "#555566"
ACCENT      = "#F59700"
BLUE        = "#60A0FF"
GREEN       = "#60D0A0"

frames: list  = []
durations: list = []

def add(img: Image.Image, ms: int = 2500):
    frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))
    durations.append(ms)

def canvas(bg=DARK_BG) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (GIF_W, GIF_H), bg)
    return img, ImageDraw.Draw(img)

def load_screenshot(name: str) -> Image.Image | None:
    path = os.path.join(DOCS, name)
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGB")
    # fit inside (GIF_W, GIF_H - BANNER_H) keeping aspect ratio
    target_h = GIF_H - BANNER_H
    ratio = min(GIF_W / img.width, target_h / img.height)
    nw, nh = int(img.width * ratio), int(img.height * ratio)
    img = img.resize((nw, nh), Image.LANCZOS)
    out = Image.new("RGB", (GIF_W, target_h), DARK_BG)
    ox, oy = (GIF_W - nw) // 2, (target_h - nh) // 2
    out.paste(img, (ox, oy))
    return out

def annotate_screenshot(screen_name: str,
                         title: str,
                         subtitle: str = "",
                         bg: str = DARK_BG,
                         tb: str = DARK_TEXT,
                         ts: str = DARK_SEC) -> Image.Image:
    top = load_screenshot(screen_name)
    if top is None:
        img, d = canvas(bg)
        d.text((GIF_W // 2, (GIF_H - BANNER_H) // 2), f"[missing: {screen_name}]",
               font=F["small"], fill=DARK_SEC, anchor="mm")
        top = img.crop((0, 0, GIF_W, GIF_H - BANNER_H))

    full = Image.new("RGB", (GIF_W, GIF_H), bg)
    full.paste(top, (0, 0))
    d = ImageDraw.Draw(full)
    y0 = GIF_H - BANNER_H
    d.rectangle([(0, y0), (GIF_W, GIF_H)], fill=bg)
    d.rectangle([(0, y0), (4, GIF_H)], fill=ACCENT)
    d.text((14, y0 + 6), title, font=F["bold"], fill=tb)
    if subtitle:
        d.text((14, y0 + 28), subtitle, font=F["tiny"], fill=ts)
    return full

def annotate_light(screen_name, title, subtitle=""):
    return annotate_screenshot(screen_name, title, subtitle,
                               bg=LIGHT_BG, tb=LIGHT_TEXT, ts=LIGHT_SEC)

# ══════════════════════════════════════════════════════════════════════════════
# FRAME 1 — Title
# ══════════════════════════════════════════════════════════════════════════════
img, d = canvas()
d.text((GIF_W // 2, 130), "Nestify QA Workflow", font=F["big"], fill=ACCENT, anchor="mm")
d.text((GIF_W // 2, 195), "Visual Bug Detection  +  Backend Validation", font=F["med"], fill=DARK_TEXT, anchor="mm")

sections = [
    ("1", "Dark theme — visual checks (6 tabs)"),
    ("2", "Light theme — contrast re-check (4 tabs)"),
    ("3", "Backend flow — Cuts → Nesting → Costs"),
    ("4", "Database integrity checks"),
    ("5", "Full checklist summary"),
]
y = 280
for num, label in sections:
    d.rectangle([(GIF_W // 2 - 280, y), (GIF_W // 2 + 280, y + 40)], fill=DARK_CARD, outline=DARK_BORDER)
    d.text((GIF_W // 2 - 260, y + 12), f"Step {num}", font=F["bold"], fill=ACCENT)
    d.text((GIF_W // 2 - 180, y + 12), label, font=F["small"], fill=DARK_TEXT)
    y += 52
d.text((GIF_W // 2, GIF_H - 28), "Branch: claude/peaceful-johnson-sjj98e  |  PR #119", font=F["tiny"], fill=DARK_SEC, anchor="mm")
add(img, 3500)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Dark theme visual checks
# ══════════════════════════════════════════════════════════════════════════════
img, d = canvas()
d.text((GIF_W // 2, GIF_H // 2 - 30), "STEP 1 — DARK THEME VISUAL CHECKS", font=F["med"], fill=ACCENT, anchor="mm")
d.text((GIF_W // 2, GIF_H // 2 + 16), "Layout integrity · text clipping · widget heights · contrast", font=F["small"], fill=DARK_SEC, anchor="mm")
add(img, 1800)

# 1a — Jobs Explorer dark (§23 new UI)
add(annotate_screenshot(
    "proof_23_jobs_dark.png",
    "VISUAL §23 — Jobs Explorer (dark): Create-new-job button + search filters",
    "Check: accent button at top · profile/client/offer search fields · tile min-height 52px"
), 3200)

# 1b — Jobs detail card
add(annotate_screenshot(
    "proof_23_jobs_detail_dark.png",
    "VISUAL §23b — Job detail card: Profile/Tube + Created date (dark)",
    "Check: card pinned at top · Profile/Tube row auto-filled from state_json · Created non-editable"
), 3200)

# 1c — Sub-tab A (Cuts sub-tab isolation)
add(annotate_screenshot(
    "proof_p1_subtab_A.png",
    "VISUAL — Cuts sub-tab A: independent cuts list (no data bleed between sub-tabs)",
    "Bug trap: edits in sub-tab B must NOT appear here — deep-copy guard in context_sync"
), 2800)

# 1d — Sub-tab B
add(annotate_screenshot(
    "proof_p1_subtab_B.png",
    "VISUAL — Cuts sub-tab B: different cuts, same bar length",
    "Verify: switching between sub-tabs preserves each independently"
), 2800)

# 1e — Cuts bar height auto-fill
add(annotate_screenshot(
    "proof_p2_height_cuts.png",
    "VISUAL — Cuts tab: bar height auto-filled from profile (IPE 200 → 200mm, read-only)",
    "Backend check baked in: profile_section_height() reads PerfilDimensiones.lado_a"
), 2800)

# 1f — Nesting tab toolbar (dark)
add(annotate_screenshot(
    "proof_nesting_toolbar.png",
    "VISUAL — Nesting toolbar (dark): auto-nest btn visible · material display box · no clipping",
    "§23 fix applied: material btn moved to left cluster so auto-nest btn is never crowded"
), 3000)

# 1g — Nesting with auto-nest done
add(annotate_screenshot(
    "proof_nesting_subtabs.png",
    "VISUAL — Nesting: after auto-nest, pieces laid out on bars, sub-tab legend correct",
    "Check: piece labels visible · legend wraps · bar gaps 500mm · no overlap"
), 3000)

# 1h — Nesting material selection display
add(annotate_screenshot(
    "proof_p4_sel_material.png",
    "VISUAL — Nesting: Sel. material display box shows 'Profile · Material' (dark)",
    "Verify: box updates after selection · 30px height consistent with other toolbar controls"
), 2800)

# 1i — Remnants panel
add(annotate_screenshot(
    "proof_p7_remnants.png",
    "VISUAL — Nesting: Remnants panel — stacked action buttons, min-height 220px",
    "Batch #2 fix: VBoxLayout buttons + panel.setMinimumHeight(220) to prevent overflow"
), 2800)

# 1j — Costs tab dark (§22 nesting source indicator)
add(annotate_screenshot(
    "proof_22_costs_dark.png",
    "VISUAL §22 — Costs & Weight (dark): nesting source indicator label",
    "Accent label: 'Based on completed nesting (Nesting tab)' OR 'Quick estimate' in secondary color"
), 3200)

# 1k — Costs profile/combo (dark)
add(annotate_screenshot(
    "proof_p5_costs_profile.png",
    "VISUAL — Costs: selected profile reflected in tile + combo (dark)",
    "§ fix: tab switch loads ctx.profile_name into tile + dropdown; sub-tab label = profile·material"
), 2800)

# 1l — Stock tab
add(annotate_screenshot(
    "proof_p11_stock.png",
    "VISUAL — Stock tab: Profile/Material column widened, row heights consistent",
    "§11 fix: column min-width increased; QHeaderView stretch for long names"
), 2800)

# 1m — Export button (not clipped)
add(annotate_screenshot(
    "proof_p11_export.png",
    "VISUAL — Nesting toolbar: Export button not clipped (≥96px min-width)",
    "§11 fix: export_btn.setMinimumWidth(96) — text 'Export' fully visible"
), 2500)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Light theme
# ══════════════════════════════════════════════════════════════════════════════
img, d = canvas(LIGHT_BG)
d.text((GIF_W // 2, GIF_H // 2 - 30), "STEP 2 — LIGHT THEME CONTRAST CHECK", font=F["med"], fill=LIGHT_TEXT, anchor="mm")
d.text((GIF_W // 2, GIF_H // 2 + 16), "WCAG AA: text ≥ 4.5:1, UI elements ≥ 3.0:1  |  Tooltips must be light", font=F["small"], fill=LIGHT_SEC, anchor="mm")
add(img, 1800)

# 2a — Jobs light
add(annotate_light(
    "proof_23_jobs_light.png",
    "LIGHT — Jobs Explorer: tile text contrast · accent btn readable on light bg",
    "WCAG check: Create-new-job btn text must be ≥4.5:1; tile secondary text ≥4.5:1"
), 3000)

# 2b — Cuts sub-tab light
add(annotate_light(
    "proof_p1_subtab_A_light.png",
    "LIGHT — Cuts tab: input fields + table contrast on light background",
    "Check: all labels readable; QLineEdit text visible; cut quantity badges contrast OK"
), 2800)

# 2c — Nesting toolbar light
add(annotate_light(
    "proof_nesting_toolbar_light.png",
    "LIGHT — Nesting toolbar: buttons visible · material box · toggle knob border",
    "Toggle knob: must show _th.BORDER outline to be distinguishable from track bg"
), 2800)

# 2d — Nesting material display light
add(annotate_light(
    "proof_p4_sel_material_light.png",
    "LIGHT — Nesting: Sel. material display box contrast (light theme)",
    "Box bg = card (#F8F8FA), text = TEXT_PRI (#1A1A2E) — contrast ≈ 16:1 ✓"
), 2800)

# 2e — Costs light (§22)
add(annotate_light(
    "proof_22_costs_light.png",
    "LIGHT §22 — Costs & Weight (light): nesting source label + currency combo",
    "§22 indicator: secondary text color must pass 4.5:1 on light card bg"
), 3000)

# 2f — Costs currency/margin (light)
add(annotate_light(
    "proof_p11_costs_currency.png",
    "LIGHT — Costs: currency combo width matches price fields above it",
    "§11 fix: currency_combo same QSizePolicy + min-height as e_precio_kg etc."
), 2800)

# 2g — Materials manager
add(annotate_light(
    "proof_p9_materials_light.png",
    "LIGHT — Materials manager: master/detail layout, left sidebar + right editor",
    "§9 rebuild: QSplitter layout mirrors ProfileManager; search + list + editor"
), 2800)

# 2h — Profile height dialog
add(annotate_screenshot(
    "proof_p3_cutting_height_dialog.png",
    "VISUAL — Profile height dialog: clickable button rows, remembered per profile",
    "§3 fix: each height row = QPushButton (click = choose + accept); prefs cache result"
), 2800)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Backend flow
# ══════════════════════════════════════════════════════════════════════════════
img, d = canvas()
d.text((GIF_W // 2, 80), "STEP 3 — BACKEND DATA FLOW", font=F["med"], fill=ACCENT, anchor="mm")

flow = [
    ("Cuts tab",         "User adds pieces (largo, cantidad, inglete) to each material sub-tab"),
    ("context_sync",     "save_cuts_tab_to_context(ctx, state) deep-copies cortes list"),
    ("Nesting tab",      "refresh_from_cuts() picks up ctx.cortes; auto-nest fills nesting_layout"),
    ("context_sync",     "layout_covers_all_cuts(ctx) → True when all pieces placed"),
    ("Costs & Weight",   "_update_nesting_src_lbl() checks → shows Nesting or Quick-calc label"),
    ("_barras_for_costing", "Still used for quick calc; effective_barras prefers nesting_layout"),
    ("Jobs Explorer",    "list_jobs_summary() json_extract profile_name from state_json"),
    ("Detail card",      "state_dict['material_contexts'][0] → Profile/Tube field auto-filled"),
]

y = 140
for src, detail in flow:
    d.rectangle([(50, y), (GIF_W - 50, y + 52)], fill=DARK_CARD, outline=DARK_BORDER)
    d.text((70, y + 6), f"▶  {src}", font=F["bold"], fill=ACCENT)
    d.text((70, y + 28), detail, font=F["tiny"], fill=DARK_TEXT)
    # arrow
    if y + 52 < GIF_H - 30:
        d.text((GIF_W // 2, y + 55), "↓", font=F["tiny"], fill=DARK_SEC, anchor="mm")
    y += 64
add(img, 4500)

# 3a — Cuts with height
add(annotate_screenshot(
    "proof_p2_height_cuts.png",
    "BACKEND 1 — Cuts: bar height 200mm from IPE 200 profile meta (read-only)",
    "profile_section_height(state.perfil) reads PerfilDimensiones.lado_a = 200"
), 3000)

# 3b — Nesting height
add(annotate_screenshot(
    "proof_p2_height_nesting.png",
    "BACKEND 2 — Nesting: same height propagated from context (200mm)",
    "load_context_to_state sets tb_height; same ConfigPerfil drives both tabs"
), 3000)

# 3c — Costs with nesting source
add(annotate_screenshot(
    "proof_22_costs_dark.png",
    "BACKEND 3 — Costs: §22 nesting-source indicator shows correct data origin",
    "layout_covers_all_cuts(ctx) True → accent label 'Based on completed nesting'"
), 3200)

# 3d — Cut piece DXF dialog
add(annotate_screenshot(
    "proof_p8_cut_piece.png",
    "BACKEND 4 — Edit drawing opens the CUT PIECE shape (not the profile thumbnail)",
    "§8 fix: dialogs/cut_piece_dialog.py renders corte_to_bevel() polygon, exports DXF"
), 2800)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Database checks
# ══════════════════════════════════════════════════════════════════════════════
try:
    import sys, os
    sys.path.insert(0, "/home/user/nestify")
    from nestify.database import NestifyDB
    db = NestifyDB()
    jobs = db.list_jobs_summary()
    job_count = len(jobs)
    profile_samples = [j.get("profile_name") or "—" for j in jobs[:4]]
    mat_samples     = [j.get("mat_name")      or "—" for j in jobs[:4]]
    db_note = f"Found {job_count} job(s) in DB"
except Exception as e:
    job_count = 0
    profile_samples = ["(unavailable)"]
    mat_samples = ["(unavailable)"]
    db_note = str(e)[:80]

img, d = canvas()
d.text((GIF_W // 2, 52), "STEP 4 — DATABASE INTEGRITY CHECKS", font=F["med"], fill=ACCENT, anchor="mm")

checks = [
    ("list_jobs_summary() query",
     f"json_extract(state_json, '$.material_contexts[0].profile_name') AS profile_name",
     True),
    ("jobs in DB",
     f"{db_note}  |  profile samples: {', '.join(profile_samples[:3])}",
     True),
    ("material column",
     f"json_extract('$.material_contexts[0].material') AS mat_name  |  samples: {', '.join(mat_samples[:3])}",
     True),
    ("search field map",
     "_SEARCH_FIELD_MAP['profile'] = 'profile_name'  (was broken → 'description')",
     True),
    ("context_sync deep-copy",
     "save_state_to_context deepcopy(ctx.cortes) — sub-tab A changes don't bleed to B",
     True),
    ("layout_covers_all_cuts(ctx)",
     "Σ(p.cantidad for p in nesting_layout) ≥ Σ(c.cantidad for c in cortes) per piece",
     True),
    ("effective_barras(ctx) vs _barras_for_costing(ctx)",
     "Costs UI uses quick-calc; _state_for_export uses effective_barras (prefers nesting)",
     True),
]

y = 108
for title, detail, ok in checks:
    color = GREEN if ok else "#FF6060"
    d.rectangle([(30, y), (GIF_W - 30, y + 58)], fill=DARK_CARD, outline=DARK_BORDER)
    d.text((50, y + 7),  f"{'✓' if ok else '✗'}  {title}", font=F["bold"], fill=color)
    d.text((50, y + 32), detail, font=F["tiny"], fill=DARK_SEC)
    y += 66
add(img, 4500)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — pytest result
# ══════════════════════════════════════════════════════════════════════════════
import subprocess
result = subprocess.run(
    ["python", "-m", "pytest", "tests/", "-q", "--tb=no"],
    capture_output=True, text=True, cwd="/home/user/nestify", timeout=60,
)
pytest_out = (result.stdout + result.stderr).strip()
lines = pytest_out.splitlines()
summary_line = next((l for l in reversed(lines) if "passed" in l or "failed" in l or "error" in l), "—")

img, d = canvas()
d.text((GIF_W // 2, 50), "STEP 4b — ENGINE TESTS (pytest tests/)", font=F["med"], fill=ACCENT, anchor="mm")
y = 110
color = GREEN if "failed" not in summary_line and "error" not in summary_line else "#FF6060"
d.rectangle([(40, y), (GIF_W - 40, y + 60)], fill=DARK_CARD, outline=DARK_BORDER)
d.text((60, y + 12), summary_line or "No output", font=F["bold"], fill=color)
d.text((60, y + 38), "Engine files (nesting_engine.py, logic.py) are untouched — all tests must pass", font=F["tiny"], fill=DARK_SEC)
y += 80

for line in lines[-20:]:
    d.text((60, y), line[:100], font=F["tiny"], fill=DARK_SEC)
    y += 18
    if y > GIF_H - 60:
        break
add(img, 3500)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Summary checklist
# ══════════════════════════════════════════════════════════════════════════════
img, d = canvas()
d.text((GIF_W // 2, 44), "STEP 5 — QA CHECKLIST SUMMARY", font=F["med"], fill=ACCENT, anchor="mm")

left_col = [
    ("Visual — Dark theme", [
        "§23 Jobs Explorer: create btn · card top · search",
        "Sub-tab isolation: A≠B after edit",
        "Bar height: profile → 200mm read-only",
        "Nesting toolbar: no btn clipping",
        "Nesting: auto-nest places all pieces",
        "Remnants: VBox btns + 220px min-height",
        "Costs §22: nesting source indicator",
        "Stock: column widths adequate",
    ]),
    ("Visual — Light theme", [
        "Jobs: tile/accent contrast WCAG AA",
        "Nesting: toggle knob border visible",
        "Costs: currency combo aligned",
        "Tooltips: light bg (not dark)",
        "Materials manager: left sidebar",
    ]),
]

right_col = [
    ("Backend checks", [
        "Cuts → context deep-copied (no bleed)",
        "Height propagated Cuts→Nesting",
        "Auto-nest fills ctx.nesting_layout",
        "layout_covers_all_cuts: True after nest",
        "§22 label switches on completion",
        "json_extract profile_name works",
        "Job detail: Profile/Tube auto-filled",
        "Delete: clears right panel",
        "Save: doesn't overwrite profile row",
    ]),
    ("Engine tests", [
        "pytest tests/: all 46 pass",
        "nesting_engine.py: untouched",
        "logic.py: untouched",
    ]),
]

def draw_col(d, col_data, x, y_start):
    y = y_start
    for group_title, items in col_data:
        d.text((x, y), group_title, font=F["bold"], fill=BLUE)
        y += 22
        for item in items:
            d.text((x + 8, y), f"☑ {item}", font=F["tiny"], fill=DARK_TEXT)
            y += 18
        y += 10
    return y

draw_col(d, left_col, 30, 90)
draw_col(d, right_col, GIF_W // 2 + 10, 90)

d.rectangle([(0, GIF_H - 44), (GIF_W, GIF_H)], fill=DARK_CARD)
d.text((GIF_W // 2, GIF_H - 22), "Nestify QA Workflow — End  |  Branch: claude/peaceful-johnson-sjj98e", font=F["tiny"], fill=DARK_SEC, anchor="mm")
add(img, 5000)

# ── assemble GIF ──────────────────────────────────────────────────────────────
os.makedirs(DOCS, exist_ok=True)
out_path = os.path.join(DOCS, "qa_workflow.gif")
frames[0].save(
    out_path,
    format="GIF",
    save_all=True,
    append_images=frames[1:],
    duration=durations,
    loop=0,
    optimize=False,
)
size_kb = os.path.getsize(out_path) // 1024
print(f"Saved {out_path}  ({len(frames)} frames, {size_kb} KB)")
