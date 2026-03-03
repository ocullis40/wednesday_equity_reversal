# Wednesday Equity Reversal — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python script that tests whether stocks revert to their Friday closing price by Wednesday after moving in the first 30 minutes of Mon/Tue trading.

**Architecture:** Single-script analysis tool (`analyze.py`) that downloads 60 days of 30-minute intraday data from Yahoo Finance, identifies valid Fri–Tue–Wed periods, computes retracement metrics, and outputs CSV files plus console summary statistics.

**Tech Stack:** Python 3, yfinance, pandas, numpy

---

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `analyze.py` (empty placeholder)
- Create: `output/` directory

**Step 1: Create requirements.txt**

```
yfinance
pandas
numpy
```

**Step 2: Create virtual environment and install dependencies**

Run: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
Expected: All packages install successfully.

**Step 3: Create output directory and empty script**

Run: `mkdir -p output && touch analyze.py`

**Step 4: Verify yfinance works**

Run: `python3 -c "import yfinance as yf; data = yf.download('SPY', period='5d', interval='30m'); print(data.head())"`
Expected: A few rows of 30-minute SPY candles printed.

**Step 5: Commit**

```bash
git add requirements.txt analyze.py output/.gitkeep
git commit -m "chore: project setup with yfinance, pandas, numpy"
```

---

### Task 2: Data Download Module

**Files:**
- Modify: `analyze.py`

**Step 1: Write the failing test — download function**

Create `test_analyze.py`:

```python
import pandas as pd
from analyze import download_intraday_data

def test_download_returns_dataframe():
    df = download_intraday_data("SPY")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "Close" in df.columns or ("Close", "SPY") in df.columns
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest test_analyze.py::test_download_returns_dataframe -v`
Expected: FAIL — `ImportError: cannot import name 'download_intraday_data'`

**Step 3: Implement download_intraday_data**

In `analyze.py`:

```python
import yfinance as yf
import pandas as pd
import numpy as np

SYMBOLS = [
    "IREN", "QQQ", "SPY", "TSLA", "NVDA", "AAPL", "GOOG", "HOOD", "MSFT", "OKLO",
    "ILMN", "FSLR", "AMZN", "SMCI", "META", "AMD", "JPM", "GS", "SLV", "BP",
]

def download_intraday_data(symbol: str) -> pd.DataFrame:
    """Download 60 days of 30-minute intraday data for a symbol."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="60d", interval="30m")
    df.index = df.index.tz_convert("America/New_York")
    return df
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest test_analyze.py::test_download_returns_dataframe -v`
Expected: PASS

**Step 5: Commit**

```bash
git add analyze.py test_analyze.py
git commit -m "feat: add intraday data download from yfinance"
```

---

### Task 3: Identify Valid Fri–Tue–Wed Periods

**Files:**
- Modify: `analyze.py`
- Modify: `test_analyze.py`

**Step 1: Write the failing test — period finder**

In `test_analyze.py`:

```python
from analyze import find_valid_periods

def test_find_valid_periods_returns_list_of_tuples():
    df = download_intraday_data("SPY")
    periods = find_valid_periods(df)
    assert isinstance(periods, list)
    assert len(periods) > 0
    # Each period is (friday_date, monday_date, tuesday_date, wednesday_date)
    for fri, mon, tue, wed in periods:
        assert fri.weekday() == 4  # Friday
        assert mon.weekday() == 0  # Monday
        assert tue.weekday() == 1  # Tuesday
        assert wed.weekday() == 2  # Wednesday
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest test_analyze.py::test_find_valid_periods_returns_list_of_tuples -v`
Expected: FAIL — `ImportError: cannot import name 'find_valid_periods'`

**Step 3: Implement find_valid_periods**

In `analyze.py`:

```python
from datetime import date

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
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest test_analyze.py::test_find_valid_periods_returns_list_of_tuples -v`
Expected: PASS

**Step 5: Commit**

```bash
git add analyze.py test_analyze.py
git commit -m "feat: identify valid Fri-Tue-Wed trading periods"
```

---

### Task 4: Extract Price Points

**Files:**
- Modify: `analyze.py`
- Modify: `test_analyze.py`

**Step 1: Write the failing test — price extraction**

In `test_analyze.py`:

```python
from analyze import extract_prices

def test_extract_prices_returns_dict():
    df = download_intraday_data("SPY")
    periods = find_valid_periods(df)
    assert len(periods) > 0
    fri, mon, tue, wed = periods[0]
    prices = extract_prices(df, fri, tue, wed)
    assert "friday_close" in prices
    assert "tuesday_10am" in prices
    assert "wednesday_high" in prices
    assert "wednesday_low" in prices
    assert all(isinstance(v, float) for v in prices.values())
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest test_analyze.py::test_extract_prices_returns_dict -v`
Expected: FAIL — `ImportError: cannot import name 'extract_prices'`

**Step 3: Implement extract_prices**

In `analyze.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest test_analyze.py::test_extract_prices_returns_dict -v`
Expected: PASS

**Step 5: Commit**

```bash
git add analyze.py test_analyze.py
git commit -m "feat: extract Friday close, Tuesday 10am, Wednesday high/low prices"
```

---

### Task 5: Compute Retracement

**Files:**
- Modify: `analyze.py`
- Modify: `test_analyze.py`

**Step 1: Write the failing test — retracement calculation**

In `test_analyze.py`:

