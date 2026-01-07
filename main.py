from datetime import datetime, timedelta
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from clients.finnhub_client import FinnhubRateLimitError, finnhub
from config import NEWS_TTL
from database.db_manager import db
from models import MarketNewsItem, MarketState, Portfolio, Stock
from services.market import get_market_state
from services.portfolio import get_mock_portfolio
from utils.cache import TTLCache
from services.refresh_scheduler import start_scheduler_background

app = FastAPI(
    title="AlphaStream API",
    description="Backend for AlphaStream Intelligence Terminal",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/macro/latest")
async def get_latest_macro_snapshot():
    """
    Get latest values for Today's Snapshot
    Returns: SPX, NDX, DJI, RUT, US10Y, VIX with current values and changes
    """
    try:
        indices = db.get_all_indices()
        if not indices:
            raise HTTPException(status_code=503, detail="Data not available")
        indices_dict = {idx["symbol"]: idx for idx in indices}

        treasury = db.get_treasury_history(days=2)
        if not treasury:
            raise HTTPException(status_code=503, detail="Data not available")
        us10y = treasury[-1]["yield_10y"] if treasury else None
        us10y_change = None
        if len(treasury) >= 2:
            us10y_change = treasury[-1]["yield_10y"] - treasury[-2]["yield_10y"]

        vix_history = db.get_vix_history(days=2)
        if not vix_history:
            raise HTTPException(status_code=503, detail="Data not available")
        vix_value = vix_history[-1]["vix_close"] if vix_history else None
        vix_change = None
        if len(vix_history) >= 2 and vix_history[-2]["vix_close"]:
            prev_vix = vix_history[-2]["vix_close"]
            if prev_vix:
                vix_change = ((vix_history[-1]["vix_close"] - prev_vix) / prev_vix) * 100

        snapshot = {
            "SPX": {
                "value": indices_dict.get("^GSPC", {}).get("value"),
                "change_percent": indices_dict.get("^GSPC", {}).get("change_pct")
                or indices_dict.get("^GSPC", {}).get("change_percent"),
            },
            "NDX": {
                "value": indices_dict.get("^IXIC", {}).get("value"),
                "change_percent": indices_dict.get("^IXIC", {}).get("change_pct")
                or indices_dict.get("^IXIC", {}).get("change_percent"),
            },
            "DJI": {
                "value": indices_dict.get("^DJI", {}).get("value"),
                "change_percent": indices_dict.get("^DJI", {}).get("change_pct")
                or indices_dict.get("^DJI", {}).get("change_percent"),
            },
            "RUT": {
                "value": indices_dict.get("^RUT", {}).get("value"),
                "change_percent": indices_dict.get("^RUT", {}).get("change_pct")
                or indices_dict.get("^RUT", {}).get("change_percent"),
            },
            "US10Y": {"value": us10y, "change": us10y_change},
            "VIX": {"value": vix_value, "change_percent": vix_change},
            "last_updated": datetime.now().isoformat(),
        }

        return snapshot
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_latest_macro_snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup"""
    start_scheduler_background()


# ============================================================================
# ROOT / HEALTH
# ============================================================================

@app.get("/")
def root():
    try:
        return {"name": "AlphaStream API", "version": "0.1.0", "status": "running"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in root: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in health_check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# UNIVERSE / SCREENER ENDPOINTS
# ============================================================================

@app.get("/api/universe/core")
def get_universe_core():
    """
    Get all S&P 500 stocks from database
    Returns: List of all stocks with full data
    """
    try:
        stocks = db.get_all_stocks(order_by="market_cap DESC")
        if not stocks:
            raise HTTPException(status_code=503, detail="Data not available")
        result = []
        for stock in stocks:
            result.append(
                {
                    "ticker": stock["ticker"],
                    "name": stock["name"],
                    "sector": stock["sector"],
                    "industry": stock["industry"],
                    "price": stock["price"],
                    "change1D": stock["change_1d"],
                    "change1W": stock["change_1w"],
                    "change1M": stock["change_1m"],
                    "change1Y": stock["change_1y"],
                    "volume": stock["volume"],
                    "peRatio": stock["pe_ratio"],
                    "eps": stock["eps"],
                    "dividendYield": stock["dividend_yield"],
                    "marketCap": stock["market_cap"],
                    "netProfitMargin": stock["net_profit_margin"],
                    "grossMargin": stock["gross_margin"],
                    "roe": stock["roe"],
                    "revenue": stock["revenue_ttm"],
                    "beta": stock["beta"],
                    "institutionalOwnership": stock["institutional_ownership"],
                    "yearFounded": stock["year_founded"],
                    "website": stock["website"],
                    "updatedAt": stock["last_updated"],
                }
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_universe_core: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/universe/search")
def search_universe(q: str = Query(..., min_length=1)):
    """
    Search stocks by ticker or name
    """
    try:
        stocks = db.search_stocks(q)
        if not stocks:
            raise HTTPException(status_code=503, detail="Data not available")
        result = []
        for stock in stocks:
            result.append(
                {
                    "ticker": stock["ticker"],
                    "name": stock["name"],
                    "sector": stock["sector"],
                    "industry": stock["industry"],
                    "price": stock["price"],
                    "change1D": stock["change_1d"],
                    "change1W": stock["change_1w"],
                    "change1M": stock["change_1m"],
                    "change1Y": stock["change_1y"],
                    "volume": stock["volume"],
                    "peRatio": stock["pe_ratio"],
                    "eps": stock["eps"],
                    "dividendYield": stock["dividend_yield"],
                    "marketCap": stock["market_cap"],
                    "netProfitMargin": stock["net_profit_margin"],
                    "grossMargin": stock["gross_margin"],
                    "roe": stock["roe"],
                    "revenue": stock["revenue_ttm"],
                    "beta": stock["beta"],
                    "institutionalOwnership": stock["institutional_ownership"],
                    "yearFounded": stock["year_founded"],
                    "website": stock["website"],
                    "updatedAt": stock["last_updated"],
                }
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in search_universe: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/{ticker}")
def get_stock(ticker: str):
    """
    Get detailed information for a specific stock
    """
    try:
        stock = db.get_stock(ticker.upper())
        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

        return {
            "ticker": stock["ticker"],
            "name": stock["name"],
            "sector": stock["sector"],
            "industry": stock["industry"],
            "price": stock["price"],
            "change1D": stock["change_1d"],
            "change1W": stock["change_1w"],
            "change1M": stock["change_1m"],
            "change1Y": stock["change_1y"],
            "change5Y": stock["change_5y"],
            "changeYTD": stock["change_ytd"],
            "volume": stock["volume"],
            "high1D": stock["high_1d"],
            "low1D": stock["low_1d"],
            "high1M": stock["high_1m"],
            "low1M": stock["low_1m"],
            "high1Y": stock["high_1y"],
            "low1Y": stock["low_1y"],
            "high5Y": stock["high_5y"],
            "low5Y": stock["low_5y"],
            "peRatio": stock["pe_ratio"],
            "eps": stock["eps"],
            "dividendYield": stock["dividend_yield"],
            "marketCap": stock["market_cap"],
            "sharesOutstanding": stock["shares_outstanding"],
            "netProfitMargin": stock["net_profit_margin"],
            "grossMargin": stock["gross_margin"],
            "roe": stock["roe"],
            "revenue": stock["revenue_ttm"],
            "beta": stock["beta"],
            "institutionalOwnership": stock["institutional_ownership"],
            "debtToEquity": stock["debt_to_equity"],
            "yearFounded": stock["year_founded"],
            "website": stock["website"],
            "city": stock["city"],
            "state": stock["state"],
            "zip": stock["zip"],
            "updatedAt": stock["last_updated"],
            "dataSource": stock["data_source"],
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MARKET DATA ENDPOINTS
# ============================================================================

@app.get("/api/market/sectors")
def get_sector_performance():
    """Calculate sector performance by aggregating stocks in database"""
    try:
        all_stocks = db.get_all_stocks()
        if not all_stocks:
            raise HTTPException(status_code=503, detail="Data not available")
        sectors = {}
        for stock in all_stocks:
            sector = stock["sector"]
            if sector and sector not in ["", "--"]:
                if sector not in sectors:
                    sectors[sector] = {
                        "sector": sector,
                        "change1D": [],
                        "change1W": [],
                        "change1M": [],
                        "count": 0,
                    }
                sectors[sector]["change1D"].append(stock["change_1d"])
                sectors[sector]["change1W"].append(stock["change_1w"])
                sectors[sector]["change1M"].append(stock["change_1m"])
                sectors[sector]["count"] += 1

        result = []
        for sector, data in sectors.items():
            result.append(
                {
                    "sector": sector,
                    "change1D": round(sum(data["change1D"]) / len(data["change1D"]), 2)
                    if data["change1D"]
                    else 0.0,
                    "change1W": round(sum(data["change1W"]) / len(data["change1W"]), 2)
                    if data["change1W"]
                    else 0.0,
                    "change1M": round(sum(data["change1M"]) / len(data["change1M"]), 2)
                    if data["change1M"]
                    else 0.0,
                    "stockCount": data["count"],
                }
            )

        result.sort(key=lambda x: x["change1D"], reverse=True)
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_sector_performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/top-movers")
def get_top_movers(limit: int = 10):
    """Get top gaining and losing stocks today"""
    try:
        gainers = db.get_all_stocks(order_by="change_1d DESC")[:limit]
        losers = db.get_all_stocks(order_by="change_1d ASC")[:limit]
        if not gainers or not losers:
            raise HTTPException(status_code=503, detail="Data not available")

        return {
            "gainers": [
                {
                    "ticker": s["ticker"],
                    "name": s["name"],
                    "price": s["price"],
                    "change1D": s["change_1d"],
                    "volume": s["volume"],
                }
                for s in gainers
            ],
            "losers": [
                {
                    "ticker": s["ticker"],
                    "name": s["name"],
                    "price": s["price"],
                    "change1D": s["change_1d"],
                    "volume": s["volume"],
                }
                for s in losers
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_top_movers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PORTFOLIO & NEWS (existing behavior)
# ============================================================================

@app.get("/api/market-state", response_model=MarketState)
def market_state():
    try:
        result = get_market_state()
        if not result:
            raise HTTPException(status_code=503, detail="Data not available")
        return result
    except FinnhubRateLimitError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        print(f"Error in market_state: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/portfolio", response_model=Portfolio)
def portfolio():
    try:
        result = get_mock_portfolio()
        if not result:
            raise HTTPException(status_code=503, detail="Data not available")
        return result
    except Exception as exc:
        print(f"Error in portfolio: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


news_cache = TTLCache(NEWS_TTL)


@app.get("/api/news", response_model=List[MarketNewsItem])
def news(category: str = "general"):
    try:
        cache_key = f"news:{category}"
        cached, stale = news_cache.get(cache_key)
        if cached and not stale:
            return cached

        news_data = finnhub.get_market_news(category)
        items = []
        for item in news_data[:20]:
            items.append(
                MarketNewsItem(
                    id=str(item.get("id", item.get("datetime", ""))),
                    headline=item.get("headline", ""),
                    summary=item.get("summary", ""),
                    source=item.get("source", ""),
                    publishedAt=datetime.fromtimestamp(item.get("datetime", 0)).isoformat(),
                    category=category,
                    sentiment="neutral",
                    url=item.get("url"),
                )
            )
        news_cache.set(cache_key, items)
        return items
    except FinnhubRateLimitError as exc:
        cached, _ = news_cache.get(f"news:{category}")
        if cached:
            return cached
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        print(f"Error in news: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/news/{ticker}", response_model=List[MarketNewsItem])
def company_news(ticker: str):
    try:
        cache_key = f"news:{ticker.upper()}"
        cached, stale = news_cache.get(cache_key)
        if cached and not stale:
            return cached

        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        news_data = finnhub.get_company_news(ticker.upper(), from_date, to_date)
        items = []
        for item in news_data[:20]:
            items.append(
                MarketNewsItem(
                    id=str(item.get("id", item.get("datetime", ""))),
                    headline=item.get("headline", ""),
                    summary=item.get("summary", ""),
                    source=item.get("source", ""),
                    publishedAt=datetime.fromtimestamp(item.get("datetime", 0)).isoformat(),
                    category="company",
                    sentiment="neutral",
                    tickers=[ticker.upper()],
                    url=item.get("url"),
                )
            )
        news_cache.set(cache_key, items)
        return items
    except FinnhubRateLimitError as exc:
        cached, _ = news_cache.get(f"news:{ticker.upper()}")
        if cached:
            return cached
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        print(f"Error in company_news: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# SYSTEM / MONITORING
# ============================================================================

@app.get("/api/data/status")
def get_data_status():
    """Get database refresh status and data age"""
    try:
        age_minutes = db.get_data_age()
        refresh_history = db.get_refresh_history(limit=5)
        if age_minutes is None and refresh_history is None:
            raise HTTPException(status_code=503, detail="Data not available")
        return {
            "data_age_minutes": round(age_minutes, 2) if age_minutes else None,
            "last_refresh": refresh_history if refresh_history else None,
            "recent_refreshes": refresh_history,
            "total_stocks": len(db.get_all_stocks()),
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_data_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# MACRO DATA ENDPOINTS
# ============================================================================

@app.get("/api/macro/indices")
def get_market_indices():
    """Get current market indices (SPX, NDX, DJI, RUT, VIX)"""
    try:
        indices = db.get_all_indices()
        if not indices:
            raise HTTPException(status_code=503, detail="Data not available")
        return indices
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_market_indices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/macro/indicators")
def get_macro_indicators():
    """Get current macro indicators (yields, CPI, GDP, unemployment, DXY)"""
    try:
        indicators = db.get_all_indicators()
        if not indicators:
            raise HTTPException(status_code=503, detail="Data not available")
        return indicators
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_macro_indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/macro/treasury-history")
def get_treasury_history(days: int = 365):
    """Get 12 months of US 10Y and 2Y treasury yield history for chart"""
    try:
        history = db.get_treasury_history(days=days)
        if not history:
            raise HTTPException(status_code=503, detail="Data not available")
        return history
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_treasury_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/macro/cpi-history")
def get_cpi_history(months: int = 12):
    """Get 12 months of CPI history for chart"""
    try:
        history = db.get_cpi_history(months=months)
        if not history:
            raise HTTPException(status_code=503, detail="Data not available")
        return [
            {
                "date": item["date"],
                "cpi_value": item.get("cpi_value"),
                "mom_change": item.get("mom_change"),
                "yoy_change": item.get("yoy_change"),
            }
            for item in history
        ]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_cpi_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/macro/vix-history")
def get_vix_history(days: int = 365):
    """Get 12 months of VIX history for chart"""
    try:
        history = db.get_vix_history(days=days)
        if not history:
            raise HTTPException(status_code=503, detail="Data not available")
        return [
            {
                "date": item["date"],
                "vix_value": item.get("vix_close"),
                "vix_high": item.get("vix_high"),
                "vix_low": item.get("vix_low"),
            }
            for item in history
        ]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_vix_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/status/summary")
def get_data_status_summary():
    """Get database refresh status (summary)"""
    try:
        age_minutes = db.get_data_age()
        refresh_history = db.get_refresh_history(limit=5)
        if age_minutes is None and refresh_history is None:
            raise HTTPException(status_code=503, detail="Data not available")
        return {
            "data_age_minutes": round(age_minutes, 2) if age_minutes else None,
            "recent_refreshes": refresh_history,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_data_status_summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/macro/alternative-assets")
async def get_alternative_assets():
    """
    Get all alternative assets (crypto, commodities, currencies).
    Returns NULL values when fetch failed; no synthetic data.
    """
    try:
        assets = db.get_all_alternative_assets()
        if not assets:
            raise HTTPException(
                status_code=503,
                detail="Alternative assets table is empty - initialization may have failed",
            )

        failed = [a for a in assets if a.get("fetch_error") is not None]
        if failed:
            print(f"⚠ Warning: {len(failed)} alternative assets have fetch errors")
            for asset in failed:
                print(f"  - {asset['symbol']}: {asset.get('fetch_error')}")

        return assets
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in get_alternative_assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/macro/ticker-all")
async def get_ticker_all():
    """
    Get combined ticker data for global ticker.
    Returns NULLs when data is missing; no fallbacks or synthetic values.
    """
    try:
        ticker_items = []

        # Market indices
        try:
            indices = db.get_all_indices()
            for idx in indices:
                ticker_items.append(
                    {
                        "symbol": idx.get("symbol"),
                        "name": idx.get("name"),
                        "value": idx.get("value"),
                        "change": idx.get("change"),
                        "changePercent": idx.get("change_pct") or idx.get("change_percent"),
                        "category": "equity",
                        "displayFormat": "decimal",
                        "error": None,
                    }
                )
        except Exception as e:
            print(f"❌ Failed to fetch indices for ticker: {e}")

        # Treasury yields (US10Y, US2Y)
        try:
            treasury = db.get_treasury_history(days=2)
            if treasury and len(treasury) >= 2:
                latest = treasury[-1]
                prev = treasury[-2]

                if latest.get("yield_10y") is not None and prev.get("yield_10y") is not None:
                    us10y_change = latest["yield_10y"] - prev["yield_10y"]
                    us10y_change_pct = (us10y_change / prev["yield_10y"]) * 100 if prev["yield_10y"] else None
                    ticker_items.append(
                        {
                            "symbol": "US10Y",
                            "name": "10-Year Treasury",
                            "value": latest["yield_10y"],
                            "change": round(us10y_change, 3) if us10y_change is not None else None,
                            "changePercent": round(us10y_change_pct, 2) if us10y_change_pct is not None else None,
                            "category": "macro",
                            "displayFormat": "percent",
                            "error": None,
                        }
                    )

                if latest.get("yield_2y") is not None and prev.get("yield_2y") is not None:
                    us2y_change = latest["yield_2y"] - prev["yield_2y"]
                    us2y_change_pct = (us2y_change / prev["yield_2y"]) * 100 if prev["yield_2y"] else None
                    ticker_items.append(
                        {
                            "symbol": "US2Y",
                            "name": "2-Year Treasury",
                            "value": latest["yield_2y"],
                            "change": round(us2y_change, 3) if us2y_change is not None else None,
                            "changePercent": round(us2y_change_pct, 2) if us2y_change_pct is not None else None,
                            "category": "macro",
                            "displayFormat": "percent",
                            "error": None,
                        }
                    )
        except Exception as e:
            print(f"❌ Failed to fetch treasury data for ticker: {e}")

        # Alternative assets (crypto, commodities, currencies)
        try:
            alt_assets = db.get_all_alternative_assets()
            for asset in alt_assets:
                ticker_items.append(
                    {
                        "symbol": asset.get("symbol"),
                        "name": asset.get("name"),
                        "value": asset.get("value"),
                        "change": asset.get("change"),
                        "changePercent": asset.get("change_percent"),
                        "category": asset.get("asset_type"),
                        "displayFormat": "currency" if asset.get("asset_type") != "currency" else "decimal",
                        "error": asset.get("fetch_error"),
                    }
                )
        except Exception as e:
            print(f"❌ Failed to fetch alternative assets for ticker: {e}")

        if not ticker_items:
            raise HTTPException(
                status_code=503, detail="No ticker data available - all data sources failed"
            )

        total = len(ticker_items)
        failed = sum(
            1
            for item in ticker_items
            if item.get("error") is not None or item.get("value") is None
        )
        print(f"📊 Ticker endpoint: {total} items ({failed} with errors or nulls)")

        return ticker_items
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in get_ticker_all: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
