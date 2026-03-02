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
