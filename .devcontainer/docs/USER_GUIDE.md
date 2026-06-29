# Nestify

> Applies to the **Qt** line (`2.0.0-alpha`). For installation see the
> [README](../README.md). This guide walks through the application module by
> module, with screenshots of every tab.

Nestify helps metal fabrication shops plan how to cut bars, tubes, and
structural profiles with as little waste as possible, and turn that plan into
a costed quote. Everything runs **offline** and your data stays on your
machine.

The window is organised as five tabs, left to right in a natural workflow:

| Tab | What you do there |
|-----|-------------------|
| **Jobs Explorer** | Browse, search and reopen saved jobs. |
| **Cuts** | Enter the bar parameters and the list of pieces to cut, then calculate. |
| **Nesting** | Fine-tune the bar layout visually (drag, snap, auto-nest, remnants). |
| **Costs & Weight** | Pick a profile, enter material/price data, get per-cut and total costs. |
| **Stock** | Keep an inventory of the bars you already have on hand. |

---

## Quick start

1. Open **Cuts**. Set **Bar length** (e.g. `6000` mm) and **Kerf** (blade width).
2. Add one row per piece: description, length and quantity. Add a mitre/bevel on
   either end if needed (this requires a **Bar height**).
3. Press **Calculate** — the preview on the right shows how many bars are needed
   and the utilisation percentage.
4. Open **Nesting** to review and adjust the layout, or run **Auto-nest**.
5. Open **Costs & Weight**, choose the profile and enter the material price to
   get the quote.
6. Export to **PDF / Excel / DOCX**, and **File → Save** to store the job.

---

## Walkthrough: Canopy Steel Frame (IPE 200, 24 pieces)

This end-to-end example shows a complete job from scratch.

### Step 0 — Launch: Jobs Explorer

![Jobs Explorer – empty](img/01_jobs_empty.png)

On first launch the Jobs Explorer is empty. Every job you save appears here as a
tile with its name, client and modification date.

---

### Step 1 — Enter bar parameters

![Cuts – bar parameters](img/02_cuts_params.png)

Open the **Cuts** tab and set:

- **Bar length**: `6000` mm (standard stock length)
- **Kerf**: `3` mm (blade width — subtracted between pieces)
- **Margin**: `50` mm (safety margin at the bar end)
- **Algorithm**: **FFD** (First-Fit Decreasing)

---

### Step 2 — Enter the cut list

![Cuts – cut list entered](img/03_cuts_list.png)

Add one row per piece type. For this canopy frame:

| Description | Length (mm) | Qty | Bevel |
|-------------|-------------|-----|-------|
| Viga principal | 3500 | 4 | 45° both ends |
| Correa | 1200 | 6 | — |
| Montante | 800 | 8 | — |
| Diagonal | 2800 | 2 | 45° compound |
| Placa base | 400 | 4 | — |

Each row shows a coloured swatch that carries through to the Nesting canvas.

---

### Step 3 — Calculate

![Cuts – FFD result](img/04_cuts_result.png)

Press **Calculate**. The engine reports:

> **7 bars · 82.9% efficiency** — 24 pieces placed, 17.1% offcuts.

The bar preview on the right shows each bar with piece colours and the remaining
offcut in grey.

---

### Step 4 — Nesting: initial state

![Nesting – initial state](img/05_nesting_initial.png)

Switch to **Nesting**. The status bar reads:
`By length · 7 bars · 0/24 placed · 0.0%`

Pieces are loaded from the cut list but not yet placed on the canvas.

---

### Step 5 — Add a bar manually

![Nesting – bar added](img/06_nesting_bar_added.png)

Click **Add bar** (+) to insert a spare bar. The status bar updates to show 8 bars.
You can drag pieces from the left panel onto any bar, snap them to neighbours,
and adjust mitre geometry visually.

---

### Step 6 — Auto-nest

![Nesting – after auto-nest](img/07_nesting_autonest.png)

Click **Auto-nest**. In simple mode (1D packer) all 24 pieces are placed
instantly across 7 bars at 82.9% efficiency — the extra bar is left empty and
can be removed. In advanced mode the 2D contour engine considers real bevel
shapes for tighter packing.

---

### Step 7 — Costs & Weight: select profile

![Costs – IPE 200 from catalog](img/09_costs_ipe200.png)

Open **Costs & Weight**. Click the **IPE 200** tile (loaded from the built-in
structural profile catalogue). The fields populate automatically:

- **kg/m**: 22.4 — from the catalogue entry
- **Specific weight** field disables — the catalogue value takes precedence

---

### Step 8 — Enter pricing and calculate

![Costs – calculation result](img/10_costs_result.png)

Fill in:

- **Price/kg**: `0.85` €
- **Profit margin**: `15` %
- **Straight cut time**: `3` min
- **Miter extra**: `35` %
- **Operator cost**: `30` €/h

Press **Calculate**. The results panel shows weight, area, material cost, labour
cost and line total for each cut type, plus a grand total.

> Example result: **800 EUR** total for 24 pieces of IPE 200.

---

### Step 9 — Profiles & Tubes library

![Profiles & Tubes](img/profiles.png)

The **Profiles & Tubes** tab (Settings) shows all built-in and custom sections.
Switch between **list view** and **grid view**, or search by name:

![Profiles – search IPE](img/13_profiles_search.png)

---

### Step 10 — Stock inventory

![Stock – filled](img/15_stock_filled.png)

Open **Stock** to record the bars you have on hand. Each entry stores profile,
material, length and quantity. Offcuts generated in Nesting can be sent here as
reusable remnants.

---

### Step 11 — Save and find the job

After saving (**File → Save**), return to the **Jobs Explorer**:

![Jobs Explorer – saved job](img/17_jobs_saved.png)

