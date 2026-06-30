#!/usr/bin/env bash
# record_live.sh — one command: launch a headless display, record a live tour of
# the running Nestify app, and compose the finished promo (title + footage +
# outro, captions, crossfades).
#
# Usage:
#   .claude/skills/promo-video/record_live.sh [--lang es|en] [--out promo.mp4]
#                                             [--size 1920x1080] [--fps 60]
#                                             [--audio music.mp3]
#
# Needs: ffmpeg, Xvfb, and the Qt xcb runtime libs. On Debian/Ubuntu:
#   sudo apt-get install -y ffmpeg xvfb libxcb-cursor0 libxkbcommon-x11-0 \
#        libxcb-xkb1 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
#        libxcb-randr0 libxcb-render-util0 libxcb-shape0 libegl1
set -euo pipefail

LANG_OPT=es
OUT=nestify_promo_live.mp4
SIZE=1920x1080
FPS=30
AUDIO=""
TRANSITION=0.7
STYLE=wide   # wide (16:9 + cards) | linkedin (vertical 4:5, flashy)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) LANG_OPT="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --size) SIZE="$2"; shift 2;;
    --fps) FPS="$2"; shift 2;;
    --audio) AUDIO="$2"; shift 2;;
    --transition) TRANSITION="$2"; shift 2;;
    --style) STYLE="$2"; shift 2;;
    *) echo "Unknown option: $1" >&2; exit 2;;
  esac
done

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SKILL_DIR/../../.." && pwd)"
WORK="$(mktemp -d)"
RAW="$WORK/raw_tour.mp4"
TL="$WORK/timeline.json"

command -v ffmpeg >/dev/null || { echo "ffmpeg not found — see header for apt deps." >&2; exit 1; }
command -v Xvfb   >/dev/null || { echo "Xvfb not found — see header for apt deps." >&2; exit 1; }

# Pick a free X display number.
DISP_NUM=99
while [[ -e "/tmp/.X11-unix/X${DISP_NUM}" ]]; do DISP_NUM=$((DISP_NUM+1)); done
DISPLAY_ID=":${DISP_NUM}"

Xvfb "$DISPLAY_ID" -screen 0 "${SIZE}x24" -nolisten tcp >/tmp/promo_xvfb.log 2>&1 &
XVFB_PID=$!
cleanup() { kill "$XVFB_PID" 2>/dev/null || true; rm -rf "$WORK"; }
trap cleanup EXIT

# Wait for the display to come up.
for _ in $(seq 1 40); do
  DISPLAY="$DISPLAY_ID" xdpyinfo >/dev/null 2>&1 && break || sleep 0.25
done

echo "▶ Recording live tour on $DISPLAY_ID ($SIZE @ ${FPS}fps)…"
QT_QPA_PLATFORM=xcb DISPLAY="$DISPLAY_ID" \
  python3 "$SKILL_DIR/record_tour.py" \
    --display "$DISPLAY_ID" --size "$SIZE" --fps "$FPS" --lang "$LANG_OPT" \
    --out "$RAW" --timeline "$TL"

echo "▶ Composing final promo (style: $STYLE)…"
COMPOSE_ARGS=(--live "$RAW" --timeline "$TL" --lang "$LANG_OPT"
              --transition "$TRANSITION" --resolution "$SIZE" --out "$OUT")
[[ "$STYLE" == "linkedin" ]] && COMPOSE_ARGS+=(--linkedin)
[[ -n "$AUDIO" ]] && COMPOSE_ARGS+=(--audio "$AUDIO")
python3 "$SKILL_DIR/build_promo.py" "${COMPOSE_ARGS[@]}"

echo "✓ Done → $OUT"
