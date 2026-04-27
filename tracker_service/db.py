from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime

from postgrest.exceptions import APIError
from supabase import SupabaseException
from supabase import Client, create_client


@dataclass(frozen=True)
class AtmRecord:
    timestamp: datetime
    futures_price: float
    atm_strike: int
    ce_price: float | None
    pe_price: float | None
    futures_symbol: str | None = None

    def as_payload(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "futures_price": self.futures_price,
            "atm_strike": self.atm_strike,
            "ce_price": self.ce_price,
            "pe_price": self.pe_price,
            "futures_symbol": self.futures_symbol,
        }


class SupabaseRepository:
    def __init__(self, url: str, key: str, table: str = "atm_data") -> None:
        try:
            self.client: Client = create_client(url, key)
        except SupabaseException as exc:
            raise RuntimeError(
                "Supabase client setup failed. Check SUPABASE_URL and SUPABASE_KEY in .env. "
                "Use a valid sb_publishable, sb_secret, anon, or service_role key."
            ) from exc
        self.table = table

    def insert_atm_record(self, record: AtmRecord, retries: int = 3) -> dict[str, object] | None:
        payload = record.as_payload()
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                response = self.client.table(self.table).insert(payload).execute()
                return response.data[0] if response.data else None
            except APIError as exc:
                last_error = exc
                if self._is_permission_error(exc):
                    raise RuntimeError(
                        "Supabase rejected the insert due to table permissions/RLS. "
                        "Use a Supabase secret/service_role key for SUPABASE_KEY, or run "
                        "sql/create_atm_data.sql to add insert/select policies for atm_data."
                    ) from exc
                if attempt < retries - 1:
                    time.sleep(2**attempt)
            except Exception as exc:
                last_error = exc
                if attempt < retries - 1:
                    time.sleep(2**attempt)

        raise RuntimeError("Failed to insert ATM record into Supabase") from last_error

    def fetch_recent(self, limit: int = 200) -> list[dict[str, object]]:
        response = (
            self.client.table(self.table)
            .select("*")
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return list(response.data or [])

    def fetch_since(self, since: datetime, limit: int = 5000) -> list[dict[str, object]]:
        response = (
            self.client.table(self.table)
            .select("*")
            .gte("timestamp", since.isoformat())
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return list(response.data or [])

    def fetch_between(
        self,
        start: datetime,
        end: datetime,
        limit: int = 5000,
    ) -> list[dict[str, object]]:
        response = (
            self.client.table(self.table)
            .select("*")
            .gte("timestamp", start.isoformat())
            .lt("timestamp", end.isoformat())
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return list(response.data or [])

    @staticmethod
    def _is_permission_error(exc: APIError) -> bool:
        payload = getattr(exc, "args", [{}])[0]
        if isinstance(payload, dict):
            return payload.get("code") == "42501" or "row-level security" in str(
                payload.get("message", "")
            ).lower()
        return "row-level security" in str(exc).lower() or "401" in str(exc)
