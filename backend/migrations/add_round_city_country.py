"""Add city and country columns to rounds table."""
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

    cur.execute("PRAGMA table_info(rounds)")
    columns = [row[1] for row in cur.fetchall()]

    added = []
    if "city" not in columns:
        cur.execute("ALTER TABLE rounds ADD COLUMN city TEXT")
        added.append("city")
    if "country" not in columns:
        cur.execute("ALTER TABLE rounds ADD COLUMN country TEXT")
        added.append("country")

    conn.commit()
    conn.close()

    if added:
        print(f"Added columns to rounds: {', '.join(added)}")
    else:
        print("Columns 'city' and 'country' already exist on rounds. Nothing to do.")


if __name__ == "__main__":
    main()
