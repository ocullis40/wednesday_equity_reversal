# Streamlit Dashboard Design

## Purpose

Visualize Wednesday equity reversal analysis results. Show per-symbol hit rates for both 10 AM and 12 PM timeframes side by side, with ability to rerun analysis.

## Technology

Streamlit — single `app.py` file, no separate frontend. Runs with `streamlit run app.py`.

## Layout

1. **Title**: "Wednesday Equity Reversal Dashboard"
2. **Rerun Analysis button**: Triggers full `analyze_symbol()` run for all symbols, refreshes data
3. **Summary metrics row** (st.columns): Total periods, 10 AM hit rate, 12 PM hit rate, average retracement
4. **Grouped bar chart**: Symbols on x-axis, two bars per symbol (10 AM vs 12 PM hit rate %). Uses st.bar_chart or Altair for grouped bars.
5. **Data table**: Per-symbol breakdown with columns: Symbol, Periods, 10 AM Hits, 10 AM %, 12 PM Hits, 12 PM %

## Data Flow

- On load: reads existing CSV files from `output/` directory
- On rerun: calls `analyze_symbol()` for each symbol, then `compute_summary()`, refreshes all views
- No database — CSV files are the data store

## Dependencies

- `streamlit`
- Existing `analyze.py` functions (imported directly)
