import os
from dotenv import load_dotenv

load_dotenv()

print("Testing environment variables:")
print(f"FRED_API_KEY exists: {bool(os.getenv('FRED_API_KEY'))}")
print(f"FRED_API_KEY length: {len(os.getenv('FRED_API_KEY', ''))}")
print(f"FRED_API_KEY first 5 chars: {os.getenv('FRED_API_KEY', '')[:5]}")