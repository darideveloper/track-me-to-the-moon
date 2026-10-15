#!/usr/bin/env bash
# moon-tracker launcher: checks git + Python, bootstraps uv, syncs, runs.
# Double-click or ./run.sh to start. Update with: git pull --ff-only
set -euo pipefail
cd "$(dirname "$0")"

diagnostic=0
for arg in "$@"; do
  case "$arg" in
    --once|--shot|--version) diagnostic=1 ;;
  esac
done

# Graphical starts detach from the launcher terminal. The child inherits this
# marker, so it performs bootstrap once and sends output to the same log.
if [ "${MOON_TRACKER_HIDDEN_LAUNCH:-}" != "1" ] \
  && [ "$diagnostic" -eq 0 ] \
  && [ "${MOON_TRACKER_FOREGROUND:-}" != "1" ]; then
  log_dir="${XDG_STATE_HOME:-$HOME/.local/state}/moon-tracker"
  mkdir -p "$log_dir"
  export MOON_TRACKER_HIDDEN_LAUNCH=1
  if command -v setsid >/dev/null 2>&1; then
    nohup setsid "$0" "$@" </dev/null >> "$log_dir/launcher.log" 2>&1 &
  else
    nohup "$0" "$@" </dev/null >> "$log_dir/launcher.log" 2>&1 &
  fi
  exit 0
fi

if ! command -v git >/dev/null 2>&1; then
  echo "[moon-tracker] git not found. Install it first:" >&2
  echo "  Debian/Ubuntu: sudo apt install git" >&2
  echo "  Fedora: sudo dnf install git" >&2
  exit 1
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if [ -n "$BRANCH" ] && [ "$BRANCH" != "main" ]; then
  echo "[moon-tracker] WARNING: not on branch 'main' (on '$BRANCH'). Continuing..."
fi

if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
  echo "[moon-tracker] NOTE: Wayland session detected - window titles are best-effort. X11 recommended."
fi

PY=""
for cand in python3.12 python3.11 python3.10 python3; do
  if command -v "$cand" >/dev/null 2>&1 \
    && "$cand" -c "import sys; raise SystemExit(0 if sys.version_info>=(3,10) else 1)" 2>/dev/null; then
    PY="$cand"
    break
  fi
done

if ! command -v uv >/dev/null 2>&1; then
  echo "[moon-tracker] Installing uv (package manager)..."
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://astral.sh/uv/install.sh | sh
  else
    echo "[moon-tracker] Need curl or wget to install uv:" >&2
    echo "  https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
  fi
  export PATH="$HOME/.local/bin:$PATH"
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "[moon-tracker] uv not found after install. Restart your terminal and re-run ./run.sh" >&2
  exit 1
fi

if [ -z "$PY" ]; then
  echo "[moon-tracker] No Python 3.10+ found. Installing Python 3.12 via uv..."
  uv python install 3.12 || {
    echo "[moon-tracker] Python install failed. Install Python 3.10+ manually." >&2
    exit 1
  }
fi

if [ ! -d ".venv" ]; then
  echo "[moon-tracker] First run: downloading dependencies (~100MB for Flet, please wait)..."
fi

# Pin the venv interpreter to the detected Python so every machine builds
# the same env; without --python, uv picks its own per machine.
SYNC_ARGS=(--frozen)
[ -n "$PY" ] && SYNC_ARGS+=(--python "$PY")
uv sync "${SYNC_ARGS[@]}" || {
  echo "[moon-tracker] Dependency sync failed. Check your connection and re-run." >&2
  exit 1
}

if ! uv run --frozen python -c "import Xlib" 2>/dev/null; then
  echo "[moon-tracker] NOTE: python3-xlib not importable."
  echo "  If window titles show as unknown, try: sudo apt install python3-xlib"
fi

exec uv run --frozen python -m moon_tracker "$@"
