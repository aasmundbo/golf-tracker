import math

def calculate_playing_handicap(hcp_index: float, slope: float, course_rating: float, par: int) -> int:
    return round(hcp_index * (slope / 113))


def calculate_projected_handicap(
    scores: list[dict],
    hole_data: list[dict],
    playing_handicap: int,
    course_rating: float,
    slope: float,
) -> dict:
    """
    Project a full-round WHS handicap differential mid-round.

    Completed holes use actual gross capped at net double bogey.
    Unplayed holes are assumed to be played to net par (par + hcp_strokes).

    hole_by_hole[h] = full projected differential assuming actual scores for
    played holes ≤ h and net-par projection for all others.
    """
    scored_by_hole = {s["hole_number"]: s for s in scores}
    data_by_hole = {h["hole_number"]: h for h in hole_data}

    per_hole = {}
    for h in range(1, 19):
        par, si = None, None
        if h in scored_by_hole:
            s = scored_by_hole[h]
            par = s.get("hole_par")
            si = s.get("hole_stroke_index")
        if (par is None or si is None) and h in data_by_hole:
            hd = data_by_hole[h]
            par = par or hd.get("par")
            si = si or hd.get("stroke_index")
        if par is None or si is None:
            return {
                "holes_played": len(scores),
                "projected_differential": None,
                "hole_by_hole": [],
            }

        hcp_str = handicap_strokes_on_hole(si, playing_handicap)
        projected = par + hcp_str

        if h in scored_by_hole:
            adj_actual = min(scored_by_hole[h]["strokes"], par + 2 + hcp_str)
        else:
            adj_actual = projected

        per_hole[h] = {"projected": projected, "actual": adj_actual, "scored": h in scored_by_hole}

    projected_total = sum(v["projected"] for v in per_hole.values())

    hole_by_hole = []
    cumulative_delta = 0
    for h in range(1, 19):
        ph = per_hole[h]
        if ph["scored"]:
            cumulative_delta += ph["actual"] - ph["projected"]
        adj_at_h = projected_total + cumulative_delta
        hole_by_hole.append({
            "hole": h,
            "projected_differential_after_hole": round((adj_at_h - course_rating) * 113 / slope, 1),
        })

    total_delta = sum(v["actual"] - v["projected"] for v in per_hole.values() if v["scored"])
    total_adj = projected_total + total_delta
    return {
        "holes_played": len(scores),
        "projected_differential": round((total_adj - course_rating) * 113 / slope, 1),
        "hole_by_hole": hole_by_hole,
    }

def handicap_strokes_on_hole(hole_stroke_index: int | None, playing_handicap: int) -> int:
    if hole_stroke_index is None or playing_handicap <= 0:
        return 0
    base = playing_handicap // 18
    extra = playing_handicap % 18
    return base + (1 if hole_stroke_index <= extra else 0)

def net_score_on_hole(strokes: int, par: int, hcp_strokes: int) -> int:
    return strokes - par - hcp_strokes

def calculate_live_stats(scores: list[dict], playing_handicap: int, total_holes: int = 18) -> dict:
    gross_total = 0
    net_total = 0
    stableford_total = 0
    par_played = 0
    holes_played = 0

    for s in scores:
        strokes = s.get("strokes")
        hole_par = s.get("hole_par")
        if strokes is None or hole_par is None:
            continue
        holes_played += 1
        hcp_strokes = handicap_strokes_on_hole(s.get("hole_stroke_index"), playing_handicap)
        gross_total += strokes
        par_played += hole_par
        net = net_score_on_hole(strokes, hole_par, hcp_strokes)
        net_total += net
        stableford_total += max(0, 2 + hcp_strokes - (strokes - hole_par))

    return {
        "holes_played": holes_played,
        "gross_total": gross_total,
        "net_total": net_total,
        "gross_to_par": gross_total - par_played,
        "net_to_par": net_total,
        "stableford_total": stableford_total,
    }
