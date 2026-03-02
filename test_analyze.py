import pandas as pd
from analyze import extract_prices, download_intraday_data, find_valid_periods, compute_retracement

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

def test_extract_prices_returns_dict():
    df = download_intraday_data("SPY")
    periods = find_valid_periods(df)
    assert len(periods) > 0
    fri, mon, tue, wed = periods[0]
    prices = extract_prices(df, fri, tue, wed)
    assert "friday_close" in prices
    assert "tuesday_10am" in prices
    assert "wednesday_high" in prices
    assert "wednesday_low" in prices
    assert all(isinstance(v, float) for v in prices.values())

def test_retracement_up_move_full_retrace():
    # Price went up 10, Wednesday low came all the way back
    result = compute_retracement(100.0, 110.0, 115.0, 100.0)
    assert result["move_direction"] == "up"
    assert result["retracement_pct"] == 100.0
    assert result["retraced_90pct"] is True

def test_retracement_down_move_partial():
    # Price went down 10, Wednesday high only recovered 5
    result = compute_retracement(100.0, 90.0, 95.0, 88.0)
    assert result["move_direction"] == "down"
    assert result["retracement_pct"] == 50.0
    assert result["retraced_90pct"] is False

def test_retracement_flat_move():
    result = compute_retracement(100.0, 100.02, 100.5, 99.5)
    assert result["move_direction"] == "flat"
