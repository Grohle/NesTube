# Nestify — Development Guidelines

# MANDATORY AND PERMANENT BEHAVIORAL RULES

## 1. RADICAL HONESTY AND VISUAL CAPABILITIES
* You are strictly FORBIDDEN from automatically claiming "it's fixed" or "it works perfectly" unless you have performed a rigorous, end-to-end logical and visual verification of the state.
* The user prefers the harsh, raw reality regarding your limitations over a false confirmation or deception. If you are not entirely sure that a state is successfully preserved between components, you must explicitly admit it.
* When analyzing or providing a GIF or image (such as checking tab consistency), you are not just generating it for the user to see. You have a strict OBLIGATION to critically self-analyze that image/GIF frame-by-frame in your response, transparently pointing out any UI desynchronization, layout shifts, or glitches that still persist.
  
## 2. STRICT SCREENSHOT AND VISUAL VERIFICATION PROTOCOL (100% MANDATORY)
* **NON-NEGOTIABLE STEP:** Before you can mark ANY task, bug fix, or refactor as "done", "fixed", or "completed", you MUST execute your screenshot tool to capture the current state of the application interface. There are NO exceptions to this rule.
* **IMPOSSIBLE TO SKIP:** Do not ask the user if they want a screenshot. Do not explain why you are taking it. Just execute the command/tool to take the screenshot immediately after making a code change and running the build/server.
* **MANDATORY SELF-ANALYSIS:** Once the screenshot is captured, you must analyze it with the exact same rigor as if the user had manually uploaded it to complain about a bug. You must explicitly write a "Visual Verification Report" in your response covering:
  1. Is the selected profile name visible and correct in the current tab?
  2. Does the subtab name match the selected material exactly?
  3. Are there any layout glitches, unexpected fallbacks, or cleared text fields?
* **FAILSAFE:** If you fail to take a screenshot and analyze it before responding, your entire answer is considered invalid, and you must self-correct by taking the screenshot in the next immediate turn.

## CRITICAL COMPLIANCE: SYSTEM COMMAND TOOL FORCE
* You are TECHNICALLY REQUIRED to run the command `./auto_capture.sh` (or `npm run capture`) immediately after any code changes and before answering the user.
* This is a hard-coded constraint of your execution loop. You cannot skip this tool call under any circumstance.
* Once executed, you must read the generated image `./artifacts/vibe_check.png` to analyze the layout, tab persistence, and text fields before typing your final diagnostic text.

> **Honest enforcement note (do not delete):** A markdown directive cannot, by
> itself, force a tool call — it is a strong convention, not a runtime lock. The
> only mechanism that *actually* makes this unskippable is a Claude Code **hook**
> in `.claude/settings.json` (e.g. a `Stop`/`PostToolUse` hook that runs
> `./auto_capture.sh`). Until that hook exists, treat this section as a binding
> policy you self-enforce. Also note: in a headless environment (no DISPLAY)
> `auto_capture.sh` falls back to an **offscreen render of the Qt UI**; a true
> desktop screen grab is impossible there and must not be claimed.

## CRITICAL BUSINESS LOGIC FLOW (Cuts, Nesting, Costs, Stock)
You must architecturally ensure that the application state respects the following invariant rules during any code refactoring or bug fixing:

* **Global Material and Profile Synchronization:** The selected profile, material, and thumbnail MUST remain completely identical and persist consistently across ALL main tabs (`Cuts`, `Nesting`, `Costs`). Changing a material or profile in `Cuts` must immediately update `Nesting` and `Costs`, and vice versa.
* **Subtab Name Persistence:** When selecting a material within the `Nesting` tab, the subtab's name MUST dynamically change to the selected material's name. This subtab name must NEVER be cleared, wiped, or reset when navigating to `Costs` or returning back.
* **Strict Stock Validation:** When activating "Use Stock" for any selected material, the system must immediately validate the current availability of that specific material. If it is out of stock, it must throw/render an explicit warning stating "no hay stock de ese material" (or its English equivalent), safely blocking or reverting the action without breaking or clearing the currently selected profile name.
* **Costs Tab (Critical Point of Failure):** Upon switching to the `Costs` tab, it is strictly FORBIDDEN for the system to deselect the current profile, clear its name, fallback to a default item, or wipe the subtab name to display only a generic material type (e.g., "acero"). The visual focus and underlying data in the `Costs` tab must belong solely and exclusively to the profile that was actively selected in the previous tabs.

