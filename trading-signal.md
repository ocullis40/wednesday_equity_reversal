# Wednesday Equity Reversal — Trading Signal

## Thesis

Stocks that make a significant move from Friday's close through early in the following week tend to reverse direction on Wednesday. This system identifies those moves, confirms momentum, and generates reversal trade signals.

## Symbols Tracked

20 symbols across equities and indices: IREN, QQQ, SPY, TSLA, NVDA, AAPL, GOOG, HOOD, MSFT, OKLO, ILMN, FSLR, AMZN, SMCI, META, AMD, JPM, GS, SLV, BP.

QQQ and SPY are classified as index symbols and use a lower move threshold.

## Signal Generation

### Timeframes

The system evaluates three entry timeframes, all measured from Friday's closing price:

- **Monday 2:00 PM** — the primary and strongest signal
- **Tuesday 10:00 AM**
- **Tuesday 12:00 PM**

### Trigger Criteria

1. **Minimum move threshold:** The stock must move at least 0.5% (indices) or 0.75% (individual stocks) from Friday's close to the signal timeframe price.

2. **90% retracement check:** The Friday-to-signal move must be at least 90% retraced by Wednesday's intraday extreme. This is evaluated historically to determine hit rates and is used to qualify periods for analysis.

3. **Earnings exclusion:** Any non-index symbol that reported earnings during the Friday-through-Wednesday window is excluded from analysis.

### Entry Confirmation

After the Monday 2 PM signal fires, the system waits for a 0.2% continuation in the same direction during the remaining Monday session (2:00–4:00 PM). This filters for signals where momentum is still building, resulting in higher quality entries with a ~90% win rate on a 2% target (vs 78% without the wait).

## Trade Execution

### Direction

- If the stock moved **up** from Friday to the signal price → **Short** (bet on reversal down)
- If the stock moved **down** from Friday to the signal price → **Long** (bet on reversal up)

### Entry, Target, and Stop

- **Entry price:** Signal price + 0.2% continuation (the confirmed entry level)
- **Profit target:** 2% reversal from the entry price
- **Stop loss:** 1.5% adverse move from the entry price

### Timing

The reversal primarily occurs on Wednesday. Historical analysis shows the bulk of the move happens at the Wednesday open — the median reversal reaches ~2.6% by 9:30 AM and ~3.1% by 10:00 AM, with diminishing gains through the rest of the day.

## Historical Performance (60-day backtest)

### Monday 2 PM Signal (primary)

- **Hit rate:** ~40% of periods meet the 90% retracement threshold
- **Fixed target hit rates (on triggered trades):**
  - 1% target: ~98% hit rate
  - 2% target: ~78% hit rate
  - 3% target: ~63% hit rate
  - 5% target: ~29% hit rate
- **Median reversal on triggered trades:** ~3.5%
- **Median continuation (same direction):** ~1.3%
- **Reversal outperforms continuation by roughly 2–3x**

### With 0.2% Wait Entry + 1.5% Stop + 2% Target

- 29 trades filled out of 51 triggers
- 90% win rate (26W / 2L / 1 expired)
- Net return: $49 on $2,900 invested ($100/trade)

### Without Wait (immediate entry) + 1.5% Stop + 2% Target

- 51 trades
- 73% win rate (37W / 5L / 9 expired)
- Net return: $66.50 on $5,100 invested

The wait strategy has a higher win rate and better per-trade quality. The immediate entry strategy generates more total profit through higher trade volume.

## Dashboard

The Streamlit dashboard provides:

- **Current Signals table** — confirmed trades for the active week with entry, target, and stop prices. Includes editable fields for recording actual entry/exit prices with auto-calculated net gain. Signals persist from Monday through Wednesday market close.
- **Historical summary** — hit rates, median retracement/continuation, and P&L across all three timeframes
- **Fixed target hit rates** — what percentage of triggered trades reach 1%, 2%, 3%, and 5% reversal targets
- **Wednesday intraday chart** — how the median reversal builds through the Wednesday session
- **Per-symbol breakdown** — hit rates for each individual symbol across timeframes

## Limitations

- Based on 60 days of 30-minute intraday data from yfinance — limited historical depth
- The reversal is measured to the Wednesday intraday extreme, which is not fully capturable in real trading
- Bar-by-bar stop/target ordering uses 30-minute granularity — intrabar dynamics may differ
- No transaction costs or slippage modeled
