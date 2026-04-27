from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import unittest

import pandas as pd

from dashboard import fetch_previous_close
from tracker_service.data_fetcher import GrowwDataFetcher
from tracker_service.intraday_windows import LOCAL_TIMEZONE, filter_sampled_rows
from tracker_service.option_selector import OptionSelector


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
                "instrument_type": "FUT",
                "trading_symbol": "NATURALGAS26MAY26FUT",
                "groww_symbol": "MCX-NATURALGAS-26May26-FUT",
                "name": "",
                "underlying_symbol": "NATURALGAS",
                "expiry": "2026-05-26",
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
            {
                "exchange": "MCX",
                "segment": "COMMODITY",
                "instrument_type": "CE",
                "trading_symbol": "NATURALGAS28MAY26240CE",
                "groww_symbol": "MCX-NATURALGAS-28May26-240-CE",
                "name": "",
                "underlying_symbol": "NATURALGAS",
                "expiry": "2026-05-28",
                "strike": 240,
            },
            {
                "exchange": "MCX",
                "segment": "COMMODITY",
                "instrument_type": "PE",
                "trading_symbol": "NATURALGAS28MAY26240PE",
                "groww_symbol": "MCX-NATURALGAS-28May26-240-PE",
                "name": "",
                "underlying_symbol": "NATURALGAS",
                "expiry": "2026-05-28",
                "strike": 240,
            },
        ]
    )


def ist_to_utc(day: date, hh: int, mm: int) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(day, time(hh, mm), tzinfo=IST)).tz_convert("UTC")


class SelectionAndWindowTests(unittest.TestCase):
    def test_contract_selection_rolls_on_option_expiry(self) -> None:
        instruments = build_instruments()
        fetcher = object.__new__(GrowwDataFetcher)

        current_future = GrowwDataFetcher.get_natural_gas_future(
            fetcher,
            instruments,
            as_of_date=date(2026, 4, 22),
        )
        rolled_future = GrowwDataFetcher.get_natural_gas_future(
            fetcher,
            instruments,
            as_of_date=date(2026, 4, 23),
        )

        selector = OptionSelector(instruments)
        current_pair = selector.find_atm_pair(240, as_of_date=date(2026, 4, 22))
        rolled_pair = selector.find_atm_pair(240, as_of_date=date(2026, 4, 23))

        self.assertEqual(current_future["trading_symbol"], "NATURALGAS27APR26FUT")
        self.assertEqual(rolled_future["trading_symbol"], "NATURALGAS26MAY26FUT")
        self.assertEqual(str(current_pair.expiry.date()), "2026-04-23")
        self.assertEqual(str(rolled_pair.expiry.date()), "2026-05-28")
        self.assertEqual(current_pair.ce_symbol, "NATURALGAS23APR26240CE")
        self.assertEqual(current_pair.pe_symbol, "NATURALGAS23APR26240PE")
        self.assertEqual(rolled_pair.ce_symbol, "NATURALGAS28MAY26240CE")
        self.assertEqual(rolled_pair.pe_symbol, "NATURALGAS28MAY26240PE")

    def test_filter_sampled_rows_keeps_5_minute_marks(self) -> None:
        day = date(2026, 4, 27)
        raw = pd.DataFrame(
            {
                "timestamp": [
                    ist_to_utc(day, 8, 59),
                    ist_to_utc(day, 9, 0),
                    ist_to_utc(day, 9, 1),
                    ist_to_utc(day, 9, 5),
                    ist_to_utc(day, 9, 10),
                    ist_to_utc(day, 9, 15),
                    ist_to_utc(day, 9, 20),
                    ist_to_utc(day, 15, 0),
                    ist_to_utc(day, 15, 3),
                    ist_to_utc(day, 15, 5),
                    ist_to_utc(day, 17, 0),
                    ist_to_utc(day, 17, 30),
                    ist_to_utc(day, 20, 30),
                    ist_to_utc(day, 20, 35),
                ],
                "close": range(14),
            }
        )

        filtered = filter_sampled_rows(
            raw,
            start_date=day,
            end_date=day,
            now=datetime(2026, 4, 27, 21, 0, tzinfo=IST),
        )
        got = [
            pd.Timestamp(value).tz_convert(LOCAL_TIMEZONE).strftime("%H:%M")
            for value in filtered["timestamp"]
        ]

        self.assertEqual(
            got,
            [
                "09:00",
                "09:05",
                "09:10",
                "09:15",
                "15:00",
                "15:05",
                "17:00",
                "17:30",
                "20:30",
            ],
        )

    def test_fetch_previous_close_walks_back_to_last_trading_day(self) -> None:
        class FakeFetcher:
            def get_minute_candles(self, **kwargs):  # noqa: ANN003
                start_time = kwargs["start_time"]
                if start_time.date() == date(2026, 4, 25):
                    return pd.DataFrame(
                        {
                            "timestamp": [pd.Timestamp("2026-04-25T10:00:00+05:30")],
                            "close": [238.5],
                        }
                    )
                return pd.DataFrame(columns=["timestamp", "close"])

        previous_close = fetch_previous_close(
            FakeFetcher(),
            trading_symbol="NATURALGAS26MAY26FUT",
            trading_date=date(2026, 4, 27),
        )

        self.assertEqual(previous_close, 238.5)
