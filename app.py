import streamlit as st
import pandas as pd
import altair as alt
from analyze import SYMBOLS, analyze_symbol, compute_summary

st.set_page_config(page_title="Wednesday Reversal", layout="wide")
st.title("Wednesday Equity Reversal Dashboard")


@st.cache_data
def run_analysis():
    all_results = []
    progress = st.progress(0, text="Analyzing symbols...")
    for i, symbol in enumerate(SYMBOLS):
        results = analyze_symbol(symbol)
        all_results.extend(results)
        progress.progress((i + 1) / len(SYMBOLS), text=f"Analyzing {symbol}...")
    progress.empty()
    summary = compute_summary(all_results)
    return all_results, summary


if st.button("Rerun Analysis"):
    run_analysis.clear()

all_results, summary = run_analysis()

# Summary metrics
sm = summary["mon2pm"]
s10 = summary["10am"]
s12 = summary["12pm"]
summary_df = pd.DataFrame([
    {
        "Timeframe": "Mon 2 PM",
        "Periods": sm["total_periods"],
        "Hit Rate %": sm["hit_rate"],
        "Median Retrace %": sm["median_retracement"],
        "Median Continuation %": sm["median_continuation"],
        "Avg When Hit %": sm["avg_retracement_on_hit"],
        "Avg Top 10% %": sm["avg_top_10_pct"],
    },
    {
        "Timeframe": "Tue 10 AM",
        "Periods": s10["total_periods"],
        "Hit Rate %": s10["hit_rate"],
        "Median Retrace %": s10["median_retracement"],
        "Median Continuation %": s10["median_continuation"],
        "Avg When Hit %": s10["avg_retracement_on_hit"],
        "Avg Top 10% %": s10["avg_top_10_pct"],
    },
    {
        "Timeframe": "Tue 12 PM",
        "Periods": s12["total_periods"],
        "Hit Rate %": s12["hit_rate"],
        "Median Retrace %": s12["median_retracement"],
        "Median Continuation %": s12["median_continuation"],
        "Avg When Hit %": s12["avg_retracement_on_hit"],
        "Avg Top 10% %": s12["avg_top_10_pct"],
    },
])
st.dataframe(summary_df, use_container_width=True, hide_index=True)

# Overall P&L: $100 per trade on every triggered symbol
st.subheader("$100/Trade P&L (on triggered periods)")
pnl_rows = []
for label, s in [("Mon 2 PM", sm), ("Tue 10 AM", s10), ("Tue 12 PM", s12)]:
    pnl_rows.append({
        "Timeframe": label,
        "Trades": s["num_trades"],
        "Invested": f"${s['total_invested']:,.0f}",
        "Reversal Return": f"${s['reversal_return']:,.2f}",
        "Continuation Return": f"${s['continuation_return']:,.2f}",
        "Reversal ROI %": round(s["reversal_return"] / s["total_invested"] * 100, 2) if s["total_invested"] > 0 else 0,
        "Continuation ROI %": round(s["continuation_return"] / s["total_invested"] * 100, 2) if s["total_invested"] > 0 else 0,
        "Median Reversal %": s["median_reversal_trade"],
        "Median Continuation %": s["median_continuation_trade"],
    })
st.dataframe(pd.DataFrame(pnl_rows), use_container_width=True, hide_index=True)

# Fixed target hit rates
st.subheader("Fixed Target Hit Rates (% of triggered trades)")
target_rows = []
for label, s in [("Mon 2 PM", sm), ("Tue 10 AM", s10), ("Tue 12 PM", s12)]:
    row = {"Timeframe": label}
    for target, rate in s["target_hit_rates"].items():
        row[target] = f"{rate}%"
    target_rows.append(row)
st.dataframe(pd.DataFrame(target_rows), use_container_width=True, hide_index=True)

# Time-based reversal chart
st.subheader("Median Reversal % Through Wednesday (triggered trades)")
time_rows = []
for label, s in [("Mon 2 PM", sm), ("Tue 10 AM", s10), ("Tue 12 PM", s12)]:
    for time, pct in s["time_based"].items():
        time_rows.append({"Timeframe": label, "Wednesday Time": time, "Median Reversal %": pct})
time_df = pd.DataFrame(time_rows)
time_chart = alt.Chart(time_df).mark_line(point=True).encode(
    x=alt.X("Wednesday Time:N", sort=None),
    y="Median Reversal %:Q",
    color="Timeframe:N",
).properties(height=350)
st.altair_chart(time_chart, use_container_width=True)

# Build per-symbol dataframe
rows = []
all_syms = sorted(set(sm["per_symbol"].keys()) | set(s10["per_symbol"].keys()) | set(s12["per_symbol"].keys()))
for sym in all_syms:
    psm = sm["per_symbol"].get(sym, {"total": 0, "hits": 0, "hit_rate": 0})
    ps10 = s10["per_symbol"].get(sym, {"total": 0, "hits": 0, "hit_rate": 0})
    ps12 = s12["per_symbol"].get(sym, {"total": 0, "hits": 0, "hit_rate": 0})
    rows.append({
        "Symbol": sym,
        "Periods": ps10["total"],
        "Mon 2 PM Hits": psm["hits"],
        "Mon 2 PM %": psm["hit_rate"],
        "Tue 10 AM Hits": ps10["hits"],
        "Tue 10 AM %": ps10["hit_rate"],
        "Tue 12 PM Hits": ps12["hits"],
        "Tue 12 PM %": ps12["hit_rate"],
    })
df = pd.DataFrame(rows)

# Grouped bar chart
chart_data = df.melt(id_vars=["Symbol"], value_vars=["Mon 2 PM %", "Tue 10 AM %", "Tue 12 PM %"],
                     var_name="Timeframe", value_name="Hit Rate %")
chart = alt.Chart(chart_data).mark_bar().encode(
    x=alt.X("Symbol:N", sort=all_syms),
    y=alt.Y("Hit Rate %:Q", scale=alt.Scale(domain=[0, 100])),
    color="Timeframe:N",
    xOffset="Timeframe:N",
).properties(height=400)
st.altair_chart(chart, use_container_width=True)

# Data table
st.dataframe(df, use_container_width=True, hide_index=True)
