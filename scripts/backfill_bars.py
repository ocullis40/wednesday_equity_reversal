#!/usr/bin/env python3
"""Download 2 years of 30-min bars from Alpaca and save as CSVs."""

import os
import sys
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

# Import SYMBOLS from analyze.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analyze import SYMBOLS

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "bars")


def main():
    load_dotenv()

    api_key = os.environ.get("ALPACA_API_KEY")
    secret_key = os.environ.get("ALPACA_API_SECRET")
    if not api_key or not secret_key:
        print("Error: ALPACA_API_KEY and ALPACA_API_SECRET must be set in .env")
        sys.exit(1)

    client = StockHistoricalDataClient(api_key, secret_key)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # ~2 years

    for symbol in SYMBOLS:
        request = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame(30, TimeFrameUnit.Minute),
            start=start_date,
            end=end_date,
        )
        bars = client.get_stock_bars(request)
        df = bars.df

        if df.empty:
            print(f"Skipped {symbol}: no data returned")
            continue

        # Reset multi-index (symbol, timestamp) to just timestamp
        if isinstance(df.index, __import__("pandas").MultiIndex):
            df = df.droplevel("symbol")

        # Convert timezone to Eastern
        df.index = df.index.tz_convert("America/New_York")
        df.index.name = "timestamp"

        # Rename columns to match expected format (Open, High, Low, Close, Volume)
        df = df.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        })
        df = df[["Open", "High", "Low", "Close", "Volume"]]

        csv_path = os.path.join(OUTPUT_DIR, f"{symbol}.csv")
        df.to_csv(csv_path)
        print(f"Downloaded {symbol}: {len(df):,} bars")

        time.sleep(0.5)  # Rate limit courtesy

    print(f"\nDone. Files saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
