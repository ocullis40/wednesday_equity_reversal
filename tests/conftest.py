import datetime as dt

import pandas as pd
import pytest


@pytest.fixture
def make_bars():
    """Build a synthetic 30-minute bar DataFrame with timezone-aware Eastern index.

    Accepts a dict mapping ``(date, time_str)`` tuples to price values.
    ``date`` is a :class:`datetime.date` and ``time_str`` a string like ``"09:30"``.

    Each entry produces one row where Open = High = Low = Close = price and
    Volume = 1000.  The index is a :class:`pd.DatetimeIndex` localized to
    ``America/New_York``.
    """

    def _make(prices: dict[tuple[dt.date, str], float]) -> pd.DataFrame:
        rows = []
        for (day, time_str), price in prices.items():
            ts = pd.Timestamp(
                dt.datetime.combine(day, dt.time.fromisoformat(time_str)),
                tz="America/New_York",
            )
            rows.append(
                {
                    "timestamp": ts,
                    "Open": price,
                    "High": price,
                    "Low": price,
                    "Close": price,
                    "Volume": 1000,
                }
            )
        df = pd.DataFrame(rows).set_index("timestamp").sort_index()
        return df

    return _make
