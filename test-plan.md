# Test Plan

## Unit Tests (no network, fast)

### Price Extraction
- Extracts correct prices from a synthetic DataFrame for all timeframes (Friday close, Monday 2 PM, Tuesday 10 AM, Tuesday 12 PM, Wednesday high/low)
- Returns empty dict when any required data is missing

### Retracement Calculation
- Correctly identifies up and down move directions
- Computes retracement percentage as stock % move from entry to Wednesday extreme
- Computes continuation percentage as stock % move in the same direction
- Applies 90% threshold using the original move ratio, not the stock % move
- Classifies flat moves when below the dollar and percentage thresholds

### Minimum Move Threshold
- Index symbols (QQQ, SPY) use 0.5% threshold
- All other symbols use 0.75% threshold

### Earnings Exclusion
- Periods with earnings on any day (Friday through Wednesday) are excluded
- Earnings on Thursday before the Friday — period is included (outside window)
- Earnings on the Friday — period is excluded
- Earnings on the Wednesday — period is excluded
- Index symbols are never excluded for earnings
- Symbol with no earnings data available (e.g. ETFs like SLV) — period is included
- Symbol where the earnings API call fails — period is included, not silently dropped

### Per-Timeframe Filtering
- Summary stats for each timeframe only include periods where that timeframe's move meets the symbol's threshold
- A period can count for one timeframe but not another

### Wednesday Intraday Analysis
- Fixed targets correctly identify whether reversal hit 1%, 2%, 3%, 5% during Wednesday
- Time-based checkpoints capture the max reversal reached by each half-hour mark
- Only triggered (90% retraced) trades get intraday analysis

### Summary Statistics
- Hit rate, median retracement, median continuation computed correctly
- Average when hit only includes triggered trades
- Top 10% average uses the correct slice
- P&L calculation: $100 per trade, reversal and continuation returns
- Median trade returns computed correctly
- Target hit rates are percentages of triggered trades
- Time-based medians aggregate correctly across trades

### Signal Scanner
- Identifies symbols meeting the move threshold
- Correctly determines trade direction (long vs short)
- Computes entry price as signal + 0.2% continuation
- Confirms entry only when continuation occurs in Monday afternoon bars
- Computes target (2%) and stop (1.5%) from the entry price

### Net Gain Calculation
- Short trades: gain = (entry - exit) / entry
- Long trades: gain = (exit - entry) / entry
- Returns null when entry or exit is missing

## Integration Tests (network required, slow)

### Data Download
- Index is timezone-aware in Eastern time

### End-to-End Analysis
- Full analysis for a single symbol produces results with all expected fields
- CSV output is written with correct headers

## Signal Persistence

- Signals save to and load from JSON correctly
- Signals expire after Wednesday 4 PM
- Saved signals are not overwritten by rescans
- Editable fields (Actual Entry, Actual Exit) persist across loads
