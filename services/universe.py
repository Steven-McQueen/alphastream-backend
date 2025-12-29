import logging
from datetime import datetime
from typing import Dict, List, Optional

from clients.sp500live import fetch_sp500_live
from config import STOCK_TTL, UNIVERSE_TTL
from models import Stock
from utils.cache import TTLCache
from utils.parsers import (
    clean_market_cap,
    clean_number,
    clean_percentage,
    optional_float,
)

logger = logging.getLogger(__name__)

_universe_cache = TTLCache(UNIVERSE_TTL)
_stock_cache = TTLCache(STOCK_TTL)


def _map_raw_to_stock(ticker: str, data: Dict) -> Stock:
    if not isinstance(data, dict):
        raise ValueError("invalid data")

    updated_at = data.get("date") or datetime.utcnow().isoformat()

    return Stock(
        ticker=ticker,
        name=data.get("name", ticker),
        sector=data.get("sector", "Unknown"),
        industry=data.get("industry", "Unknown"),
        marketCap=clean_market_cap(data.get("MarketCap")),
        price=clean_number(data.get("last")),
        change1D=clean_percentage(data.get("change_1d")),
        change1W=clean_percentage(data.get("change_1w")),
        change1M=clean_percentage(data.get("change_1m")),
        changeYTD=clean_percentage(data.get("change_YTD")),
        change1Y=clean_percentage(data.get("change_1y")),
        change5Y=clean_percentage(data.get("change_5y")),
        peRatio=optional_float(data.get("pe_ratio")),
        forwardPE=optional_float(data.get("pe_forward")),
        pegRatio=optional_float(data.get("peg")),
        priceToBook=optional_float(data.get("price_to_book")),
        evToEbitda=optional_float(data.get("ev_to_ebitda")),
        evToSales=optional_float(data.get("ev_to_sales")),
        dividendYield=optional_float(data.get("dividendyield")),
        beta=optional_float(data.get("beta")),
        eps=optional_float(data.get("eps")),
        volume=clean_number(data.get("volume_1d")),
        avgVolume=0.0,
        grossMargin=clean_percentage(data.get("gross_margin")),
        operatingMargin=clean_percentage(data.get("operating_margin")),
        netMargin=clean_percentage(data.get("net_margin")),
        roe=clean_percentage(data.get("roe")),
        roic=clean_percentage(data.get("roic")),
        revenueGrowth=clean_percentage(data.get("revenue_growth")),
        earningsGrowth=clean_percentage(data.get("earnings_growth")),
        fcfYield=clean_percentage(data.get("fcf_yield")),
        catalysts=[],
        weight=float(data.get("weight") or 0.0),
        updatedAt=updated_at,
    )


def get_core_universe(force_refresh: bool = False) -> List[Stock]:
    cached, stale = _universe_cache.get("core")
    if cached and not force_refresh and not stale:
        return cached

    try:
        raw_data, source = fetch_sp500_live()
    except Exception as exc:
        logger.warning("SP500Live fetch failed: %s", exc)
        if cached:
            return cached
        raise

    stocks: List[Stock] = []
    for ticker, payload in raw_data.items():
        try:
            stock = _map_raw_to_stock(ticker, payload)
            stocks.append(stock)
        except Exception as exc:
            logger.warning("Skipping %s due to parse error: %s", ticker, exc)
            continue

    _universe_cache.set("core", stocks)
    return stocks


def search_symbol(query: str) -> List[Stock]:
    universe = get_core_universe()
    query_lower = query.lower()
    return [
        stock
        for stock in universe
        if query_lower in stock.ticker.lower() or query_lower in stock.name.lower()
    ]


def get_stock_detail(ticker: str) -> Optional[Stock]:
    cached, stale = _stock_cache.get(ticker)
    if cached and not stale:
        return cached

    universe = get_core_universe()
    for stock in universe:
        if stock.ticker == ticker:
            _stock_cache.set(ticker, stock)
            return stock
    return None
