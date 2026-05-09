"""Add projected_hcp column to rounds table."""
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

    if "projected_hcp" not in columns:
        cur.execute("ALTER TABLE rounds ADD COLUMN projected_hcp REAL")
        conn.commit()
        print("Added column 'projected_hcp' to rounds.")
    else:
        print("Column 'projected_hcp' already exists on rounds. Nothing to do.")

    conn.close()


if __name__ == "__main__":
    main()
