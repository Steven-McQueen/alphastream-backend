from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Sector = str
CatalystTag = str
StrategyTag = Literal["Core Quality", "Tactical", "Macro Bet", "Income", "Growth"]
MarketRegime = Literal["Risk-On", "Risk-Off", "Neutral"]
MarketStatus = Literal["Open", "Closed", "Pre-Market", "After-Hours"]


class Stock(BaseModel):
    ticker: str
    name: str
    sector: Sector
    industry: str
    marketCap: float
    price: float

    change1D: float
    change1W: float = 0.0
    change1M: float = 0.0
    changeYTD: float = 0.0
    change1Y: float = 0.0
    change5Y: float = 0.0

    peRatio: Optional[float] = None
    forwardPE: Optional[float] = None
    pegRatio: Optional[float] = None
    priceToBook: Optional[float] = None
    evToEbitda: Optional[float] = None
    evToSales: Optional[float] = None
    dividendYield: Optional[float] = None
    beta: Optional[float] = None
    eps: Optional[float] = None

    volume: float = 0.0
    avgVolume: float = 0.0

    grossMargin: float = 0.0
    operatingMargin: float = 0.0
    netMargin: float = 0.0
    roe: float = 0.0
    roic: float = 0.0
    revenueGrowth: float = 0.0
    earningsGrowth: float = 0.0
    fcfYield: float = 0.0

    catalysts: List[CatalystTag] = Field(default_factory=list)
    weight: float = 0.0
    updatedAt: str


class MarketIndex(BaseModel):
    symbol: str
    name: str
    value: float
    change: float
    changePercent: float


class CryptoPrice(BaseModel):
    symbol: str
    name: str
    price: float
    change24h: float
    changePercent24h: float
    marketCap: float


class MacroIndicator(BaseModel):
    name: str
    value: float
    previousValue: float
    change: float
    unit: str
    lastUpdated: str


class SectorPerformance(BaseModel):
    sector: Sector
    change1D: float
    change1W: float = 0.0
    change1M: float = 0.0
    change1Y: float = 0.0


class MarketState(BaseModel):
    status: MarketStatus
    regime: MarketRegime
    regimeProbabilities: Dict[str, float]
    indices: List[MarketIndex]
    cryptoPrices: List[CryptoPrice]
    macroIndicators: List[MacroIndicator]
    sectorPerformance: List[SectorPerformance]
    lastUpdated: str


class PortfolioHolding(BaseModel):
    ticker: str
    name: str
    sector: Sector
    shares: float
    avgCostBasis: float
    currentPrice: float
    marketValue: float
    weight: float
    unrealizedPnL: float
    unrealizedPnLPercent: float
    dailyPnL: float
    dailyPnLPercent: float
    strategy: StrategyTag


class Portfolio(BaseModel):
    id: str
    name: str
    holdings: List[PortfolioHolding]
    totalValue: float
    totalCost: float
    cash: float
    ytdReturn: float
    dailyPnL: float
    dailyPnLPercent: float
    totalUnrealizedPnL: float
    volatility: float
    sharpeRatio: float
    beta: float
    lastUpdated: str


class MarketNewsItem(BaseModel):
    id: str
    headline: str
    summary: str
    source: str
    publishedAt: str
    category: str
    sentiment: Literal["bullish", "bearish", "neutral"] = "neutral"
    tickers: List[str] = Field(default_factory=list)
    url: Optional[str] = None
