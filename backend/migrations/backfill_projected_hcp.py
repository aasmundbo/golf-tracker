"""Backfill projected_hcp for finished rounds that have NULL projected_hcp."""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.handicap import calculate_projected_handicap


def main() -> None:
    db_url = os.environ.get("DATABASE_URL", "sqlite:///./data/golf.db")
    if "sqlite" not in db_url:
        print("This script only supports SQLite.")
        sys.exit(1)

    db_path = db_url.split("///", 1)[-1]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        "SELECT id, playing_handicap, course_rating, slope, tee_id "
        "FROM rounds WHERE status='finished' AND projected_hcp IS NULL"
    )
    rounds = cur.fetchall()

    if not rounds:
        print("No rounds to backfill.")
        conn.close()
        return

    updated = 0
    for r in rounds:
        rid = r["id"]

        cur.execute(
            "SELECT hole_number, strokes, hole_par, hole_stroke_index "
            "FROM hole_scores WHERE round_id=? ORDER BY hole_number, id DESC",
            (rid,),
        )
        seen: dict[int, dict] = {}
        for s in cur.fetchall():
            hn = s["hole_number"]
            if hn not in seen:
                seen[hn] = {
                    "hole_number": hn,
                    "strokes": s["strokes"],
                    "hole_par": s["hole_par"],
                    "hole_stroke_index": s["hole_stroke_index"],
                }
        scores = list(seen.values())

        hole_data = []
        if r["tee_id"]:
            cur.execute(
                "SELECT hole_number, par, stroke_index FROM local_holes "
                "WHERE tee_id=? ORDER BY hole_number",
                (r["tee_id"],),
            )
            hole_data = [
                {"hole_number": h["hole_number"], "par": h["par"], "stroke_index": h["stroke_index"]}
                for h in cur.fetchall()
            ]

        try:
            proj = calculate_projected_handicap(
                scores=scores,
                hole_data=hole_data,
                playing_handicap=r["playing_handicap"],
                course_rating=r["course_rating"],
                slope=r["slope"],
            )
            diff = proj["projected_differential"]
        except Exception as e:
            print(f"  Round {rid}: calculation failed ({e}), skipping.")
            continue

        if diff is None:
            print(f"  Round {rid}: projected_differential is None (missing hole data), skipping.")
            continue

        cur.execute("UPDATE rounds SET projected_hcp=? WHERE id=?", (diff, rid))
        print(f"  Round {rid}: projected_hcp set to {diff}")
        updated += 1

    conn.commit()
    conn.close()
    print(f"Done. Updated {updated} round(s).")


if __name__ == "__main__":
    main()
