"""Fetch and import macro economic data into database"""
import yfinance as yf
from fredapi import Fred
import pandas as pd
from datetime import datetime, timedelta
from database.db_manager import db
from config import FRED_API_KEY
import requests


# Initialize FRED client
try:
    fred = Fred(api_key=FRED_API_KEY) if FRED_API_KEY else None
    if fred:
        print("FRED API client initialized")
    else:
        print("FRED API key not found in environment variables")
except Exception as e:
    print(f"FRED API initialization failed: {e}")
    fred = None


# ============================================================================
# CURRENT VALUES (REAL-TIME)
# ============================================================================

def fetch_and_import_indices():
  """Fetch current market indices from yfinance"""
  print("Fetching market indices...")

  indices = {
    'SPX': ('^GSPC', 'S&P 500'),
    'NDX': ('^IXIC', 'Nasdaq 100'),
    'DJI': ('^DJI', 'Dow Jones'),
    'RUT': ('^RUT', 'Russell 2000'),
    'VIX': ('^VIX', 'VIX')
  }

  count = 0
  for symbol, (ticker_symbol, name) in indices.items():
    try:
      ticker = yf.Ticker(ticker_symbol)
      hist = ticker.history(period='5d')

      if len(hist) < 2:
        print(f"Insufficient data for {symbol}")
        continue

      current = float(hist['Close'].iloc[-1])
      previous = float(hist['Close'].iloc[-2])
      change = current - previous
      change_pct = (change / previous) * 100

      db.insert_or_update_index(
        symbol=symbol,
        name=name,
        value=round(current, 2),
        change=round(change, 2),
        change_pct=round(change_pct, 2)
      )
      count += 1

    except Exception as e:
      print(f"Error fetching {symbol}: {e}")
      continue

  print(f"Imported {count}/5 market indices")
  return count


def fetch_and_import_macro_indicators():
  """Fetch current macro indicators from FRED and yfinance"""
  if not fred:
    print("Skipping macro indicators - FRED API not configured")
    return 0

  print("Fetching macro indicators...")

  indicators = {
    'US_10Y_YIELD': ('DGS10', 'US 10Y Treasury Yield', '%'),
    'US_2Y_YIELD': ('DGS2', 'US 2Y Treasury Yield', '%'),
    'FED_FUNDS_RATE': ('DFF', 'Fed Funds Rate', '%'),
    'UNEMPLOYMENT': ('UNRATE', 'Unemployment Rate', '%'),
    'CPI_YOY': ('CPIAUCSL', 'CPI (YoY)', '%'),
    'CORE_PCE_YOY': ('PCEPILFE', 'Core PCE (YoY)', '%'),
    'GDP_GROWTH': ('A191RL1Q225SBEA', 'GDP Growth (QoQ Annual)', '%'),
  }

  count = 0
  for indicator_id, (series_id, name, unit) in indicators.items():
    try:
      data = fred.get_series(series_id, observation_start='2023-01-01')

      if len(data) == 0:
        print(f"No data for {indicator_id}")
        continue

      current_value = float(data.iloc[-1])

      # Calculate YoY for CPI and Core PCE
      if 'YOY' in indicator_id and len(data) >= 13:
        year_ago_value = float(data.iloc[-13])
        current_value = ((current_value - year_ago_value) / year_ago_value) * 100

      # Calculate change
      change = 0
      if len(data) >= 2:
        previous_value = float(data.iloc[-2])
        if 'YOY' in indicator_id and len(data) >= 14:
          year_ago_prev = float(data.iloc[-14])
          previous_value = ((previous_value - year_ago_prev) / year_ago_prev) * 100
        change = current_value - previous_value

      db.insert_or_update_indicator(
        indicator_id=indicator_id,
        name=name,
        value=round(current_value, 2),
        change=round(change, 2) if change else None,
        unit=unit
      )
      count += 1

    except Exception as e:
      print(f"Error fetching {indicator_id}: {e}")
      continue

  # DXY from yfinance
  try:
    dxy = yf.Ticker('DX-Y.NYB')
    dxy_hist = dxy.history(period='5d')
    if len(dxy_hist) >= 2:
      current_dxy = float(dxy_hist['Close'].iloc[-1])
      previous_dxy = float(dxy_hist['Close'].iloc[-2])
      change_dxy = current_dxy - previous_dxy

      db.insert_or_update_indicator(
        indicator_id='DXY',
        name='Dollar Index (DXY)',
        value=round(current_dxy, 2),
        change=round(change_dxy, 2),
        unit='index'
      )
      count += 1
  except Exception as e:
    print(f"Error fetching DXY: {e}")

  print(f"Imported {count}/8 macro indicators")
  return count


