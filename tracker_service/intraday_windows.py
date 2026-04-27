from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd


LOCAL_TIMEZONE = ZoneInfo("Asia/Kolkata")
WINDOW_RANGES: tuple[tuple[time, time], ...] = (
    (time(9, 0), time(9, 16)),
    (time(15, 0), time(15, 16)),
    (time(17, 0), time(17, 31)),
    (time(20, 0), time(20, 31)),
)


def build_intraday_windows(
    start_date: date,
    end_date: date,
    now: datetime | None = None,
) -> list[tuple[datetime, datetime]]:
    local_now = now or datetime.now(LOCAL_TIMEZONE)
    windows: list[tuple[datetime, datetime]] = []

    current_day = start_date
    while current_day <= end_date:
        for start_time, end_time in WINDOW_RANGES:
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
    for window_start, window_end in WINDOW_RANGES:
        sampled_mask |= (
            (local_times >= window_start)
            & (local_times <= window_end)
            & (local_timestamps.dt.minute % 5 == 0)
        )

    filtered = data.loc[mask & sampled_mask].copy()
    if filtered.empty:
        return filtered

    filtered.loc[:, "local_date"] = local_dates.loc[filtered.index]
    filtered.loc[:, "local_time"] = local_timestamps.loc[filtered.index].dt.strftime("%Y-%m-%d %H:%M:%S")
    return filtered
