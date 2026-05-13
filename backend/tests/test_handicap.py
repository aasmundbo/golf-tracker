import pytest
from services.handicap import (
    calculate_playing_handicap,
    handicap_strokes_on_hole,
    calculate_live_stats,
    calculate_projected_handicap,
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


def test_hcp_36_gives_two_strokes_all_holes():
    # floor(36/18)=2, 36%18=0 → base=2, no extra; all holes get 2
    for si in range(1, 19):
        assert handicap_strokes_on_hole(si, 36) == 2


def test_hcp_37_gives_three_strokes_on_si1_two_on_rest():
    # floor(37/18)=2, 37%18=1 → extra stroke only for SI=1
    assert handicap_strokes_on_hole(1, 37) == 3
    for si in range(2, 19):
        assert handicap_strokes_on_hole(si, 37) == 2


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


# ── calculate_live_stats edge cases (T4) ──────────────────────────────────────

def test_live_stats_empty_scores_all_zeros():
    stats = calculate_live_stats([], playing_handicap=18)
    assert stats["holes_played"] == 0
    assert stats["gross_total"] == 0
    assert stats["net_total"] == 0
    assert stats["gross_to_par"] == 0
    assert stats["net_to_par"] == 0
    assert stats["stableford_total"] == 0


def test_live_stats_skips_entries_with_hole_par_none():
    scores = [
        {"strokes": 5, "hole_par": None, "hole_stroke_index": 1},
        {"strokes": 4, "hole_par": 4, "hole_stroke_index": 2},
    ]
    stats = calculate_live_stats(scores, playing_handicap=0)
    assert stats["gross_total"] == 4
    assert stats["holes_played"] == 1


def test_live_stats_holes_played_counts_only_valid_entries():
    scores = [
        {"strokes": 4, "hole_par": 4, "hole_stroke_index": 1},
        {"strokes": None, "hole_par": 4, "hole_stroke_index": 2},
        {"strokes": 5, "hole_par": None, "hole_stroke_index": 3},
        {"strokes": 3, "hole_par": 3, "hole_stroke_index": 4},
    ]
    stats = calculate_live_stats(scores, playing_handicap=0)
    assert stats["holes_played"] == 2


# ── calculate_projected_handicap (T2) ─────────────────────────────────────────

def _make_hole_data(n: int = 18, par: int = 4) -> list[dict]:
    return [{"hole_number": h, "par": par, "stroke_index": h} for h in range(1, n + 1)]


def test_projected_handicap_no_scores_all_par4():
    # Slope=113, CR=72, playing_hcp=18 → 1 stroke on every hole (SI 1-18)
    # Projected total = 18 * (4+1) = 90 → diff = (90-72)*113/113 = 18.0
    result = calculate_projected_handicap(
        scores=[],
        hole_data=_make_hole_data(),
        playing_handicap=18,
        course_rating=72.0,
        slope=113.0,
    )
    assert result["holes_played"] == 0
    assert result["projected_differential"] == pytest.approx(18.0, abs=0.1)
    assert len(result["hole_by_hole"]) == 18


def test_projected_handicap_9_holes_played_par_on_each():
    # Holes 1-9 played at par (strokes=4); projected was par+1=5 each.
    # delta for holes 1-9: (4-5)*9 = -9; remaining 9 projected to net par.
    # Projected total = 18*5=90; adj = 90 + (-9) = 81 → diff = (81-72)*113/113 = 9.0
    scores = [
        {"hole_number": h, "strokes": 4, "hole_par": 4, "hole_stroke_index": h}
        for h in range(1, 10)
    ]
    result = calculate_projected_handicap(
        scores=scores,
        hole_data=_make_hole_data(),
        playing_handicap=18,
        course_rating=72.0,
        slope=113.0,
    )
    assert result["holes_played"] == 9
    assert result["projected_differential"] == pytest.approx(9.0, abs=0.1)


def test_projected_handicap_returns_none_when_hole_data_missing():
    # No hole_data and no si on scores → can't project
    result = calculate_projected_handicap(
        scores=[{"hole_number": 1, "strokes": 4, "hole_par": 4, "hole_stroke_index": None}],
        hole_data=[],
        playing_handicap=18,
        course_rating=72.0,
        slope=113.0,
    )
    assert result["projected_differential"] is None
