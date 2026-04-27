from __future__ import annotations

import argparse
from pathlib import Path

import pyotp
from dotenv import set_key
from growwapi import GrowwAPI

from tracker_service.config import get_groww_auth_settings


class GrowwAccessTokenGenerator:
    def __init__(
        self,
        api_key: str,
        api_secret: str | None = None,
        totp_secret: str | None = None,
        env_file: str = ".env",
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.totp_secret = totp_secret
        self.env_file = Path(env_file)

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
            resolved_totp = pyotp.TOTP(self.totp_secret).now()
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

    def save_to_env(self, access_token: str) -> None:
        if not self.env_file.exists():
            self.env_file.touch()
        set_key(str(self.env_file), "GROWW_ACCESS_TOKEN", access_token)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate and save a Groww API access token."
    )
    parser.add_argument(
        "--totp",
        help="Current TOTP code for Groww's TOTP-token flow.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print the generated access token without writing it to .env.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = get_groww_auth_settings()
    generator = GrowwAccessTokenGenerator(
        api_key=settings.groww_api_key,
        api_secret=settings.groww_api_secret,
        totp_secret=settings.groww_totp_secret,
        env_file=settings.env_file,
    )
    access_token = generator.generate(totp=args.totp)

    if not args.no_save:
        generator.save_to_env(access_token)
        print(f"Saved GROWW_ACCESS_TOKEN to {settings.env_file}")

    print(f"Access token: {access_token}")


if __name__ == "__main__":
    main()
