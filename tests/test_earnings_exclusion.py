"""Tests for earnings exclusion logic in analyze.py."""

import datetime as dt
from unittest.mock import patch, MagicMock

import pandas as pd

from analyze import get_earnings_dates


# Convenient dates: a Fri-Mon-Tue-Wed sequence
FRI = dt.date(2025, 1, 3)
MON = dt.date(2025, 1, 6)
TUE = dt.date(2025, 1, 7)
WED = dt.date(2025, 1, 8)
THU_BEFORE = dt.date(2025, 1, 2)  # Thursday before Friday


def _period_excluded(earnings_dates: set, fri=FRI, mon=MON, tue=TUE, wed=WED) -> bool:
    """Replicate the exclusion check from analyze_symbol."""
    period_days = {fri, mon, tue, wed}
    return bool(period_days & earnings_dates)


def _mock_earnings(dates: list[dt.date]):
    """Create a mock yf.Ticker whose earnings_dates has the given dates."""
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in dates])
    earnings_df = pd.DataFrame({"dummy": [0] * len(dates)}, index=idx)
    mock_ticker = MagicMock()
    mock_ticker.earnings_dates = earnings_df
    return mock_ticker


# ── 1. Earnings on any day Fri-Wed excludes the period ──────────────────────

def test_earnings_on_friday_excludes():
    assert _period_excluded({FRI}) is True


def test_earnings_on_monday_excludes():
    assert _period_excluded({MON}) is True


def test_earnings_on_tuesday_excludes():
    assert _period_excluded({TUE}) is True


def test_earnings_on_wednesday_excludes():
    assert _period_excluded({WED}) is True


# ── 2. Earnings on Thursday before Friday — period is included ──────────────

def test_earnings_on_thursday_before_does_not_exclude():
    assert _period_excluded({THU_BEFORE}) is False


# ── 3. Index symbols are never excluded for earnings ────────────────────────

def test_index_qqq_returns_empty_earnings():
    result = get_earnings_dates("QQQ")
    assert result == set()


def test_index_spy_returns_empty_earnings():
    result = get_earnings_dates("SPY")
    assert result == set()


# ── 4. Symbol with no earnings data (e.g. ETFs like SLV) — included ────────

@patch("analyze.yf.Ticker")
def test_no_earnings_data_returns_empty_set(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.earnings_dates = None
    mock_ticker_cls.return_value = mock_ticker
    result = get_earnings_dates("SLV")
    assert result == set()
    # Empty set means no exclusion → period included
    assert _period_excluded(result) is False


@patch("analyze.yf.Ticker")
def test_empty_earnings_dataframe_returns_empty_set(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.earnings_dates = pd.DataFrame()
    mock_ticker_cls.return_value = mock_ticker
    result = get_earnings_dates("SLV")
    assert result == set()


# ── 5. Earnings API failure — period included, not silently dropped ─────────

@patch("analyze.yf.Ticker")
def test_earnings_api_failure_returns_empty_set(mock_ticker_cls):
    mock_ticker_cls.side_effect = Exception("API error")
    result = get_earnings_dates("AAPL")
    assert result == set()
    # Empty set means no exclusion → period included
    assert _period_excluded(result) is False


@patch("analyze.yf.Ticker")
def test_earnings_dates_property_raises_returns_empty_set(mock_ticker_cls):
    mock_ticker = MagicMock()
    type(mock_ticker).earnings_dates = property(lambda self: (_ for _ in ()).throw(Exception("fail")))
    mock_ticker_cls.return_value = mock_ticker
    result = get_earnings_dates("AAPL")
    assert result == set()


# ── 6. Normal earnings dates are extracted correctly ────────────────────────

@patch("analyze.yf.Ticker")
def test_earnings_dates_extracted_from_ticker(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_earnings([FRI, dt.date(2025, 4, 15)])
    result = get_earnings_dates("AAPL")
    assert FRI in result
    assert dt.date(2025, 4, 15) in result
    assert len(result) == 2
