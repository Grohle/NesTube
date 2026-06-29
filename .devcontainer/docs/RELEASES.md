# Nestify — Release lines

Nestify ships two product lines from this repository.

## 1.x — CustomTkinter (frozen alpha)

| Item | Value |
|------|--------|
| **Version** | `1.0.0-alpha.1` |
| **Tag** | [`v1.0.0-alpha.1`](https://github.com/Grohle/nestify/releases/tag/v1.0.0-alpha.1) |
| **Branch** | `legacy/v1.0-ctk` (frozen, no new features) |
| **UI** | CustomTkinter / Tkinter |
| **Entry point** | `python3 main.py` on that tag/branch |
| **Dependencies** | `requirements.txt` on `legacy/v1.0-ctk` (same as `requirements-legacy.txt` on `main`) |
| **Windows build** | `packaging/nestify.spec` on `legacy/v1.0-ctk` |
| **Downloads** | GitHub Release **v1.0.0-alpha.1** — `.exe`, `.zip`, `.tar.gz` |

This line is **archived for users who want the original alpha**. Bug fixes only if strictly necessary; all new work happens on 2.x (Qt).

### Install from source (1.x)

```bash
git clone https://github.com/Grohle/nestify.git
cd nestify
git checkout v1.0.0-alpha.1    # or: git checkout legacy/v1.0-ctk
pip install -r requirements.txt
python3 main.py
```

---

## 2.x — PySide6 / Qt (current)

| Item | Value |
|------|--------|
| **Version** | `2.0.0-alpha.4` |
| **Tag** | [`v2.0.0-alpha.4`](https://github.com/Grohle/nestify/releases/tag/v2.0.0-alpha.4) |
| **Branch** | `main` |
| **UI** | PySide6 (Qt) |
| **Entry point** | `python3 main.py` |
| **Dependencies** | `requirements.txt` |
| **Windows build** | `packaging/nestify.spec` on `main` |
| **Legacy CTk entry** | `python3 main_ctk.py` (dev only; use 1.x tag for supported CTk) |
| **Downloads** | GitHub Release **v2.0.0-alpha.3** — `.exe`, `.zip`, `.tar.gz` |

### Release history (2.x)

| Version | Highlights |
|---------|-----------|
| `2.0.0-alpha.4` | Bug fixes: installer always named after current version, FFD packing no longer drops full-length pieces when gap > 0, stock `display_name` no longer crashes on non-numeric IDs; 14 new packing regression tests |
| `2.0.0-alpha.3` | Bug fixes (stock IDs, cross-platform file open, kg/m leak, nesting status bar, FFD combo width), `btn_export_pdf` tooltip, built-in profile catalogue (22 structural sections), screenshot gallery in README, full workflow walkthrough in User Guide |
| `2.0.0-alpha.2` | SVG icon system, `Profiles & Tubes` tab rename, UI consistency pass (heights, borders, contrast), bevel/kerf snap fixes |
| `2.0.0-alpha.1` | Initial Qt alpha — Jobs Explorer, Cuts, Nesting, Costs & Weight, Stock tabs; multi-material contexts; dark/light themes |

### Install from source (2.x)

```bash
git clone https://github.com/Grohle/nestify.git
cd nestify
pip install -r requirements.txt
python3 main.py
```

---

## Rebuilding installers (maintainers)

| Line | Workflow | Trigger |
|------|----------|---------|
| 2.x Windows | `Build Windows release` | Push tag `v2.0.0-alpha.1` or workflow_dispatch |
| 1.x Windows | `Build Windows release (Legacy 1.x CTk)` | workflow_dispatch → `v1.0.0-alpha.1` |
| Linux `.tar.gz` | `Build Linux portable` | workflow_dispatch → choose `qt` or `legacy` + tag |

Job file formats (`.nestjob`) are compatible between lines where the same engine version applies; always recalculate nesting after opening a job in a new major UI line.
