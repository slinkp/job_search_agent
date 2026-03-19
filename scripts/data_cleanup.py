#!/usr/bin/env python
"""
Inspect Chroma's SQLite metadata and the on-disk HNSW index directories under
`data/` to find *orphaned* index directories that are no longer referenced by
any segment in the database.

By default this script is read-only: it prints what it finds and exits.
If you pass --delete-orphans, it will remove only those directories that are
confirmed to be unused according to the SQLite metadata.

Usage (from repo root):

    python scripts/chroma_vector_dir_gc.py
    python scripts/chroma_vector_dir_gc.py --delete-orphans
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sqlite3
from typing import Iterable, Set, Tuple

DEFAULT_DATA_DIR = pathlib.Path("data")
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "chroma.sqlite3"
DEFAULT_BACKUP_DB_PATH = DEFAULT_DATA_DIR / "chroma.sqlite3.1"

HNSW_SEGMENT_TYPE = "urn:chroma:segment/vector/hnsw-local-persisted"


def get_hnsw_segment_ids(conn: sqlite3.Connection) -> Set[str]:
    """Return IDs of HNSW vector segments that should have on-disk index dirs."""
    # segments.id is a TEXT primary key; for HNSW vector segments we expect a
    # corresponding directory named <id> in the data directory.
    cur = conn.execute(
        """
        SELECT id
        FROM segments
        WHERE type = ?
          AND scope = 'VECTOR'
        """,
        (HNSW_SEGMENT_TYPE,),
    )
    rows = cur.fetchall()
    return {row[0] for row in rows}


def get_hnsw_segment_ids_from_db(path: pathlib.Path) -> Set[str]:
    """
    Open the given DB path (if it exists) and return HNSW segment IDs.

    If the file does not exist, an empty set is returned.
    """
    if not path.exists():
        return set()
    conn = sqlite3.connect(path)
    try:
        return get_hnsw_segment_ids(conn)
    finally:
        conn.close()


def list_uuid_like_dirs(data_dir: pathlib.Path) -> Set[str]:
    """
    Return basenames of UUID-like subdirectories directly under data_dir.

    We intentionally do not recurse. Chroma's HNSW index directories live
    directly under the data/ root.
    """
    if not data_dir.is_dir():
        return set()

    result: Set[str] = set()
    for child in data_dir.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        # Very loose UUID-ish check: 4 hyphens and at least one character part.
        if name.count("-") == 4:
            result.add(name)
    return result


def compute_orphans(
    dir_names: Iterable[str], segment_ids: Iterable[str]
) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    Given on-disk directory names and known HNSW segment IDs, return:

    - orphan_dirs: directory basenames that are not referenced by any segment
    - missing_dirs: segment IDs that have no corresponding directory on disk
    - matched: intersection of both sets
    """
    dir_set = set(dir_names)
    seg_set = set(segment_ids)
    matched = dir_set & seg_set
    orphan_dirs = dir_set - seg_set
    missing_dirs = seg_set - dir_set
    return orphan_dirs, missing_dirs, matched


def delete_orphan_dirs(data_dir: pathlib.Path, orphan_names: Iterable[str]) -> None:
    """Delete the given orphan directories under data_dir."""
    for name in orphan_names:
        path = data_dir / name
        if not path.exists():
            continue
        if not path.is_dir():
            continue
        # Final safety check: ensure this still looks like a UUID-ish name.
        if name.count("-") != 4:
            continue
        print(f"Deleting orphan directory: {path}")
        # Use os.removedirs to remove the directory and any empty parents;
        # in practice parents should not be removed because data_dir is not empty.
        for root, dirs, files in os.walk(path, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
            for d in dirs:
                os.rmdir(os.path.join(root, d))
        os.rmdir(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Identify (and optionally delete) Chroma HNSW index directories "
            "under data/ that are no longer referenced by any segment in "
            "chroma.sqlite3."
        )
    )
    parser.add_argument(
        "--data-dir",
        type=pathlib.Path,
        default=DEFAULT_DATA_DIR,
        help="Path to data directory containing chroma.sqlite3 and index dirs "
        "(default: data/)",
    )
    parser.add_argument(
        "--db-path",
        type=pathlib.Path,
        default=DEFAULT_DB_PATH,
        help="Path to primary chroma.sqlite3 (default: data/chroma.sqlite3)",
    )
    parser.add_argument(
        "--backup-db-path",
        type=pathlib.Path,
        default=DEFAULT_BACKUP_DB_PATH,
        help=(
            "Path to backup chroma.sqlite3 to also preserve segments from "
            "(default: data/chroma.sqlite3.1; ignored if missing)"
        ),
    )
    parser.add_argument(
        "--delete-orphans",
        action="store_true",
        help="Actually delete orphaned index directories. By default this runs "
        "in read-only mode and only reports what it would delete.",
    )

    args = parser.parse_args()

    data_dir: pathlib.Path = args.data_dir
    db_path: pathlib.Path = args.db_path
    backup_db_path: pathlib.Path = args.backup_db_path

    if not db_path.exists():
        raise SystemExit(f"Chroma DB not found at {db_path}")

    print(f"Using data dir: {data_dir}")
    print(f"Using Chroma DB: {db_path}")
    if backup_db_path.exists():
        print(f"Also preserving segments referenced in backup DB: {backup_db_path}")
    else:
        print(f"Backup DB not found (will ignore): {backup_db_path}")
    print()

    # Collect HNSW segment IDs from primary and backup DB (if present).
    primary_segment_ids = get_hnsw_segment_ids_from_db(db_path)
    backup_segment_ids = get_hnsw_segment_ids_from_db(backup_db_path)
    segment_ids = primary_segment_ids | backup_segment_ids

    dir_names = list_uuid_like_dirs(data_dir)

    orphan_dirs, missing_dirs, matched = compute_orphans(dir_names, segment_ids)

    print(f"HNSW segment IDs in DB: {len(segment_ids)}")
    print(f"UUID-like index dirs on disk: {len(dir_names)}")
    print(f"Matched (have DB segment and dir): {len(matched)}")
    print(f"Orphan dirs (on disk, no DB segment): {len(orphan_dirs)}")
    print(f"Missing dirs (DB segment, no dir on disk): {len(missing_dirs)}")
    print()

    if matched:
        print("Matched segment/dir IDs (examples):")
        for sid in sorted(list(matched))[:10]:
            print(f"  {sid}")
        if len(matched) > 10:
            print(f"  ... and {len(matched) - 10} more")
        print()

    if orphan_dirs:
        print("Orphan directory candidates (on disk, not referenced in DB):")
        for name in sorted(orphan_dirs):
            print(f"  {data_dir / name}")
        print()
    else:
        print("No orphan directory candidates found.")
        print()

    if missing_dirs:
        print("WARNING: DB references segments with no on-disk directory:")
        for sid in sorted(missing_dirs):
            print(f"  {sid}")
        print(
            "This may indicate a previous partial cleanup or data corruption; "
            "consider investigating before deleting anything."
        )
        print()

    if not orphan_dirs:
        return

    if not args.delete_orphans:
        print(
            "Dry run only. Re-run with --delete-orphans to remove the orphan "
            "directories listed above."
        )
        return

    print("Deleting orphan directories (as requested with --delete-orphans)...")
    delete_orphan_dirs(data_dir, orphan_dirs)
    print("Done.")


if __name__ == "__main__":
    main()
