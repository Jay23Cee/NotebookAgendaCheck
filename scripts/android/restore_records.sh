#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PROOT_DISTRO="${PROOT_DISTRO:-debian}"
PROJECT_DIR="${PROJECT_DIR:-/root/NotebookAgendaCheck}"
BACKUP_ROOT="${BACKUP_ROOT:-/sdcard/Documents/App_Backups/NotebookAgendaCheck}"
REQUESTED_BACKUP="${1:-latest}"

if [ "$REQUESTED_BACKUP" = "latest" ]; then
  SOURCE_DIR="$BACKUP_ROOT/latest"
elif [ -d "$REQUESTED_BACKUP" ]; then
  SOURCE_DIR="$REQUESTED_BACKUP"
else
  SOURCE_DIR="$BACKUP_ROOT/$REQUESTED_BACKUP"
fi

INNER_SCRIPT='
set -euo pipefail

if [ ! -d "$SOURCE_DIR" ]; then
  echo "ERROR: backup source not found: $SOURCE_DIR" >&2
  exit 3
fi

src_csv="$SOURCE_DIR/notebook_agenda_checks.csv"
src_log="$SOURCE_DIR/na_check_error_log.csv"
src_quarantine="$SOURCE_DIR/quarantine"

if [ ! -f "$src_csv" ] && [ ! -f "$src_log" ] && [ ! -d "$src_quarantine" ]; then
  echo "ERROR: backup source does not include expected files." >&2
  exit 4
fi

records_dir="$PROJECT_DIR/records"
mkdir -p "$records_dir"

if [ -f "$src_csv" ]; then
  cp -f "$src_csv" "$records_dir/notebook_agenda_checks.csv"
fi

if [ -f "$src_log" ]; then
  cp -f "$src_log" "$records_dir/na_check_error_log.csv"
fi

if [ -d "$src_quarantine" ]; then
  mkdir -p "$records_dir/quarantine"
  cp -a "$src_quarantine/." "$records_dir/quarantine/"
fi

echo "Restore complete from: $SOURCE_DIR"
echo "Restored into: $records_dir"
'

if command -v proot-distro >/dev/null 2>&1; then
  proot-distro login "$PROOT_DISTRO" -- env \
    PROJECT_DIR="$PROJECT_DIR" \
    SOURCE_DIR="$SOURCE_DIR" \
    bash -lc "$INNER_SCRIPT"
else
  env \
    PROJECT_DIR="$PROJECT_DIR" \
    SOURCE_DIR="$SOURCE_DIR" \
    bash -lc "$INNER_SCRIPT"
fi
