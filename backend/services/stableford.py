from services.handicap import handicap_strokes_on_hole

def stableford_points(strokes: int, par: int, hole_stroke_index: int | None, playing_handicap: int) -> int:
    hcp_strokes = handicap_strokes_on_hole(hole_stroke_index, playing_handicap)
    return max(0, 2 + hcp_strokes - (strokes - par))
