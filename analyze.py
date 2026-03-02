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

def extract_prices(df: pd.DataFrame, friday, tuesday, wednesday) -> dict:
    """Extract the key price points for a Fri-Tue-Wed period.

    Returns dict with friday_close, tuesday_10am, wednesday_high, wednesday_low.
    Returns empty dict if any data is missing.
    """
    # Friday close: last candle of the day
    fri_data = df[df.index.date == friday]
    if fri_data.empty:
        return {}
    friday_close = float(fri_data["Close"].iloc[-1])

    # Tuesday 10:00 AM: close of the 9:30 candle (covers 9:30-10:00)
    tue_data = df[df.index.date == tuesday]
    if tue_data.empty:
        return {}
    tue_morning = tue_data.between_time("09:30", "10:00")
    if tue_morning.empty:
        return {}
    tuesday_10am = float(tue_morning["Close"].iloc[-1])

    # Wednesday high and low (full day)
    wed_data = df[df.index.date == wednesday]
    if wed_data.empty:
        return {}
    wednesday_high = float(wed_data["High"].max())
    wednesday_low = float(wed_data["Low"].min())

    return {
        "friday_close": friday_close,
        "tuesday_10am": tuesday_10am,
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

    if move > 0:  # Price went UP
        direction = "up"
        retracement_price = wednesday_low
        retracement_pct = (tuesday_10am - wednesday_low) / move * 100
    else:  # Price went DOWN
        direction = "down"
        retracement_price = wednesday_high
        retracement_pct = (wednesday_high - tuesday_10am) / abs(move) * 100

    return {
        "move": move,
        "move_direction": direction,
        "retracement_price": retracement_price,
        "retracement_pct": round(retracement_pct, 2),
        "retraced_90pct": retracement_pct >= 90.0,
    }

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

    results = []
    for fri, mon, tue, wed in periods:
        prices = extract_prices(df, fri, tue, wed)
        if not prices:
            continue

        retracement = compute_retracement(
            prices["friday_close"], prices["tuesday_10am"],
            prices["wednesday_high"], prices["wednesday_low"],
        )

        if retracement["move_direction"] == "flat":
            continue

        row = {
            "symbol": symbol,
            "friday_date": str(fri),
            "tuesday_date": str(tue),
            "wednesday_date": str(wed),
            **prices,
            **retracement,
        }
        results.append(row)

    # Write CSV
    os.makedirs(output_dir, exist_ok=True)
    if results:
        csv_path = os.path.join(output_dir, f"{symbol}.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    return results


def compute_summary(all_results: list) -> dict:
    """Compute aggregate statistics across all symbols."""
    total = len(all_results)
    hits = [r for r in all_results if r["retraced_90pct"]]
    hit_rate = (len(hits) / total * 100) if total > 0 else 0

    retrace_values = [r["retracement_pct"] for r in all_results]
    avg_retracement = np.mean(retrace_values) if retrace_values else 0

    # Per-symbol breakdown
    per_symbol = {}
    for r in all_results:
        sym = r["symbol"]
        if sym not in per_symbol:
            per_symbol[sym] = {"total": 0, "hits": 0}
        per_symbol[sym]["total"] += 1
        if r["retraced_90pct"]:
            per_symbol[sym]["hits"] += 1
    for sym in per_symbol:
        s = per_symbol[sym]
        s["hit_rate"] = round(s["hits"] / s["total"] * 100, 2) if s["total"] > 0 else 0

    # Distribution buckets
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
        "per_symbol": per_symbol,
        "distribution": buckets,
    }


def print_summary(summary: dict):
    """Print summary statistics to console."""
    print("\n" + "=" * 60)
    print("WEDNESDAY REVERSAL ANALYSIS — SUMMARY")
    print("=" * 60)
    print(f"Total valid Fri-Wed periods analyzed: {summary['total_periods']}")
    print(f"Periods with >= 90% retracement:      {summary['hit_count']}")
    print(f"Overall hit rate:                      {summary['hit_rate']}%")
    print(f"Average retracement:                   {summary['avg_retracement']}%")

    print("\n--- Distribution ---")
    for bucket, count in summary["distribution"].items():
        pct = round(count / summary["total_periods"] * 100, 1) if summary["total_periods"] > 0 else 0
        bar = "#" * int(pct / 2)
        print(f"  {bucket:>8s}: {count:3d} ({pct:5.1f}%) {bar}")

    print("\n--- Per-Symbol Hit Rates ---")
    for sym, stats in sorted(summary["per_symbol"].items()):
        print(f"  {sym:>6s}: {stats['hits']}/{stats['total']} = {stats['hit_rate']}%")
    print("=" * 60)


def write_summary_csv(summary: dict, output_dir: str = "output"):
    """Write aggregate summary to CSV."""
    csv_path = os.path.join(output_dir, "summary.csv")
    rows = []
    for sym, stats in sorted(summary["per_symbol"].items()):
        rows.append({
            "symbol": sym,
            "total_periods": stats["total"],
            "hits_90pct": stats["hits"],
            "hit_rate_pct": stats["hit_rate"],
        })
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["symbol", "total_periods", "hits_90pct", "hit_rate_pct"])
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
