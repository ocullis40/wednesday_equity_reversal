import pandas as pd
from analyze import download_intraday_data

def test_download_returns_dataframe():
    df = download_intraday_data("SPY")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "Close" in df.columns or ("Close", "SPY") in df.columns