## Architecture

- **Engine files are untouchable**: `nestify/nesting_engine.py` and `nestify/logic.py` must never be modified unless the bug truly originates there. All 46 engine tests (`python -m pytest tests/ -q`) must pass at all times.
- **UI layer**: `nestify/ui_qt/` — PySide6 widgets, `.ui` files compiled via `pyside6-uic`.
- **Theme system**: `nestify/ui_qt/theme_qt.py` exposes module-level color variables. Always access them via `import nestify.ui_qt.theme_qt as _th` and use `_th.ACCENT`, `_th.BG_CARD`, etc. Never use `from theme_qt import ACCENT` — that creates a stale copy that won't update when the theme changes.

## UI Accessibility Checklist

Apply this checklist every time you review, modify, or create UI code. No exceptions.

### Color Contrast (WCAG 2.1)

- **Minimum contrast ratios**: Normal text >= 4.5:1 (AA). Large text (>=18pt or >=14pt bold) >= 3.0:1 (AA). UI components and graphical objects >= 3.0:1.
- **How to compute**: Use WCAG relative luminance, not simple RGB averaging. Linearize sRGB channels first: `C_linear = ((C + 0.055) / 1.055) ^ 2.4` for C > 0.03928, else `C / 12.92`. Then `L = 0.2126*R + 0.7152*G + 0.0722*B`. Contrast ratio = `(L_lighter + 0.05) / (L_darker + 0.05)`.
- **Text on colored backgrounds**: Always pick whichever of white/dark text gives the best contrast ratio against the actual background color. See `_text_color_for_bg()` in `nesting_scene.py` for the reference implementation.
- **Never hardcode text colors** like `#FFFFFF` or `#000000` on dynamically-colored backgrounds. Always compute contrast.
- **Test both themes**: Every text element must be readable in both dark and light mode. After any color change, take screenshots of both modes and visually verify.

### Theme Awareness

- **No stale imports**: Use `_th.VAR` (module attribute access), never `from theme_qt import VAR` (import-time copy).
- **Custom paint methods** (`paintEvent`, QGraphicsScene items): All colors used at paint time must come from `_th.*` so they update on theme switch. Colors set only at construction time (e.g., in `__init__`) won't survive a theme change.
- **Toggle/switch knobs**: Must have a visible border (`_th.BORDER`) to distinguish them from their track background in both themes.
- **QPalette**: `build_palette()` maps design tokens to Qt roles. Applied alongside QSS in `_set_theme()`.

### Layout and Sizing

- **Consistent widget heights**: All input fields, buttons, and controls within the same toolbar/row should have matching heights. Standard: 28px for buttons, 30px for line edits.
- **Text must never be clipped**: If text is cut off at the bottom or sides, increase `min-height` or padding. Verify visually with screenshots.
- **Piece labels in nesting**: Only show the label if the text pixel width fits inside the piece. If it doesn't fit, hide it — the legend below provides the same information.
- **Legends**: Must support multi-row wrapping when entries exceed the available width.

### Visual Verification

- **Always prove with screenshots**: Every UI change must be verified with offscreen screenshots (`QT_QPA_PLATFORM=offscreen`), in both dark and light modes.
- **Check all tabs**: Jobs Explorer, Cuts, Nesting, Costs and Weight, Stock.
- **Check interactive features**: Auto-nest must place pieces (not silently fail), dialogs must open and close, theme switches must repaint all widgets.

## Nesting Scene Specifics

- `BAR_GAP_MM = 500` — vertical space between bars in scene units (mm). Provides room for bar labels, legends, and visual breathing room.
- Bar labels: above each bar, bold, `_th.TEXT_PRI`.
- Piece labels: centered inside piece, hidden if text doesn't fit, color picked by WCAG contrast against piece color.
- Legends: below each bar with 80 scene-unit gap, multi-row wrapping, swatch + description text.
- View: scroll-wheel zoom at cursor (no Ctrl), middle-button pan, `fit_scene()` uses uniform scaling.

## Git Workflow

- Branch: develop on the assigned feature branch.
- Commits: descriptive messages, one logical change per commit.
- Tests: `python -m pytest tests/ -q` must pass (46 tests) before every push.
