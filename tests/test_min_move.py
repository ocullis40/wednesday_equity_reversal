"""Tests for analyze.min_move_pct() minimum move thresholds."""

from analyze import min_move_pct


def test_qqq_uses_half_percent():
    assert min_move_pct("QQQ") == 0.005


def test_spy_uses_half_percent():
    assert min_move_pct("SPY") == 0.005


def test_regular_stock_uses_075_percent():
    assert min_move_pct("AAPL") == 0.0075


def test_another_regular_stock():
    assert min_move_pct("MSFT") == 0.0075
