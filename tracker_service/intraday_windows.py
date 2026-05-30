from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd


LOCAL_TIMEZONE = ZoneInfo("Asia/Kolkata")
WINDOW_RANGES: tuple[tuple[time, time], ...] = (
    (time(9, 0), time(23, 59)),
)

_bse_calendar = None


def get_bse_calendar():
    global _bse_calendar
    if _bse_calendar is None:
        import exchange_calendars as xcals
        _bse_calendar = xcals.get_calendar("XBOM")
    return _bse_calendar


def get_mcx_trading_windows(d: date) -> list[tuple[time, time]]:
    """Determine the MCX trading session windows for a given date."""
    if d.weekday() >= 5:
        # Weekend - Closed all day
        return []

    # Check if this day is a BSE regular session
    bse = get_bse_calendar()
    if bse.is_session(d):
        # Regular trading day - both sessions open
        return [(time(9, 0), time(23, 59))]

    # Weekday but BSE is closed -> MCX Holiday
    # Check if it is a full-day holiday for MCX
    from dateutil.easter import easter
    year = d.year
    good_friday = easter(year) - timedelta(days=2)
    
    full_holidays = {
        date(year, 1, 26),   # Republic Day
        date(year, 8, 15),   # Independence Day
        date(year, 10, 2),   # Mahatma Gandhi Jayanti
        date(year, 12, 25),  # Christmas
        good_friday,
    }
    
    if d in full_holidays:
        # Full-day MCX holiday - closed all day
        return []

    # Otherwise, it's a partial MCX holiday (Morning closed, Evening open)
    return [(time(17, 0), time(23, 59))]


def build_intraday_windows(
    start_date: date,
    end_date: date,
    now: datetime | None = None,
) -> list[tuple[datetime, datetime]]:
    local_now = now or datetime.now(LOCAL_TIMEZONE)
    windows: list[tuple[datetime, datetime]] = []

    current_day = start_date
    while current_day <= end_date:
        day_windows = get_mcx_trading_windows(current_day)
        for start_time, end_time in day_windows:
            window_start = datetime.combine(current_day, start_time, tzinfo=LOCAL_TIMEZONE)
            window_end = datetime.combine(current_day, end_time, tzinfo=LOCAL_TIMEZONE)
            if window_start > local_now:
                continue
            windows.append((window_start, min(window_end, local_now)))
        current_day += timedelta(days=1)

    return windows


def filter_sampled_rows(
    data: pd.DataFrame,
    start_date: date | None = None,
    end_date: date | None = None,
    now: datetime | None = None,
) -> pd.DataFrame:
    if data.empty or "timestamp" not in data.columns:
        return pd.DataFrame(columns=data.columns)

    local_now = now or datetime.now(LOCAL_TIMEZONE)
    local_timestamps = pd.to_datetime(data.loc[:, "timestamp"], utc=True, errors="coerce").dt.tz_convert(
        LOCAL_TIMEZONE
    )
    local_dates = local_timestamps.dt.date
    local_times = local_timestamps.dt.time

    lower_date = start_date or local_now.date()
    upper_date = end_date or local_now.date()

    mask = local_dates.between(lower_date, upper_date)
    sampled_mask = pd.Series(False, index=data.index)
    
    unique_dates = local_dates.dropna().unique()
    for d in unique_dates:
        day_mask = (local_dates == d)
        day_windows = get_mcx_trading_windows(d)
        for window_start, window_end in day_windows:
            sampled_mask |= (
                day_mask
                & (local_times >= window_start)
                & (local_times <= window_end)
                & (local_timestamps.dt.minute % 5 == 0)
            )

    filtered = data.loc[mask & sampled_mask].copy()
    if filtered.empty:
        return filtered

    filtered.loc[:, "local_date"] = local_dates.loc[filtered.index]
    filtered.loc[:, "local_time"] = local_timestamps.loc[filtered.index].dt.strftime("%Y-%m-%d %H:%M:%S")
    return filtered

