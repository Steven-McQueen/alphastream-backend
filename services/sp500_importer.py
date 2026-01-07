import requests
import time
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path so we can import database module
sys.path.append(str(Path(__file__).parent.parent))

from database.db_manager import db


def clean_percent(value: str) -> float:
    """Convert '+12.34%' or '-5.67%' to float 12.34 or -5.67"""
    if not value or value in ['--', 'N/A', '', 'None']:
        return 0.0
    try:
        clean_val = value.replace('%', '').replace('+', '').replace(',', '').strip()
        return float(clean_val)
    except (ValueError, AttributeError):
        return 0.0


def clean_float(value: str) -> float:
    """Convert any string to float, handling commas and invalid data"""
    if not value or value in ['--', 'N/A', '', 'None']:
        return 0.0
    try:
        clean_val = str(value).replace(',', '').strip()
        return float(clean_val)
    except (ValueError, AttributeError):
        return 0.0


def clean_int(value: str) -> int:
    """Convert string to int, handling commas, slashes, and invalid data"""
    if not value or value in ['--', 'N/A', '', 'None']:
        return 0
    try:
        clean_val = str(value).replace(',', '').strip()
        if '/' in clean_val:
            clean_val = clean_val.split('/')[0]
        return int(float(clean_val))
    except (ValueError, AttributeError):
        return 0


def parse_market_cap(value: str) -> float:
    """Convert '405,280.20M' to float 405280.20 (millions)"""
    if not value or value in ['--', 'N/A', '', 'None']:
        return 0.0
    try:
        clean_val = str(value).replace(',', '').strip()
        if 'T' in clean_val:
            return float(clean_val.replace('T', '')) * 1_000_000
        elif 'B' in clean_val:
            return float(clean_val.replace('B', '')) * 1_000
        elif 'M' in clean_val:
            return float(clean_val.replace('M', ''))
        else:
            return float(clean_val)
    except (ValueError, AttributeError):
        return 0.0


def parse_stock_data(raw: dict) -> dict:
    """Parse raw SP500Live data into clean database format"""
    return {
        'ticker': raw.get('ticker', '').strip(),
        'name': raw.get('name', '').strip(),
        'sector': raw.get('sector', ''),
        'industry': raw.get('industry', ''),

        'price': clean_float(raw.get('last', '0')),
        'change_1d': clean_percent(raw.get('change_1d', '0%')),
        'change_1w': clean_percent(raw.get('change_1w', '0%')),
        'change_1m': clean_percent(raw.get('change_1m', '0%')),
        'change_1y': clean_percent(raw.get('change_1y', '0%')),
        'change_5y': clean_percent(raw.get('change_5y', '0%')),
        'change_ytd': clean_percent(raw.get('change_YTD', '0%')),

        'volume': clean_int(raw.get('volume_1d', '0')),

        'high_1d': clean_float(raw.get('high', '0')),
        'low_1d': clean_float(raw.get('low', '0')),
        'high_1m': clean_percent(raw.get('high_1m', '0%')),
        'low_1m': clean_percent(raw.get('low_1m', '0%')),
        'high_1y': clean_percent(raw.get('high_1y', '0%')),
        'low_1y': clean_percent(raw.get('low_1y', '0%')),
        'high_5y': clean_percent(raw.get('high_5y', '0%')),
        'low_5y': clean_percent(raw.get('low_5y', '0%')),

        'pe_ratio': clean_float(raw.get('pe_ratio', '0')),
        'eps': clean_float(raw.get('eps', '0')),
        'dividend_yield': clean_percent(raw.get('dividendyield', '0%')),
        'market_cap': parse_market_cap(raw.get('MarketCap', '0M')),
        'shares_outstanding': parse_market_cap(raw.get('SharesOutstanding', '0M')),

        'net_profit_margin': clean_percent(raw.get('NETPROFTTM', '0%')),
        'gross_margin': clean_percent(raw.get('GROSMGNTTM', '0%')),
        'roe': clean_percent(raw.get('ROETTM', '0%')),
        'revenue_ttm': parse_market_cap(raw.get('revenuettm', '0M')),

        'beta': clean_float(raw.get('beta', '1.0')),
        'institutional_ownership': clean_percent(raw.get('InstitutionalOwnership', '0%')),
        'debt_to_equity': clean_percent(raw.get('DEBTEQTYQ', '0%')) if raw.get('DEBTEQTYQ') not in ['--', 'N/A'] else None,

        'year_founded': clean_int(raw.get('year_founded', '0')),
        'website': raw.get('Url', ''),
        'city': raw.get('city', ''),
        'state': raw.get('state', ''),
        'zip': raw.get('zip', ''),
        'weight': clean_float(raw.get('weight', '0')),

        'last_updated': datetime.now().isoformat(),
        'data_source': 'sp500live',
        'is_sp500': 1
    }


def fetch_and_import_sp500() -> int:
    """Fetch data from SP500Live and import to database"""
    url = "https://www.sp500live.co/sp500_companies.json"

    print(f"Fetching S&P 500 data from {url}...")
    start_time = time.time()

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        raw_data = response.json()

        print(f"Fetched {len(raw_data)} stocks")

        parsed_stocks = []
        for ticker, stock_data in raw_data.items():
          try:
            stock_data['ticker'] = ticker
            parsed = parse_stock_data(stock_data)
            if parsed['ticker']:
              parsed_stocks.append(parsed)
          except Exception as e:
            print(f"Error parsing {ticker}: {e}")

        count = db.insert_stocks_bulk(parsed_stocks)

        duration = time.time() - start_time
        db.log_refresh(
            stocks_updated=count,
            data_source='sp500live',
            success=True,
            duration=duration
        )

        print(f"Import complete in {duration:.2f}s")
        return count

    except Exception as e:
        duration = time.time() - start_time
        db.log_refresh(
            stocks_updated=0,
            data_source='sp500live',
            success=False,
            duration=duration,
            error_msg=str(e)
        )
        print(f"Import failed: {e}")
        return 0

