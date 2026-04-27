from __future__ import annotations

import argparse
import logging
import time as time_module
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta, timezone

from tracker_service.atm_calculator import calculate_atm_strike
from tracker_service.config import get_settings
from tracker_service.data_fetcher import COMMODITY_SEGMENT, MCX_EXCHANGE, GrowwDataFetcher
from tracker_service.db import AtmRecord, SupabaseRepository
from tracker_service.intraday_windows import (
    LOCAL_TIMEZONE,
    build_intraday_windows,
    filter_sampled_rows,
)
from tracker_service.market_rules import as_ist_date
from tracker_service.option_selector import OptionPair, OptionSelector
import pandas as pd


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DailySelection:
    trading_date: date
    trading_symbol: str
    atm_strike: int
    option_pair: OptionPair


def resolve_daily_selection(
    fetcher: GrowwDataFetcher,
    repository: SupabaseRepository,
    instruments,
    trading_date: date,
) -> DailySelection:
    future = fetcher.get_natural_gas_future(instruments, as_of_date=trading_date)
    trading_symbol = str(future["trading_symbol"])
    day_start = datetime.combine(trading_date, dt_time.min, tzinfo=LOCAL_TIMEZONE).astimezone(
        timezone.utc
    )
    day_end = datetime.combine(
        trading_date + timedelta(days=1),
        dt_time.min,
        tzinfo=LOCAL_TIMEZONE,
    ).astimezone(
        timezone.utc
    )
    existing_rows = repository.fetch_between(day_start, day_end)

    if existing_rows:
        first_row = sorted(existing_rows, key=lambda row: str(row.get("timestamp", "")))[0]
        locked_atm = int(float(first_row["atm_strike"]))
    else:
        future_quote = fetcher.get_ltp(MCX_EXCHANGE, trading_symbol)
        locked_atm = calculate_atm_strike(future_quote.last_price)

    option_pair = OptionSelector(instruments).find_atm_pair(locked_atm, as_of_date=trading_date)
    return DailySelection(
        trading_date=trading_date,
        trading_symbol=trading_symbol,
        atm_strike=locked_atm,
        option_pair=option_pair,
    )


def run_once(
    fetcher: GrowwDataFetcher,
    repository: SupabaseRepository,
    selection: DailySelection,
) -> AtmRecord:
    symbols = [
        selection.trading_symbol,
        selection.option_pair.ce_symbol,
        selection.option_pair.pe_symbol,
    ]
    quotes = fetcher.get_multiple_ltp(MCX_EXCHANGE, symbols)
    
    # Capture timestamp immediately after fetch for maximum accuracy
    # User requested local time for accuracy
    now = datetime.now(LOCAL_TIMEZONE)
    
    future_quote = quotes.get(f"{MCX_EXCHANGE}_{selection.trading_symbol}")
    ce_quote = quotes.get(f"{MCX_EXCHANGE}_{selection.option_pair.ce_symbol}")
    pe_quote = quotes.get(f"{MCX_EXCHANGE}_{selection.option_pair.pe_symbol}")

    if not future_quote or not ce_quote or not pe_quote:
        raise RuntimeError(f"One or more quotes missing in multi-fetch: {quotes.keys()}")

    record = AtmRecord(
        timestamp=now,
        futures_price=future_quote.last_price,
        atm_strike=selection.atm_strike,
        ce_price=ce_quote.last_price,
        pe_price=pe_quote.last_price,
        futures_symbol=selection.trading_symbol,
    )
    # Check if we already have a record for this exact minute to prevent duplicates on restart
    existing = repository.fetch_between(
        now.replace(second=0, microsecond=0),
        now.replace(second=59, microsecond=999999)
    )
    if existing:
        print(f"SKIPPED (Duplicate): {now.strftime('%H:%M:%S')} already exists", flush=True)
        return None

    if now.minute % 5 == 0:
        repository.insert_atm_record(record)
        print(
            f"RECORDED: {now.strftime('%H:%M:%S')} | "
            f"{record.futures_price:.2f} | "
            f"{record.atm_strike} | "
            f"{record.ce_price:.2f} | "
            f"{record.pe_price:.2f}",
            flush=True,
        )
    else:
        print(f"SKIPPED (Not 5m): {now.strftime('%H:%M:%S')} | {record.futures_price:.2f}", flush=True)
    return record


