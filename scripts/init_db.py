"""Initialize database and perform first data import"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.db_manager import db
from services.sp500_importer import fetch_and_import_sp500


def main():
    print("=" * 60)
    print("AlphaStream Intelligence Terminal - Database Setup")
    print("=" * 60)

    print("\n📋 Step 1: Creating database schema...")
    db.init_database()

    print("\n📊 Step 2: Importing S&P 500 data...")
    count = fetch_and_import_sp500()

    if count > 0:
        print(f"\n✅ Database setup complete!")
        print(f"   - {count} stocks imported")
        print(f"   - Database location: {db.db_path}")

        data_age = db.get_data_age()
        if data_age is not None:
            print(f"   - Data age: {data_age:.2f} minutes")
    else:
        print("\n❌ Database setup failed!")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

