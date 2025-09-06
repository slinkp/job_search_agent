#!/usr/bin/env bash
set -euo pipefail

# Backup and rotate SQLite databases in a directory.
# - Creates consistent snapshots using `sqlite3 .backup` when available
# - Rotates: file -> file.1 (and shifts .1->.2 ... up to --keep)
# - Optionally gzips backups older than the most recent (.2+)
#
# Usage:
#   backup_sqlite.sh --dir /path/to/data --keep 7 --gzip
#
# Notes:
# - Only files ending with .db or .sqlite3 are considered as primaries (not numbered backups)
# - .1 remains uncompressed for quick access; .2+ may be gzipped with --gzip

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_DIR="${SCRIPT_DIR}/../data"
TARGET_DIR="$DEFAULT_DIR"
KEEP=7
GZIP=false

while [ $# -gt 0 ]; do
  case "$1" in
    --dir)
      TARGET_DIR="${2:-}"
      shift 2
      ;;
    --keep)
      KEEP="${2:-}"
      shift 2
      ;;
    --gzip)
      GZIP=true
      shift 1
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

# Validate KEEP as positive integer
case "$KEEP" in
  ''|*[!0-9]*) echo "--keep must be a positive integer" >&2; exit 2;;
  0) echo "--keep must be >= 1" >&2; exit 2;;
  *) ;;
esac

if [ ! -d "$TARGET_DIR" ]; then
  echo "Target directory does not exist: $TARGET_DIR" >&2
  exit 1
fi

have_sqlite=false
if command -v sqlite3 >/dev/null 2>&1; then
  have_sqlite=true
fi

backup_one() {
  local db_path="$1"
  local base="$db_path"  # e.g., /path/companies.db

  # Remove the oldest generation
  rm -f "${base}.${KEEP}" "${base}.${KEEP}.gz"

  # Shift older generations up
  local i
  for (( i=KEEP-1; i>=1; i-- )); do
    local src_plain="${base}.${i}"
    local src_gz="${base}.${i}.gz"
    local dest="${base}.$((i+1))"
    if [ -e "$src_gz" ]; then
      mv -f "$src_gz" "${dest}.gz"
    elif [ -e "$src_plain" ]; then
      mv -f "$src_plain" "$dest"
    fi
  done

  # Create fresh snapshot into .1
  local tmp="${base}.tmp.$$"
  if $have_sqlite; then
    if ! sqlite3 "$db_path" ".backup \"$tmp\""; then
      # Fallback to cp if .backup fails
      cp -p "$db_path" "$tmp"
    fi
  else
    cp -p "$db_path" "$tmp"
  fi
  mv -f "$tmp" "${base}.1"

  # Optionally gzip older generations (keep .1 uncompressed)
  if $GZIP; then
    for (( i=KEEP; i>=2; i-- )); do
      local older="${base}.${i}"
      if [ -e "$older" ]; then
        gzip -f "$older"
      fi
    done
  fi
}

# Enumerate base databases (not already numbered backups)
# Use find to avoid shell glob pitfalls and handle spaces safely.
while IFS= read -r -d '' db; do
  backup_one "$db"
done < <(find "$TARGET_DIR" -maxdepth 1 -type f \( -name '*.db' -o -name '*.sqlite3' \) ! -regex '.*\.[0-9]+\(\.gz\)?$' -print0)
