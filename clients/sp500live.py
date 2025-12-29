from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Tuple

import requests

from config import FALLBACK_FILE

SP500_URL = "https://www.sp500live.co/sp500_companies.json"
TIMEOUT = 10
RETRIES = 2


def _load_fallback() -> Dict:
    if not FALLBACK_FILE.exists():
        return {}
    try:
        with FALLBACK_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def fetch_sp500_live() -> Tuple[Dict, str]:
    """
    Fetch SP500Live data with retries.
    Returns (data, source) where source is 'live' or 'fallback'.
    """
    last_error = None
    for attempt in range(RETRIES + 1):
        try:
            response = requests.get(SP500_URL, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json(), "live"
        except Exception as exc:
            last_error = exc
            time.sleep(1)

    fallback = _load_fallback()
    if fallback:
        return fallback, "fallback"

    raise RuntimeError(f"Failed to fetch SP500 live data: {last_error}")

