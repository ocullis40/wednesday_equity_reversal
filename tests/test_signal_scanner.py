"""Tests for signal scanner logic from app.scan_current_signals().

The scanner lives in app.py and is coupled to download_intraday_data.
We test the core logic by replicating its computations on synthetic data.
"""

import datetime as dt

from analyze import min_move_pct

FRI = dt.date(2025, 1, 3)
MON = dt.date(2025, 1, 6)


def _compute_signal(fri_close, signal_price, symbol):
    """Replicate the scanner's move check and direction logic."""
    move_pct = (signal_price - fri_close) / fri_close * 100
    threshold = min_move_pct(symbol) * 100
    if abs(move_pct) < threshold:
        return None
    direction = "UP" if move_pct > 0 else "DOWN"
    trade = "Short" if direction == "UP" else "Long"
    return {"direction": direction, "trade": trade, "move_pct": move_pct}


def _compute_entry(signal_price, direction):
    """Replicate entry price = signal + 0.2% continuation."""
    if direction == "UP":
        return signal_price * 1.002
    else:
        return signal_price * 0.998


def _confirm_entry(df_mon_after, entry_price, direction):
    """Replicate confirmation: continuation occurs in Monday afternoon bars."""
    for _, bar in df_mon_after.iterrows():
        if direction == "UP" and float(bar["High"]) >= entry_price:
            return True
        if direction == "DOWN" and float(bar["Low"]) <= entry_price:
            return True
    return False


def _compute_targets(entry_price, direction):
    """Replicate target (2%) and stop (1.5%) from entry price."""
    if direction == "UP":
        return entry_price * 0.98, entry_price * 1.015
    else:
        return entry_price * 1.02, entry_price * 0.985


# ── 1. Identifies symbols meeting the move threshold ────────────────────────

def test_meets_threshold_stock():
    # AAPL: 0.75% threshold. Move of 1% → signal generated.
    result = _compute_signal(100.0, 101.0, "AAPL")
    assert result is not None
    assert result["direction"] == "UP"


def test_below_threshold_stock():
    # AAPL: 0.75% threshold. Move of 0.5% → no signal.
    result = _compute_signal(100.0, 100.50, "AAPL")
    assert result is None


def test_meets_threshold_index():
    # SPY: 0.5% threshold. Move of 0.6% → signal generated.
    result = _compute_signal(100.0, 100.60, "SPY")
    assert result is not None


def test_below_threshold_index():
    # SPY: 0.5% threshold. Move of 0.4% → no signal.
    result = _compute_signal(100.0, 100.40, "SPY")
    assert result is None


# ── 2. Correctly determines trade direction ─────────────────────────────────

def test_up_move_means_short():
    result = _compute_signal(100.0, 102.0, "AAPL")
    assert result["direction"] == "UP"
    assert result["trade"] == "Short"


def test_down_move_means_long():
    result = _compute_signal(100.0, 98.0, "AAPL")
    assert result["direction"] == "DOWN"
    assert result["trade"] == "Long"


# ── 3. Entry price = signal + 0.2% continuation ────────────────────────────

def test_entry_price_up():
    # UP direction: entry = signal * 1.002
    entry = _compute_entry(100.0, "UP")
    assert entry == 100.2


def test_entry_price_down():
    # DOWN direction: entry = signal * 0.998
    entry = _compute_entry(100.0, "DOWN")
    assert entry == 99.8


# ── 4. Confirms entry only when continuation occurs in Mon afternoon bars ───

def test_confirmation_up_hits(make_bars):
    entry_price = 100.2
    prices = {
        (MON, "14:00"): 100.0,  # High = 100, below entry
        (MON, "14:30"): 100.3,  # High = 100.3, above entry → confirmed
    }
    df = make_bars(prices)
    mon_after = df[df.index.date == MON].between_time("14:00", "16:00")
    assert _confirm_entry(mon_after, entry_price, "UP") is True


def test_confirmation_up_misses(make_bars):
    entry_price = 100.2
    prices = {
        (MON, "14:00"): 100.0,
        (MON, "14:30"): 100.1,  # High = 100.1, below entry
    }
    df = make_bars(prices)
    mon_after = df[df.index.date == MON].between_time("14:00", "16:00")
    assert _confirm_entry(mon_after, entry_price, "UP") is False


def test_confirmation_down_hits(make_bars):
    entry_price = 99.8
    prices = {
        (MON, "14:00"): 100.0,
        (MON, "14:30"): 99.7,  # Low = 99.7, below entry → confirmed
    }
    df = make_bars(prices)
    mon_after = df[df.index.date == MON].between_time("14:00", "16:00")
    assert _confirm_entry(mon_after, entry_price, "DOWN") is True


def test_confirmation_down_misses(make_bars):
    entry_price = 99.8
    prices = {
        (MON, "14:00"): 100.0,
        (MON, "14:30"): 99.9,  # Low = 99.9, above entry
    }
    df = make_bars(prices)
    mon_after = df[df.index.date == MON].between_time("14:00", "16:00")
    assert _confirm_entry(mon_after, entry_price, "DOWN") is False


# ── 5. Target (2%) and stop (1.5%) from entry price ────────────────────────

def test_target_and_stop_up():
    # UP move → short trade: target 2% below, stop 1.5% above
    target, stop = _compute_targets(100.0, "UP")
    assert target == 98.0              # 100 * 0.98
    assert round(stop, 2) == 101.5     # 100 * 1.015


def test_target_and_stop_down():
    # DOWN move → long trade: target 2% above, stop 1.5% below
    target, stop = _compute_targets(100.0, "DOWN")
    assert target == 102.0   # 100 * 1.02
    assert stop == 98.5      # 100 * 0.985
