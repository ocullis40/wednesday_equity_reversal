"""Tests for summary statistics in analyze._summarize_timeframe()."""

import numpy as np

from analyze import _summarize_timeframe, FIXED_TARGETS, WED_CHECKPOINTS


def _row(symbol, friday_close, move, retracement_pct, continuation_pct,
         retraced_90pct, prefix="10am", **extra):
    """Build a minimal result row for _summarize_timeframe."""
    direction = "up" if move > 0 else "down"
    r = {
        "symbol": symbol,
        "friday_close": friday_close,
        f"{prefix}_move": move,
        f"{prefix}_move_direction": direction,
        f"{prefix}_retracement_pct": retracement_pct,
        f"{prefix}_continuation_pct": continuation_pct,
        f"{prefix}_retraced_90pct": retraced_90pct,
    }
    r.update(extra)
    return r


# ── 1. Hit rate ──────────────────────────────────────────────────────────────

def test_hit_rate():
    rows = [
        _row("AAPL", 100.0, 1.0, 95.0, 1.0, True),
        _row("AAPL", 100.0, 1.0, 50.0, 2.0, False),
        _row("AAPL", 100.0, 1.0, 92.0, 0.5, True),
    ]
    s = _summarize_timeframe(rows, "10am")
    # 2 out of 3 hit
    assert s["hit_rate"] == round(2 / 3 * 100, 2)
    assert s["hit_count"] == 2
    assert s["total_periods"] == 3


# ── 2. Median retracement ───────────────────────────────────────────────────

def test_median_retracement():
    rows = [
        _row("AAPL", 100.0, 1.0, 80.0, 1.0, False),
        _row("AAPL", 100.0, 1.0, 90.0, 2.0, True),
        _row("AAPL", 100.0, 1.0, 100.0, 3.0, True),
    ]
    s = _summarize_timeframe(rows, "10am")
    assert s["median_retracement"] == round(float(np.median([80.0, 90.0, 100.0])), 2)


# ── 3. Median continuation ──────────────────────────────────────────────────

def test_median_continuation():
    rows = [
        _row("AAPL", 100.0, 1.0, 80.0, 1.5, False),
        _row("AAPL", 100.0, 1.0, 90.0, 2.5, True),
        _row("AAPL", 100.0, 1.0, 100.0, 3.5, True),
    ]
    s = _summarize_timeframe(rows, "10am")
    assert s["median_continuation"] == round(float(np.median([1.5, 2.5, 3.5])), 2)


# ── 4. Average when hit only includes triggered trades ──────────────────────

def test_avg_retracement_on_hit():
    rows = [
        _row("AAPL", 100.0, 1.0, 50.0, 1.0, False),   # not hit
        _row("AAPL", 100.0, 1.0, 95.0, 2.0, True),     # hit
        _row("AAPL", 100.0, 1.0, 105.0, 3.0, True),    # hit
    ]
    s = _summarize_timeframe(rows, "10am")
    expected = round(float(np.mean([95.0, 105.0])), 2)
    assert s["avg_retracement_on_hit"] == expected


# ── 5. Top 10% average uses the correct slice ───────────────────────────────

def test_top_10_pct_average():
    # 10 rows so top 10% = 1 row (the highest retracement)
    retrace_values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 150.0]
    rows = [_row("AAPL", 100.0, 1.0, rv, 1.0, rv >= 90) for rv in retrace_values]

    s = _summarize_timeframe(rows, "10am")
    # Top 10% of 10 items = max(1, 10//10) = 1 item → the highest (150.0)
    assert s["avg_top_10_pct"] == 150.0


def test_top_10_pct_minimum_one():
    # 3 rows: top 10% = max(1, 0) = 1 → highest value
    rows = [
        _row("AAPL", 100.0, 1.0, 80.0, 1.0, False),
        _row("AAPL", 100.0, 1.0, 90.0, 2.0, True),
        _row("AAPL", 100.0, 1.0, 100.0, 3.0, True),
    ]
    s = _summarize_timeframe(rows, "10am")
    assert s["avg_top_10_pct"] == 100.0


