from datetime import datetime, timedelta
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from clients.finnhub_client import FinnhubRateLimitError, finnhub
from config import NEWS_TTL
from models import MarketNewsItem, MarketState, Portfolio, Stock
from services.market import get_market_state
from services.portfolio import get_mock_portfolio
from services.universe import get_core_universe, get_stock_detail, search_symbol
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


@app.get("/")
def root():
    return {"name": "AlphaStream API", "version": "0.1.0", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/universe/core", response_model=List[Stock])
def universe_core():
    try:
        return get_core_universe()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/universe/search", response_model=List[Stock])
def universe_search(q: str = Query(..., min_length=1)):
    try:
        return search_symbol(q)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/stock/{ticker}", response_model=Stock)
def stock_detail(ticker: str):
    stock = get_stock_detail(ticker.upper())
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")
    return stock


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
