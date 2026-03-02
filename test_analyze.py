import pandas as pd
from analyze import download_intraday_data, find_valid_periods

def test_download_returns_dataframe():
    df = download_intraday_data("SPY")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "Close" in df.columns or ("Close", "SPY") in df.columns

def test_find_valid_periods_returns_list_of_tuples():
    df = download_intraday_data("SPY")
    periods = find_valid_periods(df)
    assert isinstance(periods, list)
    assert len(periods) > 0
    # Each period is (friday_date, monday_date, tuesday_date, wednesday_date)
    for fri, mon, tue, wed in periods:
        assert fri.weekday() == 4  # Friday
        assert mon.weekday() == 0  # Monday
        assert tue.weekday() == 1  # Tuesday
        assert wed.weekday() == 2  # Wednesday
