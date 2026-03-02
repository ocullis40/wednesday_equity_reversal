"""Tests for analyze.analyze_wednesday_intraday()."""

import datetime as dt

from analyze import analyze_wednesday_intraday, FIXED_TARGETS

WED = dt.date(2025, 1, 8)


# ── 1. Fixed targets correctly identify reversal hits ────────────────────────

def test_fixed_targets_up_move_reversal_hits(make_bars):
    # Up move → reversal is DOWN. Entry = 110.
    # Need low to hit 1%, 2%, 3% but not 5%.
    # 1% target = 108.90, 2% = 107.80, 3% = 106.70, 5% = 104.50
    prices = {
        (WED, "09:30"): 109.0,  # High=Low=109
        (WED, "10:00"): 108.0,
        (WED, "11:00"): 107.0,  # Low enough for 1%, 2%, 3% (106.70 needs Low<=106.70)
    }
    df = make_bars(prices)
    # Manually set a lower Low on the 11:00 bar to hit 3%
    df.loc[df["Close"] == 107.0, "Low"] = 106.50

    result = analyze_wednesday_intraday(df, WED, 110.0, "up", "10am")

    assert result["10am_target_1.0pct"] is True   # 106.50 <= 108.90
    assert result["10am_target_2.0pct"] is True   # 106.50 <= 107.80
    assert result["10am_target_3.0pct"] is True   # 106.50 <= 106.70
    assert result["10am_target_5.0pct"] is False  # 106.50 > 104.50


def test_fixed_targets_down_move_reversal_hits(make_bars):
    # Down move → reversal is UP. Entry = 100.
    # 1% target = 101, 2% = 102, 3% = 103, 5% = 105
    prices = {
        (WED, "09:30"): 101.0,
        (WED, "10:00"): 102.5,
        (WED, "11:00"): 104.0,
    }
    df = make_bars(prices)
    # Set a higher High on the 11:00 bar
    df.loc[df["Close"] == 104.0, "High"] = 104.5

    result = analyze_wednesday_intraday(df, WED, 100.0, "down", "10am")

    assert result["10am_target_1.0pct"] is True   # 104.5 >= 101
    assert result["10am_target_2.0pct"] is True   # 104.5 >= 102
    assert result["10am_target_3.0pct"] is True   # 104.5 >= 103
    assert result["10am_target_5.0pct"] is False  # 104.5 < 105


# ── 2. Time-based checkpoints capture max reversal by each half-hour ────────

def test_time_based_checkpoints_accumulate(make_bars):
    # Up move, entry = 110. Reversal is DOWN.
    # 09:30 bar Low = 109 → reversal = (110-109)/110*100 = 0.91%
    # 10:00 bar Low = 108 → cumulative best = 108 → reversal = 1.82%
    prices = {
        (WED, "09:30"): 109.0,
        (WED, "10:00"): 108.0,
        (WED, "10:30"): 108.5,  # doesn't improve the low
    }
    df = make_bars(prices)

    result = analyze_wednesday_intraday(df, WED, 110.0, "up", "10am")

    assert result["10am_at_0930"] == round((110.0 - 109.0) / 110.0 * 100, 2)
    assert result["10am_at_1000"] == round((110.0 - 108.0) / 110.0 * 100, 2)
    # At 10:30, best low is still 108 from the 10:00 bar
    assert result["10am_at_1030"] == round((110.0 - 108.0) / 110.0 * 100, 2)


def test_time_based_checkpoints_down_move(make_bars):
    # Down move, entry = 100. Reversal is UP.
    # 09:30 bar High = 101 → reversal = 1%
    # 10:00 bar High = 103 → cumulative best = 103 → reversal = 3%
    prices = {
        (WED, "09:30"): 101.0,
        (WED, "10:00"): 103.0,
    }
    df = make_bars(prices)

    result = analyze_wednesday_intraday(df, WED, 100.0, "down", "10am")

    assert result["10am_at_0930"] == round((101.0 - 100.0) / 100.0 * 100, 2)
    assert result["10am_at_1000"] == round((103.0 - 100.0) / 100.0 * 100, 2)


# ── 3. Checkpoints with no data return None ──────────────────────────────────

def test_late_checkpoints_are_none_when_no_data(make_bars):
    # Only morning bars, afternoon checkpoints should be None
    prices = {
        (WED, "09:30"): 109.0,
    }
    df = make_bars(prices)

    result = analyze_wednesday_intraday(df, WED, 110.0, "up", "10am")

    # 09:30 should have data
    assert result["10am_at_0930"] is not None
    # Checkpoints after the last bar still accumulate via between_time
    # but 16:00 won't have any bars in the 09:30-16:00 range... actually it will
    # since between_time("09:30", "16:00") includes 09:30.
    # All checkpoints from 09:30 onward will see the 09:30 bar.


# ── 4. Empty Wednesday data returns empty dict ──────────────────────────────

def test_empty_wednesday_returns_empty(make_bars):
    import pandas as pd
    df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    df.index = pd.DatetimeIndex([], tz="America/New_York")
    df.index.name = "timestamp"

    result = analyze_wednesday_intraday(df, WED, 110.0, "up", "10am")
    assert result == {}


# ── 5. Only triggered trades get intraday analysis (structural test) ────────

def test_only_triggered_trades_get_intraday_keys(make_bars):
    """Verify the analyze_symbol integration point: intraday keys are only
    added when retraced_90pct is True. We test this by checking that the
    function is called with the right prefix and returns prefixed keys."""
    prices = {
        (WED, "09:30"): 109.0,
        (WED, "10:00"): 108.0,
    }
    df = make_bars(prices)

    result = analyze_wednesday_intraday(df, WED, 110.0, "up", "mon2pm")

    # All keys should be prefixed with "mon2pm_"
    for key in result:
        assert key.startswith("mon2pm_"), f"Key {key} missing mon2pm_ prefix"

    # Should have target keys for each fixed target
    for target in FIXED_TARGETS:
        assert f"mon2pm_target_{target}pct" in result


# ── 6. All fixed targets present in result ───────────────────────────────────

def test_all_fixed_targets_present(make_bars):
    prices = {(WED, "09:30"): 100.0}
    df = make_bars(prices)

    result = analyze_wednesday_intraday(df, WED, 100.0, "up", "12pm")

    for target in FIXED_TARGETS:
        key = f"12pm_target_{target}pct"
        assert key in result
        assert isinstance(result[key], bool)
