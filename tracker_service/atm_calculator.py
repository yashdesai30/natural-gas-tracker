from __future__ import annotations


def calculate_atm_strike(price: float, strike_step: int = 5) -> int:
    if price <= 0:
        raise ValueError(f"Futures price must be positive, got {price}")
    return int(round(price / strike_step) * strike_step)
