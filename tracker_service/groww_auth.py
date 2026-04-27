from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pyotp
from growwapi import GrowwAPI

from tracker_service.config import get_groww_auth_settings

logger = logging.getLogger(__name__)

class GrowwAccessTokenGenerator:
    def __init__(
        self,
        api_key: str,
        api_secret: str | None = None,
        totp_secret: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.totp_secret = totp_secret

    def generate(self, totp: str | None = None) -> str:
        if self.api_secret:
            return str(
                GrowwAPI.get_access_token(
                    api_key=self.api_key,
                    secret=self.api_secret,
                )
            )

        resolved_totp = totp
        if not resolved_totp and self.totp_secret:
            resolved_totp = pyotp.TOTP(self.totp_secret.replace(" ", "")).now()
        
        if not resolved_totp:
            raise RuntimeError(
                "Groww TOTP flow requires --totp or GROWW_TOTP_SECRET. "
                "For API key/secret flow, set GROWW_API_SECRET."
            )

        return str(
            GrowwAPI.get_access_token(
                api_key=self.api_key,
                totp=resolved_totp,
            )
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Groww API access token."
    )
    parser.add_argument(
        "--totp",
        help="Current TOTP code for Groww's TOTP-token flow.",
    )
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = build_parser().parse_args()
    settings = get_groww_auth_settings()
    generator = GrowwAccessTokenGenerator(
        api_key=settings.groww_api_key,
        api_secret=settings.groww_api_secret,
        totp_secret=settings.groww_totp_secret,
    )
    access_token = generator.generate(totp=args.totp)
    print(f"\nSuccessfully generated access token:\n{access_token}")


if __name__ == "__main__":
    main()
