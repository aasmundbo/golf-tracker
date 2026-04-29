import math

def calculate_playing_handicap(hcp_index: float, slope: float, course_rating: float, par: int) -> int:
    return round(hcp_index * (slope / 113))

def handicap_strokes_on_hole(hole_stroke_index: int | None, playing_handicap: int) -> int:
    if hole_stroke_index is None:
        return 0
    strokes = 0
    if playing_handicap >= hole_stroke_index:
        strokes += 1
    if playing_handicap > 18 and hole_stroke_index <= (playing_handicap - 18):
        strokes += 1
    return strokes

def net_score_on_hole(strokes: int, par: int, hcp_strokes: int) -> int:
    return strokes - par - hcp_strokes

def calculate_live_stats(scores: list[dict], playing_handicap: int, total_holes: int = 18) -> dict:
    gross_total = 0
    net_total = 0
    stableford_total = 0
    par_played = 0

    for s in scores:
        par = s.get("hole_par") or 4
        hcp_strokes = handicap_strokes_on_hole(s.get("hole_stroke_index"), playing_handicap)
        gross_total += s["strokes"]
        par_played += par
        net = net_score_on_hole(s["strokes"], par, hcp_strokes)
        net_total += net
        stableford_total += max(0, 2 + hcp_strokes - (s["strokes"] - par))

    return {
        "holes_played": len(scores),
        "gross_total": gross_total,
        "net_total": net_total,
        "gross_to_par": gross_total - par_played,
        "net_to_par": net_total,
        "stableford_total": stableford_total,
    }
