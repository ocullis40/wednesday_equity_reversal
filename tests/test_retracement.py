"""Tests for analyze.compute_retracement()."""

from analyze import compute_retracement


# ── 1. Up move direction ────────────────────────────────────────────────────

def test_up_move_direction():
    result = compute_retracement(
        friday_close=100.0, tuesday_10am=110.0,
        wednesday_high=112.0, wednesday_low=105.0,
    )
    assert result["move_direction"] == "up"
    assert result["move"] == 10.0


# ── 2. Down move direction ──────────────────────────────────────────────────

def test_down_move_direction():
    result = compute_retracement(
        friday_close=110.0, tuesday_10am=100.0,
        wednesday_high=105.0, wednesday_low=98.0,
    )
    assert result["move_direction"] == "down"
    assert result["move"] == -10.0


# ── 3. Retracement pct is stock % move from entry to Wednesday extreme ──────

def test_retracement_pct_up_move():
    # Up move: retracement = |tue10am - wed_low| / tue10am * 100
    result = compute_retracement(
        friday_close=100.0, tuesday_10am=110.0,
        wednesday_high=112.0, wednesday_low=105.0,
    )
    expected = abs(110.0 - 105.0) / 110.0 * 100
    assert result["retracement_pct"] == round(expected, 2)


def test_retracement_pct_down_move():
    # Down move: retracement = |wed_high - tue10am| / tue10am * 100
    result = compute_retracement(
        friday_close=110.0, tuesday_10am=100.0,
        wednesday_high=105.0, wednesday_low=98.0,
    )
    expected = abs(105.0 - 100.0) / 100.0 * 100
    assert result["retracement_pct"] == round(expected, 2)


# ── 4. Continuation pct is stock % move in the same direction ───────────────

def test_continuation_pct_up_move():
    # Up move continues: wed_high vs tue10am
    result = compute_retracement(
        friday_close=100.0, tuesday_10am=110.0,
        wednesday_high=115.0, wednesday_low=108.0,
    )
    expected = abs(115.0 - 110.0) / 110.0 * 100
    assert result["continuation_pct"] == round(expected, 2)


def test_continuation_pct_down_move():
    # Down move continues: wed_low vs tue10am
    result = compute_retracement(
        friday_close=110.0, tuesday_10am=100.0,
        wednesday_high=103.0, wednesday_low=96.0,
    )
    expected = abs(100.0 - 96.0) / 100.0 * 100
    assert result["continuation_pct"] == round(expected, 2)


# ── 5. 90% threshold uses original move ratio, not stock % ─────────────────

def test_90pct_threshold_uses_move_ratio_triggered():
    # Up move of 10. Wednesday low = 101 → retraced 9/10 = 90% of move.
    result = compute_retracement(
        friday_close=100.0, tuesday_10am=110.0,
        wednesday_high=111.0, wednesday_low=101.0,
    )
    assert result["retraced_90pct"] is True


def test_90pct_threshold_uses_move_ratio_not_triggered():
    # Up move of 10. Wednesday low = 102 → retraced 8/10 = 80% of move.
    result = compute_retracement(
        friday_close=100.0, tuesday_10am=110.0,
        wednesday_high=111.0, wednesday_low=102.0,
    )
    assert result["retraced_90pct"] is False


def test_90pct_threshold_exact_boundary():
    # Up move of 10. Wednesday low = 101 → retraced exactly 9/10 = 90%.
    result = compute_retracement(
        friday_close=100.0, tuesday_10am=110.0,
        wednesday_high=111.0, wednesday_low=101.0,
    )
    assert result["retraced_90pct"] is True


def test_90pct_threshold_down_move():
    # Down move of -10. Wednesday high = 109 → retraced 9/10 = 90%.
    result = compute_retracement(
        friday_close=110.0, tuesday_10am=100.0,
        wednesday_high=109.0, wednesday_low=99.0,
    )
    assert result["retraced_90pct"] is True


# ── 6. Flat move classification ─────────────────────────────────────────────

def test_flat_move_below_dollar_threshold():
    # Move of $0.04 — below the $0.05 threshold
    result = compute_retracement(
        friday_close=100.0, tuesday_10am=100.04,
        wednesday_high=100.10, wednesday_low=99.90,
    )
    assert result["move_direction"] == "flat"
    assert result["retracement_pct"] is None
    assert result["retraced_90pct"] is None


def test_flat_move_below_percentage_threshold():
    # $200 stock, move of $0.08 → 0.04% which is below 0.05%
    result = compute_retracement(
        friday_close=200.0, tuesday_10am=200.08,
        wednesday_high=200.50, wednesday_low=199.50,
    )
    assert result["move_direction"] == "flat"
    assert result["retracement_pct"] is None


def test_non_flat_move_above_thresholds():
    # Move of $1.0 on a $100 stock → 1%, well above both thresholds
    result = compute_retracement(
        friday_close=100.0, tuesday_10am=101.0,
        wednesday_high=102.0, wednesday_low=99.0,
    )
    assert result["move_direction"] == "up"
    assert result["retracement_pct"] is not None


# ── 7. Retracement price returned correctly ─────────────────────────────────

def test_retracement_price_up_move_is_wednesday_low():
    result = compute_retracement(
        friday_close=100.0, tuesday_10am=110.0,
        wednesday_high=112.0, wednesday_low=105.0,
    )
    assert result["retracement_price"] == 105.0


def test_retracement_price_down_move_is_wednesday_high():
    result = compute_retracement(
        friday_close=110.0, tuesday_10am=100.0,
        wednesday_high=105.0, wednesday_low=98.0,
    )
    assert result["retracement_price"] == 105.0
