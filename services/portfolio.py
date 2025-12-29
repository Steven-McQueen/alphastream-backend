from models import Portfolio, PortfolioHolding
from datetime import datetime

def get_mock_portfolio() -> Portfolio:
    """Return mock portfolio for testing."""
    return Portfolio(
        id="portfolio-1",
        name="Main Portfolio",
        holdings=[
            PortfolioHolding(
                ticker="AAPL",
                name="Apple Inc.",
                sector="Technology",
                shares=50,
                avgCostBasis=150.0,
                currentPrice=180.0,
                marketValue=9000.0,
                weight=30.0,
                unrealizedPnL=1500.0,
                unrealizedPnLPercent=20.0,
                dailyPnL=100.0,
                dailyPnLPercent=1.1,
                strategy="Core Quality"
            ),
            PortfolioHolding(
                ticker="MSFT",
                name="Microsoft Corp.",
                sector="Technology",
                shares=30,
                avgCostBasis=300.0,
                currentPrice=350.0,
                marketValue=10500.0,
                weight=35.0,
                unrealizedPnL=1500.0,
                unrealizedPnLPercent=16.7,
                dailyPnL=150.0,
                dailyPnLPercent=1.45,
                strategy="Core Quality"
            ),
        ],
        totalValue=30000.0,
        totalCost=25000.0,
        cash=500.0,
        ytdReturn=12.5,
        dailyPnL=250.0,
        dailyPnLPercent=0.85,
        totalUnrealizedPnL=5000.0,
        volatility=15.2,
        sharpeRatio=1.2,
        beta=1.05,
        lastUpdated=datetime.utcnow().isoformat()
    )
