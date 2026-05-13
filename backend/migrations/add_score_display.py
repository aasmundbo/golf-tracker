"""Add score_display column to users table (default 'netto')."""
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
    if "score_display" in columns:
        print("Column 'score_display' already exists. Nothing to do.")
        conn.close()
        return

    cur.execute("ALTER TABLE users ADD COLUMN score_display TEXT NOT NULL DEFAULT 'netto'")
    conn.commit()
    conn.close()
    print("Added 'score_display' column to users table with default 'netto'.")


if __name__ == "__main__":
    main()
