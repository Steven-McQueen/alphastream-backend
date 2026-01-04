"""Test database queries"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from database.db_manager import db


def main():
    print("Testing database queries...\n")

    print("1️⃣ Get AAPL:")
    aapl = db.get_stock('AAPL')
    if aapl:
        print(f"   Name: {aapl['name']}")
        print(f"   Price: ${aapl['price']:.2f}")
        print(f"   Change 1D: {aapl['change_1d']:.2f}%")
        print(f"   P/E Ratio: {aapl['pe_ratio']:.2f}")

    print("\n2️⃣ Search 'Apple':")
    results = db.search_stocks('Apple')
    for stock in results[:3]:
        print(f"   {stock['ticker']}: {stock['name']}")

    print("\n3️⃣ Technology stocks (top 5 by market cap):")
    tech_stocks = db.get_stocks_by_sector('Information Technology')[:5]
    for stock in tech_stocks:
        print(f"   {stock['ticker']}: ${stock['market_cap']:.0f}M")

    print("\n4️⃣ Data age:")
    age = db.get_data_age()
    if age is not None:
        print(f"   {age:.2f} minutes old")
    else:
        print("   No data yet.")


if __name__ == "__main__":
    main()

