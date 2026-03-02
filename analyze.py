import os
import csv
from datetime import date

import yfinance as yf
import pandas as pd
import numpy as np

SYMBOLS = [
    "IREN", "QQQ", "SPY", "TSLA", "NVDA", "AAPL", "GOOG", "HOOD", "MSFT", "OKLO",
    "ILMN", "FSLR", "AMZN", "SMCI", "META", "AMD", "JPM", "GS", "SLV", "BP",
]

INDEX_SYMBOLS = {"QQQ", "SPY"}

def min_move_pct(symbol: str) -> float:
    """Return minimum move % threshold: 0.5% for indices, 0.75% for stocks."""
    return 0.005 if symbol in INDEX_SYMBOLS else 0.0075


def get_earnings_dates(symbol: str) -> set:
    """Return set of earnings dates for a symbol. Empty set for index symbols."""
    if symbol in INDEX_SYMBOLS:
        return set()
    try:
        ticker = yf.Ticker(symbol)
        ed = ticker.earnings_dates
        if ed is not None and not ed.empty:
            return {d.date() for d in ed.index}
    except Exception:
        pass
    return set()

def find_valid_periods(df: pd.DataFrame) -> list:
    """Find all valid Fri-Mon-Tue-Wed periods in the data.

    Returns list of (friday_date, monday_date, tuesday_date, wednesday_date) tuples
    where all four days have trading data present.
    """
    trading_dates = sorted(set(df.index.date))

    periods = []
    for d in trading_dates:
        if d.weekday() != 4:  # Not a Friday
            continue
        friday = d
        monday = date.fromordinal(friday.toordinal() + 3)
        tuesday = date.fromordinal(friday.toordinal() + 4)
        wednesday = date.fromordinal(friday.toordinal() + 5)

        if monday in trading_dates and tuesday in trading_dates and wednesday in trading_dates:
            periods.append((friday, monday, tuesday, wednesday))

    return periods

def extract_prices(df: pd.DataFrame, friday, monday, tuesday, wednesday) -> dict:
    """Extract the key price points for a Fri-Mon-Tue-Wed period.

    Returns dict with friday_close, monday_2pm, tuesday_10am, tuesday_12pm,
    wednesday_high, wednesday_low.
    Returns empty dict if any data is missing.
    """
    # Friday close: last candle of the day
    fri_data = df[df.index.date == friday]
    if fri_data.empty:
        return {}
    friday_close = float(fri_data["Close"].iloc[-1])

    # Monday 2:00 PM: close of the 1:30 candle (covers 1:30-2:00)
    mon_data = df[df.index.date == monday]
    if mon_data.empty:
        return {}
    mon_afternoon = mon_data.between_time("13:30", "14:00")
    if mon_afternoon.empty:
        return {}
    monday_2pm = float(mon_afternoon["Close"].iloc[-1])

    # Tuesday 10:00 AM: close of the 9:30 candle (covers 9:30-10:00)
    tue_data = df[df.index.date == tuesday]
    if tue_data.empty:
        return {}
    tue_morning = tue_data.between_time("09:30", "10:00")
    if tue_morning.empty:
        return {}
    tuesday_10am = float(tue_morning["Close"].iloc[-1])

    # Tuesday 12:00 PM: close of the 11:30 candle (covers 11:30-12:00)
    tue_midday = tue_data.between_time("11:30", "12:00")
    if tue_midday.empty:
        return {}
    tuesday_12pm = float(tue_midday["Close"].iloc[-1])

    # Wednesday high and low (full day)
    wed_data = df[df.index.date == wednesday]
    if wed_data.empty:
        return {}
    wednesday_high = float(wed_data["High"].max())
    wednesday_low = float(wed_data["Low"].min())

    return {
        "friday_close": friday_close,
        "monday_2pm": monday_2pm,
        "tuesday_10am": tuesday_10am,
        "tuesday_12pm": tuesday_12pm,
        "wednesday_high": wednesday_high,
        "wednesday_low": wednesday_low,
    }

