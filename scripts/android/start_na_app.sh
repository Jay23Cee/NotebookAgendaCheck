#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SESSION_NAME="${SESSION_NAME:-na_app}"
PROOT_DISTRO="${PROOT_DISTRO:-debian}"
PROJECT_DIR="${PROJECT_DIR:-/root/NotebookAgendaCheck}"
NACH_HOST="${NACH_HOST:-127.0.0.1}"
NACH_PORT="${NACH_PORT:-8080}"
NACH_SHOW="${NACH_SHOW:-false}"
NACH_RELOAD="${NACH_RELOAD:-false}"

if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock
fi

INNER_SCRIPT='
set -euo pipefail

if ! command -v tmux >/dev/null 2>&1; then
  echo "ERROR: tmux is not installed inside Debian." >&2
  exit 3
fi

if [ ! -d "$PROJECT_DIR" ]; then
  echo "ERROR: project directory not found: $PROJECT_DIR" >&2
  exit 4
fi

if [ ! -f "$PROJECT_DIR/.venv/bin/activate" ]; then
  echo "ERROR: venv not found at $PROJECT_DIR/.venv" >&2
  exit 5
fi

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "Session '\''$SESSION_NAME'\'' already running."
  exit 0
fi

APP_CMD="cd \"$PROJECT_DIR\" && . .venv/bin/activate && export NACH_HOST=\"$NACH_HOST\" NACH_PORT=\"$NACH_PORT\" NACH_SHOW=\"$NACH_SHOW\" NACH_RELOAD=\"$NACH_RELOAD\" && python -m notebookagendacheck"
tmux new-session -d -s "$SESSION_NAME" "$APP_CMD"
echo "Started session '\''$SESSION_NAME'\'' with host=$NACH_HOST port=$NACH_PORT."
'

if command -v proot-distro >/dev/null 2>&1; then
  proot-distro login "$PROOT_DISTRO" -- env \
    SESSION_NAME="$SESSION_NAME" \
    PROJECT_DIR="$PROJECT_DIR" \
    NACH_HOST="$NACH_HOST" \
    NACH_PORT="$NACH_PORT" \
    NACH_SHOW="$NACH_SHOW" \
    NACH_RELOAD="$NACH_RELOAD" \
    bash -lc "$INNER_SCRIPT"
else
  env \
    SESSION_NAME="$SESSION_NAME" \
    PROJECT_DIR="$PROJECT_DIR" \
    NACH_HOST="$NACH_HOST" \
    NACH_PORT="$NACH_PORT" \
    NACH_SHOW="$NACH_SHOW" \
    NACH_RELOAD="$NACH_RELOAD" \
    bash -lc "$INNER_SCRIPT"
fi
