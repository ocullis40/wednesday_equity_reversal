"""Tests for analyze.extract_prices()."""

import datetime as dt

from analyze import extract_prices

# Convenient test dates: a real Fri-Mon-Tue-Wed sequence
FRI = dt.date(2025, 1, 3)
MON = dt.date(2025, 1, 6)
TUE = dt.date(2025, 1, 7)
WED = dt.date(2025, 1, 8)


def _full_prices() -> dict:
    """Return a minimal price dict that covers every slot extract_prices needs."""
    return {
        (FRI, "09:30"): 100.0,
        (FRI, "15:30"): 105.0,
        (MON, "09:30"): 106.0,
        (MON, "13:30"): 108.0,
        (TUE, "09:30"): 110.0,
        (TUE, "11:30"): 112.0,
        (WED, "09:30"): 114.0,
        (WED, "10:00"): 120.0,
        (WED, "11:00"): 109.0,
    }


# ── 1. Happy path ──────────────────────────────────────────────────────────

def test_happy_path(make_bars):
    df = make_bars(_full_prices())
    result = extract_prices(df, FRI, MON, TUE, WED)

    assert result == {
        "friday_close": 105.0,
        "monday_2pm": 108.0,
        "tuesday_10am": 110.0,
        "tuesday_12pm": 112.0,
        "wednesday_high": 120.0,
        "wednesday_low": 109.0,
    }


# ── 2. Friday close uses last bar of the day ───────────────────────────────

def test_friday_close_uses_last_bar(make_bars):
    prices = _full_prices()
    prices[(FRI, "12:00")] = 999.0  # mid-day bar, not the last
    prices[(FRI, "15:30")] = 105.0  # last bar
    df = make_bars(prices)
    result = extract_prices(df, FRI, MON, TUE, WED)
    assert result["friday_close"] == 105.0


# ── 3. Monday 2 PM uses close of 13:30 bar ─────────────────────────────────

def test_monday_2pm_uses_1330_bar(make_bars):
    prices = _full_prices()
    prices[(MON, "13:30")] = 108.5
    df = make_bars(prices)
    result = extract_prices(df, FRI, MON, TUE, WED)
    assert result["monday_2pm"] == 108.5


# ── 4. Tuesday 10 AM uses close of 9:30 bar ────────────────────────────────

def test_tuesday_10am_uses_0930_bar(make_bars):
    prices = _full_prices()
    prices[(TUE, "09:30")] = 110.5
    df = make_bars(prices)
    result = extract_prices(df, FRI, MON, TUE, WED)
    assert result["tuesday_10am"] == 110.5


# ── 5. Tuesday 12 PM uses close of 11:30 bar ───────────────────────────────

def test_tuesday_12pm_uses_1130_bar(make_bars):
    prices = _full_prices()
    prices[(TUE, "11:30")] = 112.5
    df = make_bars(prices)
    result = extract_prices(df, FRI, MON, TUE, WED)
    assert result["tuesday_12pm"] == 112.5


# ── 6. Wednesday high/low span full day ─────────────────────────────────────

def test_wednesday_high_low_span_full_day(make_bars):
    prices = _full_prices()
    # Override Wednesday bars with distinct High/Low values
    prices[(WED, "09:30")] = 114.0
    prices[(WED, "10:00")] = 120.0
    prices[(WED, "11:00")] = 109.0
    df = make_bars(prices)

    # The fixture sets High=Low=Close=price, so manually adjust High/Low
    wed_mask = df.index.date == WED
    df.loc[wed_mask & (df["Close"] == 120.0), "High"] = 125.0
    df.loc[wed_mask & (df["Close"] == 109.0), "Low"] = 104.0

    result = extract_prices(df, FRI, MON, TUE, WED)
    assert result["wednesday_high"] == 125.0
    assert result["wednesday_low"] == 104.0


# ── 7. Missing Friday data returns empty dict ───────────────────────────────

def test_missing_friday_returns_empty(make_bars):
    prices = _full_prices()
    prices = {k: v for k, v in prices.items() if k[0] != FRI}
    df = make_bars(prices)
    assert extract_prices(df, FRI, MON, TUE, WED) == {}


# ── 8. Missing Monday data returns empty dict ──────────────────────────────

def test_missing_monday_returns_empty(make_bars):
    prices = _full_prices()
    prices = {k: v for k, v in prices.items() if k[0] != MON}
    df = make_bars(prices)
    assert extract_prices(df, FRI, MON, TUE, WED) == {}


# ── 9. Missing Tuesday data returns empty dict ─────────────────────────────

def test_missing_tuesday_returns_empty(make_bars):
    prices = _full_prices()
    prices = {k: v for k, v in prices.items() if k[0] != TUE}
    df = make_bars(prices)
    assert extract_prices(df, FRI, MON, TUE, WED) == {}


# ── 10. Missing Wednesday data returns empty dict ───────────────────────────

def test_missing_wednesday_returns_empty(make_bars):
    prices = _full_prices()
    prices = {k: v for k, v in prices.items() if k[0] != WED}
    df = make_bars(prices)
    assert extract_prices(df, FRI, MON, TUE, WED) == {}


# ── 11. Missing Monday 13:30 bar specifically returns empty dict ────────────

def test_missing_monday_1330_bar_returns_empty(make_bars):
    prices = _full_prices()
    del prices[(MON, "13:30")]
    # Monday still has bars, just not the 13:30 one
    df = make_bars(prices)
    assert extract_prices(df, FRI, MON, TUE, WED) == {}


# ── 12. Missing Tuesday 9:30 bar returns empty dict ────────────────────────

def test_missing_tuesday_0930_bar_returns_empty(make_bars):
    prices = _full_prices()
    del prices[(TUE, "09:30")]
    # Tuesday still has the 11:30 bar
    df = make_bars(prices)
    assert extract_prices(df, FRI, MON, TUE, WED) == {}


# ── 13. Missing Tuesday 11:30 bar returns empty dict ───────────────────────

def test_missing_tuesday_1130_bar_returns_empty(make_bars):
    prices = _full_prices()
    del prices[(TUE, "11:30")]
    # Tuesday still has the 9:30 bar
    df = make_bars(prices)
    assert extract_prices(df, FRI, MON, TUE, WED) == {}


# ── 14. All returned values are floats ──────────────────────────────────────

def test_all_returned_values_are_floats(make_bars):
    df = make_bars(_full_prices())
    result = extract_prices(df, FRI, MON, TUE, WED)
    assert result  # non-empty
    for key, value in result.items():
        assert isinstance(value, float), f"{key} is {type(value)}, expected float"
