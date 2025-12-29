import time
from typing import Optional, Dict, List, Any

import requests

from config import FINNHUB_API_KEY, FINNHUB_RATE_LIMIT


class FinnhubRateLimitError(Exception):
    pass


class FinnhubClient:
    """
    Finnhub API client with rate limiting and retry logic.
    """

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str = FINNHUB_API_KEY):
        self.api_key = api_key
        self.session = requests.Session()
        self._call_times: List[float] = []

    def _rate_limit(self):
        now = time.time()
        self._call_times = [t for t in self._call_times if now - t < 60]

        if len(self._call_times) >= FINNHUB_RATE_LIMIT:
            sleep_time = 61 - (now - self._call_times[0])
            if sleep_time > 0:
                time.sleep(sleep_time)

        self._call_times.append(now)

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        params = params or {}
        params["token"] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"

        last_error: Exception | None = None
        for attempt in range(3):
            self._rate_limit()
            try:
                response = self.session.get(url, params=params, timeout=10)
                if response.status_code == 429:
                    raise FinnhubRateLimitError("Rate limit exceeded")
                response.raise_for_status()
                return response.json()
            except FinnhubRateLimitError as exc:
                last_error = exc
                break
            except Exception as exc:
                last_error = exc
                time.sleep(1 + attempt)

        if last_error:
            raise last_error
        raise RuntimeError("Unknown Finnhub error")

    def get_quote(self, symbol: str) -> Dict:
        return self._get("/quote", {"symbol": symbol})

    def get_profile(self, symbol: str) -> Dict:
        return self._get("/stock/profile2", {"symbol": symbol})

    def get_company_news(self, symbol: str, from_date: str, to_date: str) -> List[Dict]:
        return self._get("/company-news", {"symbol": symbol, "from": from_date, "to": to_date})

    def get_market_news(self, category: str = "general") -> List[Dict]:
        return self._get("/news", {"category": category})

    def symbol_lookup(self, query: str) -> List[Dict]:
        result = self._get("/search", {"q": query})
        return result.get("result", [])


finnhub = FinnhubClient()
