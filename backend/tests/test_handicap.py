from services.handicap import (
    calculate_playing_handicap,
    handicap_strokes_on_hole,
    calculate_live_stats,
)


# ── calculate_playing_handicap ────────────────────────────────────────────────

def test_barum_gul_playing_handicap():
    # Bærum GK, Gul tee: slope 132, CR 69.7, par 71, HCI 18.4 → 21
    assert calculate_playing_handicap(18.4, 132, 69.7, 71) == 21


def test_scratch_player_is_zero():
    assert calculate_playing_handicap(0.0, 113, 72, 72) == 0


# ── handicap_strokes_on_hole ──────────────────────────────────────────────────

def test_no_stroke_when_si_above_playing_hcp():
    # Hole SI 9, playing hcp 8 → 8 < 9, so 0 strokes
    assert handicap_strokes_on_hole(9, 8) == 0


def test_one_stroke_when_si_within_playing_hcp():
    assert handicap_strokes_on_hole(9, 9) == 1
    assert handicap_strokes_on_hole(1, 18) == 1


def test_none_si_returns_zero():
    assert handicap_strokes_on_hole(None, 18) == 0


def test_hcp_over_18_gives_two_strokes_on_lowest_si_holes():
    # playing_hcp=21: double strokes on SI ≤ (21-18)=3
    assert handicap_strokes_on_hole(1, 21) == 2
    assert handicap_strokes_on_hole(2, 21) == 2
    assert handicap_strokes_on_hole(3, 21) == 2
    # SI 4 is outside the extra-stroke band
    assert handicap_strokes_on_hole(4, 21) == 1


# ── Stableford via calculate_live_stats ───────────────────────────────────────

def test_stableford_gross_par_with_one_hcp_stroke_gives_three_points():
    # Gross par on a hole where player gets 1 hcp stroke → net birdie → 3 pts
    scores = [{"strokes": 4, "hole_par": 4, "hole_stroke_index": 1}]
    stats = calculate_live_stats(scores, playing_handicap=1)
    assert stats["stableford_total"] == 3


def test_stableford_bogey_no_hcp_stroke_gives_one_point():
    scores = [{"strokes": 5, "hole_par": 4, "hole_stroke_index": 18}]
    stats = calculate_live_stats(scores, playing_handicap=0)
    assert stats["stableford_total"] == 1


def test_stableford_double_bogey_no_hcp_stroke_gives_zero_points():
    scores = [{"strokes": 6, "hole_par": 4, "hole_stroke_index": 18}]
    stats = calculate_live_stats(scores, playing_handicap=0)
    assert stats["stableford_total"] == 0
