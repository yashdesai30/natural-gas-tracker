from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from tracker_service.market_rules import (
    COMMODITY_SEGMENT,
    MCX_EXCHANGE,
    normalise_instruments,
    select_natural_gas_contract_rows,
)


@dataclass(frozen=True)
class OptionPair:
    expiry: pd.Timestamp
    ce_symbol: str
    pe_symbol: str
    ce_groww_symbol: str
    pe_groww_symbol: str


class OptionSelector:
    def __init__(self, instruments: pd.DataFrame) -> None:
        self.instruments = self._normalise(instruments)

    def find_atm_pair(
        self,
        atm_strike: int,
        as_of_date: date | datetime | None = None,
    ) -> OptionPair:
        options = select_natural_gas_contract_rows(
            self.instruments,
            as_of_date=as_of_date,
            instrument_types={"CE", "PE"},
        )
        options = options[options["strike"] == float(atm_strike)].copy()

        if options.empty:
            raise RuntimeError(f"No NATURALGAS options found for ATM strike {atm_strike}")

        for expiry in sorted(options["expiry"].dropna().unique()):
            expiry_options = options[options["expiry"] == expiry]
            ce = expiry_options[expiry_options["instrument_type"] == "CE"]
            pe = expiry_options[expiry_options["instrument_type"] == "PE"]
            if not ce.empty and not pe.empty:
                return OptionPair(
                    expiry=pd.Timestamp(expiry),
                    ce_symbol=str(ce.sort_values("trading_symbol").iloc[0]["trading_symbol"]),
                    pe_symbol=str(pe.sort_values("trading_symbol").iloc[0]["trading_symbol"]),
                    ce_groww_symbol=str(
                        ce.sort_values("trading_symbol").iloc[0]["groww_symbol"]
                    ),
                    pe_groww_symbol=str(
                        pe.sort_values("trading_symbol").iloc[0]["groww_symbol"]
                    ),
                )

        raise RuntimeError(f"Missing CE/PE pair for NATURALGAS strike {atm_strike}")

    @staticmethod
    def _normalise(frame: pd.DataFrame) -> pd.DataFrame:
        return normalise_instruments(frame)
