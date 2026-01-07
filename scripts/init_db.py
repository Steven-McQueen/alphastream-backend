"""Initialize database with S&P 500 data and macro data"""
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import db
from services.sp500_importer import fetch_and_import_sp500
from services.macro_importer import initialize_all_macro_data, initialize_alternative_assets

print("=" * 60)
print("AlphaStream Intelligence Terminal - Database Setup")
print("=" * 60)

# ============================================================================
# STEP 1: CREATE DATABASE SCHEMA
# ============================================================================

print("\nStep 1: Creating database schema...")
db.init_database()
print(f"Database initialized at {db.db_path}")

# ============================================================================
# STEP 2: IMPORT S&P 500 DATA
# ============================================================================

print("\nStep 2: Importing S&P 500 data...")
stock_count = fetch_and_import_sp500()

if stock_count > 0:
    print(f"{stock_count} stocks imported successfully")
else:
    print("Warning: No stocks were imported")

# ============================================================================
# STEP 3: IMPORT MACRO ECONOMIC DATA
# ============================================================================

print("\nStep 3: Importing macro economic data...")
macro_stats = initialize_all_macro_data()

# ============================================================================
# STEP 4: IMPORT ALTERNATIVE ASSETS
# ============================================================================

print("\nStep 4: Importing alternative assets (crypto, commodities, currencies)...")
assets_stats = initialize_alternative_assets()

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print("\n" + "=" * 60)
print("Database setup complete!")
print(f"   - {stock_count} S&P 500 stocks")
print(f"   - {macro_stats['indices']} market indices")
print(f"   - {macro_stats['indicators']} macro indicators")
print(f"   - {assets_stats['assets']} alternative assets")
print(f"   - {macro_stats['treasury_days']} days of treasury history")
print(f"   - {macro_stats['cpi_months']} months of CPI history")
print(f"   - {macro_stats['vix_days']} days of VIX history")
print(f"   - Database location: {db.db_path}")
print(f"   - Data age: {db.get_data_age():.2f} minutes")
print("=" * 60 + "\n")
