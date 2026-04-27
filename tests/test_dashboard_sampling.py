from __future__ import annotations

from datetime import date, datetime, time, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pandas as pd
import unittest

import dashboard
import tracker_service.main as tracker_main
from tracker_service.data_fetcher import GrowwDataFetcher


IST = ZoneInfo("Asia/Kolkata")


def build_instruments() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "exchange": "MCX",
                "segment": "COMMODITY",
                "instrument_type": "FUT",
                "trading_symbol": "NATURALGAS27APR26FUT",
                "groww_symbol": "MCX-NATURALGAS-27Apr26-FUT",
                "name": "",
                "underlying_symbol": "NATURALGAS",
                "expiry": "2026-04-27",
                "strike": 0,
            },
            {
                "exchange": "MCX",
                "segment": "COMMODITY",
                "instrument_type": "CE",
                "trading_symbol": "NATURALGAS23APR26240CE",
                "groww_symbol": "MCX-NATURALGAS-23Apr26-240-CE",
                "name": "",
                "underlying_symbol": "NATURALGAS",
                "expiry": "2026-04-23",
                "strike": 240,
            },
            {
                "exchange": "MCX",
                "segment": "COMMODITY",
                "instrument_type": "PE",
                "trading_symbol": "NATURALGAS23APR26240PE",
                "groww_symbol": "MCX-NATURALGAS-23Apr26-240-PE",
                "name": "",
                "underlying_symbol": "NATURALGAS",
                "expiry": "2026-04-23",
                "strike": 240,
            },
        ]
    )


def utc(day: date, hh: int, mm: int) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(day, time(hh, mm), tzinfo=IST)).tz_convert("UTC")


class FakeFetcher:
    def __init__(self) -> None:
        self.future = {
            "trading_symbol": "NATURALGAS27APR26FUT",
            "groww_symbol": "MCX-NATURALGAS-27Apr26-FUT",
        }

    def get_natural_gas_future(self, instruments, as_of_date=None):  # noqa: ANN001
        return self.future

    def get_ltp(self, exchange, trading_symbol, retries=3):  # noqa: ANN001
        return SimpleNamespace(instrument_key=f"{exchange}_{trading_symbol}", last_price=240.2)

    def get_minute_candles(
        self,
        exchange,
        segment,
        groww_symbol,
        start_time,
        end_time,
        trading_symbol=None,
    ):  # noqa: ANN001
        symbol = trading_symbol or groww_symbol
        day = start_time.date()
        if symbol == "NATURALGAS27APR26FUT":
            return pd.DataFrame(
                {
                    "timestamp": [utc(day, 9, 0), utc(day, 9, 5)],
                    "open": [240.0, 245.0],
                    "high": [240.5, 245.5],
                    "low": [239.5, 244.5],
                    "close": [240.2, 245.2],
                    "volume": [1, 1],
                }
            )
        if symbol == "NATURALGAS23APR26240CE":
            return pd.DataFrame(
                {
                    "timestamp": [utc(day, 9, 0), utc(day, 9, 5)],
                    "open": [10.0, 11.0],
                    "high": [10.5, 11.5],
                    "low": [9.5, 10.5],
                    "close": [10.2, 11.2],
                    "volume": [1, 1],
                }
            )
        if symbol == "NATURALGAS23APR26240PE":
            return pd.DataFrame(
                {
                    "timestamp": [utc(day, 9, 0), utc(day, 9, 5)],
                    "open": [12.0, 13.0],
                    "high": [12.5, 13.5],
                    "low": [11.5, 12.5],
                    "close": [12.2, 13.2],
                    "volume": [1, 1],
                }
            )
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])


class DashboardSamplingTests(unittest.TestCase):
    def test_build_daily_frame_locks_atm_to_first_row(self) -> None:
        fetcher = FakeFetcher()
        instruments = build_instruments()
        frame = dashboard.build_daily_frame(
            fetcher=fetcher,
            instruments=instruments,
            trading_date=date(2026, 4, 27),
            local_now=datetime(2026, 4, 27, 10, 0, tzinfo=IST),
        )

        self.assertEqual(list(frame["atm_strike"]), [240, 240])
        self.assertEqual(list(frame["futures_price"]), [240.2, 245.2])
        self.assertEqual(list(frame["ce_price"]), [10.2, 11.2])
        self.assertEqual(list(frame["pe_price"]), [12.2, 13.2])

    def test_sync_today_rows_skips_existing_timestamps(self) -> None:
        inserted = []

        today_frame = pd.DataFrame(
            {
                "timestamp": [utc(date(2026, 4, 27), 9, 0), utc(date(2026, 4, 27), 9, 5)],
                "futures_price": [240.2, 245.2],
                "atm_strike": [240, 240],
                "ce_price": [10.2, 11.2],
                "pe_price": [12.2, 13.2],
            }
        )

        repository = MagicMock()
        repository.fetch_between.return_value = [
            {"timestamp": today_frame.iloc[0]["timestamp"].isoformat()},
        ]

        def capture(record):  # noqa: ANN001
            inserted.append(record)
            return None

        repository.insert_atm_record.side_effect = capture

        with patch.object(dashboard, "build_daily_frame", return_value=today_frame):
            count_inserted, count_skipped = dashboard.sync_today_rows(
                fetcher=FakeFetcher(),
                repository=repository,
                instruments=build_instruments(),
                local_now=datetime(2026, 4, 27, 10, 0, tzinfo=IST),
            )

        self.assertEqual(count_inserted, 1)
        self.assertEqual(count_skipped, 1)
        self.assertEqual(len(inserted), 1)
        self.assertEqual(inserted[0].timestamp.isoformat(), today_frame.iloc[1]["timestamp"].isoformat())

    def test_resolve_daily_selection_reuses_existing_atm(self) -> None:
        fetcher = FakeFetcher()
        fetcher.get_ltp = MagicMock()
        repository = MagicMock()
        repository.fetch_between.return_value = [
            {"timestamp": "2026-04-27T03:30:00+00:00", "atm_strike": 240},
            {"timestamp": "2026-04-27T03:35:00+00:00", "atm_strike": 245},
        ]

        selection = tracker_main.resolve_daily_selection(
            fetcher=fetcher,
            repository=repository,
            instruments=build_instruments(),
            trading_date=date(2026, 4, 27),
        )

        self.assertEqual(selection.atm_strike, 240)
        fetcher.get_ltp.assert_not_called()
