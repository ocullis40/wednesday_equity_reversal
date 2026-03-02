"""Tests for per-timeframe filtering in analyze._summarize_timeframe()."""

from analyze import _summarize_timeframe


def _make_row(symbol, friday_close, mon2pm_move, ten_am_move, twelve_pm_move):
    """Build a minimal result row with three timeframes.

    Each *_move value is the raw move (tue/mon price - friday_close).
    Retracement fields are filled with plausible non-None values so the row
    is not filtered out unless the move is too small.
    """
    row = {
        "symbol": symbol,
        "friday_close": friday_close,
    }
    for prefix, move in [("mon2pm", mon2pm_move), ("10am", ten_am_move), ("12pm", twelve_pm_move)]:
        direction = "up" if move > 0 else ("down" if move < 0 else "flat")
        row[f"{prefix}_move"] = move
        row[f"{prefix}_move_direction"] = direction
        if direction == "flat":
            row[f"{prefix}_retracement_pct"] = None
            row[f"{prefix}_continuation_pct"] = None
            row[f"{prefix}_retraced_90pct"] = None
        else:
            row[f"{prefix}_retracement_pct"] = 2.5
            row[f"{prefix}_continuation_pct"] = 1.0
            row[f"{prefix}_retraced_90pct"] = True
    return row


# ── 1. Summary stats only include periods meeting that timeframe's threshold ─

def test_timeframe_filtered_by_own_threshold():
    # AAPL threshold = 0.75%. friday_close = 100.
    # 10am move = $1.0 (1.0%) → above threshold → included
    # 12pm move = $0.50 (0.5%) → below 0.75% → excluded
    rows = [_make_row("AAPL", 100.0, 1.0, 1.0, 0.50)]

    summary_10am = _summarize_timeframe(rows, "10am")
    summary_12pm = _summarize_timeframe(rows, "12pm")

    assert summary_10am["total_periods"] == 1
    assert summary_12pm["total_periods"] == 0


# ── 2. A period can count for one timeframe but not another ──────────────────

def test_period_counts_for_one_timeframe_not_another():
    # Two rows: both have 10am above threshold, only one has 12pm above threshold.
    row1 = _make_row("AAPL", 100.0, 1.0, 1.0, 1.0)   # both above
    row2 = _make_row("AAPL", 100.0, 1.0, 1.0, 0.50)   # 12pm below

    rows = [row1, row2]

    summary_10am = _summarize_timeframe(rows, "10am")
    summary_12pm = _summarize_timeframe(rows, "12pm")

    assert summary_10am["total_periods"] == 2
    assert summary_12pm["total_periods"] == 1


# ── 3. Index symbols use 0.5% threshold ─────────────────────────────────────

def test_index_symbol_uses_lower_threshold():
    # SPY threshold = 0.5%. friday_close = 100.
    # 10am move = $0.60 (0.6%) → above 0.5% for SPY
    rows = [_make_row("SPY", 100.0, 0.60, 0.60, 0.60)]

    summary = _summarize_timeframe(rows, "10am")
    assert summary["total_periods"] == 1


def test_same_move_excluded_for_stock_but_included_for_index():
    # 0.6% move: included for SPY (0.5% threshold), excluded for AAPL (0.75%)
    row_spy = _make_row("SPY", 100.0, 0.60, 0.60, 0.60)
    row_aapl = _make_row("AAPL", 100.0, 0.60, 0.60, 0.60)

    spy_summary = _summarize_timeframe([row_spy], "10am")
    aapl_summary = _summarize_timeframe([row_aapl], "10am")

    assert spy_summary["total_periods"] == 1
    assert aapl_summary["total_periods"] == 0


# ── 4. Flat timeframes are excluded ─────────────────────────────────────────

def test_flat_timeframe_excluded():
    # 10am is flat (move=0), 12pm has a real move
    row = _make_row("AAPL", 100.0, 1.0, 0.0, 1.0)

    summary_10am = _summarize_timeframe([row], "10am")
    summary_12pm = _summarize_timeframe([row], "12pm")

    assert summary_10am["total_periods"] == 0
    assert summary_12pm["total_periods"] == 1
