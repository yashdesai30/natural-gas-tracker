from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    groww_access_token: str | None
    supabase_url: str
    supabase_key: str
    groww_api_key: str | None = None
    groww_totp_secret: str | None = None
    poll_interval_seconds: int = 60
    instrument_cache_ttl_hours: int = 12
    supabase_table: str = "atm_data"


@dataclass(frozen=True)
class GrowwAuthSettings:
    groww_api_key: str
    groww_api_secret: str | None = None
    groww_totp_secret: str | None = None
    env_file: str = ".env"


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        extra = ""
        if name == "GROWW_ACCESS_TOKEN":
            extra = " Run: python -m tracker_service.groww_auth"
        raise RuntimeError(f"Missing required environment variable: {name}.{extra}")
    return value.strip()


def _validate_supabase_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc.endswith(".supabase.co"):
        raise RuntimeError(
            "SUPABASE_URL must look like https://<project-ref>.supabase.co. "
            "Copy it from Supabase Project Settings > API > Project URL."
        )
    return url


def _validate_supabase_key(key: str) -> str:
    jwt_pattern = r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$"
    supabase_platform_key_pattern = r"^sb_(publishable|secret)_[A-Za-z0-9_-]+$"
    if not re.match(jwt_pattern, key) and not re.match(supabase_platform_key_pattern, key):
        raise RuntimeError(
            "SUPABASE_KEY is not a valid Supabase API key. "
            "Use the Supabase publishable/secret key that starts with 'sb_' "
            "or the JWT-style anon/service_role key that starts with 'eyJ'."
        )
    return key


def get_settings() -> Settings:
    return Settings(
        groww_access_token=os.getenv("GROWW_ACCESS_TOKEN"),
        supabase_url=_validate_supabase_url(_required_env("SUPABASE_URL")),
        supabase_key=_validate_supabase_key(_required_env("SUPABASE_KEY")),
        groww_api_key=os.getenv("GROWW_API_KEY"),
        groww_totp_secret=os.getenv("GROWW_TOTP_SECRET"),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "60")),
        instrument_cache_ttl_hours=int(os.getenv("INSTRUMENT_CACHE_TTL_HOURS", "12")),
        supabase_table=os.getenv("SUPABASE_TABLE", "atm_data"),
    )


def get_groww_auth_settings() -> GrowwAuthSettings:
    return GrowwAuthSettings(
        groww_api_key=_required_env("GROWW_API_KEY"),
        groww_api_secret=os.getenv("GROWW_API_SECRET", "").strip() or None,
        groww_totp_secret=os.getenv("GROWW_TOTP_SECRET", "").strip() or None,
        env_file=os.getenv("ENV_FILE", ".env"),
    )