def fetch_window_candles(
    fetcher: GrowwDataFetcher,
    groww_symbol: str,
    trading_symbol: str,
    windows: list[tuple[datetime, datetime]],
) -> pd.DataFrame:
    if not windows:
        return pd.DataFrame()

    frames = [
        fetcher.get_minute_candles(
            exchange=MCX_EXCHANGE,
            segment=COMMODITY_SEGMENT,
            groww_symbol=groww_symbol,
            start_time=start_time,
            end_time=end_time,
            trading_symbol=trading_symbol,
        )
        for start_time, end_time in windows
    ]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    candles = (
        pd.concat(frames, ignore_index=True)
        .sort_values("timestamp")
        .drop_duplicates("timestamp", keep="last")
        .reset_index(drop=True)
    )
    return filter_sampled_rows(
        candles,
        start_date=windows[0][0].date(),
        end_date=windows[-1][0].date(),
        now=windows[-1][1],
    )


def build_daily_frame(
    fetcher: GrowwDataFetcher,
    instruments: pd.DataFrame,
    trading_date: date,
    local_now: datetime,
) -> pd.DataFrame:
    windows = build_intraday_windows(trading_date, trading_date, now=local_now)
    if not windows:
        return pd.DataFrame()

    future = fetcher.get_natural_gas_future(instruments, as_of_date=trading_date)
    future_groww_symbol = str(future.get("groww_symbol", "")).strip()
    future_trading_symbol = str(future.get("trading_symbol", "")).strip()
    
    future_candles = fetch_window_candles(
        fetcher=fetcher,
        groww_symbol=future_groww_symbol,
        trading_symbol=future_trading_symbol,
        windows=windows,
    )
    if future_candles.empty:
        return pd.DataFrame()

    day_data = future_candles.loc[:, ["timestamp", "close"]].rename(columns={"close": "futures_price"})
    day_data = day_data.sort_values("timestamp").reset_index(drop=True)
    
    atm_strike = calculate_atm_strike(float(day_data.iloc[0]["futures_price"]))
    day_data.loc[:, "atm_strike"] = atm_strike
    
    option_pair = OptionSelector(instruments).find_atm_pair(atm_strike, as_of_date=trading_date)
    
    ce_candles = fetch_window_candles(
        fetcher, option_pair.ce_groww_symbol, option_pair.ce_symbol, windows
    )
    pe_candles = fetch_window_candles(
        fetcher, option_pair.pe_groww_symbol, option_pair.pe_symbol, windows
    )
    
    if not ce_candles.empty:
        ce_prices = ce_candles.loc[:, ["timestamp", "close"]].rename(columns={"close": "ce_price"})
        day_data = day_data.merge(ce_prices, on="timestamp", how="left")
    else:
        day_data["ce_price"] = None

    if not pe_candles.empty:
        pe_prices = pe_candles.loc[:, ["timestamp", "close"]].rename(columns={"close": "pe_price"})
        day_data = day_data.merge(pe_prices, on="timestamp", how="left")
    else:
        day_data["pe_price"] = None
        
    return day_data


