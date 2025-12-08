#!/usr/bin/env bash

# NOTE: This script is intended to be both executed and sourced.
# - When executed: run the migration CLI.
# - When sourced:  only register completion; DO NOT change shell options or exit.

# Wrapper script for running database migrations
# Usage:
#   run_migration.sh migrate <migration_file>
#   run_migration.sh rollback <migration_file>
#
# Tab completion is available for migration files after typing migrate/rollback

# When sourced from an interactive shell, \$0 may be something like "-bash" or "-zsh",
# which breaks dirname. In that case, fall back to the current working directory.
if [[ "$0" == -* ]]; then
    SCRIPT_DIR="$PWD"
else
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MIGRATIONS_DIR="$PROJECT_ROOT/migrations"
DB_PATH="$PROJECT_ROOT/data/companies.db"

show_help() {
    cat <<EOF
Usage: run_migration.sh <command> <migration_file>

Commands:
  migrate   Run the migrate() function from the specified migration
  rollback  Run the rollback() function from the specified migration

Examples:
  run_migration.sh migrate 20251203000000_normalize_compensation_values.py
  run_migration.sh rollback 20251203000000_normalize_compensation_values.py

Tab completion:
  To enable tab completion, source this script first:
    source scripts/run_migration.sh
  Then type 'run_migration.sh migrate ' or 'run_migration.sh rollback ' and press Tab
  to see available migrations.

Database: $DB_PATH
Migrations directory: $MIGRATIONS_DIR
EOF
}

# Get list of migration files (excluding __init__.py and __pycache__)
get_migration_files() {
    if [ ! -d "$MIGRATIONS_DIR" ]; then
        return
    fi
    # Use portable find command (works on both GNU and BSD find)
    find "$MIGRATIONS_DIR" -maxdepth 1 -type f -name "*.py" ! -name "__init__.py" -exec basename {} \; | sort
}

# Tab completion function
_complete_migrations() {
    local cur="${COMP_WORDS[COMP_CWORD]}"

    # If we're completing the first argument (command), suggest migrate/rollback
    if [ "$COMP_CWORD" -eq 1 ]; then
        COMPREPLY=($(compgen -W "migrate rollback" -- "$cur"))
        return
    fi

    # For second and subsequent arguments, always suggest migration files
    if [ "$COMP_CWORD" -ge 2 ]; then
        # Find migrations directory relative to script location of the command
        local script_path="${COMP_WORDS[0]}"
        local script_dir
        if [[ "$script_path" == /* ]]; then
            # Absolute path
            script_dir="$(dirname "$script_path")"
        else
            # Relative path - resolve from current directory
            script_dir="$(cd "$(dirname "$script_path")" && pwd)"
        fi
        local migrations_dir="$script_dir/../migrations"

        if [ -d "$migrations_dir" ]; then
            local migrations
            migrations=$(find "$migrations_dir" -maxdepth 1 -type f -name "*.py" ! -name "__init__.py" -exec basename {} \; 2>/dev/null | sort)
            COMPREPLY=($(compgen -W "$migrations" -- "$cur"))
        else
            COMPREPLY=()
        fi
        return
    fi
}

run_migration_main() {
    # Enable strict mode only for the CLI execution path
    set -euo pipefail

    if [ $# -eq 0 ]; then
        show_help
        return 0
    fi

    local COMMAND="${1:-}"
    local MIGRATION_FILE="${2:-}"

    if [ -z "$COMMAND" ]; then
        show_help
        return 0
    fi

    if [ "$COMMAND" != "migrate" ] && [ "$COMMAND" != "rollback" ]; then
        echo "Error: Command must be 'migrate' or 'rollback'" >&2
        echo ""
        show_help
        return 1
    fi

    if [ -z "$MIGRATION_FILE" ]; then
        echo "Error: Migration file is required" >&2
        echo ""
        show_help
        return 1
    fi

    local MIGRATION_PATH="$MIGRATIONS_DIR/$MIGRATION_FILE"

    if [ ! -f "$MIGRATION_PATH" ]; then
        echo "Error: Migration file not found: $MIGRATION_PATH" >&2
        return 1
    fi

    if [ ! -f "$DB_PATH" ]; then
        echo "Error: Database not found: $DB_PATH" >&2
        return 1
    fi

    # Run the migration using Python
    python3 <<PYTHON_SCRIPT
import sys
import sqlite3
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

migration_path = Path("$MIGRATION_PATH")
db_path = "$DB_PATH"
command = "$COMMAND"

# Load the migration module
module_name = migration_path.stem
spec = spec_from_file_location(module_name, str(migration_path))
if spec is None or spec.loader is None:
    print(f"Error: Failed to create module spec for {migration_path}", file=sys.stderr)
    sys.exit(1)

module = module_from_spec(spec)
spec.loader.exec_module(module)

# Check if the function exists
if not hasattr(module, command):
    print(f"Error: Migration {migration_path.name} does not have a {command}() function", file=sys.stderr)
    sys.exit(1)

# Connect to database and run the migration
conn = sqlite3.connect(db_path)
try:
    print(f"Running {command}() from {migration_path.name}...")
    func = getattr(module, command)
    func(conn)
    conn.commit()
    print(f"Successfully completed {command} for {migration_path.name}")
except Exception as e:
    conn.rollback()
    print(f"Error during {command}: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    conn.close()
PYTHON_SCRIPT
}

# Register completion (safe when sourced; does not exit or change shell options)
if command -v complete >/dev/null 2>&1; then
    script_basename="$(basename "${BASH_SOURCE[0]-$0}")"
    # Resolve directory of this script as best we can
    script_dirname="$(cd "$(dirname "${BASH_SOURCE[0]-$0}")" 2>/dev/null && pwd || printf ".")"
    script_abs="${script_dirname}/${script_basename}"

    # Common invocation forms:
    #   run_migration.sh
    #   ./run_migration.sh
    #   scripts/run_migration.sh
    #   ./scripts/run_migration.sh
    #   /abs/path/to/scripts/run_migration.sh
    complete -F _complete_migrations "$script_basename" 2>/dev/null || true
    complete -F _complete_migrations "./$script_basename" 2>/dev/null || true
    complete -F _complete_migrations "scripts/$script_basename" 2>/dev/null || true
    complete -F _complete_migrations "./scripts/$script_basename" 2>/dev/null || true
    complete -F _complete_migrations "$script_abs" 2>/dev/null || true
fi

# If the script is executed directly, run the main CLI. If sourced, do nothing.
if [[ "${BASH_SOURCE[0]-$0}" == "$0" ]]; then
    run_migration_main "$@"
fi

 