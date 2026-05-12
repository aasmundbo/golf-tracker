"""Add preferred_tee_gender column to users table."""
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

    cur.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cur.fetchall()]
    if "preferred_tee_gender" in columns:
        print("Column 'preferred_tee_gender' already exists. Nothing to do.")
        conn.close()
        return

    cur.execute("ALTER TABLE users ADD COLUMN preferred_tee_gender TEXT NULL")
    conn.commit()
    conn.close()
    print("Added 'preferred_tee_gender' column to users table.")


if __name__ == "__main__":
    main()
