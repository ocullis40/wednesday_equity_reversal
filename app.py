import streamlit as st
import pandas as pd
import altair as alt
import json
import os
from datetime import date, datetime, timedelta
from analyze import SYMBOLS, INDEX_SYMBOLS, analyze_symbol, compute_summary, download_intraday_data, min_move_pct

SIGNALS_FILE = os.path.join(os.path.dirname(__file__), "current_signals.json")

st.set_page_config(page_title="Wednesday Reversal", layout="wide")
st.title("Wednesday Equity Reversal Dashboard")


# --- Current Signals ---
st.subheader("Current Signals (Mon 2 PM)")


def load_saved_signals():
    """Load persisted signals from disk."""
    if not os.path.exists(SIGNALS_FILE):
        return None
    with open(SIGNALS_FILE, "r") as f:
        data = json.load(f)
    # Expire after Wednesday 4 PM
    expires = date.fromisoformat(data["wednesday"])
    now = datetime.now()
    if now.date() > expires or (now.date() == expires and now.hour >= 16):
        os.remove(SIGNALS_FILE)
        return None
    return data


def save_signals(signals, friday, monday, wednesday):
    """Persist confirmed signals to disk."""
    data = {
        "friday": str(friday),
        "monday": str(monday),
        "wednesday": str(wednesday),
        "signals": signals,
    }
    with open(SIGNALS_FILE, "w") as f:
        json.dump(data, f, indent=2)


@st.cache_data(ttl=300)
def scan_current_signals():
    today = date.today()
    # Find most recent Friday
    days_since_friday = (today.weekday() - 4) % 7
    friday = today - timedelta(days=days_since_friday)
    monday = friday + timedelta(days=3)
    wednesday = friday + timedelta(days=5)

    signals = []
    for symbol in SYMBOLS:
        try:
            df = download_intraday_data(symbol)
            fri_data = df[df.index.date == friday]
            if fri_data.empty:
                continue
            fri_close = float(fri_data["Close"].iloc[-1])

            mon_data = df[df.index.date == monday]
            if mon_data.empty:
                continue
            mon_2pm = mon_data.between_time("13:30", "14:00")
            if mon_2pm.empty:
                continue
            signal_price = float(mon_2pm["Close"].iloc[-1])

            move_pct = (signal_price - fri_close) / fri_close * 100
            threshold = min_move_pct(symbol) * 100
            if abs(move_pct) < threshold:
                continue

            direction = "UP" if move_pct > 0 else "DOWN"
            trade = "Short" if direction == "UP" else "Long"

            # Entry price after 0.2% continuation
            if direction == "UP":
                entry_price = signal_price * 1.002
            else:
                entry_price = signal_price * 0.998

            # Check if 0.2% continuation happened in Mon afternoon bars
            mon_after = mon_data.between_time("14:00", "16:00")
            confirmed = False
            if direction == "UP":
                for _, bar in mon_after.iterrows():
                    if float(bar["High"]) >= entry_price:
                        confirmed = True
                        break
            else:
                for _, bar in mon_after.iterrows():
                    if float(bar["Low"]) <= entry_price:
                        confirmed = True
                        break

            if not confirmed:
                continue

            # Target and stop from the entry price
            if direction == "UP":
                target_price = entry_price * 0.98
                stop_price = entry_price * 1.015
            else:
                target_price = entry_price * 1.02
                stop_price = entry_price * 0.985

            signals.append({
                "Symbol": symbol,
                "Trade": f"🔴 {trade}" if trade == "Short" else f"🟢 {trade}",
                "Fri Close": round(fri_close, 2),
                "Signal (2 PM)": round(signal_price, 2),
                "Move %": round(move_pct, 2),
                "Entry (+0.2%)": round(entry_price, 2),
                "Target (2%)": round(target_price, 2),
                "Stop (1.5%)": round(stop_price, 2),
            })
        except Exception:
            continue
    return signals, friday, monday, wednesday


# Load saved signals or scan for new ones
saved = load_saved_signals()
if saved:
    signals = saved["signals"]
    sig_friday = saved["friday"]
    sig_monday = saved["monday"]
else:
    signals, sig_friday, sig_monday, sig_wednesday = scan_current_signals()
    if signals:
        save_signals(signals, sig_friday, sig_monday, sig_wednesday)

if signals:
    st.caption(f"Friday {sig_friday} → Monday {sig_monday} | Expires Wednesday close")

    # Ensure editable fields exist on each signal
    for s in signals:
        s.setdefault("Actual Entry", None)
        s.setdefault("Actual Exit", None)

    sig_df = pd.DataFrame(signals)

    # Compute Net Gain %
    def calc_net_gain(row):
        entry = row.get("Actual Entry")
        exit_ = row.get("Actual Exit")
        if entry and exit_ and entry > 0:
            if "Short" in str(row["Trade"]):
                return round((entry - exit_) / entry * 100, 2)
            else:
                return round((exit_ - entry) / entry * 100, 2)
        return None

    for s in signals:
        s["Net Gain %"] = calc_net_gain(s)

    column_config = {
        "Symbol": st.column_config.TextColumn(width="small", disabled=True),
        "Trade": st.column_config.TextColumn(width="small", disabled=True),
        "Fri Close": st.column_config.NumberColumn(format="%.2f", disabled=True),
        "Signal (2 PM)": st.column_config.NumberColumn(format="%.2f", disabled=True),
        "Move %": st.column_config.NumberColumn(format="%.2f", disabled=True),
        "Entry (+0.2%)": st.column_config.NumberColumn(format="%.2f", disabled=True),
        "Target (2%)": st.column_config.NumberColumn(format="%.2f", disabled=True),
        "Stop (1.5%)": st.column_config.NumberColumn(format="%.2f", disabled=True),
        "Actual Entry": st.column_config.NumberColumn(format="%.2f"),
        "Actual Exit": st.column_config.NumberColumn(format="%.2f"),
        "Net Gain %": st.column_config.NumberColumn(format="%.2f", disabled=True),
    }

    edited_df = st.data_editor(
        sig_df,
        column_config=column_config,
        use_container_width=False,
        hide_index=True,
        height=(len(signals) + 1) * 35 + 3,
        key="signals_editor",
    )

    # Persist edits back to JSON
    if edited_df is not None:
        updated_signals = edited_df.to_dict(orient="records")
        # Recalculate Net Gain from edited values
        for s in updated_signals:
            s["Net Gain %"] = calc_net_gain(s)
        current_saved = load_saved_signals()
        if current_saved:
            current_saved["signals"] = updated_signals
            with open(SIGNALS_FILE, "w") as f:
                json.dump(current_saved, f, indent=2)
else:
    st.info("No confirmed signals. Signals appear after Monday 2 PM.")

st.divider()

# --- Historical Analysis ---
st.subheader("Historical Analysis")

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