def compute_retracement(friday_close: float, tuesday_10am: float,
                        wednesday_high: float, wednesday_low: float) -> dict:
    """Compute retracement metrics for a Fri-Wed period.

    Args:
        friday_close: Friday closing price
        tuesday_10am: Tuesday 10:00 AM Eastern price
        wednesday_high: Wednesday intraday high
        wednesday_low: Wednesday intraday low

    Returns dict with move, move_direction, retracement_price, retracement_pct, retraced_90pct.
    """
    move = tuesday_10am - friday_close

    # Flat threshold: < $0.05 or < 0.05%
    if abs(move) < 0.05 or (friday_close > 0 and abs(move) / friday_close < 0.0005):
        return {
            "move": move,
            "move_direction": "flat",
            "retracement_price": None,
            "retracement_pct": None,
            "retraced_90pct": None,
        }

    if move > 0:  # Price went UP, reversal is down to wednesday_low
        direction = "up"
        retracement_price = wednesday_low
        continuation_price = wednesday_high
        move_retraced_pct = (tuesday_10am - wednesday_low) / move * 100
        retracement_pct = abs(tuesday_10am - wednesday_low) / tuesday_10am * 100
        continuation_pct = abs(wednesday_high - tuesday_10am) / tuesday_10am * 100
    else:  # Price went DOWN, reversal is up to wednesday_high
        direction = "down"
        retracement_price = wednesday_high
        continuation_price = wednesday_low
        move_retraced_pct = (wednesday_high - tuesday_10am) / abs(move) * 100
        retracement_pct = abs(wednesday_high - tuesday_10am) / tuesday_10am * 100
        continuation_pct = abs(tuesday_10am - wednesday_low) / tuesday_10am * 100

    return {
        "move": move,
        "move_direction": direction,
        "retracement_price": retracement_price,
        "retracement_pct": round(retracement_pct, 2),
        "continuation_price": continuation_price,
        "continuation_pct": round(continuation_pct, 2),
        "retraced_90pct": move_retraced_pct >= 90.0,
    }

FIXED_TARGETS = [1.0, 2.0, 3.0, 5.0]
WED_CHECKPOINTS = ["09:30", "10:00", "10:30", "11:00", "11:30", "12:00",
                   "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00"]


def analyze_wednesday_intraday(df: pd.DataFrame, wednesday, entry_price: float,
                               direction: str, prefix: str) -> dict:
    """Analyze Wednesday intraday path for a triggered trade.

    Args:
        df: Full intraday DataFrame
        wednesday: Wednesday date
        entry_price: The entry price (mon2pm, tue10am, or tue12pm)
        direction: 'up' or 'down' - the move direction (reversal goes opposite)
        prefix: Timeframe prefix for key naming

    Returns dict with fixed target hits and time-based reversal %.
    """
    wed_data = df[df.index.date == wednesday].sort_index()
    if wed_data.empty:
        return {}

    result = {}

    # Fixed targets: did the reversal hit X% at any point during Wednesday?
    for target in FIXED_TARGETS:
        if direction == "up":
            # Reversal is DOWN, check if price dropped target% from entry
            target_price = entry_price * (1 - target / 100)
            hit = float(wed_data["Low"].min()) <= target_price
        else:
            # Reversal is UP, check if price rose target% from entry
            target_price = entry_price * (1 + target / 100)
            hit = float(wed_data["High"].max()) >= target_price
        result[f"{prefix}_target_{target}pct"] = hit

    # Time-based: reversal % at each checkpoint
    for checkpoint in WED_CHECKPOINTS:
        bars_up_to = wed_data.between_time("09:30", checkpoint)
        if bars_up_to.empty:
            result[f"{prefix}_at_{checkpoint.replace(':', '')}"] = None
            continue
        if direction == "up":
            # Reversal is DOWN, best reversal price is lowest low so far
            best_price = float(bars_up_to["Low"].min())
            reversal_pct = (entry_price - best_price) / entry_price * 100
        else:
            # Reversal is UP, best reversal price is highest high so far
            best_price = float(bars_up_to["High"].max())
            reversal_pct = (best_price - entry_price) / entry_price * 100
        result[f"{prefix}_at_{checkpoint.replace(':', '')}"] = round(reversal_pct, 2)

    return result