# ============================================================================
# HISTORICAL DATA (12 MONTHS / 365 DAYS)
# ============================================================================

def fetch_and_import_treasury_history():
  """Fetch 12 months of daily US 10Y and 2Y Treasury yields"""
  if not fred:
    print("Skipping treasury history - FRED API not configured")
    return 0

  print("Fetching 12 months of treasury yield history...")

  try:
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    data_10y = fred.get_series('DGS10', observation_start=start_date)
    data_2y = fred.get_series('DGS2', observation_start=start_date)

    count = 0
    for date in data_10y.index:
      yield_10y = float(data_10y.loc[date]) if not pd.isna(data_10y.loc[date]) else None
      yield_2y = float(data_2y.loc[date]) if date in data_2y.index and not pd.isna(data_2y.loc[date]) else None

      if yield_10y is not None:
        db.insert_treasury_history(
          date=date.strftime('%Y-%m-%d'),
          yield_10y=round(yield_10y, 2),
          yield_2y=round(yield_2y, 2) if yield_2y else None
        )
        count += 1

    print(f"Imported {count} days of treasury history")
    return count
  except Exception as e:
    print(f"Error fetching treasury history: {e}")
    return 0


def fetch_and_import_cpi_history():
    """Fetch 12 months of CPI data"""
    if not fred:
        print("Skipping CPI history - FRED API not configured")
        return 0
    
    print("Fetching 12 months of CPI history...")
    
    try:
        # Get 36 months to ensure we have enough data after cleaning
        start_date = (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d')
        data_cpi = fred.get_series('CPIAUCSL', observation_start=start_date)
        
        print(f"  Retrieved {len(data_cpi)} CPI data points from FRED")
        
        # Remove any NaN values
        data_cpi_clean = data_cpi.dropna()
        print(f"  After removing NaN: {len(data_cpi_clean)} valid data points")
        
        if len(data_cpi_clean) < 13:
            print(f"  Error: Insufficient CPI data (need at least 13, got {len(data_cpi_clean)})")
            return 0
        
        # Get only the last 24 months of clean data (to calculate 12 months with YoY)
        data_cpi_recent = data_cpi_clean.iloc[-24:]
        
        count = 0
        errors = 0
        
        # Start from index 12 to ensure we can calculate YoY
        for i in range(12, len(data_cpi_recent)):
            try:
                date = data_cpi_recent.index[i]
                cpi_value = float(data_cpi_recent.iloc[i])
                
                # Double-check value is valid
                if pd.isna(cpi_value) or cpi_value <= 0:
                    print(f"  Skipping invalid CPI value at {date}: {cpi_value}")
                    errors += 1
                    continue
                
                # Month-over-month change
                prev_value = float(data_cpi_recent.iloc[i-1])
                if pd.isna(prev_value) or prev_value <= 0:
                    mom_change = None
                else:
                    mom_change = ((cpi_value - prev_value) / prev_value) * 100
                
                # Year-over-year change
                year_ago_value = float(data_cpi_recent.iloc[i-12])
                if pd.isna(year_ago_value) or year_ago_value <= 0:
                    yoy_change = None
                else:
                    yoy_change = ((cpi_value - year_ago_value) / year_ago_value) * 100
                
                # Insert into database
                db.insert_cpi_history(
                    date=date.strftime('%Y-%m-%d'),
                    cpi_value=round(cpi_value, 2),
                    mom_change=round(mom_change, 2) if mom_change is not None else None,
                    yoy_change=round(yoy_change, 2) if yoy_change is not None else None
                )
                count += 1
                
            except Exception as e:
                print(f"  Error processing CPI data point {i}: {e}")
                errors += 1
                continue
        
        if errors > 0:
            print(f"  Warning: {errors} CPI data points skipped due to errors")
        
        print(f"Imported {count} months of CPI history")
        return count
        
    except Exception as e:
        print(f"Error fetching CPI history: {e}")
        import traceback
        traceback.print_exc()
        return 0





def fetch_and_import_vix_history():
  """Fetch 12 months of daily VIX data"""
  print("Fetching 12 months of VIX history...")
  try:
    vix = yf.Ticker('^VIX')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    hist = vix.history(start=start_date, end=end_date)

    count = 0
    for date, row in hist.iterrows():
      db.insert_vix_history(
        date=date.strftime('%Y-%m-%d'),
        vix_close=round(float(row['Close']), 2),
        vix_high=round(float(row['High']), 2),
        vix_low=round(float(row['Low']), 2)
      )
      count += 1

    print(f"Imported {count} days of VIX history")
    return count
  except Exception as e:
    print(f"Error fetching VIX history: {e}")
    return 0


# ============================================================================
# REFRESH ALL MACRO DATA (called by scheduler)
# ============================================================================

def refresh_all_macro_data():
  """Refresh current values only (not historical data)."""
  indices_count = fetch_and_import_indices()
  indicators_count = fetch_and_import_macro_indicators()
  assets_count = fetch_and_import_alternative_assets()
  return {
    'indices': indices_count,
    'indicators': indicators_count,
    'assets': assets_count,
  }


def initialize_all_macro_data():
  """Initialize both current and historical data (called once on setup)"""
  print("\n" + "=" * 60)
  print("INITIALIZING MACRO DATA")
  print("=" * 60)

  indices_count = fetch_and_import_indices()
  indicators_count = fetch_and_import_macro_indicators()
  treasury_count = fetch_and_import_treasury_history()
  cpi_count = fetch_and_import_cpi_history()
  vix_count = fetch_and_import_vix_history()
  assets_count = fetch_and_import_alternative_assets()

  print("\n" + "=" * 60)
  print("MACRO DATA INITIALIZATION COMPLETE")
  print(f"   Current: {indices_count} indices, {indicators_count} indicators")
  print(f"   Current Alt Assets: {assets_count} alternative assets")
  print(f"   Historical: {treasury_count} treasury days, {cpi_count} CPI months, {vix_count} VIX days")
  print("=" * 60 + "\n")

  return {
    'indices': indices_count,
    'indicators': indicators_count,
    'assets': assets_count,
    'treasury_days': treasury_count,
    'cpi_months': cpi_count,
    'vix_days': vix_count
  }


COINGECKO_API = "https://api.coingecko.com/api/v3"

def fetch_crypto_from_coingecko(coin_id: str) -> dict:
  """
  Fetch crypto price from CoinGecko (fallback for yfinance).
  Returns: {'value': float, 'change_24h': float|None, 'change_percent_24h': float}
  """
  try:
    url = f"{COINGECKO_API}/simple/price"
    params = {
      'ids': coin_id,
      'vs_currencies': 'usd',
      'include_24hr_change': 'true'
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    if coin_id not in data:
      raise ValueError(f"CoinGecko returned no data for {coin_id}")
    coin_data = data[coin_id]
    return {
      'value': coin_data['usd'],
      'change_24h': None,
      'change_percent_24h': coin_data.get('usd_24h_change', 0)
    }
  except Exception as e:
    raise Exception(f"CoinGecko fetch failed: {e}")


def fetch_and_import_alternative_assets():
  """
  Fetch crypto, commodities, and currencies with intelligent fallbacks.
  Primary: yfinance -> Secondary: CoinGecko/FRED -> NULL if all fail.
  """
  print("\n" + "=" * 60)
  print("FETCHING ALTERNATIVE ASSETS (with fallbacks)")
  print("=" * 60)

  success_count = 0
  fail_count = 0

  # --------------------------------------------------------------------------
  # Helpers
  # --------------------------------------------------------------------------
  def store_failure(sym, name, asset_type, msg):
    nonlocal fail_count
    print(f"❌ All sources failed: {msg}")
    db.insert_or_update_alternative_asset(
      symbol=sym,
      name=name,
      asset_type=asset_type,
      value=None,
      change=None,
      change_percent=None,
      fetch_error=msg,
    )
    fail_count += 1

  # --------------------------------------------------------------------------
  # BTC
  # --------------------------------------------------------------------------
  symbol = 'BTC'
  try:
    print(f"Fetching {symbol}... ", end="")
    success = False

    # Primary: yfinance
    try:
      ticker = yf.Ticker('BTC-USD')
      hist = ticker.history(period='5d')
      if len(hist) >= 2:
        current = float(hist['Close'].iloc[-1])
        previous = float(hist['Close'].iloc[-2])
        change = current - previous
        change_pct = (change / previous) * 100
        db.insert_or_update_alternative_asset(
          symbol=symbol, name='Bitcoin', asset_type='crypto',
          value=round(current, 2), change=round(change, 2),
          change_percent=round(change_pct, 2), fetch_error=None
        )
        print(f"✅ yfinance: {current:,.2f} ({change_pct:+.2f}%)")
        success_count += 1
        success = True
    except Exception as e:
      print(f"⚠ yfinance failed ({e}), trying CoinGecko... ", end="")

    if not success:
      # Fallback: CoinGecko
      cg_data = fetch_crypto_from_coingecko('bitcoin')
      db.insert_or_update_alternative_asset(
        symbol=symbol, name='Bitcoin', asset_type='crypto',
        value=round(cg_data['value'], 2),
        change=None,
        change_percent=round(cg_data['change_percent_24h'], 2),
        fetch_error=None
      )
      print(f"✅ CoinGecko: {cg_data['value']:,.2f} ({cg_data['change_percent_24h']:+.2f}%)")
      success_count += 1

  except Exception as e:
    store_failure(symbol, 'Bitcoin', 'crypto', f"yfinance + CoinGecko failed: {e}")

  # --------------------------------------------------------------------------
  # ETH
  # --------------------------------------------------------------------------
  symbol = 'ETH'
  try:
    print(f"Fetching {symbol}... ", end="")
    success = False

    try:
      ticker = yf.Ticker('ETH-USD')
      hist = ticker.history(period='5d')
      if len(hist) >= 2:
        current = float(hist['Close'].iloc[-1])
        previous = float(hist['Close'].iloc[-2])
        change = current - previous
        change_pct = (change / previous) * 100
        db.insert_or_update_alternative_asset(
          symbol=symbol, name='Ethereum', asset_type='crypto',
          value=round(current, 2), change=round(change, 2),
          change_percent=round(change_pct, 2), fetch_error=None
        )
        print(f"✅ yfinance: {current:,.2f} ({change_pct:+.2f}%)")
        success_count += 1
        success = True
    except Exception as e:
      print(f"⚠ yfinance failed ({e}), trying CoinGecko... ", end="")

    if not success:
      cg_data = fetch_crypto_from_coingecko('ethereum')
      db.insert_or_update_alternative_asset(
        symbol=symbol, name='Ethereum', asset_type='crypto',
        value=round(cg_data['value'], 2),
        change=None,
        change_percent=round(cg_data['change_percent_24h'], 2),
        fetch_error=None
      )
      print(f"✅ CoinGecko: {cg_data['value']:,.2f} ({cg_data['change_percent_24h']:+.2f}%)")
      success_count += 1

  except Exception as e:
    store_failure(symbol, 'Ethereum', 'crypto', f"yfinance + CoinGecko failed: {e}")

  # --------------------------------------------------------------------------
  # GOLD
  # --------------------------------------------------------------------------
  symbol = 'GOLD'
  try:
    print(f"Fetching {symbol}... ", end="")
    success = False

    try:
      ticker = yf.Ticker('GC=F')
      hist = ticker.history(period='5d')
      if len(hist) >= 2:
        current = float(hist['Close'].iloc[-1])
        previous = float(hist['Close'].iloc[-2])
        change = current - previous
        change_pct = (change / previous) * 100
        db.insert_or_update_alternative_asset(
          symbol=symbol, name='Gold Futures', asset_type='commodity',
          value=round(current, 2), change=round(change, 2),
          change_percent=round(change_pct, 2), fetch_error=None
        )
        print(f"✅ yfinance: {current:,.2f} ({change_pct:+.2f}%)")
        success_count += 1
        success = True
    except Exception as e:
      print(f"⚠ yfinance failed ({e}), trying FRED... ", end="")

    if not success:
      if not fred:
        raise Exception("FRED API not configured")
      start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
      gold_data = fred.get_series('GOLDPMGBD228NLBM', observation_start=start_date)
      if len(gold_data) < 2:
        raise Exception(f"Insufficient FRED data: {len(gold_data)} points")
      current = float(gold_data.iloc[-1])
      previous = float(gold_data.iloc[-2])
      change = current - previous
      change_pct = (change / previous) * 100
      db.insert_or_update_alternative_asset(
        symbol=symbol, name='Gold Spot', asset_type='commodity',
        value=round(current, 2), change=round(change, 2),
        change_percent=round(change_pct, 2), fetch_error=None
      )
      print(f"✅ FRED: {current:,.2f} ({change_pct:+.2f}%)")
      success_count += 1

  except Exception as e:
    store_failure(symbol, 'Gold', 'commodity', f"yfinance + FRED failed: {e}")

  # --------------------------------------------------------------------------
  # OIL
  # --------------------------------------------------------------------------
  symbol = 'OIL'
  try:
    print(f"Fetching {symbol}... ", end="")
    success = False

    try:
      ticker = yf.Ticker('CL=F')
      hist = ticker.history(period='5d')
      if len(hist) >= 2:
        current = float(hist['Close'].iloc[-1])
        previous = float(hist['Close'].iloc[-2])
        change = current - previous
        change_pct = (change / previous) * 100
        db.insert_or_update_alternative_asset(
          symbol=symbol, name='WTI Crude Oil', asset_type='commodity',
          value=round(current, 2), change=round(change, 2),
          change_percent=round(change_pct, 2), fetch_error=None
        )
        print(f"✅ yfinance: {current:,.2f} ({change_pct:+.2f}%)")
        success_count += 1
        success = True
    except Exception as e:
      print(f"⚠ yfinance failed ({e}), trying FRED... ", end="")

    if not success:
      if not fred:
        raise Exception("FRED API not configured")
      start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
      oil_data = fred.get_series('DCOILWTICO', observation_start=start_date)
      if len(oil_data) < 2:
        raise Exception(f"Insufficient FRED data: {len(oil_data)} points")
      current = float(oil_data.iloc[-1])
      previous = float(oil_data.iloc[-2])
      change = current - previous
      change_pct = (change / previous) * 100
      db.insert_or_update_alternative_asset(
        symbol=symbol, name='WTI Crude Oil Spot', asset_type='commodity',
        value=round(current, 2), change=round(change, 2),
        change_percent=round(change_pct, 2), fetch_error=None
      )
      print(f"✅ FRED: {current:,.2f} ({change_pct:+.2f}%)")
      success_count += 1

  except Exception as e:
    store_failure(symbol, 'WTI Crude Oil', 'commodity', f"yfinance + FRED failed: {e}")

  # --------------------------------------------------------------------------
  # NOK/USD
  # --------------------------------------------------------------------------
  symbol = 'NOKUSD'
  try:
    print(f"Fetching {symbol}... ", end="")
    success = False

    try:
      ticker = yf.Ticker('NOKUSD=X')
      hist = ticker.history(period='5d')
      if len(hist) >= 2:
        current = float(hist['Close'].iloc[-1])
        previous = float(hist['Close'].iloc[-2])
        change = current - previous
        change_pct = (change / previous) * 100 if previous else None
        db.insert_or_update_alternative_asset(
          symbol=symbol, name='Norwegian Krone', asset_type='currency',
          value=round(current, 4), change=round(change, 4) if change_pct is not None else None,
          change_percent=round(change_pct, 2) if change_pct is not None else None,
          fetch_error=None
        )
        print(f"✅ yfinance: {current:.4f} ({change_pct:+.2f}%)")
        success_count += 1
        success = True
    except Exception as e:
      print(f"⚠ yfinance failed ({e}), trying FRED... ", end="")

    if not success:
      if not fred:
        raise Exception("FRED API not configured")
      start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
      nok_data = fred.get_series('DEXNOUS', observation_start=start_date)
      if len(nok_data) < 2:
        raise Exception(f"Insufficient FRED data: {len(nok_data)} points")
      current = float(nok_data.iloc[-1])
      previous = float(nok_data.iloc[-2])
      change = current - previous
      change_pct = (change / previous) * 100 if previous else None
      db.insert_or_update_alternative_asset(
        symbol=symbol, name='Norwegian Krone', asset_type='currency',
        value=round(current, 4), change=round(change, 4) if change_pct is not None else None,
        change_percent=round(change_pct, 2) if change_pct is not None else None,
        fetch_error=None
      )
      print(f"✅ FRED: {current:.4f} ({change_pct:+.2f}%)")
      success_count += 1

  except Exception as e:
    store_failure(symbol, 'Norwegian Krone', 'currency', f"yfinance + FRED failed: {e}")

  print("=" * 60)
  print(f"✅ Success: {success_count}/5 assets")
  if fail_count > 0:
    print(f"❌ Failed: {fail_count}/5 assets (all sources exhausted)")
  print("=" * 60)

  return success_count


def initialize_alternative_assets():
  """Initialize alternative assets table during database setup."""
  print("\n" + "=" * 60)
  print("INITIALIZING ALTERNATIVE ASSETS")
  print("=" * 60)

  count = fetch_and_import_alternative_assets()
  return {'assets': count}