The job appears as a tile with its name, client data and modification date.
Double-click to reopen it — it restores exactly the tab and state you were on.

---

## Tab reference

### 1. Cuts

![Cuts tab](img/cuts.png)

The starting point for most jobs.

- **Header row** — material, quality and the magnifier button to search the
  materials database; plus order number, offer number and client.
- **Parameters row** — **Kerf (mm)**, **Margin (mm)**, **Bar length (mm)** and
  **Bar height (mm)**. Bar height is only required when a cut uses a mitre/bevel.
- **Calculation system** (combo on the right): **FFD**, **BFD** or **NFD**
  (see the table below). **Calculate** runs the packing engine.
- **Cuts list** (left) — one row per piece: description, length, quantity, and a
  bevel toggle + direction + angle for each end. The coloured swatch matches the
  piece colour used in the preview and the Nesting tab.
- **Nesting Preview** (right) — a schematic of each bar with the placed pieces,
  the per-bar utilisation, and the leftover (remnant) length.

| Code | Algorithm | Behaviour |
|------|-----------|-----------|
| **FFD** | First-Fit Decreasing | Sort pieces largest-first; pack into the first bar that fits. |
| **BFD** | Best-Fit Decreasing | Place each piece in the bar that leaves the least leftover. |
| **NFD** | Next-Fit Decreasing | Fill the current bar; open a new one when the next piece does not fit. |

Kerf and margin are applied between pieces, never subtracted from the bar ends,
so the lengths you type stay the true piece sizes.

**Toolbar buttons:**

| Button | Tooltip | Action |
|--------|---------|--------|
| XLSX Template | Download XLSX cut list template | Download a pre-formatted Excel file ready to fill in |
| Import XLSX | Import cut list from XLSX file | Load cuts from a filled-in template |
| Export PDF | Export cut list to PDF | Save the cut list as a PDF document |

---

### 2. Nesting

![Nesting tab](img/nesting.png)

An interactive layout editor for the calculated job.

- **Pieces remaining** (left) — every piece grouped by type, with how many are
  still unplaced. Click a piece to pick it up and place it on a bar.
- **Canvas** (centre) — each bar with its placed pieces, a "Bar N" heading and a
  legend underneath. Click a placed piece to select it; click it again to grab
  and move it. With **Snap** on it locks to the nearest valid position.
- **Toolbar** — Save / Clear, **Add bar**, **Remnants**, rotate/flip,
  **Simple ↔ Advanced** mode, **Use stock**, **Common cut**, **Snap**, the
  packing-system (simple) or time + strategy (advanced) controls, the zoom
  indicator, and **Auto-nest**.
- **Bar list** (right) — one entry per bar with its piece count; click to filter
  the canvas to a single bar.

**Simple mode** uses the instant 1D best-fit packer (FFD/BFD/NFD). **Advanced
mode** runs the 2D contour engine with a time budget and a strategy
(by length, NFP compaction, remnants, symmetry). Collisions always use the real
cut-edge contours, including mitred ends — never nominal lengths alone.

---

### 3. Costs & Weight

![Costs and Weight tab](img/costs.png)

Turn the cut list into weight and money.

- **Profile gallery** — Rectangular, Round, L-profile, U-profile, H-profile (I-beams),
  plus catalog profiles (IPE, HEA, UPN, tubes, angles…) and the **+** tile to draw
  your own custom profile. The selected profile's dimension fields appear below.
- **Catalog profiles** — selecting a catalog entry (e.g. IPE 200) auto-fills the
  kg/m field and disables the specific-weight input; switching back to a builtin
  re-enables it.
- **Pricing** — specific weight, price per kg / m² / m, price per bar and profit
  margin. **Calculate** fills the right-hand panel.
- **Results per cut** — for every line: weight, cross-section area, material and
  labour price per unit, price per metre, and the line total. The **Total** tab
  at the top aggregates the whole job.
- **Export Excel / PDF / DOCX** and **Print** produce a formal quote.

---

### 4. Stock

![Stock tab](img/stock.png)

A local inventory of the bars you already have.

- **Add to stock** creates a bar (profile, material, length, quantity);
  **Edit fields** and **Remove** manage the selection.
- **Filter row** — search by profile/material and constrain by minimum/maximum
  length and minimum remnant length.
- **Table** — availability dot, profile, material/quality, length, quantity, an
  availability toggle, and a remnant indicator. Offcuts generated in Nesting can
  be sent back here as reusable remnants.

---

### 5. Jobs Explorer

![Jobs Explorer tab](img/jobs.png)

Every job you save with **File → Save** is stored locally and listed here.

- Sort by **Name** (or other fields) and **Search** by text.
- Each tile shows the job name, client and last-modified date.
- Double-click a tile to reopen the job; it restores the tab you were last on.

---

## Menus at a glance

| Menu | Highlights |
|------|------------|
| **File** | Open / Save / Save as, Export PDF & Excel, Import Excel (template), save/load app config. |
| **View** | Theme (dark/light/system), font size, UI language, UI font, metric/imperial units, cut colours on/off. |
| **Settings** | Cost mode (shared / individual), materials library, profile types (add / edit), currency, PDF config (font, template, FastReport), optimization time levels, nesting layout, name assignment, reset. |
| **About** | Version, GitHub link, check for updates. |
| **Help** | Donate, report an issue. |

---

## Tips

- **Theme**: every screen works in dark and light (View → Theme).
- **Languages**: English and Spanish (View → Language).
- **Offline**: Nestify never connects to the internet on its own; menu links open
  in your browser only when you click them.
- **Units**: switch between metric and imperial at any time (View → Units).
- **Custom profiles**: draw your own cross-section in Settings → Profile types,
  or import an outline from a DXF file.
