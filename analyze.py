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
