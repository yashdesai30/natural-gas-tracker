from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

import pandas as pd

IST_TZ = "Asia/Kolkata"
MCX_EXCHANGE = "MCX"
COMMODITY_SEGMENT = "COMMODITY"
NATURAL_GAS_NAME = "NATURALGAS"


def as_ist_date(value: date | datetime | None = None) -> date:
    if value is None:
        return pd.Timestamp.now(tz=IST_TZ).date()
    if isinstance(value, datetime):
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(IST_TZ)
        else:
            timestamp = timestamp.tz_convert(IST_TZ)
        return timestamp.date()
    return value


def normalise_instruments(frame: pd.DataFrame) -> pd.DataFrame:
    text_columns = [
        "exchange",
        "segment",
        "instrument_type",
        "trading_symbol",
        "groww_symbol",
        "name",
        "underlying_symbol",
    ]
    expiry_column = "expiry_date" if "expiry_date" in frame.columns else "expiry"
    strike_column = "strike_price" if "strike_price" in frame.columns else "strike"

    base = frame.drop(
        columns=[*text_columns, "expiry", "expiry_date", "strike", "strike_price"],
        errors="ignore",
    )
    normalised_columns = pd.DataFrame(
        {
            "exchange": frame.get("exchange", "").astype(str).str.upper()
            if "exchange" in frame.columns
            else "",
            "segment": frame.get("segment", "").astype(str).str.upper()
            if "segment" in frame.columns
            else "",
            "instrument_type": frame.get("instrument_type", "").astype(str).str.upper()
            if "instrument_type" in frame.columns
            else "",
            "trading_symbol": frame.get("trading_symbol", ""),
            "groww_symbol": frame.get("groww_symbol", ""),
            "name": frame.get("name", ""),
            "underlying_symbol": frame.get("underlying_symbol", ""),
            "expiry": pd.to_datetime(frame.get(expiry_column), errors="coerce"),
            "strike": pd.to_numeric(frame.get(strike_column), errors="coerce"),
        },
        index=frame.index,
    )
    return pd.concat([base, normalised_columns], axis=1)


def get_last_thursday(year: int, month: int) -> date:
    """Find the last Thursday of a given month."""
    last_day = calendar.monthrange(year, month)[1]
    last_date = date(year, month, last_day)
    offset = (last_date.weekday() - 3) % 7
    return last_date - timedelta(days=offset)


def natural_gas_mask(frame: pd.DataFrame) -> pd.Series:
    text = (
        frame["underlying_symbol"].fillna("").astype(str)
        + " "
        + frame["name"].fillna("").astype(str)
        + " "
        + frame["trading_symbol"].fillna("").astype(str)
        + " "
        + frame["groww_symbol"].fillna("").astype(str)
    ).str.upper().str.replace(" ", "", regex=False)
    return text.str.contains(NATURAL_GAS_NAME, regex=False)


def resolve_target_contract_period(
    instruments: pd.DataFrame,
    as_of_date: date | datetime | None = None,
) -> pd.Period:
    frame = normalise_instruments(instruments)
    target_date = as_ist_date(as_of_date)

    options = frame[
        natural_gas_mask(frame)
        & (frame["exchange"] == MCX_EXCHANGE)
        & (frame["segment"] == COMMODITY_SEGMENT)
        & (frame["instrument_type"].isin(["CE", "PE"]))
        & (frame["expiry"].notna())
    ].copy()
    if options.empty:
        raise RuntimeError("No NATURALGAS option contracts found")

    monthly_expiries = (
        options.assign(contract_period=options["expiry"].dt.to_period("M"))
        .groupby("contract_period")["expiry"]
        .max()
        .sort_index()
    )
    if monthly_expiries.empty:
        raise RuntimeError("No monthly NATURALGAS option expiries found")

    current_period = pd.Period(target_date, freq="M")
    last_thursday = get_last_thursday(target_date.year, target_date.month)
    
    # Check if current month contracts still exist
    current_period_options = options[options["expiry"].dt.to_period("M") == current_period]
    has_current_options = not current_period_options.empty and current_period_options["expiry"].max().date() >= target_date
    
    if target_date < last_thursday and has_current_options:
        target_period = current_period
    else:
        target_period = current_period + 1

    if target_period not in monthly_expiries.index:
        later_periods = [period for period in monthly_expiries.index if period >= target_period]
        if later_periods:
            target_period = sorted(later_periods)[0]
        else:
            target_period = monthly_expiries.index[-1]

    return target_period


def select_natural_gas_contract_rows(
    instruments: pd.DataFrame,
    as_of_date: date | datetime | None = None,
    instrument_types: set[str] | None = None,
) -> pd.DataFrame:
    frame = normalise_instruments(instruments)
    target_period = resolve_target_contract_period(frame, as_of_date=as_of_date)

    mask = (
        natural_gas_mask(frame)
        & (frame["exchange"] == MCX_EXCHANGE)
        & (frame["segment"] == COMMODITY_SEGMENT)
        & (frame["expiry"].notna())
        & (frame["expiry"].dt.to_period("M") == target_period)
    )
    if instrument_types is not None:
        mask &= frame["instrument_type"].isin(sorted(instrument_types))
    return frame.loc[mask].copy()
