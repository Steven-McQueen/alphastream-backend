import sqlite3
from pathlib import Path
from typing import List, Optional


class DatabaseManager:
  """Manages SQLite database for stock data caching"""

  def __init__(self, db_path: str = "data/stocks.db"):
    self.db_path = Path(db_path)
    self.db_path.parent.mkdir(parents=True, exist_ok=True)
    self.conn = None

  def connect(self):
    """Connect to database"""
    self.conn = sqlite3.connect(
      self.db_path,
      check_same_thread=False,
      timeout=10.0
    )
    self.conn.row_factory = sqlite3.Row
    return self.conn

  def close(self):
    """Close database connection"""
    if self.conn:
      self.conn.close()
      self.conn = None

  def init_database(self):
    """Initialize database with schema"""
    schema_path = Path(__file__).parent / "schema.sql"

    with open(schema_path, 'r', encoding='utf-8') as f:
      schema = f.read()

    conn = self.connect()
    conn.executescript(schema)
    conn.commit()
    print(f"✅ Database initialized at {self.db_path}")
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
          print(f"❌ Error inserting {stock.get('ticker')}: {e}")

      conn.commit()
      print(f"✅ Inserted/updated {success_count}/{len(stocks)} stocks")
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


# Global database instance
db = DatabaseManager()

