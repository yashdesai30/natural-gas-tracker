from __future__ import annotations

import argparse
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from tracker_service.config import get_settings
from tracker_service.data_fetcher import COMMODITY_SEGMENT, MCX_EXCHANGE, GrowwDataFetcher


LOCAL_TIMEZONE = ZoneInfo("Asia/Kolkata")


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Groww historical candles for MCX symbols.")
    parser.add_argument("--symbol", help="Trading symbol to test, e.g. NATURALGAS27APR26FUT")
    parser.add_argument("--date", help="IST date to test in YYYY-MM-DD format")
    parser.add_argument("--start", default="09:00:00", help="IST start time, default 09:00:00")
    parser.add_argument("--end", default="09:05:00", help="IST end time, default 09:05:00")
    parser.add_argument("--interval", type=int, default=1, help="Candle interval in minutes")
    args = parser.parse_args()

    settings = get_settings()
    fetcher = GrowwDataFetcher(
        access_token=settings.groww_access_token,
        cache_ttl_hours=settings.instrument_cache_ttl_hours,
    )
    instruments = fetcher.get_mcx_instruments()
    future = fetcher.get_natural_gas_future(instruments)
    trading_symbol = args.symbol or str(future["trading_symbol"])

    target_date = (
        datetime.strptime(args.date, "%Y-%m-%d").date()
        if args.date
        else datetime.now(LOCAL_TIMEZONE).date() - timedelta(days=1)
    )
    start_time = datetime.combine(
        target_date,
        datetime.strptime(args.start, "%H:%M:%S").time(),
        tzinfo=LOCAL_TIMEZONE,
    )
    end_time = datetime.combine(
        target_date,
        datetime.strptime(args.end, "%H:%M:%S").time(),
        tzinfo=LOCAL_TIMEZONE,
    )

    print(f"trading_symbol={trading_symbol}")
    print(f"exchange={MCX_EXCHANGE} segment={COMMODITY_SEGMENT}")
    print(f"start_time={start_time:%Y-%m-%d %H:%M:%S} end_time={end_time:%Y-%m-%d %H:%M:%S}")

    raw = fetcher.groww.get_historical_candle_data(
        trading_symbol=trading_symbol,
        exchange=MCX_EXCHANGE,
        segment=COMMODITY_SEGMENT,
        start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
        end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
        interval_in_minutes=args.interval,
    )
    print(f"raw_type={type(raw).__name__}")
    print(f"raw_preview={str(raw)[:1000]}")

    frame = fetcher._normalise_candles(raw)
    print(f"normalised_rows={len(frame)}")
    if not frame.empty:
        display = frame.copy()
        display.loc[:, "timestamp_ist"] = display.loc[:, "timestamp"].dt.tz_convert(LOCAL_TIMEZONE)
        print(display.head(20).to_string(index=False))

    if not args.symbol:
        natural_gas_futures = instruments[
            (instruments["exchange"] == MCX_EXCHANGE)
            & (instruments["segment"] == COMMODITY_SEGMENT)
            & (instruments["instrument_type"] == "FUT")
            & (instruments["underlying_symbol"].astype(str).str.upper() == "NATURALGAS")
        ].sort_values("expiry")
        print("\nNATURALGAS futures from instrument dump:")
        print(
            natural_gas_futures[
                ["trading_symbol", "groww_symbol", "expiry", "exchange_token"]
            ].head(10).to_string(index=False)
        )


if __name__ == "__main__":
    main()
