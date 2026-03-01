#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SESSION_NAME="${SESSION_NAME:-na_app}"
PROOT_DISTRO="${PROOT_DISTRO:-debian}"
NACH_PORT="${NACH_PORT:-8080}"

INNER_SCRIPT='
set -euo pipefail

session_up=0
listener_up=0

if command -v tmux >/dev/null 2>&1 && tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  session_up=1
fi

if command -v ss >/dev/null 2>&1; then
  if ss -ltn 2>/dev/null | grep -Eq "[:.]${NACH_PORT}([[:space:]]|$)"; then
    listener_up=1
  fi
fi

if [ "$session_up" -eq 1 ]; then
  echo "tmux session: up ($SESSION_NAME)"
else
  echo "tmux session: down ($SESSION_NAME)"
fi

if [ "$listener_up" -eq 1 ]; then
  echo "port listener: up (:$NACH_PORT)"
else
  echo "port listener: down (:$NACH_PORT)"
fi

if [ "$session_up" -eq 1 ] && [ "$listener_up" -eq 1 ]; then
  exit 0
fi
exit 1
'

set +e
if command -v proot-distro >/dev/null 2>&1; then
  proot-distro login "$PROOT_DISTRO" -- env \
    SESSION_NAME="$SESSION_NAME" \
    NACH_PORT="$NACH_PORT" \
    bash -lc "$INNER_SCRIPT"
  status=$?
else
  env \
    SESSION_NAME="$SESSION_NAME" \
    NACH_PORT="$NACH_PORT" \
    bash -lc "$INNER_SCRIPT"
  status=$?
fi
set -e

exit "$status"