def sync_history(
    fetcher: GrowwDataFetcher, 
    repository: SupabaseRepository, 
    days: int = 30
) -> None:
    instruments = fetcher.get_mcx_instruments()
    local_now = datetime.now(LOCAL_TIMEZONE)
    
    for i in range(days):
        target_date = local_now.date() - timedelta(days=i)
        logger.info("Syncing historical data for %s", target_date)
        
        # Check if we already have data for this day
        start_time = datetime.combine(target_date, datetime.min.time(), tzinfo=LOCAL_TIMEZONE)
        end_time = datetime.combine(target_date + timedelta(days=1), datetime.min.time(), tzinfo=LOCAL_TIMEZONE)
        
        existing = repository.fetch_between(start_time, end_time)
        if len(existing) >= 15: # Expecting around 15-20 snaps per day
            logger.info("Skipping %s, already has %d records", target_date, len(existing))
            continue
            
        day_frame = build_daily_frame(fetcher, instruments, target_date, local_now)
        if day_frame.empty:
            continue
            
        # Get future instrument for the symbol name
        future = fetcher.get_natural_gas_future(instruments, as_of_date=target_date)
        
        # Prepare deduplication set
        existing_timestamps = {
            pd.Timestamp(row.get("timestamp")).isoformat()
            for row in existing
            if row.get("timestamp")
        }
            
        inserted = 0
        for row in day_frame.itertuples():
            if pd.isna(row.ce_price) or pd.isna(row.pe_price):
                continue
            
            ts_iso = pd.Timestamp(row.timestamp).isoformat()
            if ts_iso in existing_timestamps:
                continue
            
            ts = pd.Timestamp(row.timestamp).to_pydatetime()
            repository.insert_atm_record(
                AtmRecord(
                    timestamp=ts,
                    futures_price=float(row.futures_price),
                    atm_strike=int(row.atm_strike),
                    ce_price=row.ce_price if not pd.isna(row.ce_price) else None,
                    pe_price=row.pe_price if not pd.isna(row.pe_price) else None,
                    futures_symbol=future["trading_symbol"] if future is not None else "",
                )
            )
            inserted += 1
        logger.info("Inserted %d records for %s", inserted, target_date)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--sync", type=int, help="Sync historical data for N days")
    args = parser.parse_args()

    settings = get_settings()
    fetcher = GrowwDataFetcher(
        access_token=settings.groww_access_token,
        api_key=settings.groww_api_key,
        totp_secret=settings.groww_totp_secret,
        cache_ttl_hours=settings.instrument_cache_ttl_hours,
    )
    repository = SupabaseRepository(
        url=settings.supabase_url,
        key=settings.supabase_key,
        table=settings.supabase_table,
    )

    if args.sync:
        sync_history(fetcher, repository, days=args.sync)
        return

    if args.once:
        # For 'once', we just do the current LTP and save it (like main.py used to do)
        # But maybe we also want to sync today's history?
        # Let's just do a 1-day history sync for 'once' to fill gaps
        sync_history(fetcher, repository, days=1)
        return

    print("Time | Price  ATM | CE | PE", flush=True)
    current_selection: DailySelection | None = None
    while True:
        started = time_module.monotonic()
        try:
            local_now = datetime.now(LOCAL_TIMEZONE)
            current_date = local_now.date()
            
            # Check if we are in a monitoring window
            windows = build_intraday_windows(current_date, current_date, now=local_now)
            is_in_window = any(w[0] <= local_now <= w[1] for w in windows)
            
            if is_in_window:
                if current_selection is None or current_selection.trading_date != current_date:
                    instruments = fetcher.get_mcx_instruments()
                    current_selection = resolve_daily_selection(
                        fetcher=fetcher,
                        repository=repository,
                        instruments=instruments,
                        trading_date=current_date,
                    )
                run_once(fetcher, repository, current_selection)
            else:
                # Just logging occasionally so we know it's alive
                if local_now.minute % 15 == 0 and local_now.second < 10:
                    logger.info("Outside monitoring windows. Sleeping...")

        except Exception:
            logger.exception("ATM tracker cycle failed")

        elapsed = time_module.monotonic() - started
        time_module.sleep(max(1, settings.poll_interval_seconds - elapsed))


if __name__ == "__main__":
    main()
