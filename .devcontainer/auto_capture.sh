#!/usr/bin/env bash
#
# auto_capture.sh — Nestify visual-verification capture helper.
#
# Goal: produce ./artifacts/vibe_check.png representing the CURRENT UI state, so
# it can be inspected before answering a verification question.
#
# It is "infallible" in the only honest sense that matters: it NEVER produces a
# fake or silently-empty image. It tries, in order:
#
#   1. A real desktop screen grab, IF a graphical session + a capture tool exist.
#   2. An offscreen render of the actual Nestify Qt window (headless-friendly).
#
# If neither is possible it exits non-zero with a clear diagnostic instead of
# leaving a stale or black PNG behind.
#
# Usage (run from project root):
#   .devcontainer/auto_capture.sh                 # auto: desktop if available, else offscreen
#   .devcontainer/auto_capture.sh --offscreen     # force the Qt offscreen render
#   THEME=light .devcontainer/auto_capture.sh     # offscreen theme (dark|light), default dark
#
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
ARTIFACTS_DIR="${ROOT_DIR}/artifacts"
OUT="${ARTIFACTS_DIR}/vibe_check.png"
THEME="${THEME:-dark}"
FORCE_OFFSCREEN=0
[ "${1:-}" = "--offscreen" ] && FORCE_OFFSCREEN=1

mkdir -p "${ARTIFACTS_DIR}"

log() { printf '[auto_capture] %s\n' "$1" >&2; }

# --- Strategy 1: real desktop capture (only if a display is actually present) ---
try_desktop_capture() {
  # No display server -> nothing on screen to grab.
  if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
    log "no DISPLAY / WAYLAND_DISPLAY -> skipping desktop capture"
    return 1
  fi
  if command -v screencapture >/dev/null 2>&1; then        # macOS
    screencapture -x "${OUT}" && return 0
  elif command -v grim >/dev/null 2>&1; then               # Wayland
    grim "${OUT}" && return 0
  elif command -v maim >/dev/null 2>&1; then               # X11
    maim "${OUT}" && return 0
  elif command -v scrot >/dev/null 2>&1; then              # X11
    scrot -o "${OUT}" && return 0
  elif command -v import >/dev/null 2>&1; then             # ImageMagick / X11
    import -window root "${OUT}" && return 0
  else
    log "a display exists but no capture tool (screencapture/grim/maim/scrot/import) is installed"
    return 1
  fi
  return 1
}

# --- Strategy 2: offscreen Qt render of the real Nestify window ---
try_offscreen_capture() {
  local py
  py="$(command -v python3 || command -v python)" || { log "no python interpreter found"; return 1; }
  QT_QPA_PLATFORM=offscreen "${py}" "${SCRIPT_DIR}/scripts/_vibe_capture.py" "${OUT}" "${THEME}" 1
  return $?
}

rm -f "${OUT}"

if [ "${FORCE_OFFSCREEN}" -eq 0 ] && try_desktop_capture; then
  log "captured real desktop -> ${OUT}"
elif try_offscreen_capture; then
  log "captured Nestify UI offscreen (theme=${THEME}) -> ${OUT}"
else
  log "FAILED: could not produce a screenshot by any method."
  log "  - no graphical desktop is available in this environment, and"
  log "  - the offscreen Qt render could not run (is PySide6 installed? pip install -r requirements.txt)."
  exit 1
fi

# Final integrity check: refuse to report success on a missing/empty file.
if [ ! -s "${OUT}" ]; then
  log "FAILED: ${OUT} is missing or empty after capture."
  exit 1
fi

log "OK: $(wc -c < "${OUT}") bytes at ${OUT}"
echo "${OUT}"
