import logging
import time
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyotp
from growwapi import GrowwAPI

from tracker_service.market_rules import (
    COMMODITY_SEGMENT,
    MCX_EXCHANGE,
    normalise_instruments,
    select_natural_gas_contract_rows,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Quote:
    instrument_key: str
    last_price: float


class GrowwDataFetcher:
    def __init__(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        totp_secret: str | None = None,
        cache_ttl_hours: int = 12,
        cache_path: str | Path = ".cache/groww_instruments.csv",
    ) -> None:
        if not access_token and (api_key and totp_secret):
            logger.info("No access token provided. Attempting TOTP login...")
            totp = pyotp.TOTP(totp_secret.replace(" ", ""))
            current_otp = totp.now()
            # According to Groww documentation/SDK patterns
            access_token = GrowwAPI.get_access_token(api_key=api_key, totp=current_otp)
            logger.info("Successfully obtained access token via TOTP")
        
        if not access_token:
            raise RuntimeError("Either access_token or (api_key and totp_secret) must be provided")

        self.groww = GrowwAPI(access_token)
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.cache_path = Path(cache_path)
        self.exchange_mcx = getattr(self.groww, "EXCHANGE_MCX", MCX_EXCHANGE)
        self.segment_commodity = getattr(self.groww, "SEGMENT_COMMODITY", COMMODITY_SEGMENT)

    def get_mcx_instruments(self, force_refresh: bool = False) -> pd.DataFrame:
        if not force_refresh and self._cache_is_fresh():
            return self._read_cache()

        frame = self.groww.get_all_instruments()
        if not isinstance(frame, pd.DataFrame):
            frame = pd.DataFrame(frame)
        if frame.empty:
            raise RuntimeError("Groww returned an empty instruments dump")

        frame = normalise_instruments(frame)
        frame = frame[frame["exchange"] == MCX_EXCHANGE].copy()
        if frame.empty:
            raise RuntimeError("Groww instruments dump does not contain MCX instruments")

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(self.cache_path, index=False)
        return frame

    def get_natural_gas_future(
        self,
        instruments: pd.DataFrame,
        as_of_date: datetime | None = None,
    ) -> pd.Series:
        futures = select_natural_gas_contract_rows(
            instruments,
            as_of_date=as_of_date,
            instrument_types={"FUT"},
        )

        if futures.empty:
            raise RuntimeError("No active MCX NATURALGAS futures contract found")

        return futures.sort_values("expiry").iloc[0]

    def get_ltp(self, exchange: str, trading_symbol: str, retries: int = 3) -> Quote:
        instrument_key = f"{exchange}_{trading_symbol}"
        quotes = self.get_multiple_ltp(exchange, [trading_symbol], retries)
        if instrument_key not in quotes:
            raise RuntimeError(f"Failed to fetch LTP for {instrument_key}")
        return quotes[instrument_key]

    def get_multiple_ltp(
        self, exchange: str, trading_symbols: list[str], retries: int = 3
    ) -> dict[str, Quote]:
        instrument_keys = [f"{exchange}_{ts}" for ts in trading_symbols]
        query_key = ",".join(instrument_keys)
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                logger.info(
                    "Fetching LTP for %s (attempt %d/%d). Request: segment=%s, exchange_trading_symbols=%s",
                    instrument_keys,
                    attempt + 1,
                    retries,
                    self.segment_commodity,
                    query_key,
                )
                data: dict[str, Any] = self.groww.get_ltp(
                    segment=self.segment_commodity,
                    exchange_trading_symbols=query_key,
                )
                
                results: dict[str, Quote] = {}
                for key in instrument_keys:
                    raw_price = data.get(key)
                    if raw_price is not None:
                        results[key] = Quote(instrument_key=key, last_price=float(raw_price))
                
                if results:
                    return results
                
                raise RuntimeError(f"Groww LTP response missing keys {instrument_keys}: {data}")
            except Exception as exc:
                last_error = exc
                if attempt < retries - 1:
                    time.sleep(2**attempt)

        raise RuntimeError(f"Failed to fetch multiple LTPs for {instrument_keys}") from last_error

    def get_minute_candles(
        self,
        exchange: str,
        segment: str,
        groww_symbol: str,
        start_time: datetime,
        end_time: datetime,
        trading_symbol: str | None = None,
    ) -> pd.DataFrame:
        formatted_start = start_time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_end = end_time.strftime("%Y-%m-%d %H:%M:%S")
        if trading_symbol:
            response = self._get_legacy_minute_candles(
                trading_symbol=trading_symbol,
                exchange=exchange,
                segment=segment,
                start_time=formatted_start,
                end_time=formatted_end,
            )
            frame = self._normalise_candles(response)
            if frame.empty:
                return frame
            frame = frame.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
            return frame.reset_index(drop=True)

        try:
            logger.info(
                "Fetching historical candles for %s (groww_symbol=%s). Range: %s to %s",
                trading_symbol or "unknown",
                groww_symbol,
                formatted_start,
                formatted_end,
            )
            response = self.groww.get_historical_candles(
                exchange=exchange,
                segment=segment,
                groww_symbol=groww_symbol,
                start_time=formatted_start,
                end_time=formatted_end,
                candle_interval=getattr(self.groww, "CANDLE_INTERVAL_MIN_1", "1minute"),
            )
        except Exception as exc:
            if not trading_symbol:
                raise
            response = self._get_legacy_minute_candles(
                trading_symbol=trading_symbol,
                exchange=exchange,
                segment=segment,
                start_time=formatted_start,
                end_time=formatted_end,
                original_error=exc,
            )
        frame = self._normalise_candles(response)
        if frame.empty:
            return frame
        frame = frame.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
        return frame.reset_index(drop=True)

    def _get_legacy_minute_candles(
        self,
        trading_symbol: str,
        exchange: str,
        segment: str,
        start_time: str,
        end_time: str,
        original_error: Exception | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    return self.groww.get_historical_candle_data(
                        trading_symbol=trading_symbol,
                        exchange=exchange,
                        segment=segment,
                        start_time=start_time,
                        end_time=end_time,
                        interval_in_minutes=1,
                    )
            except Exception as exc:
                last_error = exc
                if "rate limit" not in str(exc).lower() or attempt == 2:
                    break
                time.sleep(10 * (attempt + 1))

        try:
            raise last_error or RuntimeError("Unknown Groww historical candle error")
        except Exception as legacy_error:
            if original_error is None:
                raise RuntimeError(
                    "Groww historical candle API failed. "
                    f"Legacy API error: {legacy_error}"
                ) from legacy_error
            raise RuntimeError(
                "Groww historical candle APIs failed. "
                f"New API error: {original_error}. Legacy API error: {legacy_error}"
            ) from legacy_error

    def _cache_is_fresh(self) -> bool:
        if not self.cache_path.exists():
            return False
        modified = datetime.fromtimestamp(self.cache_path.stat().st_mtime, tz=timezone.utc)
        return datetime.now(timezone.utc) - modified < self.cache_ttl

    def _read_cache(self) -> pd.DataFrame:
        return normalise_instruments(pd.read_csv(self.cache_path))

    @staticmethod
    def _normalise_candles(response: dict[str, Any]) -> pd.DataFrame:
        payload: Any = response
        if isinstance(payload, dict):
            payload = payload.get("candles") or payload.get("data") or payload.get("payload") or []
        if isinstance(payload, dict):
            payload = payload.get("candles") or []

        rows: list[dict[str, object]] = []
        for candle in payload:
            if isinstance(candle, dict):
                timestamp = (
                    candle.get("timestamp")
                    or candle.get("time")
                    or candle.get("start_time")
                    or candle.get("ts")
                )
                rows.append(
                    {
                        "timestamp": timestamp,
                        "open": candle.get("open"),
                        "high": candle.get("high"),
                        "low": candle.get("low"),
                        "close": candle.get("close"),
                        "volume": candle.get("volume"),
                    }
                )
            elif isinstance(candle, (list, tuple)) and len(candle) >= 5:
                rows.append(
                    {
                        "timestamp": candle[0],
                        "open": candle[1],
                        "high": candle[2],
                        "low": candle[3],
                        "close": candle[4],
                        "volume": candle[5] if len(candle) > 5 else None,
                    }
                )

        frame = pd.DataFrame.from_records(rows)
        if frame.empty:
            return frame
        timestamps = GrowwDataFetcher._parse_candle_timestamps(frame.loc[:, "timestamp"])
        normalised = pd.DataFrame({"timestamp": timestamps})
        for column in ("open", "high", "low", "close", "volume"):
            normalised.loc[:, column] = pd.to_numeric(frame.loc[:, column], errors="coerce")
        return normalised.dropna(subset=["timestamp", "close"])

    @staticmethod
    def _parse_candle_timestamps(values: pd.Series) -> pd.Series:
        numeric_values = pd.to_numeric(values, errors="coerce")
        if numeric_values.notna().all():
            max_value = numeric_values.max()
            unit = "ms" if max_value > 10_000_000_000 else "s"
            return pd.to_datetime(numeric_values, unit=unit, utc=True, errors="coerce")

        timestamps = pd.to_datetime(values, errors="coerce")
        if timestamps.dt.tz is None:
            timestamps = timestamps.dt.tz_localize("Asia/Kolkata")
        return timestamps.dt.tz_convert("UTC")
