import logging
from datetime import datetime
from typing import List, Dict

from clients.finnhub_client import FinnhubRateLimitError, finnhub
from config import MARKET_TTL
from models import (
    CryptoPrice,
    MacroIndicator,
    MarketIndex,
    MarketRegime,
    MarketState,
    MarketStatus,
    SectorPerformance,
)
from services.universe import get_core_universe
from utils.cache import TTLCache

logger = logging.getLogger(__name__)

_market_cache = TTLCache(MARKET_TTL)


def _market_status() -> MarketStatus:
    now = datetime.utcnow()
    hour = now.hour
    if 14 <= hour < 21:
        return "Open"
    if 9 <= hour < 14:
        return "Pre-Market"
    if 21 <= hour or hour < 9:
        return "After-Hours"
    return "Closed"


def _aggregate_sector_performance() -> List[SectorPerformance]:
    universe = get_core_universe()
    buckets: Dict[str, Dict[str, float]] = {}
    counts: Dict[str, int] = {}

    for stock in universe:
        sector = stock.sector or "Unknown"
        counts[sector] = counts.get(sector, 0) + 1
        bucket = buckets.setdefault(
            sector,
            {"change1D": 0.0, "change1W": 0.0, "change1M": 0.0, "change1Y": 0.0},
        )
        bucket["change1D"] += stock.change1D
        bucket["change1W"] += stock.change1W
        bucket["change1M"] += stock.change1M
        bucket["change1Y"] += stock.change1Y

    performances: List[SectorPerformance] = []
    for sector, sums in buckets.items():
        count = max(counts.get(sector, 1), 1)
        performances.append(
            SectorPerformance(
                sector=sector,
                change1D=sums["change1D"] / count,
                change1W=sums["change1W"] / count,
                change1M=sums["change1M"] / count,
                change1Y=sums["change1Y"] / count,
            )
        )
    return performances


def _fetch_indices(cached_state: MarketState | None) -> List[MarketIndex]:
    symbols = [
        ("^GSPC", "S&P 500"),
        ("^DJI", "Dow Jones"),
        ("^IXIC", "Nasdaq"),
    ]
    indices: List[MarketIndex] = []
    for symbol, name in symbols:
        try:
            quote = finnhub.get_quote(symbol)
            indices.append(
                MarketIndex(
                    symbol=symbol,
                    name=name,
                    value=quote.get("c", 0.0),
                    change=quote.get("d", 0.0),
                    changePercent=quote.get("dp", 0.0),
                )
            )
        except FinnhubRateLimitError:
            if cached_state:
                logger.warning("Finnhub rate limited, using cached indices")
                return cached_state.indices
            raise
        except Exception as exc:
            logger.warning("Failed to fetch index %s: %s", symbol, exc)
            if cached_state:
                return cached_state.indices
    return indices


def _regime_from_indices(indices: List[MarketIndex]) -> tuple[MarketRegime, Dict[str, float]]:
    spx = next((i for i in indices if i.symbol == "^GSPC"), None)
    change = spx.changePercent if spx else 0.0
    if change > 0.5:
        return "Risk-On", {"riskOn": 0.75, "riskOff": 0.1, "neutral": 0.15}
    if change < -0.5:
        return "Risk-Off", {"riskOn": 0.1, "riskOff": 0.75, "neutral": 0.15}
    return "Neutral", {"riskOn": 0.33, "riskOff": 0.33, "neutral": 0.34}


def get_market_state() -> MarketState:
    cached_state, stale = _market_cache.get("market")
    if cached_state and not stale:
        return cached_state

    try:
        sector_perf = _aggregate_sector_performance()
        indices = _fetch_indices(cached_state)
        regime, probs = _regime_from_indices(indices)
        state = MarketState(
            status=_market_status(),
            regime=regime,
            regimeProbabilities=probs,
            indices=indices,
            cryptoPrices=[],  # to be implemented later
            macroIndicators=[],  # to be implemented later
            sectorPerformance=sector_perf,
            lastUpdated=datetime.utcnow().isoformat(),
        )
        _market_cache.set("market", state)
        return state
    except FinnhubRateLimitError:
        if cached_state:
            return cached_state
        raise
    except Exception as exc:
        logger.error("Failed to build market state: %s", exc)
        if cached_state:
            return cached_state
        raise
