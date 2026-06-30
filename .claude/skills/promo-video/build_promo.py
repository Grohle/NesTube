#!/usr/bin/env python3
"""
build_promo.py — assemble a smooth, dynamic promotional video for Nestify.

Each "scene" is a screenshot that gets a gentle Ken Burns move (slow zoom/pan),
an animated caption, and a crossfade into the next scene. A branded title card
opens the film and an outro closes it. Output is an H.264 .mp4 ready to upload.

Two passes, on purpose:
  1. Render every segment (title, each scene, outro) to its own clip with the
     motion + caption baked in. Simple, debuggable per-segment ffmpeg calls.
  2. Crossfade-concatenate the clips (xfade) and lay optional music underneath.

Usage:
    python build_promo.py                         # auto-build from docs/img/es
    python build_promo.py --lang en --out promo_en.mp4
    python build_promo.py --spec scenes.json      # full manual control
    python build_promo.py --audio music.mp3 --duration 4.2 --transition 0.7

Run `--help` for all options. Requires ffmpeg on PATH.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# ── Branding defaults (Nestify dark theme) ──────────────────────────────────
BG = "#161618"          # theme BG_APP
ACCENT = "#F05A22"      # theme ACCENT (orange)
TEXT = "#F2F2F2"        # theme TEXT_PRI
TEXT_DIM = "#8A8A8E"    # theme TEXT_SEC

REPO_ROOT = Path(__file__).resolve().parents[3]
BUNDLED_FONT = REPO_ROOT / "nestify" / "fonts" / "IBMPlexSans-Bold.ttf"
FALLBACK_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

# Default scene order + bilingual captions, keyed by screenshot base name.
CAPTIONS = {
    "jobs":     {"es": "Explorador de trabajos",          "en": "Job explorer"},
    "cuts":     {"es": "Lista de cortes y algoritmos",    "en": "Cut list & algorithms"},
    "nesting":  {"es": "Nesting visual e interactivo",     "en": "Visual interactive nesting"},
    "profiles": {"es": "Catálogo de perfiles y tubos",     "en": "Profile & tube catalogue"},
    "stock":    {"es": "Inventario de stock y retales",    "en": "Stock & offcut inventory"},
    "costs":    {"es": "Costes y peso por pieza",           "en": "Per-piece cost & weight"},
}
DEFAULT_ORDER = ["jobs", "cuts", "nesting", "profiles", "stock", "costs"]
# Alternating moves give the film a dynamic rhythm without ever feeling jerky.
MOTION_CYCLE = ["in", "panright", "out", "panleft", "in", "panup"]


@dataclass
class Scene:
    image: str
    caption: str = ""
    motion: str = "in"          # in | out | panleft | panright | panup | pandown
    duration: float = 3.8


@dataclass
class Spec:
    scenes: List[Scene]
    title: str = "Nestify"
    subtitle: str = "Optimización de corte de barras, tubos y perfiles"
    outro_title: str = "Nestify"
    outro_subtitle: str = "github.com/Grohle/nestify · GPL-3.0"
    width: int = 1920
    height: int = 1080
    fps: int = 30
    transition: float = 0.6     # crossfade seconds
    card_seconds: float = 2.6   # title/outro duration
    bg: str = BG
    accent: str = ACCENT
    text: str = TEXT
    font: str = ""
    audio: Optional[str] = None
    oversample: float = 1.22    # canvas headroom so pans have somewhere to go


def _hex(c: str) -> str:
    """ffmpeg wants 0xRRGGBB; accept '#rrggbb' or '0x...' or named colours."""
    c = c.strip()
    if c.startswith("#"):
        return "0x" + c[1:]
    return c


def _run(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout[-4000:] + "\n")
        raise SystemExit(f"ffmpeg failed (exit {proc.returncode}): {' '.join(cmd[:6])} …")


def _font(spec: Spec) -> str:
    if spec.font and Path(spec.font).is_file():
        return spec.font
    if BUNDLED_FONT.is_file():
        return str(BUNDLED_FONT)
    if FALLBACK_FONT.is_file():
        return str(FALLBACK_FONT)
    raise SystemExit("No usable font found. Pass --font /path/to/font.ttf")


def _zoompan(motion: str, frames: int, fps: int, w: int, h: int) -> str:
    """Build a jitter-free zoompan expression for one of the named moves."""
    n = max(frames, 1)
    # 'on' is the output frame index. iw/ih here are the padded canvas.
    if motion == "out":
        z = f"max(1.0,1.12-0.12*on/{n})"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif motion == "panright":
        z = "1.06"
        x, y = f"(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"
    elif motion == "panleft":
        z = "1.06"
        x, y = f"(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"
    elif motion == "panup":
        z = "1.06"
        x, y = "iw/2-(iw/zoom/2)", f"(ih-ih/zoom)*(1-on/{n})"
    elif motion == "pandown":
        z = "1.06"
        x, y = "iw/2-(iw/zoom/2)", f"(ih-ih/zoom)*on/{n}"
    else:  # "in"
        z = f"min(1.12,1.0+0.12*on/{n})"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    return (f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={w}x{h}:fps={fps}")


def render_scene(scene: Scene, spec: Spec, font: str, cap_txt: Path, out: Path) -> None:
    w, h, fps = spec.width, spec.height, spec.fps
    # Even canvas, strictly larger than the frame so pans always have headroom.
    cw, ch = (int(w * spec.oversample) // 2) * 2, (int(h * spec.oversample) // 2) * 2
    frames = int(round(scene.duration * fps))
    bg = _hex(spec.bg)
    vf = [
        # Fit the screenshot inside the FRAME first (never cropped), then pad out
        # to the bigger dark canvas — guarantees pad target >= scaled image.
        f"scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2",
        f"pad={cw}:{ch}:(ow-iw)/2:(oh-ih)/2:color={bg}",
        _zoompan(scene.motion, frames, fps, w, h),
    ]
    if scene.caption:
        accent = _hex(spec.accent)
        fs = max(22, h // 26)
        pad = fs // 2
        # NOTE: inside drawbox, w/h mean the BOX size, so frame-relative
        # positions must use iw/ih. drawtext, by contrast, uses w/h for the frame.
        # Fixed-width accent bar just left of the caption (drawbox can't read the
        # text width, so the dark plate is drawtext's own auto-sized box).
        vf.append(
            f"drawbox=x=(iw*0.06-{pad}-12):y=(ih*0.85-{pad}):w=8:"
            f"h=({fs}+{pad*2}):color={accent}:t=fill"
        )
        vf.append(
            f"drawtext=fontfile='{font}':expansion=none:textfile='{cap_txt}':"
            f"fontcolor={_hex(spec.text)}:fontsize={fs}:x=w*0.06:y=h*0.85:"
            f"box=1:boxcolor={bg}@0.55:boxborderw={pad}"
        )
    vf.append("format=yuv420p")
    # zoompan emits `d` frames PER input image, so feed exactly one frame
    # (-loop 1 + -frames:v) — otherwise it multiplies by every looped input
    # frame and renders tens of thousands of frames.
    _run([
        "ffmpeg", "-y", "-loop", "1", "-i", scene.image,
        "-vf", ",".join(vf), "-frames:v", str(frames), "-r", str(fps), "-an",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
        "-pix_fmt", "yuv420p", str(out),
    ])


def render_card(title_txt: Path, sub_txt: Path, spec: Spec, font: str, out: Path) -> None:
    w, h, fps, dur = spec.width, spec.height, spec.fps, spec.card_seconds
    accent = _hex(spec.accent)
    big = h // 7
    small = h // 26
    vf = [
        f"drawtext=fontfile='{font}':expansion=none:textfile='{title_txt}':fontcolor={_hex(spec.text)}:"
        f"fontsize={big}:x=(w-tw)/2:y=h*0.40",
        # Accent underline centred beneath the title (drawbox → iw/ih for frame).
        f"drawbox=x=(iw-240)/2:y=ih*0.40+{int(big*1.15)}:w=240:h=6:color={accent}:t=fill",
        f"drawtext=fontfile='{font}':expansion=none:textfile='{sub_txt}':fontcolor={_hex(TEXT_DIM)}:"
        f"fontsize={small}:x=(w-tw)/2:y=h*0.40+{int(big*1.15)}+28",
        f"fade=t=in:st=0:d=0.5",
        f"fade=t=out:st={dur - 0.5:.2f}:d=0.5",
        "format=yuv420p",
    ]
    _run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c={_hex(spec.bg)}:s={w}x{h}:r={fps}:d={dur}",
        "-vf", ",".join(vf), "-an", "-c:v", "libx264", "-preset", "ultrafast",
        "-crf", "16", "-pix_fmt", "yuv420p", str(out),
    ])


def concat_xfade(clips: List[Path], durations: List[float], spec: Spec, out: Path) -> None:
    """Crossfade-concatenate clips and (optionally) add a music bed."""
    t = spec.transition
    inputs: List[str] = []
    for c in clips:
        inputs += ["-i", str(c)]

    # Build the xfade chain, tracking the running length so each offset is right.
    chain: List[str] = []
    prev = "0:v"
    acc = durations[0]
    for i in range(1, len(clips)):
        label = f"x{i}" if i < len(clips) - 1 else "vout"
        offset = max(0.0, acc - t)
        chain.append(
            f"[{prev}][{i}:v]xfade=transition=fade:duration={t}:offset={offset:.3f}[{label}]"
        )
        prev = label
        acc = acc + durations[i] - t
    total = acc
    filt = ";".join(chain)

    cmd = ["ffmpeg", "-y", *inputs]
    if spec.audio:
        cmd += ["-i", spec.audio]
        aud_idx = len(clips)
        filt += (
            f";[{aud_idx}:a]afade=t=in:st=0:d=1.5,"
            f"afade=t=out:st={max(0.0, total - 1.5):.3f}:d=1.5,"
            f"atrim=0:{total:.3f}[aout]"
        )
        cmd += ["-filter_complex", filt, "-map", "[vout]", "-map", "[aout]",
                "-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-filter_complex", filt, "-map", "[vout]"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-r", str(spec.fps), str(out)]
    _run(cmd)


def burn_captions(raw: str, segments: list, spec: Spec, font: str, out: Path) -> None:
    """Burn timed lower-third captions onto the live tour footage."""
    w, h = spec.width, spec.height
    fs = max(24, h // 28)
    pad = fs // 2
    ty, tx = "h*0.88", "w*0.06"
    bg, accent = _hex(spec.bg), _hex(spec.accent)
    vf: List[str] = [f"scale={w}:{h}", "setsar=1"]
    for i, (s, e, cap) in enumerate(segments):
        if not cap:
            continue
        cf = out.parent / f"livecap{i}.txt"
        cf.write_text(cap, encoding="utf-8")
        en = f"between(t\\,{s:.3f}\\,{e:.3f})"
        vf.append(
            f"drawbox=x=(iw*0.06-{pad}-12):y=(ih*0.88-{pad}):w=8:"
            f"h=({fs}+{pad*2}):color={accent}:t=fill:enable='{en}'"
        )
        vf.append(
            f"drawtext=fontfile='{font}':expansion=none:textfile='{cf}':fontcolor={_hex(spec.text)}:"
            f"fontsize={fs}:x={tx}:y={ty}:box=1:boxcolor={bg}@0.6:"
            f"boxborderw={pad}:enable='{en}'"
        )
    vf.append("format=yuv420p")
    _run([
        "ffmpeg", "-y", "-i", raw, "-vf", ",".join(vf), "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-r", str(spec.fps), str(out),
    ])


def compose_live(raw: str, timeline_path: str, spec: Spec, out_path: str) -> None:
    """Wrap live tour footage with a title card, outro card and captions."""
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not found on PATH.")
    tl = json.loads(Path(timeline_path).read_text(encoding="utf-8"))
    spec.fps = int(tl.get("fps", spec.fps))
    live_dur = float(tl.get("duration", 0.0))
    segments = [(float(a), float(b), c) for a, b, c in tl.get("segments", [])]
    font = _font(spec)
    with tempfile.TemporaryDirectory(prefix="promo_live_") as td:
        tmp = Path(td)
        live = tmp / "live_cap.mp4"
        burn_captions(raw, segments, spec, font, live)

        (tmp / "t.txt").write_text(spec.title, encoding="utf-8")
        (tmp / "s.txt").write_text(spec.subtitle, encoding="utf-8")
        title = tmp / "title.mp4"
        render_card(tmp / "t.txt", tmp / "s.txt", spec, font, title)

        (tmp / "ot.txt").write_text(spec.outro_title, encoding="utf-8")
        (tmp / "os.txt").write_text(spec.outro_subtitle, encoding="utf-8")
        outro = tmp / "outro.mp4"
        render_card(tmp / "ot.txt", tmp / "os.txt", spec, font, outro)

        clips = [title, live, outro]
        durations = [spec.card_seconds, live_dur, spec.card_seconds]
        concat_xfade(clips, durations, spec, Path(out_path))
    total = sum(durations) - spec.transition * (len(clips) - 1)
    print(f"✓ Wrote {out_path}  (live tour + title/outro, ~{total:.1f}s, "
          f"{spec.width}x{spec.height}@{spec.fps})")


# ── LinkedIn flashy vertical (4:5) composition ──────────────────────────────
LINKEDIN_STATS = [
    ("job",     "Save & reopen every job"),
    ("cut",     "3 packing algorithms"),
    ("nest",    "Up to ~83% material yield"),
    ("cost",    "Instant cost & weight"),
    ("profile", "Built-in profile library"),
    ("stock",   "Reuse offcuts & stock"),
]


def _seg_stat(caption: str) -> str:
    c = caption.lower()
    for key, stat in LINKEDIN_STATS:
        if key in c:
            return stat
    return ""


def _alpha(s: float, e: float, f: float = 0.45) -> str:
    """drawtext alpha that fades in over f, holds, fades out over f. Commas are
    escaped for the filter parser; drawtext clamps the result to [0,1]."""
    return (f"if(lt(t\\,{s + f:.3f})\\,(t-{s:.3f})/{f}\\,"
            f"if(lt(t\\,{e - f:.3f})\\,1\\,({e:.3f}-t)/{f}))")


def _render_text_card(out: Path, dur: float, spec: Spec, font: str,
                      texts, boxes=()) -> None:
    """Static branded card on the theme background, with a fade in/out.
    texts: (textfile, size, color, x_expr, y). boxes: (x,y,w,h,color)."""
    w, h, fps = spec.width, spec.height, spec.fps
    parts = [f"drawbox=x={x}:y={y}:w={bw}:h={bh}:color={_hex(c)}:t=fill"
             for (x, y, bw, bh, c) in boxes]
    parts += [f"drawtext=fontfile='{font}':expansion=none:textfile='{tf}':fontcolor={_hex(col)}:"
              f"fontsize={sz}:x={x}:y={y}" for (tf, sz, col, x, y) in texts]
    parts += [f"fade=t=in:st=0:d=0.45", f"fade=t=out:st={dur - 0.45:.2f}:d=0.45",
              "format=yuv420p"]
    _run(["ffmpeg", "-y", "-f", "lavfi",
          "-i", f"color=c={_hex(spec.bg)}:s={w}x{h}:r={fps}:d={dur}",
          "-vf", ",".join(parts), "-an", "-c:v", "libx264", "-preset", "veryfast",
          "-crf", "18", "-pix_fmt", "yuv420p", str(out)])


def compose_linkedin(raw: str, timeline_path: str, spec: Spec, out_path: str) -> None:
    """Eye-catching vertical 4:5 (1080x1350) cut for LinkedIn: branded header,
    centered live footage, kinetic section captions + stat lines, hook intro and
    CTA outro. Built for muted in-feed autoplay (everything readable as text)."""
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not found on PATH.")
    tl = json.loads(Path(timeline_path).read_text(encoding="utf-8"))
    spec.width, spec.height = 1080, 1350
    spec.fps = int(tl.get("fps", spec.fps))
    dur = float(tl.get("duration", 0.0))
    segments = [(float(a), float(b), c) for a, b, c in tl.get("segments", [])]
    n = len(segments) or 1
    font = _font(spec)
    white, accent, gray, dim = spec.text, spec.accent, "#8A8A8E", "#56565C"
    FY = 372  # footage band y; header above, captions below

    with tempfile.TemporaryDirectory(prefix="promo_li_") as td:
        tmp = Path(td)

        # ── body: footage on canvas + persistent header + kinetic captions ──
        (tmp / "wm.txt").write_text("NESTIFY", encoding="utf-8")
        (tmp / "tag.txt").write_text("Cutting optimization for metal fabrication", encoding="utf-8")
        (tmp / "foot.txt").write_text("github.com/Grohle/nestify", encoding="utf-8")
        chain = [
            f"drawtext=fontfile='{font}':expansion=none:textfile='{tmp/'wm.txt'}':fontcolor={_hex(white)}:fontsize=78:x=64:y=70",
            f"drawtext=fontfile='{font}':expansion=none:textfile='{tmp/'tag.txt'}':fontcolor={_hex(gray)}:fontsize=30:x=66:y=168",
            f"drawbox=x=64:y=1000:w=120:h=6:color={_hex(accent)}:t=fill",
            f"drawtext=fontfile='{font}':expansion=none:textfile='{tmp/'foot.txt'}':fontcolor={_hex(dim)}:fontsize=26:x=64:y=1300",
        ]
        for i, (s, e, cap) in enumerate(segments):
            a = _alpha(s, e)
            cnt = tmp / f"cnt{i}.txt"; cnt.write_text(f"{i+1:02d} / {n:02d}", encoding="utf-8")
            cf = tmp / f"cap{i}.txt"; cf.write_text(cap, encoding="utf-8")
            chain.append(
                f"drawtext=fontfile='{font}':expansion=none:textfile='{cnt}':fontcolor={_hex(accent)}:"
                f"fontsize=30:x=64:y=1028:alpha='{a}'")
            chain.append(
                f"drawtext=fontfile='{font}':expansion=none:textfile='{cf}':fontcolor={_hex(white)}:"
                f"fontsize=58:x=64:y=1066:alpha='{a}'")
            stat = _seg_stat(cap)
            if stat:
                sf = tmp / f"stat{i}.txt"; sf.write_text(stat, encoding="utf-8")
                chain.append(
                    f"drawtext=fontfile='{font}':expansion=none:textfile='{sf}':fontcolor={_hex(gray)}:"
                    f"fontsize=34:x=64:y=1158:alpha='{a}'")
        fc = (f"[0:v]scale=1080:608,setsar=1[foot];"
              f"[1:v][foot]overlay=(W-w)/2:{FY}[bg];"
              f"[bg]" + ",".join(chain) + ",format=yuv420p[outv]")
        body = tmp / "body.mp4"
        _run(["ffmpeg", "-y", "-i", raw, "-f", "lavfi",
              "-i", f"color=c={_hex(spec.bg)}:s=1080x1350:r={spec.fps}:d={dur}",
              "-filter_complex", fc, "-map", "[outv]", "-t", f"{dur}",
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
              "-pix_fmt", "yuv420p", str(body)])

        # ── hook intro ──
        cx = "(w-tw)/2"
        (tmp / "kick.txt").write_text("FOR METAL FABRICATION", encoding="utf-8")
        (tmp / "ttl.txt").write_text("Nestify", encoding="utf-8")
        (tmp / "sub.txt").write_text("Smarter bar, tube & profile cutting", encoding="utf-8")
        (tmp / "b1.txt").write_text("Up to ~83% material yield", encoding="utf-8")
        (tmp / "b2.txt").write_text("Interactive miter & bevel nesting", encoding="utf-8")
        (tmp / "b3.txt").write_text("PDF · DXF · Excel export", encoding="utf-8")
        intro = tmp / "intro.mp4"
        _render_text_card(intro, 3.0, spec, font, texts=[
            (tmp/"kick.txt", 36, accent, cx, 430),
            (tmp/"ttl.txt", 150, white, cx, 480),
            (tmp/"sub.txt", 40, gray, cx, 700),
            (tmp/"b1.txt", 38, white, cx, 820),
            (tmp/"b2.txt", 38, white, cx, 884),
            (tmp/"b3.txt", 38, white, cx, 948),
        ], boxes=[("(iw-240)/2", 668, 240, 8, accent)])

        # ── CTA outro ──
        (tmp / "ot.txt").write_text("Nestify", encoding="utf-8")
        (tmp / "os.txt").write_text("100% offline · GPL-3.0", encoding="utf-8")
        (tmp / "ourl.txt").write_text("github.com/Grohle/nestify", encoding="utf-8")
        (tmp / "ofree.txt").write_text("Free & open source", encoding="utf-8")
        outro = tmp / "outro.mp4"
        _render_text_card(outro, 3.2, spec, font, texts=[
            (tmp/"ot.txt", 140, white, cx, 470),
            (tmp/"os.txt", 40, gray, cx, 660),
            (tmp/"ourl.txt", 42, white, cx, 812),
            (tmp/"ofree.txt", 34, accent, cx, 936),
        ], boxes=[("(iw-260)/2", 640, 260, 8, accent),
                  ("(iw-620)/2", 792, 620, 86, "#27272A")])

        clips = [intro, body, outro]
        durations = [3.0, dur, 3.2]
        concat_xfade(clips, durations, spec, Path(out_path))
    total = sum(durations) - spec.transition * (len(clips) - 1)
    print(f"✓ Wrote {out_path}  (LinkedIn 4:5, ~{total:.1f}s, "
          f"{spec.width}x{spec.height}@{spec.fps})")


def auto_spec(args) -> Spec:
    img_dir = Path(args.img_dir) if args.img_dir else (REPO_ROOT / "docs" / "img" / args.lang)
    if not img_dir.is_dir():
        raise SystemExit(f"Image directory not found: {img_dir}")
    scenes: List[Scene] = []
    for i, base in enumerate(DEFAULT_ORDER):
        p = img_dir / f"{base}.png"
        if not p.is_file():
            continue
        scenes.append(Scene(
            image=str(p),
            caption=CAPTIONS.get(base, {}).get(args.lang, base),
            motion=MOTION_CYCLE[i % len(MOTION_CYCLE)],
            duration=args.duration,
        ))
    if not scenes:
        raise SystemExit(f"No screenshots found in {img_dir}")
    sub = ("Optimización de corte de barras, tubos y perfiles" if args.lang == "es"
           else "Bar, tube & profile cutting optimizer")
    return Spec(scenes=scenes, subtitle=sub, transition=args.transition,
                audio=args.audio, fps=args.fps,
                width=args.resolution[0], height=args.resolution[1])


def load_spec(path: str, args) -> Spec:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    scenes = [Scene(**s) for s in data.pop("scenes")]
    spec = Spec(scenes=scenes, **data)
    if args.audio:
        spec.audio = args.audio
    return spec


def build(spec: Spec, out_path: str) -> None:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not found on PATH. Install it (e.g. apt install ffmpeg).")
    font = _font(spec)
    with tempfile.TemporaryDirectory(prefix="promo_") as td:
        tmp = Path(td)
        clips: List[Path] = []
        durations: List[float] = []

        # Title card
        (tmp / "title.txt").write_text(spec.title, encoding="utf-8")
        (tmp / "sub.txt").write_text(spec.subtitle, encoding="utf-8")
        c0 = tmp / "seg00.mp4"
        render_card(tmp / "title.txt", tmp / "sub.txt", spec, font, c0)
        clips.append(c0); durations.append(spec.card_seconds)

        # Scenes
        for i, sc in enumerate(spec.scenes, 1):
            cap = tmp / f"cap{i}.txt"
            cap.write_text(sc.caption, encoding="utf-8")
            seg = tmp / f"seg{i:02d}.mp4"
            render_scene(sc, spec, font, cap, seg)
            clips.append(seg); durations.append(sc.duration)

        # Outro card
        (tmp / "otitle.txt").write_text(spec.outro_title, encoding="utf-8")
        (tmp / "osub.txt").write_text(spec.outro_subtitle, encoding="utf-8")
        cN = tmp / "segzz.mp4"
        render_card(tmp / "otitle.txt", tmp / "osub.txt", spec, font, cN)
        clips.append(cN); durations.append(spec.card_seconds)

        concat_xfade(clips, durations, spec, Path(out_path))
    total = sum(durations) - spec.transition * (len(clips) - 1)
    print(f"✓ Wrote {out_path}  ({len(clips)} segments, ~{total:.1f}s, "
          f"{spec.width}x{spec.height}@{spec.fps})")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a Nestify promo video.")
    ap.add_argument("--live", help="Live tour footage (raw_tour.mp4 from record_tour.py).")
    ap.add_argument("--timeline", help="timeline.json that pairs with --live.")
    ap.add_argument("--linkedin", action="store_true",
                    help="Eye-catching vertical 4:5 cut for LinkedIn (needs --live/--timeline).")
    ap.add_argument("--spec", help="JSON scene spec (full control). Overrides auto build.")
    ap.add_argument("--lang", choices=["es", "en"], default="es")
    ap.add_argument("--img-dir", help="Folder of screenshots (default docs/img/<lang>)")
    ap.add_argument("--out", default="nestify_promo.mp4")
    ap.add_argument("--audio", help="Optional background music (mp3/m4a/wav)")
    ap.add_argument("--duration", type=float, default=3.8, help="Seconds per scene")
    ap.add_argument("--transition", type=float, default=0.6, help="Crossfade seconds")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--resolution", default="1920x1080",
                    type=lambda s: tuple(int(x) for x in s.lower().split("x")))
    args = ap.parse_args()

    if args.live:
        if not args.timeline:
            raise SystemExit("--live requires --timeline")
        sub = ("Optimización de corte de barras, tubos y perfiles" if args.lang == "es"
               else "Bar, tube & profile cutting optimizer")
        spec = Spec(scenes=[], subtitle=sub, transition=args.transition,
                    audio=args.audio, fps=args.fps,
                    width=args.resolution[0], height=args.resolution[1])
        if args.linkedin:
            compose_linkedin(args.live, args.timeline, spec, args.out)
        else:
            compose_live(args.live, args.timeline, spec, args.out)
        return

    spec = load_spec(args.spec, args) if args.spec else auto_spec(args)
    build(spec, args.out)


if __name__ == "__main__":
    main()
