"""Remove GolfCourseAPI remnants from the database.

Drops:
  - external_api_id column from local_courses
  - course_api_cache table
Both operations are guarded: nothing happens if the artifact is already gone.
"""
import os
import sqlite3
import sys


def main() -> None:
    db_url = os.environ.get("DATABASE_URL", "sqlite:///./data/golf.db")
    if "sqlite" not in db_url:
        print("This script only supports SQLite.")
        sys.exit(1)

    db_path = db_url.split("///", 1)[-1]

    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # ── 1. Drop external_api_id from local_courses ────────────────────────────
    cur.execute("PRAGMA table_info(local_courses)")
    columns = [row[1] for row in cur.fetchall()]
    if "external_api_id" in columns:
        cur.execute("ALTER TABLE local_courses DROP COLUMN external_api_id")
        print("Dropped column 'external_api_id' from local_courses.")
    else:
        print("Column 'external_api_id' not found on local_courses. Nothing to do.")

    # ── 2. Drop course_api_cache table ────────────────────────────────────────
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='course_api_cache'"
    )
    if cur.fetchone():
        cur.execute("DROP TABLE course_api_cache")
        print("Dropped table 'course_api_cache'.")
    else:
        print("Table 'course_api_cache' not found. Nothing to do.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
