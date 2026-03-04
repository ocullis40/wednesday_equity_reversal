# Wednesday Equity Reversal

A trading research platform that analyzes weekly momentum patterns across 20 equities and indices. The core thesis: stocks that make significant moves from Friday close through early in the week tend to exhibit predictable continuation and reversal behavior by Wednesday.

## Setup

```bash
pip install -r requirements.txt
```

For historical data backfill (optional — falls back to Yahoo Finance):
```bash
# Add Alpaca credentials to .env
ALPACA_API_KEY=your_key
ALPACA_API_SECRET=your_secret

python scripts/backfill_bars.py
```

## Usage

### Run Analysis
```bash
python analyze.py
```
Analyzes all symbols, writes per-symbol CSVs to `output/`, and prints summary statistics.

### Launch Dashboard
```bash
streamlit run app.py
```
Interactive dashboard at `localhost:8501` with live signals, historical analysis, and trade tracking.

### Run Tests
```bash
python -m pytest tests/ -v
```
92 unit tests covering all core analysis logic.

## Symbols

**Indices** (0.5% move threshold): QQQ, SPY

**Stocks** (0.75% move threshold): IREN, TSLA, NVDA, AAPL, GOOG, HOOD, MSFT, OKLO, ILMN, FSLR, AMZN, SMCI, META, AMD, JPM, GS, SLV, BP

## How It Works

### Signal Detection

1. Measure the move from **Friday close** to a signal timeframe (Monday 2 PM, Tuesday 10 AM, or Tuesday 12 PM)
2. If the move exceeds the minimum threshold, a signal fires
3. Weeks with earnings for a given symbol are excluded

### Analysis Types

**Retracement Analysis** — What percentage of the Friday→signal move gets retraced by Wednesday? Tracks 90%+ retracement rates, distribution buckets, and per-symbol hit rates across all three timeframes.

**Confirmation Thresholds** — After the signal, wait for 0.1–0.5% additional continuation before entering. Compares two strategies:
- **Reversal**: Fade the move (target 2% reversal, stop 1.5%)
- **Continuation**: Ride the move (target 2% continuation, stop 1.5%)

Scans from entry time through Wednesday close (not just Wednesday bars).

**Fixed Target Hit Rates** — Of triggered trades (90%+ retracement), what percentage hit 1%, 2%, 3%, or 5% reversal targets on Wednesday?

**Time-Based Checkpoints** — Median reversal percentage at each 30-minute interval through Wednesday, showing when the bulk of the move happens.

### Live Signals

The dashboard scans all symbols each week and displays confirmed Monday 2 PM signals with:
- Entry price (after 0.2% continuation confirmation)
- Target (2% reversal) and stop (1.5%)
- Editable actual entry/exit fields with auto-calculated P&L
- Signals persist to `current_signals.json` and expire Wednesday 4 PM

## Data Sources

**Primary**: 2 years of 30-minute bars from Alpaca, stored in `data/bars/`

**Fallback**: Yahoo Finance (60 days, 30-minute interval) when local CSV not available

**Earnings dates**: Yahoo Finance `earnings_dates` API (~6 years of coverage)

## Dashboard Sections

1. **Current Signals** — Live trade signals for the active week with editable tracking
2. **Historical Summary** — Hit rates, median retracement/continuation across timeframes
3. **$100/Trade P&L** — Simulated returns on triggered periods
4. **Fixed Target Hit Rates** — % of triggered trades hitting each profit target
5. **Confirmation Threshold Analysis** — Reversal vs continuation comparison (tabbed)
6. **Wednesday Reversal Chart** — Median reversal % through the day
7. **Per-Symbol Breakdown** — Bar chart and table of hit rates by symbol

## Project Structure

```
├── analyze.py              # Core analysis engine
├── app.py                  # Streamlit dashboard
├── scripts/
│   └── backfill_bars.py    # Alpaca historical data download
├── tests/                  # 92 unit tests
├── data/bars/              # 30-minute OHLCV CSVs
├── output/                 # Analysis result CSVs
├── docs/plans/             # Design documents
└── requirements.txt
```
