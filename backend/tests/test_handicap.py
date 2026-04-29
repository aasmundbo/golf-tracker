from services.handicap import (
    calculate_playing_handicap,
    handicap_strokes_on_hole,
    net_score_on_hole,
    calculate_live_stats,
)

def test_playing_handicap_baerum_gul():
    # Bærum Golfklubb, Gul: slope=132, CR=69.7, par=71, hcp=18.4
    # WHS: round(18.4 * 132/113 + (69.7 - 71)) = round(20.19) = 20
    result = calculate_playing_handicap(18.4, 132, 69.7, 71)
    assert result == 20

def test_playing_handicap_scratch():
    result = calculate_playing_handicap(0.0, 113, 72.0, 72)
    assert result == 0

def test_playing_handicap_low():
    result = calculate_playing_handicap(5.0, 113, 72.0, 72)
    assert result == 5

def test_handicap_strokes_on_hole_basic():
    # playing hcp 18: gets 1 stroke on every hole (SI 1-18)
    assert handicap_strokes_on_hole(1, 18) == 1
    assert handicap_strokes_on_hole(18, 18) == 1

def test_handicap_strokes_on_hole_no_stroke():
    # playing hcp 10: only gets strokes on SI 1-10
    assert handicap_strokes_on_hole(10, 10) == 1
    assert handicap_strokes_on_hole(11, 10) == 0

def test_handicap_strokes_above_18():
    # playing hcp 20: 2 strokes on SI 1-2, 1 stroke on SI 3-18
    assert handicap_strokes_on_hole(1, 20) == 2
    assert handicap_strokes_on_hole(2, 20) == 2
    assert handicap_strokes_on_hole(3, 20) == 1
    assert handicap_strokes_on_hole(18, 20) == 1

def test_handicap_strokes_none_si():
    # No stroke index available → 0 strokes
    assert handicap_strokes_on_hole(None, 18) == 0

def test_net_score_par():
    # 4 strokes, par 4, 1 hcp stroke → net = 4 - 4 - 1 = -1
    assert net_score_on_hole(4, 4, 1) == -1

def test_net_score_bogey_no_stroke():
    # 5 strokes, par 4, 0 hcp strokes → net = 1
    assert net_score_on_hole(5, 4, 0) == 1

def test_stableford_par_with_stroke():
    # par with 1 hcp stroke = 2 + 1 - (4-4) = 3 points
    scores = [{"hole_number": 1, "strokes": 4, "hole_par": 4, "hole_stroke_index": 1}]
    stats = calculate_live_stats(scores, playing_handicap=18)
    assert stats["stableford_total"] == 3

def test_stableford_bogey_no_stroke():
    # bogey, no stroke = 2 + 0 - 1 = 1 point
    scores = [{"hole_number": 1, "strokes": 5, "hole_par": 4, "hole_stroke_index": 18}]
    stats = calculate_live_stats(scores, playing_handicap=10)
    assert stats["stableford_total"] == 1

def test_stableford_double_bogey_no_stroke():
    # double bogey, no stroke = max(0, 2+0-2) = 0 points
    scores = [{"hole_number": 1, "strokes": 6, "hole_par": 4, "hole_stroke_index": 18}]
    stats = calculate_live_stats(scores, playing_handicap=10)
    assert stats["stableford_total"] == 0

def test_live_stats_multiple_holes():
    scores = [
        {"hole_number": 1, "strokes": 5, "hole_par": 4, "hole_stroke_index": 1},
        {"hole_number": 2, "strokes": 3, "hole_par": 3, "hole_stroke_index": 17},
        {"hole_number": 3, "strokes": 6, "hole_par": 5, "hole_stroke_index": 9},
    ]
    stats = calculate_live_stats(scores, playing_handicap=18)
    assert stats["holes_played"] == 3
    assert stats["gross_total"] == 14
    # All SI <= 18, so 1 stroke per hole
    # net per hole: (5-4-1)=0, (3-3-1)=-1, (6-5-1)=0 → total -1
    assert stats["net_to_par"] == -1
    assert stats["gross_to_par"] == 14 - 12  # 2 over par
