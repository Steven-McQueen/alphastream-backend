import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
# Load .env file explicitly from backend directory
dotenv_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=dotenv_path)

# API keys
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "") #Macro data API key

# Interactive Brokers (future)
IB_HOST = os.getenv("IB_HOST", "127.0.0.1")
IB_PORT = int(os.getenv("IB_PORT", "7497"))
IB_CLIENT_ID = int(os.getenv("IB_CLIENT_ID", "1"))

# Cache TTLs (seconds)
UNIVERSE_TTL = 3600  # 1 hour
STOCK_TTL = 300      # 5 minutes
MARKET_TTL = 600     # 10 minutes
NEWS_TTL = 1800      # 30 minutes

# Rate limiting
FINNHUB_RATE_LIMIT = 60  # calls per minute (free tier)

# Fallback data
FALLBACK_FILE = DATA_DIR / "sp500_fallback.json"

# CORS
CORS_ORIGINS = [
    "http://localhost:5173",
]

# ============================================================================
# MACRO DATA CONFIGURATION
# ============================================================================
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# Cache TTL
CACHE_TTL_MACRO = 300  # 5 minutes for current values