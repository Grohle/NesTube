---
name: promo-video
description: Build a smooth, dynamic promotional video showcasing Nestify's features. Use when the user wants a promo/demo/teaser/trailer video, a feature showcase reel, or an animated walkthrough of the app's screens — with Ken Burns motion (slow zoom/pan), crossfade transitions, branded title/outro cards and captions. Renders an MP4 from app screenshots via ffmpeg.
---

# Promo video builder

Assemble a branded promotional video for Nestify: a title card, one scene per
feature (a screenshot with a gentle Ken Burns move + caption), crossfades
between scenes, and an outro card. Output is an upload-ready H.264 `.mp4`.

The engine is `build_promo.py` (in this skill folder). It shells out to **ffmpeg**.

## Prerequisites

- `ffmpeg` on PATH. If missing: `sudo apt-get install -y ffmpeg`.
- Screenshots of the app. The repo ships polished captures in `docs/img/es/`
  and `docs/img/en/` (jobs, cuts, nesting, profiles, stock, costs). Use those by
  default. Only regenerate captures if the UI changed materially (see below).

## Quick start

```bash
# Spanish promo from the bundled screenshots → nestify_promo.mp4
python .claude/skills/promo-video/build_promo.py --lang es --out nestify_promo.mp4

# English version
python .claude/skills/promo-video/build_promo.py --lang en --out nestify_promo_en.mp4

# With a music bed and slightly slower, more cinematic pacing
python .claude/skills/promo-video/build_promo.py --lang es --audio music.mp3 \
    --duration 4.3 --transition 0.8 --out promo.mp4
```

A ~24 s 1080p30 clip renders in well under a minute. Always preview the result
(extract a couple of frames with `ffmpeg -ss <t> -i out.mp4 -frames:v 1 f.png`
and look at them, or send the mp4 to the user) before declaring it done.

## Options

| Flag | Default | Meaning |
|------|---------|---------|
| `--lang` | `es` | Caption language and default screenshot folder (`docs/img/<lang>`). |
| `--img-dir` | — | Override the screenshot folder. |
| `--spec` | — | Path to a JSON spec for full manual control (see below). Overrides auto-build. |
| `--out` | `nestify_promo.mp4` | Output file. |
| `--audio` | — | Background music (mp3/m4a/wav); auto-faded in/out and trimmed to length. |
| `--duration` | `3.8` | Seconds per scene. |
| `--transition` | `0.6` | Crossfade seconds between segments. |
| `--fps` | `30` | Frame rate. |
| `--resolution` | `1920x1080` | Output `WxH`. |

## Full control via a JSON spec

For a custom running order, captions, per-scene motion, or different
title/outro text, write a spec and pass `--spec`:

```json
{
  "title": "Nestify",
  "subtitle": "Optimización de corte de barras, tubos y perfiles",
  "outro_title": "Pruébalo",
  "outro_subtitle": "github.com/Grohle/nestify · GPL-3.0",
  "transition": 0.7,
  "card_seconds": 2.6,
  "scenes": [
    {"image": "docs/img/es/cuts.png",    "caption": "Define tus cortes",        "motion": "in",       "duration": 4.0},
    {"image": "docs/img/es/nesting.png", "caption": "Nesting automático",        "motion": "panright", "duration": 4.5},
    {"image": "docs/img/es/costs.png",   "caption": "Costes al instante",        "motion": "out",      "duration": 4.0}
  ]
}
```

**Motion values:** `in` (push in), `out` (pull out), `panleft`, `panright`,
`panup`, `pandown`. Alternate them scene-to-scene for a dynamic rhythm — the
auto-build already cycles through them.

When auto-building, captions come from the `CAPTIONS` map in `build_promo.py`;
edit that map (or use a spec) to change wording. The default order is
jobs → cuts → nesting → profiles → stock → costs.

## Regenerating screenshots (only if the UI changed)

The bundled `docs/img/*` captures are the source of truth. If the UI changed and
they're stale, recapture with the existing headless tooling, then re-run the
builder:

```bash
xvfb-run -a python .devcontainer/scripts/shot_all_tabs.py   # or shot_<tab>.py
```

(These scripts drive PySide6 under Xvfb. See `.devcontainer/scripts/` for the
per-tab variants.) Aim for a consistent window size so every scene frames alike.

## How it works (so you can debug it)

1. **Per-segment render.** Title, each scene, and outro are rendered to their
   own short clip. Each scene: fit the screenshot inside the 1080p frame (never
   cropped), pad out to a slightly larger dark canvas (`#161618`), then a
   `zoompan` Ken Burns move over that canvas, plus a caption (dark plate +
   orange `#F05A22` accent bar).
2. **Crossfade concat.** The clips are chained with ffmpeg `xfade`, offsets
   computed from the running timeline. Optional audio is mixed under the whole
   thing with fades.

### Gotchas already handled (don't reintroduce)

- **`zoompan` multiplies frames.** It emits `d` frames *per input image*. Feed
  exactly one frame (`-loop 1 -i img … -frames:v N`), never `-loop 1 -t DUR`, or
  it renders tens of thousands of frames and appears to hang.
- **`drawbox` vs `drawtext` coordinates.** Inside `drawbox`, `w`/`h` are the
  *box* size — use `iw`/`ih` for frame-relative positions. `drawtext` uses
  `w`/`h` for the frame. Mixing these up parks overlays in the top-left corner.
- **Padding rounding.** Fit to the frame first, then pad to the larger canvas, so
  the pad target is always ≥ the scaled image.
- Captions are passed via `textfile=` to avoid drawtext escaping issues with
  accents, colons and quotes.

Branding constants (colours, fonts) live at the top of `build_promo.py`. The
title font is the app's bundled `nestify/fonts/IBMPlexSans-Bold.ttf`, falling
back to DejaVu Sans.
