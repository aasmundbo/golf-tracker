"""Add gender column to local_tees table."""
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

    cur.execute("PRAGMA table_info(local_tees)")
    columns = [row[1] for row in cur.fetchall()]
    if "gender" in columns:
        print("Column 'gender' already exists on local_tees. Nothing to do.")
        conn.close()
        return

    cur.execute("ALTER TABLE local_tees ADD COLUMN gender VARCHAR(10)")
    conn.commit()
    conn.close()
    print("Added 'gender' column to local_tees table.")


if __name__ == "__main__":
    main()
