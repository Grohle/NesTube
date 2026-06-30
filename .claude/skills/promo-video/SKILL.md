---
name: promo-video
description: Build a smooth, dynamic promotional video of Nestify. Use when the user wants a promo/demo/teaser/trailer video, a feature showcase reel, or a walkthrough of the app. The primary mode records the LIVE app running (dark theme, a cursor gliding between tabs with the demo job loaded so real cuts/nesting/costs show), then wraps it with title/outro cards, captions and crossfades. A static screenshot-slideshow mode exists as a fallback.
---

# Promo video builder

Two ways to make the film. **Prefer the live mode** — it shows the real app
working, which is what a promo needs. The slideshow mode is a fallback for when
no display is available.

The engines shell out to **ffmpeg**.

## Mode 1 — Live app recording (recommended)

Records the actual app: dark theme, fills the frame, a cursor glides smoothly
between tabs, the demo job is loaded so every panel shows real content (cut
list, a packed nesting layout with coloured bars + efficiency, costs). Then a
branded title card, lower-third captions per section, an outro card and
crossfades are composed on top.

```bash
# One command: headless display → record live tour → compose finished promo
.claude/skills/promo-video/record_live.sh --lang es --out nestify_promo.mp4

# English, with music, custom crossfade (wide 16:9 — YouTube / README / site)
.claude/skills/promo-video/record_live.sh --lang en --fps 60 \
    --audio music.mp3 --transition 0.8 --out promo_en.mp4

# Flashy vertical 4:5 cut for LinkedIn / social feeds
.claude/skills/promo-video/record_live.sh --lang en --style linkedin \
    --out nestify_linkedin.mp4
```

Produces a ~25 s clip in under a minute. `--style wide` (default) is 16:9 with
title/outro cards; `--style linkedin` is **vertical 1080x1350** with a branded
header, the live footage centered, kinetic section captions + "0X / 06" counter
and stat lines, a punchy hook intro and a CTA outro — designed for muted
in-feed autoplay (everything reads as text). Tune the hook/CTA/stat wording in
`compose_linkedin()` / `LINKEDIN_STATS` in `build_promo.py`.

To regenerate just the composition from already-recorded footage (no re-record):

```bash
python build_promo.py --live raw.mp4 --timeline timeline.json --lang en \
    [--linkedin] --out promo.mp4
```

### Prerequisites (live mode)

`ffmpeg`, `Xvfb`, and the Qt **xcb** runtime libraries. On Debian/Ubuntu:

```bash
sudo apt-get install -y ffmpeg xvfb libxcb-cursor0 libxkbcommon-x11-0 \
  libxcb-xkb1 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 \
  libxcb-render-util0 libxcb-shape0 libegl1
```

(Without `libxcb-cursor0`, Qt ≥6.5 refuses to start the xcb platform plugin.)

### How it works

- **`record_tour.py`** runs *inside* the app's Qt event loop on the X display.
  It loads the demo job, then drives a keyframe animation: a cursor eased with
  smoothstep glides to each tab (60 Hz interpolation → no stutter), switches it,
  and dwells. ffmpeg `x11grab` records the display for exactly the tour, and the
  script writes `timeline.json` of `(start, end, caption)` so captions line up
  frame-accurately. The X cursor is captured natively (`-draw_mouse 1`).
- **`build_promo.py --live raw.mp4 --timeline timeline.json`** burns the
  lower-third captions onto the footage at the timeline times, renders the
  title/outro cards, and crossfades the three together (plus optional music).
- **`record_live.sh`** ties it together: picks a free display, starts Xvfb,
  records, composes, cleans up.

### Tuning the tour

Edit `record_tour.py`:
- `CAPTIONS` — wording per tab (es/en).
- `TourDriver.build()` — dwell/glide durations, or add steps (open a dialog,
  scroll, click *Auto-anidar*). Steps are fixed-duration so the timeline stays
  deterministic.

## Mode 2 — Static screenshot slideshow (fallback)

Ken Burns moves over screenshots with crossfades. Use only when you can't run a
display. The bundled `docs/img/<lang>/*.png` are light-theme; for a dark promo,
prefer the live mode (or recapture the screenshots in dark theme first).

```bash
python .claude/skills/promo-video/build_promo.py --lang es --out promo.mp4
python .claude/skills/promo-video/build_promo.py --spec scenes.json   # full control
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--lang` | `es` | Caption language / default screenshot folder. |
| `--img-dir` | — | Override screenshot folder. |
| `--spec` | — | JSON scene spec (full control); overrides auto-build. |
| `--audio` | — | Background music, auto faded/trimmed. |
| `--duration` | `3.8` | Seconds per scene. |
| `--transition` | `0.6` | Crossfade seconds. |
| `--fps` / `--resolution` | `30` / `1920x1080` | Output frame rate / size. |

JSON spec scenes take `image`, `caption`, `motion`
(`in`/`out`/`panleft`/`panright`/`panup`/`pandown`) and `duration`.

## ffmpeg gotchas already handled (don't reintroduce)

- **`zoompan` jitter / "vibration".** It rounds the crop position to integer
  pixels each frame; on a small canvas that stair-steps visibly. The static mode
  pre-fits then pads to a larger canvas; the **live mode avoids zoompan entirely**
  by recording real footage. If you add post-zoom, upscale the source large
  first so per-frame rounding is sub-pixel.
- **`zoompan` multiplies frames.** It emits `d` frames *per input image* — feed
  exactly one frame (`-loop 1 -i img … -frames:v N`), never `-loop 1 -t DUR`.
- **`drawbox` vs `drawtext` coordinates.** Inside `drawbox`, `w`/`h` are the
  *box* size — use `iw`/`ih` for frame-relative positions. `drawtext` uses
  `w`/`h` for the frame.
- **`enable=` commas must be escaped** inside a filter (`between(t\,a\,b)`).
- **`drawtext` eats `%`.** A literal `%` (e.g. "83% yield") triggers `%{}`
  expansion and the line silently fails to render. All `drawtext` calls set
  `expansion=none` — keep it when adding text with `%`, `{`, or `\`.
- **Clean exit under Xvfb.** `record_tour.py` `os._exit(0)`s after ffmpeg
  finalises the mp4, so a lingering Qt modal/timer can't hang the process.
- **No window manager** honours `showFullScreen()` under Xvfb — set the window
  geometry explicitly (frameless, `0,0,W,H`).
- **`--lang` must drive the app UI, not just captions.** `app_config.load()`
  re-reads the stored language (often `es`) on every call — including inside
  `NestifyApp.__init__` — so `record_tour.py` patches `load()` to force the
  requested language; otherwise the recorded UI ignores `--lang`. (Job/piece
  names come from the demo job data and stay as saved — they're user content,
  not UI chrome.)

Branding (colours `#161618`/`#F05A22`, IBM Plex font) lives at the top of
`build_promo.py`.
