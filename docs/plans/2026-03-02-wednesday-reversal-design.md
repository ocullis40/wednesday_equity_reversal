# Wednesday Equity Reversal — Phase 1 Design

## Theory Under Test

Stocks tend to revert to their Friday closing price by Wednesday after making a move during the first 30 minutes of trading on Monday/Tuesday. Specifically:

1. Record **Friday's closing price** for each symbol.
2. Record the **price at 10:00 AM Eastern the following Tuesday**.
3. Check whether **Wednesday's price action** retraces at least 90% of the Friday-to-Tuesday move back toward Friday's close.

## Data Source

**Yahoo Finance via the `yfinance` Python library** (free, no API key required).

- **Intraday data**: 30-minute interval candles, available for the most recent ~60 trading days.
- **Lookback period**: ~60 trading days (approximately 12 weeks of weekly cycles to test).
- The 10:00 AM Eastern price will be captured from the close of the 9:30–10:00 AM candle.

## Symbols

20 stock/index symbols, configurable in a simple list at the top of the script:

```
IREN QQQ SPY TSLA NVDA AAPL GOOG HOOD MSFT OKLO
ILMN FSLR AMZN SMCI META AMD JPM GS SLV BP
```

## Period Selection & Exclusion Rules

A valid test period (Friday through Wednesday) requires **all four days** — Friday, the following Monday, Tuesday, and Wednesday — to be regular trading days. Any period where the market is closed on any of these four days is excluded from analysis.

We will use the NYSE trading calendar to identify holidays and half-days.

## Data Points Collected Per Valid Fri–Wed Period Per Symbol

| Field | Source |
|---|---|
| `friday_close` | Friday daily close OR last intraday candle close |
| `tuesday_10am` | Close of the 9:30–10:00 AM 30-min candle on Tuesday |
| `move` | `tuesday_10am - friday_close` |
| `move_direction` | `"up"` if move > 0, `"down"` if move < 0, `"flat"` if ~0 |
| `wednesday_high` | Wednesday intraday high (used when move was DOWN) |
| `wednesday_low` | Wednesday intraday low (used when move was UP) |
| `retracement_price` | `wednesday_low` if move was up, `wednesday_high` if move was down |
| `retracement_pct` | How much of the move was retraced (see formula below) |
| `retraced_90pct` | Boolean: did the retracement reach >= 90%? |

### Retracement Formula

```
If move is UP (tuesday_10am > friday_close):
    retracement_pct = (tuesday_10am - wednesday_low) / move * 100

If move is DOWN (tuesday_10am < friday_close):
    retracement_pct = (wednesday_high - tuesday_10am) / abs(move) * 100
```

A retracement of 100% means Wednesday's price fully returned to Friday's close. We flag any Fri–Wed period where `retracement_pct >= 90`.

Periods where the move is essentially flat (< $0.05 or < 0.05%) will be excluded as "no signal."

## Output — Phase 1

### Per-Symbol Summary Table

For each symbol, a table showing every valid week with all data points above.

### Aggregate Statistics

- **Hit rate**: % of valid Fri–Wed periods where retracement >= 90%, across all symbols.
- **Per-symbol hit rate**: Same metric broken down by symbol.
- **Average retracement %**: Mean retracement across all valid Fri–Wed periods.
- **Distribution**: Breakdown of retracement into buckets (0–25%, 25–50%, 50–75%, 75–90%, 90–100%, >100%).

### Format

Results will be output as:
1. A CSV file per symbol (raw data for further analysis).
2. A summary CSV with aggregate stats.
3. Console output with the key statistics.

## Technical Approach

- **Language**: Python 3
- **Dependencies**: `yfinance`, `pandas`, `numpy`
- **Structure**: Single script (`analyze.py`) that:
  1. Takes a list of symbols as input.
  2. Downloads 60 days of 30-minute intraday data for each symbol.
  3. Identifies valid Friday/Tuesday/Wednesday triplets.
  4. Computes the metrics above.
  5. Writes CSV output and prints summary stats.

## Limitations & Assumptions

- 60-day lookback gives roughly 10–12 valid Fri–Wed periods to test per symbol. With 20 symbols, that's 200–240 data points — enough to see a pattern but not statistically rigorous.
- Intraday data from yfinance can occasionally have gaps or missing candles; the script will flag and skip any period with missing data rather than interpolate.
- We are using the *close* of the 9:30–10:00 AM candle as the 10:00 AM price. This is the best proxy available at 30-minute granularity.

## Future Phases (out of scope for now)

- **Extend lookback**: Use daily OHLC data to approximate the analysis over a full 2-year period.
- **iOS alerting app**: Real-time monitoring for reversal setups.
- **Deeper analysis**: Win/loss by day of month, by sector, by volatility regime, etc.