def download_intraday_data(symbol: str) -> pd.DataFrame:
    """Download 60 days of 30-minute intraday data for a symbol."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="60d", interval="30m")
    df.index = df.index.tz_convert("America/New_York")
    return df

def analyze_symbol(symbol: str, output_dir: str = "output") -> list:
    """Run full analysis for a single symbol. Returns list of result dicts."""
    df = download_intraday_data(symbol)
    periods = find_valid_periods(df)
    earnings = get_earnings_dates(symbol)

    results = []
    for fri, mon, tue, wed in periods:
        # Skip periods where earnings fell in the Fri-Wed window
        period_days = {fri, mon, tue, wed}
        if period_days & earnings:
            continue

        prices = extract_prices(df, fri, mon, tue, wed)
        if not prices:
            continue

        # Skip if all timeframe moves are below minimum threshold
        threshold = min_move_pct(symbol)
        fri_close = prices["friday_close"]
        move_mon2pm_pct = abs(prices["monday_2pm"] - fri_close) / fri_close if fri_close > 0 else 0
        move_10am_pct = abs(prices["tuesday_10am"] - fri_close) / fri_close if fri_close > 0 else 0
        move_12pm_pct = abs(prices["tuesday_12pm"] - fri_close) / fri_close if fri_close > 0 else 0
        if move_mon2pm_pct < threshold and move_10am_pct < threshold and move_12pm_pct < threshold:
            continue

        ret_mon2pm = compute_retracement(
            prices["friday_close"], prices["monday_2pm"],
            prices["wednesday_high"], prices["wednesday_low"],
        )
        ret_10am = compute_retracement(
            prices["friday_close"], prices["tuesday_10am"],
            prices["wednesday_high"], prices["wednesday_low"],
        )
        ret_12pm = compute_retracement(
            prices["friday_close"], prices["tuesday_12pm"],
            prices["wednesday_high"], prices["wednesday_low"],
        )

        # Skip only if all timeframes are flat
        if (ret_mon2pm["move_direction"] == "flat"
                and ret_10am["move_direction"] == "flat"
                and ret_12pm["move_direction"] == "flat"):
            continue

        row = {
            "symbol": symbol,
            "friday_date": str(fri),
            "monday_date": str(mon),
            "tuesday_date": str(tue),
            "wednesday_date": str(wed),
            **prices,
        }
        for key, val in ret_mon2pm.items():
            row[f"mon2pm_{key}"] = val
        for key, val in ret_10am.items():
            row[f"10am_{key}"] = val
        for key, val in ret_12pm.items():
            row[f"12pm_{key}"] = val

        # Wednesday intraday analysis for triggered timeframes
        if ret_mon2pm.get("retraced_90pct"):
            row.update(analyze_wednesday_intraday(
                df, wed, prices["monday_2pm"], ret_mon2pm["move_direction"], "mon2pm"))
        if ret_10am.get("retraced_90pct"):
            row.update(analyze_wednesday_intraday(
                df, wed, prices["tuesday_10am"], ret_10am["move_direction"], "10am"))
        if ret_12pm.get("retraced_90pct"):
            row.update(analyze_wednesday_intraday(
                df, wed, prices["tuesday_12pm"], ret_12pm["move_direction"], "12pm"))

        results.append(row)

    # Write CSV
    os.makedirs(output_dir, exist_ok=True)
    if results:
        csv_path = os.path.join(output_dir, f"{symbol}.csv")
        all_keys = {}
        for r in results:
            all_keys.update(r)
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys.keys())
            writer.writeheader()
            writer.writerows(results)

    return results


def _summarize_timeframe(all_results: list, prefix: str) -> dict:
    """Compute summary stats for a single timeframe prefix (e.g. '10am' or '12pm')."""
    retrace_key = f"{prefix}_retracement_pct"
    hit_key = f"{prefix}_retraced_90pct"
    direction_key = f"{prefix}_move_direction"

    # Filter to rows where this timeframe is not flat and move meets symbol threshold
    move_key = f"{prefix}_move"
    rows = [r for r in all_results
            if r.get(direction_key) != "flat"
            and r.get(retrace_key) is not None
            and (abs(r[move_key]) / r["friday_close"] >= min_move_pct(r["symbol"]) if r["friday_close"] > 0 else False)]
    total = len(rows)
    hits = [r for r in rows if r.get(hit_key)]
    hit_rate = (len(hits) / total * 100) if total > 0 else 0

    continuation_key = f"{prefix}_continuation_pct"
    retrace_values = [r[retrace_key] for r in rows]
    continuation_values = [r[continuation_key] for r in rows]
    avg_retracement = np.mean(retrace_values) if retrace_values else 0
    median_retracement = float(np.median(retrace_values)) if retrace_values else 0
    median_continuation = float(np.median(continuation_values)) if continuation_values else 0
    hit_retrace_values = [r[retrace_key] for r in rows if r.get(hit_key)]
    avg_retracement_on_hit = np.mean(hit_retrace_values) if hit_retrace_values else 0

    # Average of top 10% reversals (highest retracement values)
    sorted_desc = sorted(retrace_values, reverse=True)
    top_10_count = max(1, len(sorted_desc) // 10)
    top_10_values = sorted_desc[:top_10_count]
    avg_top_10_pct = float(np.mean(top_10_values)) if top_10_values else 0

    # $100 per trade on hit periods: total return from reversal vs continuation
    hit_reversal_return = sum(r[retrace_key] / 100 * 100 for r in hits)
    hit_continuation_return = sum(r[continuation_key] / 100 * 100 for r in hits)
    hit_reversal_values = [r[retrace_key] for r in hits]
    hit_continuation_values = [r[continuation_key] for r in hits]
    median_reversal_trade = float(np.median(hit_reversal_values)) if hit_reversal_values else 0
    median_continuation_trade = float(np.median(hit_continuation_values)) if hit_continuation_values else 0
    num_trades = len(hits)
    total_invested = num_trades * 100

    # Fixed target hit rates (% of triggered trades that hit each target)
    target_hit_rates = {}
    for target in FIXED_TARGETS:
        key = f"{prefix}_target_{target}pct"
        hits_with_target = [r for r in hits if key in r]
        if hits_with_target:
            hit_count = sum(1 for r in hits_with_target if r[key])
            target_hit_rates[f"{target}%"] = round(hit_count / len(hits_with_target) * 100, 2)
        else:
            target_hit_rates[f"{target}%"] = 0

    # Time-based: median reversal % at each Wednesday checkpoint
    time_based = {}
    for checkpoint in WED_CHECKPOINTS:
        key = f"{prefix}_at_{checkpoint.replace(':', '')}"
        values = [r[key] for r in hits if key in r and r[key] is not None]
        time_based[checkpoint] = round(float(np.median(values)), 2) if values else 0

    per_symbol = {}
    for r in rows:
        sym = r["symbol"]
        if sym not in per_symbol:
            per_symbol[sym] = {"total": 0, "hits": 0}
        per_symbol[sym]["total"] += 1
        if r.get(hit_key):
            per_symbol[sym]["hits"] += 1
    for sym in per_symbol:
        s = per_symbol[sym]
        s["hit_rate"] = round(s["hits"] / s["total"] * 100, 2) if s["total"] > 0 else 0

    buckets = {"0-25%": 0, "25-50%": 0, "50-75%": 0, "75-90%": 0, "90-100%": 0, ">100%": 0}
    for pct in retrace_values:
        if pct > 100:
            buckets[">100%"] += 1
        elif pct >= 90:
            buckets["90-100%"] += 1
        elif pct >= 75:
            buckets["75-90%"] += 1
        elif pct >= 50:
            buckets["50-75%"] += 1
        elif pct >= 25:
            buckets["25-50%"] += 1
        else:
            buckets["0-25%"] += 1

    return {
        "total_periods": total,
        "hit_count": len(hits),
        "hit_rate": round(hit_rate, 2),
        "avg_retracement": round(float(avg_retracement), 2),
        "median_retracement": round(median_retracement, 2),
        "median_continuation": round(median_continuation, 2),
        "avg_retracement_on_hit": round(float(avg_retracement_on_hit), 2),
        "avg_top_10_pct": round(avg_top_10_pct, 2),
        "num_trades": num_trades,
        "total_invested": total_invested,
        "reversal_return": round(hit_reversal_return, 2),
        "continuation_return": round(hit_continuation_return, 2),
        "median_reversal_trade": round(median_reversal_trade, 2),
        "median_continuation_trade": round(median_continuation_trade, 2),
        "target_hit_rates": target_hit_rates,
        "time_based": time_based,
        "per_symbol": per_symbol,
        "distribution": buckets,
    }


def compute_summary(all_results: list) -> dict:
    """Compute aggregate statistics across all symbols for both timeframes."""
    return {
        "mon2pm": _summarize_timeframe(all_results, "mon2pm"),
        "10am": _summarize_timeframe(all_results, "10am"),
        "12pm": _summarize_timeframe(all_results, "12pm"),
    }


def _print_timeframe_summary(label: str, s: dict):
    """Print summary for a single timeframe."""
    print(f"\n  [{label}]")
    print(f"  Total non-flat periods:              {s['total_periods']}")
    print(f"  Periods with >= 90% retracement:     {s['hit_count']}")
    print(f"  Hit rate:                            {s['hit_rate']}%")
    print(f"  Average retracement:                 {s['avg_retracement']}%")

    print(f"\n  --- Distribution ({label}) ---")
    for bucket, count in s["distribution"].items():
        pct = round(count / s["total_periods"] * 100, 1) if s["total_periods"] > 0 else 0
        bar = "#" * int(pct / 2)
        print(f"    {bucket:>8s}: {count:3d} ({pct:5.1f}%) {bar}")

    print(f"\n  --- Per-Symbol Hit Rates ({label}) ---")
    for sym, stats in sorted(s["per_symbol"].items()):
        print(f"    {sym:>6s}: {stats['hits']}/{stats['total']} = {stats['hit_rate']}%")


def print_summary(summary: dict):
    """Print summary statistics to console."""
    print("\n" + "=" * 60)
    print("WEDNESDAY REVERSAL ANALYSIS — SUMMARY")
    print("=" * 60)

    _print_timeframe_summary("Tuesday 10 AM", summary["10am"])
    _print_timeframe_summary("Tuesday 12 PM", summary["12pm"])

    print("=" * 60)


def write_summary_csv(summary: dict, output_dir: str = "output"):
    """Write aggregate summary to CSV."""
    csv_path = os.path.join(output_dir, "summary.csv")
    # Merge per-symbol data from both timeframes
    all_syms = sorted(set(list(summary["10am"]["per_symbol"].keys()) + list(summary["12pm"]["per_symbol"].keys())))
    rows = []
    for sym in all_syms:
        s10 = summary["10am"]["per_symbol"].get(sym, {"total": 0, "hits": 0, "hit_rate": 0})
        s12 = summary["12pm"]["per_symbol"].get(sym, {"total": 0, "hits": 0, "hit_rate": 0})
        rows.append({
            "symbol": sym,
            "total_periods": s10["total"],
            "hits_90pct_10am": s10["hits"],
            "hit_rate_pct_10am": s10["hit_rate"],
            "hits_90pct_12pm": s12["hits"],
            "hit_rate_pct_12pm": s12["hit_rate"],
        })
    fieldnames = ["symbol", "total_periods", "hits_90pct_10am", "hit_rate_pct_10am", "hits_90pct_12pm", "hit_rate_pct_12pm"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSummary CSV written to {csv_path}")


if __name__ == "__main__":
    all_results = []
    for symbol in SYMBOLS:
        print(f"Analyzing {symbol}...")
        results = analyze_symbol(symbol)
        all_results.extend(results)
        print(f"  {symbol}: {len(results)} valid periods found")

    summary = compute_summary(all_results)
    print_summary(summary)
    write_summary_csv(summary)
