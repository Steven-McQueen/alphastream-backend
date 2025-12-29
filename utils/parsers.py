from __future__ import annotations

import re
from typing import Optional


def _normalize(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
    return value if value not in ("", "--") else None


def clean_percentage(value: Optional[str], default: float = 0.0) -> float:
    """Convert '+1.23%' strings to float 1.23."""
    norm = _normalize(value)
    if norm is None:
        return default
    try:
        return float(norm.replace("%", "").replace(",", ""))
    except ValueError:
        return default


def clean_number(value: Optional[str], default: float = 0.0) -> float:
    """Convert '1,234.56' to 1234.56."""
    norm = _normalize(value)
    if norm is None:
        return default
    try:
        return float(norm.replace(",", ""))
    except ValueError:
        return default


def clean_market_cap(value: Optional[str], default: float = 0.0) -> float:
    """Convert market cap strings to billions."""
    norm = _normalize(value)
    if norm is None:
        return default

    val = norm.replace(",", "")
    multiplier = 1.0
    if val.endswith("M"):
        multiplier = 0.001  # millions -> billions
        val = val[:-1]
    elif val.endswith("B"):
        multiplier = 1.0
        val = val[:-1]
    elif val.endswith("T"):
        multiplier = 1000.0
        val = val[:-1]

    try:
        return float(val) * multiplier
    except ValueError:
        return default


def optional_float(value: Optional[str]) -> Optional[float]:
    """Return float or None when value is missing or '--'."""
    norm = _normalize(value)
    if norm is None:
        return None
    try:
        return float(norm.replace(",", ""))
    except ValueError:
        return None