# ── 6. P&L calculation: $100 per trade ──────────────────────────────────────

def test_pnl_100_per_trade():
    rows = [
        _row("AAPL", 100.0, 1.0, 95.0, 2.0, True),
        _row("AAPL", 100.0, 1.0, 105.0, 3.0, True),
        _row("AAPL", 100.0, 1.0, 50.0, 1.0, False),  # not triggered
    ]
    s = _summarize_timeframe(rows, "10am")

    assert s["num_trades"] == 2
    assert s["total_invested"] == 200  # 2 trades × $100

    # reversal_return = sum(retrace_pct/100 * 100) for hits
    expected_rev = 95.0 / 100 * 100 + 105.0 / 100 * 100
    assert s["reversal_return"] == round(expected_rev, 2)

    # continuation_return = sum(cont_pct/100 * 100) for hits
    expected_cont = 2.0 / 100 * 100 + 3.0 / 100 * 100
    assert s["continuation_return"] == round(expected_cont, 2)


# ── 7. Median trade returns ─────────────────────────────────────────────────

def test_median_trade_returns():
    rows = [
        _row("AAPL", 100.0, 1.0, 90.0, 2.0, True),
        _row("AAPL", 100.0, 1.0, 100.0, 4.0, True),
        _row("AAPL", 100.0, 1.0, 110.0, 6.0, True),
    ]
    s = _summarize_timeframe(rows, "10am")

    assert s["median_reversal_trade"] == round(float(np.median([90.0, 100.0, 110.0])), 2)
    assert s["median_continuation_trade"] == round(float(np.median([2.0, 4.0, 6.0])), 2)


# ── 8. Target hit rates are percentages of triggered trades ─────────────────

def test_target_hit_rates():
    # 2 triggered trades, one hits the 1% target, both hit nothing else
    rows = [
        _row("AAPL", 100.0, 1.0, 95.0, 1.0, True,
             **{"10am_target_1.0pct": True, "10am_target_2.0pct": False,
                "10am_target_3.0pct": False, "10am_target_5.0pct": False}),
        _row("AAPL", 100.0, 1.0, 92.0, 1.0, True,
             **{"10am_target_1.0pct": False, "10am_target_2.0pct": False,
                "10am_target_3.0pct": False, "10am_target_5.0pct": False}),
        _row("AAPL", 100.0, 1.0, 50.0, 1.0, False),  # not triggered, no target keys
    ]
    s = _summarize_timeframe(rows, "10am")

    # 1 of 2 triggered trades hit 1% target
    assert s["target_hit_rates"]["1.0%"] == 50.0
    assert s["target_hit_rates"]["2.0%"] == 0.0


# ── 9. Time-based medians aggregate correctly ───────────────────────────────

def test_time_based_medians():
    rows = [
        _row("AAPL", 100.0, 1.0, 95.0, 1.0, True,
             **{"10am_at_0930": 0.5, "10am_at_1000": 1.2}),
        _row("AAPL", 100.0, 1.0, 92.0, 1.0, True,
             **{"10am_at_0930": 0.8, "10am_at_1000": 1.5}),
    ]
    s = _summarize_timeframe(rows, "10am")

    assert s["time_based"]["09:30"] == round(float(np.median([0.5, 0.8])), 2)
    assert s["time_based"]["10:00"] == round(float(np.median([1.2, 1.5])), 2)


# ── 10. Empty input returns zeros ───────────────────────────────────────────

def test_empty_input():
    s = _summarize_timeframe([], "10am")
    assert s["total_periods"] == 0
    assert s["hit_rate"] == 0
    assert s["median_retracement"] == 0
    assert s["median_continuation"] == 0
    assert s["num_trades"] == 0
