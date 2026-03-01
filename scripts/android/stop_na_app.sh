#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SESSION_NAME="${SESSION_NAME:-na_app}"
PROOT_DISTRO="${PROOT_DISTRO:-debian}"

INNER_SCRIPT='
set -euo pipefail

if ! command -v tmux >/dev/null 2>&1; then
  echo "ERROR: tmux is not installed inside Debian." >&2
  exit 3
fi

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  tmux kill-session -t "$SESSION_NAME"
  echo "Stopped session '\''$SESSION_NAME'\''."
else
  echo "Session '\''$SESSION_NAME'\'' is not running."
fi
'

if command -v proot-distro >/dev/null 2>&1; then
  proot-distro login "$PROOT_DISTRO" -- env \
    SESSION_NAME="$SESSION_NAME" \
    bash -lc "$INNER_SCRIPT"
else
  env SESSION_NAME="$SESSION_NAME" bash -lc "$INNER_SCRIPT"
fi

if command -v termux-wake-unlock >/dev/null 2>&1; then
  termux-wake-unlock
fi
