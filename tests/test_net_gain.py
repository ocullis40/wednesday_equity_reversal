"""Tests for net gain calculation logic from app.calc_net_gain()."""


def calc_net_gain(row):
    """Replicate the net gain calculation from app.py."""
    entry = row.get("Actual Entry")
    exit_ = row.get("Actual Exit")
    if entry and exit_ and entry > 0:
        if "Short" in str(row["Trade"]):
            return round((entry - exit_) / entry * 100, 2)
        else:
            return round((exit_ - entry) / entry * 100, 2)
    return None


# ── 1. Short trades: gain = (entry - exit) / entry ─────────────────────────

def test_short_trade_profit():
    row = {"Trade": "🔴 Short", "Actual Entry": 100.0, "Actual Exit": 98.0}
    assert calc_net_gain(row) == 2.0  # (100-98)/100 * 100


def test_short_trade_loss():
    row = {"Trade": "🔴 Short", "Actual Entry": 100.0, "Actual Exit": 103.0}
    assert calc_net_gain(row) == -3.0  # (100-103)/100 * 100


# ── 2. Long trades: gain = (exit - entry) / entry ──────────────────────────

def test_long_trade_profit():
    row = {"Trade": "🟢 Long", "Actual Entry": 100.0, "Actual Exit": 105.0}
    assert calc_net_gain(row) == 5.0  # (105-100)/100 * 100


def test_long_trade_loss():
    row = {"Trade": "🟢 Long", "Actual Entry": 100.0, "Actual Exit": 97.0}
    assert calc_net_gain(row) == -3.0  # (97-100)/100 * 100


# ── 3. Returns null when entry or exit is missing ───────────────────────────

def test_missing_entry():
    row = {"Trade": "🔴 Short", "Actual Entry": None, "Actual Exit": 98.0}
    assert calc_net_gain(row) is None


def test_missing_exit():
    row = {"Trade": "🔴 Short", "Actual Entry": 100.0, "Actual Exit": None}
    assert calc_net_gain(row) is None


def test_both_missing():
    row = {"Trade": "🟢 Long", "Actual Entry": None, "Actual Exit": None}
    assert calc_net_gain(row) is None


def test_no_entry_key():
    row = {"Trade": "🟢 Long", "Actual Exit": 105.0}
    assert calc_net_gain(row) is None


def test_no_exit_key():
    row = {"Trade": "🟢 Long", "Actual Entry": 100.0}
    assert calc_net_gain(row) is None
