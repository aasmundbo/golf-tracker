"""Backfill round.user_id: set all NULL rows to the first admin user's ID."""
import os
import sqlite3
import sys


def main() -> None:
    db_url = os.environ.get("DATABASE_URL", "sqlite:///./golf.db")
    if "sqlite" not in db_url:
        print("This script only supports SQLite.")
        sys.exit(1)

    # Extract filesystem path from URL (handles both sqlite:/// and sqlite+aiosqlite:///)
    db_path = db_url.split("///", 1)[-1]

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1")
    except sqlite3.OperationalError:
        print("Table 'users' not found. 0 rows updated.")
        conn.close()
        return

    row = cur.fetchone()
    if not row:
        print("No admin user found. 0 rows updated.")
        conn.close()
        return

    admin_id = row[0]

    try:
        cur.execute("UPDATE rounds SET user_id = ? WHERE user_id IS NULL", (admin_id,))
    except sqlite3.OperationalError:
        print("Table 'rounds' not found. 0 rows updated.")
        conn.close()
        return

    updated = cur.rowcount
    conn.commit()
    conn.close()
    print(f"Updated {updated} round(s) with user_id = {admin_id}.")


if __name__ == "__main__":
    main()
