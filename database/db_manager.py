import sqlite3
import threading
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta


class DatabaseManager:
  """Manages SQLite database for stock data caching"""

  def __init__(self, db_path: str = "data/stocks.db"):
      self.db_path = db_path
      Path(db_path).parent.mkdir(parents=True, exist_ok=True)
      self._local = threading.local()  # ADD THIS LINE
  
  def connect(self):
      """Get thread-local connection"""
      # REPLACE OLD connect() METHOD WITH THIS:
      if not hasattr(self._local, 'connection') or self._local.connection is None:
          self._local.connection = sqlite3.connect(
              self.db_path,
              check_same_thread=False,
              timeout=30.0
          )
          self._local.connection.row_factory = sqlite3.Row
      return self._local.connection
  
  def close(self):
      """Close thread-local connection"""
      # REPLACE OLD close() METHOD WITH THIS:
      if hasattr(self._local, 'connection') and self._local.connection:
          self._local.connection.close()
          self._local.connection = None

  def init_database(self):
    """Initialize database with schema"""
    schema_path = Path(__file__).parent / "schema.sql"

    with open(schema_path, 'r', encoding='utf-8') as f:
      schema = f.read()

    conn = self.connect()
    conn.executescript(schema)
    conn.commit()
    print(f"Database initialized at {self.db_path}")
    self.close()

  def insert_stocks_bulk(self, stocks: List[dict]) -> int:
    """Insert multiple stocks efficiently"""
    conn = self.connect()
    cursor = conn.cursor()
    success_count = 0

    try:
      for stock in stocks:
        try:
          cursor.execute("""
            INSERT OR REPLACE INTO stocks (
              ticker, name, sector, industry,
              price, change_1d, change_1w, change_1m, change_1y, change_5y, change_ytd,
              volume,
              high_1d, low_1d, high_1m, low_1m, high_1y, low_1y, high_5y, low_5y,
              pe_ratio, eps, dividend_yield, market_cap, shares_outstanding,
              net_profit_margin, gross_margin, roe, revenue_ttm,
              beta, institutional_ownership, debt_to_equity,
              year_founded, website, city, state, zip, weight,
              last_updated, data_source, is_sp500
            ) VALUES (
              :ticker, :name, :sector, :industry,
              :price, :change_1d, :change_1w, :change_1m, :change_1y, :change_5y, :change_ytd,
              :volume,
              :high_1d, :low_1d, :high_1m, :low_1m, :high_1y, :low_1y, :high_5y, :low_5y,
              :pe_ratio, :eps, :dividend_yield, :market_cap, :shares_outstanding,
              :net_profit_margin, :gross_margin, :roe, :revenue_ttm,
              :beta, :institutional_ownership, :debt_to_equity,
              :year_founded, :website, :city, :state, :zip, :weight,
              :last_updated, :data_source, :is_sp500
            )
          """, stock)
          success_count += 1
        except Exception as e:
          print(f"Error inserting {stock.get('ticker')}: {e}")

      conn.commit()
      print(f"Inserted/updated {success_count}/{len(stocks)} stocks")
      return success_count

    finally:
      self.close()

  def get_stock(self, ticker: str) -> Optional[dict]:
    """Get a single stock by ticker"""
    conn = self.connect()
    cursor = conn.cursor()

    try:
      cursor.execute("SELECT * FROM stocks WHERE ticker = ?", (ticker,))
      row = cursor.fetchone()
      return dict(row) if row else None
    finally:
      self.close()

  def get_all_stocks(self, order_by: str = "market_cap DESC") -> List[dict]:
    """Get all stocks"""
    conn = self.connect()
    cursor = conn.cursor()

    try:
      cursor.execute(f"SELECT * FROM stocks ORDER BY {order_by}")
      rows = cursor.fetchall()
      return [dict(row) for row in rows]
    finally:
      self.close()

  def search_stocks(self, query: str) -> List[dict]:
    """Search stocks by ticker or name"""
    conn = self.connect()
    cursor = conn.cursor()

    try:
      search_term = f"%{query.upper()}%"
      cursor.execute("""
        SELECT * FROM stocks 
        WHERE ticker LIKE ? OR UPPER(name) LIKE ?
        ORDER BY market_cap DESC
        LIMIT 50
      """, (search_term, search_term))

      rows = cursor.fetchall()
      return [dict(row) for row in rows]
    finally:
      self.close()

  def get_stocks_by_sector(self, sector: str) -> List[dict]:
    """Get all stocks in a sector"""
    conn = self.connect()
    cursor = conn.cursor()

    try:
      cursor.execute("""
        SELECT * FROM stocks 
        WHERE sector = ?
        ORDER BY market_cap DESC
      """, (sector,))

      rows = cursor.fetchall()
      return [dict(row) for row in rows]
    finally:
      self.close()

  def log_refresh(self, stocks_updated: int, data_source: str,
                  success: bool, duration: float, error_msg: Optional[str] = None):
    """Log a data refresh event"""
    conn = self.connect()
    cursor = conn.cursor()

    try:
      cursor.execute("""
        INSERT INTO refresh_log (
          stocks_updated, data_source, success, error_message, duration_seconds
        ) VALUES (?, ?, ?, ?, ?)
      """, (stocks_updated, data_source, success, error_msg, duration))

      conn.commit()
    finally:
      self.close()

  def get_data_age(self) -> Optional[float]:
    """Get age of cached data in minutes"""
    conn = self.connect()
    cursor = conn.cursor()

    try:
      cursor.execute("""
        SELECT 
          (julianday('now') - julianday(MAX(last_updated))) * 24 * 60 as age_minutes
        FROM stocks
      """)
      result = cursor.fetchone()
      return result['age_minutes'] if result else None
    finally:
      self.close()

  def needs_refresh(self, max_age_minutes: int = 15) -> bool:
    """Check if data needs refresh"""
    age = self.get_data_age()
    if age is None:
      return True
    return age > max_age_minutes

  def get_refresh_history(self, limit: int = 5):
    """Return recent refresh log entries"""
    conn = self.connect()
    cursor = conn.cursor()
    try:
      cursor.execute("""
        SELECT refresh_time, stocks_updated, data_source, success, error_message, duration_seconds
        FROM refresh_log
        ORDER BY refresh_time DESC
        LIMIT ?
      """, (limit,))
      rows = cursor.fetchall()
      return [dict(row) for row in rows]
    finally:
      self.close()

  # ============================================================================
  # MARKET INDICES METHODS
  # ============================================================================
  def insert_or_update_index(self, symbol: str, name: str, value: float,
                             change: float, change_pct: float):
    """Insert or update a market index"""
    conn = self.connect()
    cursor = conn.cursor()
    try:
      cursor.execute('''
        INSERT OR REPLACE INTO market_indices 
        (symbol, name, value, change, change_pct, last_updated)
        VALUES (?, ?, ?, ?, ?, ?)
      ''', (symbol, name, value, change, change_pct, datetime.now().isoformat()))
      conn.commit()
    finally:
      self.close()

  def get_all_indices(self) -> List[dict]:
    """Get all market indices"""
    conn = self.connect()
    cursor = conn.cursor()
    try:
      cursor.execute('SELECT * FROM market_indices')
      rows = cursor.fetchall()
      return [dict(row) for row in rows]
    finally:
      self.close()

  # ============================================================================
  # ALTERNATIVE ASSETS METHODS
  # ============================================================================
  def insert_or_update_alternative_asset(
      self,
      symbol: str,
      name: str,
      asset_type: str,
      value: float = None,
      change: float = None,
      change_percent: float = None,
      fetch_error: str = None,
  ):
      """Insert or update an alternative asset (crypto, commodity, currency)."""
      conn = self.connect()
      cursor = conn.cursor()
      try:
          cursor.execute(
              """
              INSERT OR REPLACE INTO alternative_assets
              (symbol, name, asset_type, value, change, change_percent, last_updated, fetch_error)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?)
              """,
              (
                  symbol,
                  name,
                  asset_type,
                  value,
                  change,
                  change_percent,
                  datetime.now().isoformat(),
                  fetch_error,
              ),
          )
          conn.commit()
      finally:
          self.close()

  def get_all_alternative_assets(self) -> List[dict]:
      """Return all alternative assets."""
      conn = self.connect()
      cursor = conn.cursor()
      try:
          cursor.execute("SELECT * FROM alternative_assets")
          rows = cursor.fetchall()
          return [dict(row) for row in rows]
      finally:
          self.close()

  # ============================================================================
  # MACRO INDICATORS METHODS
  # ============================================================================
  def insert_or_update_indicator(self, indicator_id: str, name: str,
                                 value: float, change: float = None,
                                 unit: str = '%'):
    """Insert or update a macro indicator"""
    conn = self.connect()
    cursor = conn.cursor()
    try:
      cursor.execute('''
        INSERT OR REPLACE INTO macro_indicators 
        (indicator_id, name, value, change, unit, last_updated)
        VALUES (?, ?, ?, ?, ?, ?)
      ''', (indicator_id, name, value, change, unit, datetime.now().isoformat()))
      conn.commit()
    finally:
      self.close()

  def get_all_indicators(self) -> List[dict]:
    """Get all macro indicators"""
    conn = self.connect()
    cursor = conn.cursor()
    try:
      cursor.execute('SELECT * FROM macro_indicators')
      rows = cursor.fetchall()
      return [dict(row) for row in rows]
    finally:
      self.close()

  # ============================================================================
  # HISTORICAL DATA METHODS
  # ============================================================================
  def insert_treasury_history(self, date: str, yield_10y: float, yield_2y: float = None):
    """Insert treasury yield data"""
    conn = self.connect()
    cursor = conn.cursor()
    try:
      cursor.execute('''
        INSERT OR REPLACE INTO treasury_history 
        (date, yield_10y, yield_2y, last_updated)
        VALUES (?, ?, ?, ?)
      ''', (date, yield_10y, yield_2y, datetime.now().isoformat()))
      conn.commit()
    finally:
      self.close()

  def get_treasury_history(self, days: int = 365) -> List[dict]:
    """Get treasury yield history"""
    conn = self.connect()
    cursor = conn.cursor()
    try:
      cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
      cursor.execute('''
        SELECT date, yield_10y, yield_2y FROM treasury_history 
        WHERE date >= ? 
        ORDER BY date ASC
      ''', (cutoff_date,))
      rows = cursor.fetchall()
      return [dict(row) for row in rows]
    finally:
      self.close()

  def insert_cpi_history(self, date: str, cpi_value: float,
                         mom_change: float = None, yoy_change: float = None):
    """Insert CPI historical data"""
    conn = self.connect()
    cursor = conn.cursor()
    try:
      cursor.execute('''
        INSERT OR REPLACE INTO cpi_history 
        (date, cpi_value, mom_change, yoy_change, last_updated)
        VALUES (?, ?, ?, ?, ?)
      ''', (date, cpi_value, mom_change, yoy_change, datetime.now().isoformat()))
      conn.commit()
    finally:
      self.close()

  def get_cpi_history(self, months: int = 12) -> List[dict]:
    """Get CPI history"""
    conn = self.connect()
    cursor = conn.cursor()
    try:
      cursor.execute('''
        SELECT date, cpi_value, mom_change, yoy_change FROM cpi_history 
        ORDER BY date DESC 
        LIMIT ?
      ''', (months,))
      rows = cursor.fetchall()
      # reverse to oldest -> newest
      result = [dict(row) for row in rows]
      return list(reversed(result))
    finally:
      self.close()

  def insert_vix_history(self, date: str, vix_close: float,
                         vix_high: float = None, vix_low: float = None):
    """Insert VIX historical data"""
    conn = self.connect()
    cursor = conn.cursor()
    try:
      cursor.execute('''
        INSERT OR REPLACE INTO vix_history 
        (date, vix_close, vix_high, vix_low, last_updated)
        VALUES (?, ?, ?, ?, ?)
      ''', (date, vix_close, vix_high, vix_low, datetime.now().isoformat()))
      conn.commit()
    finally:
      self.close()

  def get_vix_history(self, days: int = 365) -> List[dict]:
    """Get VIX history"""
    conn = self.connect()
    cursor = conn.cursor()
    try:
      cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
      cursor.execute('''
        SELECT date, vix_close, vix_high, vix_low FROM vix_history 
        WHERE date >= ? 
        ORDER BY date ASC
      ''', (cutoff_date,))
      rows = cursor.fetchall()
      return [dict(row) for row in rows]
    finally:
      self.close()


# Global database instance
db = DatabaseManager()

