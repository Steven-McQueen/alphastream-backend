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
    ],
    allow_credentials=True,
    allow_methods=[""],
    allow_headers=[""],
)

@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup"""
    start_scheduler_background()


# ============================================================================
# ROOT / HEALTH
# ============================================================================

@app.get("/")
def root():
    return {"name": "AlphaStream API", "version": "0.1.0", "status": "running"}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "database": "connected",
    }


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
    except Exception as e:
        print(f"❌ Error in get_universe_core: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/universe/search")
def search_universe(q: str = Query(..., min_length=1)):
    """
    Search stocks by ticker or name
    """
    try:
        stocks = db.search_stocks(q)
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
    except Exception as e:
        print(f"❌ Error in search_universe: {e}")
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
        print(f"❌ Error in get_stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MARKET DATA ENDPOINTS
# ============================================================================

@app.get("/api/market/sectors")
def get_sector_performance():
    """Calculate sector performance by aggregating stocks in database"""
    try:
        all_stocks = db.get_all_stocks()
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
    except Exception as e:
        print(f"❌ Error in get_sector_performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/top-movers")
def get_top_movers(limit: int = 10):
    """Get top gaining and losing stocks today"""
    try:
        gainers = db.get_all_stocks(order_by="change_1d DESC")[:limit]
        losers = db.get_all_stocks(order_by="change_1d ASC")[:limit]

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
    except Exception as e:
        print(f"❌ Error in get_top_movers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PORTFOLIO & NEWS (existing behavior)
# ============================================================================

@app.get("/api/market-state", response_model=MarketState)
def market_state():
    try:
        return get_market_state()
    except FinnhubRateLimitError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/portfolio", response_model=Portfolio)
def portfolio():
    try:
        return get_mock_portfolio()
    except Exception as exc:
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
        return {
            "data_age_minutes": round(age_minutes, 2) if age_minutes else None,
            "last_refresh": refresh_history if refresh_history else None,
            "recent_refreshes": refresh_history,
            "total_stocks": len(db.get_all_stocks()),
        }
    except Exception as e:
        print(f"❌ Error in get_data_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/status")
def get_data_status():
    """Get database refresh status"""
    from database.db_manager import db

    age_minutes = db.get_data_age()
    refresh_history = db.get_refresh_history(limit=5)

    return {
        "data_age_minutes": round(age_minutes, 2) if age_minutes else None,
        "recent_refreshes": refresh_history,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
