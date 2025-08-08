#!/usr/bin/env python3
import argparse
import os
import re
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[1] / 'db.sqlite3'

def normalize(db_path: str, dry_run: bool = False, limit: int | None = None):
    if not os.path.exists(db_path):
        print(f"[FAIL] Database not found: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Detect actual table name (Django default is app_model)
    # Try common names first
    table_candidates = [
        'uploader_instagramaccount',  # app_label_model
        'InstagramAccount',           # unlikely, but try
        'instagramaccount'            # lowercase
    ]

    table_name = None
    for t in table_candidates:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,))
        if cur.fetchone():
            table_name = t
            break

    if not table_name:
        # Fallback: search by columns
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for row in cur.fetchall():
            t = row['name']
            try:
                cur.execute(f"PRAGMA table_info({t})")
                cols = [r['name'] for r in cur.fetchall()]
                if {'username', 'tfa_secret'}.issubset(set(cols)):
                    table_name = t
                    break
            except Exception:
                continue

    if not table_name:
        print("[FAIL] Could not locate InstagramAccount table.")
        return 1

    # Build query
    base_query = f"SELECT id, username, tfa_secret FROM {table_name}"
    if limit:
        base_query += f" ORDER BY id ASC LIMIT {int(limit)}"

    cur.execute(base_query)
    rows = cur.fetchall()

    total = len(rows)
    updated = 0
    skipped = 0

    print(f"[START] Normalizing TFA secrets in table '{table_name}' (dry_run={dry_run}) - {total} rows")

    for r in rows:
        acc_id = r['id']
        username = r['username']
        original = r['tfa_secret'] or ''
        if not original:
            skipped += 1
            continue
        normalized = re.sub(r"\s+", "", original)
        if normalized != original:
            print(f"[UPDATE] {username}: '{original}' -> '{normalized}'" + (" (dry-run)" if dry_run else ""))
            if not dry_run:
                cur.execute(
                    f"UPDATE {table_name} SET tfa_secret = ? WHERE id = ?",
                    (normalized, acc_id),
                )
                updated += 1
        else:
            skipped += 1

    if not dry_run:
        conn.commit()

    print(f"[DONE] Updated: {updated}, Unchanged/Skipped: {skipped}, Total: {total}")
    conn.close()
    return 0


def main():
    parser = argparse.ArgumentParser(description="Normalize InstagramAccount.tfa_secret (remove whitespace)")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to SQLite DB (default: project db.sqlite3)")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without saving")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of rows to process")
    args = parser.parse_args()
    raise SystemExit(normalize(args.db, args.dry_run, args.limit))


if __name__ == "__main__":
    main() 