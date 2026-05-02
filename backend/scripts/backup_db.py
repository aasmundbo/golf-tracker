#!/usr/bin/env python3
# CRON SCHEDULE — run daily at 02:00:
#
#   0 2 * * * /usr/bin/python3 /app/scripts/backup_db.py >> /app/data/backups/backup.log 2>&1
#
# Or on the host (add to crontab with `crontab -e`):
#
#   0 2 * * * python3 /Users/aasmundbo/apps/golf-tracker/backend/scripts/backup_db.py >> /Users/aasmundbo/apps/golf-tracker/data/backups/backup.log 2>&1

import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Defaults work inside the container (/app/data/golf.db → /app/data/backups/).
# Override with DB_PATH and BACKUP_DIR env vars for host-side use.
DB_PATH = Path(os.environ.get("DB_PATH", "/app/data/golf.db"))
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/app/data/backups"))
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "7"))


def main() -> int:
    if not DB_PATH.exists():
        print(f"ERROR: database not found at {DB_PATH}", flush=True)
        return 1

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest = BACKUP_DIR / f"golf_{timestamp}.db"
    shutil.copy2(DB_PATH, dest)
    print(f"Backed up {DB_PATH} → {dest}", flush=True)

    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    for old in sorted(BACKUP_DIR.glob("golf_*.db")):
        try:
            file_time = datetime.fromtimestamp(old.stat().st_mtime)
        except OSError:
            continue
        if file_time < cutoff:
            old.unlink()
            print(f"Deleted old backup {old}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