```python
from analyze import compute_retracement

def test_retracement_up_move_full_retrace():
    # Price went up 10, Wednesday low came all the way back
    result = compute_retracement(100.0, 110.0, 115.0, 100.0)
    assert result["move_direction"] == "up"
    assert result["retracement_pct"] == 100.0
    assert result["retraced_90pct"] is True

def test_retracement_down_move_partial():
    # Price went down 10, Wednesday high only recovered 5
    result = compute_retracement(100.0, 90.0, 95.0, 88.0)
    assert result["move_direction"] == "down"
    assert result["retracement_pct"] == 50.0
    assert result["retraced_90pct"] is False

def test_retracement_flat_move():
    result = compute_retracement(100.0, 100.02, 100.5, 99.5)
    assert result["move_direction"] == "flat"
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest test_analyze.py -k "retracement" -v`
Expected: FAIL — `ImportError: cannot import name 'compute_retracement'`

**Step 3: Implement compute_retracement**

In `analyze.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest test_analyze.py -k "retracement" -v`
Expected: All 3 PASS

**Step 5: Commit**

```bash
git add analyze.py test_analyze.py
git commit -m "feat: compute retracement percentage with direction detection"
```

---

### Task 6: Main Analysis Loop & CSV Output

**Files:**
- Modify: `analyze.py`

**Step 1: Write the failing test — full analysis for one symbol**

In `test_analyze.py`:

```python
import os
from analyze import analyze_symbol

def test_analyze_symbol_produces_csv():
    results = analyze_symbol("SPY", output_dir="output")
    assert isinstance(results, list)
    assert len(results) > 0
    assert os.path.exists("output/SPY.csv")
    # Each result row has required keys
    for row in results:
        assert "friday_date" in row
        assert "retracement_pct" in row
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest test_analyze.py::test_analyze_symbol_produces_csv -v`
Expected: FAIL

**Step 3: Implement analyze_symbol**

In `analyze.py`:

```python
import os
import csv

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
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest test_analyze.py::test_analyze_symbol_produces_csv -v`
Expected: PASS

**Step 5: Commit**

```bash
git add analyze.py test_analyze.py
git commit -m "feat: per-symbol analysis loop with CSV output"
```

---

### Task 7: Summary Statistics & Console Output

**Files:**
- Modify: `analyze.py`

**Step 1: Write the failing test — summary stats**

In `test_analyze.py`:

```python
from analyze import compute_summary

def test_compute_summary():
    fake_results = [
        {"symbol": "SPY", "retracement_pct": 95.0, "retraced_90pct": True, "move_direction": "up"},
        {"symbol": "SPY", "retracement_pct": 40.0, "retraced_90pct": False, "move_direction": "down"},
        {"symbol": "QQQ", "retracement_pct": 92.0, "retraced_90pct": True, "move_direction": "up"},
    ]
    summary = compute_summary(fake_results)
    assert summary["total_periods"] == 3
    assert summary["hit_count"] == 2
    assert abs(summary["hit_rate"] - 66.67) < 0.1
    assert len(summary["per_symbol"]) == 2
    assert len(summary["distribution"]) > 0
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest test_analyze.py::test_compute_summary -v`
Expected: FAIL

**Step 3: Implement compute_summary and print_summary**

In `analyze.py`:

```python
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
    print(f"Total valid Fri–Wed periods analyzed: {summary['total_periods']}")
    print(f"Periods with >= 90% retracement:      {summary['hit_count']}")
    print(f"Overall hit rate:                      {summary['hit_rate']}%")
    print(f"Average retracement:                   {summary['avg_retracement']}%")

    print("\n--- Distribution ---")
    for bucket, count in summary["distribution"].items():
        pct = round(count / summary["total_periods"] * 100, 1) if summary["total_periods"] > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {bucket:>8s}: {count:3d} ({pct:5.1f}%) {bar}")

    print("\n--- Per-Symbol Hit Rates ---")
    for sym, stats in sorted(summary["per_symbol"].items()):
        print(f"  {sym:>6s}: {stats['hits']}/{stats['total']} = {stats['hit_rate']}%")
    print("=" * 60)
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest test_analyze.py::test_compute_summary -v`
Expected: PASS

**Step 5: Commit**

```bash
git add analyze.py test_analyze.py
git commit -m "feat: summary statistics with distribution and per-symbol breakdown"
```

---

### Task 8: Main Entrypoint & Summary CSV

**Files:**
- Modify: `analyze.py`

**Step 1: Add main block and summary CSV output**

At the bottom of `analyze.py`:

```python
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
```

**Step 2: Run the full script**

Run: `python3 analyze.py`
Expected: Downloads data for all 20 symbols, prints per-symbol progress, prints summary stats, writes CSVs to `output/`.

**Step 3: Verify output files exist**

Run: `ls output/*.csv | head -5`
Expected: Symbol CSV files and summary.csv present.

**Step 4: Commit**

```bash
git add analyze.py
git commit -m "feat: main entrypoint with full 20-symbol analysis run"
```

---

### Task 9: Run Full Analysis & Verify Results

**Step 1: Run all tests**

Run: `python3 -m pytest test_analyze.py -v`
Expected: All tests PASS.

**Step 2: Run full analysis**

Run: `python3 analyze.py`
Expected: Complete output with summary statistics for all 20 symbols.

**Step 3: Spot-check one symbol CSV**

Run: `cat output/SPY.csv`
Expected: CSV with columns for all data points, reasonable price values.

**Step 4: Final commit**

```bash
git add output/.gitkeep
git commit -m "chore: analysis verified and output directory ready"
```
