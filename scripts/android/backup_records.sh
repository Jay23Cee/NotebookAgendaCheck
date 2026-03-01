#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PROOT_DISTRO="${PROOT_DISTRO:-debian}"
PROJECT_DIR="${PROJECT_DIR:-/root/NotebookAgendaCheck}"
BACKUP_ROOT="${BACKUP_ROOT:-/sdcard/Documents/App_Backups/NotebookAgendaCheck}"

INNER_SCRIPT='
set -euo pipefail

RECORDS_DIR="$PROJECT_DIR/records"
if [ ! -d "$RECORDS_DIR" ]; then
  echo "ERROR: records directory not found: $RECORDS_DIR" >&2
  exit 3
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="$BACKUP_ROOT/$timestamp"
latest_dir="$BACKUP_ROOT/latest"
mkdir -p "$backup_dir"

copied_any=0

for filename in notebook_agenda_checks.csv na_check_error_log.csv; do
  src="$RECORDS_DIR/$filename"
  if [ -f "$src" ]; then
    cp -f "$src" "$backup_dir/$filename"
    copied_any=1
  fi
done

if [ -d "$RECORDS_DIR/quarantine" ]; then
  mkdir -p "$backup_dir/quarantine"
  cp -a "$RECORDS_DIR/quarantine/." "$backup_dir/quarantine/"
  copied_any=1
fi

if [ "$copied_any" -eq 0 ]; then
  echo "ERROR: no backup sources found in $RECORDS_DIR" >&2
  exit 4
fi

rm -rf "$latest_dir"
mkdir -p "$latest_dir"
cp -a "$backup_dir/." "$latest_dir/"

echo "Backup created: $backup_dir"
echo "Latest mirror: $latest_dir"
'

if command -v proot-distro >/dev/null 2>&1; then
  proot-distro login "$PROOT_DISTRO" -- env \
    PROJECT_DIR="$PROJECT_DIR" \
    BACKUP_ROOT="$BACKUP_ROOT" \
    bash -lc "$INNER_SCRIPT"
else
  env \
    PROJECT_DIR="$PROJECT_DIR" \
    BACKUP_ROOT="$BACKUP_ROOT" \
    bash -lc "$INNER_SCRIPT"
fi
