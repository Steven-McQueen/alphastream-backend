from fredapi import Fred

# Replace with your actual key
FRED_API_KEY = "302b744fee5892e7cfe35647ee20ac06"

try:
    fred = Fred(api_key=FRED_API_KEY)
    data = fred.get_series('DGS10', limit=1)
    print(f"SUCCESS! 10Y Yield: {data.iloc[0]}")
except Exception as e:
    print(f"ERROR: {e}")