import json

# Les original fil
with open('paste.txt', 'r') as f:
    raw_data = json.load(f)

# Mapping fra GICS Sector til frontend-sektorer
sector_mapping = {
    "Information Technology": "Technology",
    "Health Care": "Healthcare",
    "Financials": "Financials",
    "Consumer Discretionary": "Consumer Discretionary",
    "Consumer Staples": "Consumer Staples",
    "Industrials": "Industrials",
    "Energy": "Energy",
    "Materials": "Materials",
    "Utilities": "Utilities",
    "Real Estate": "Real Estate",
    "Communication Services": "Communication Services"
}

# Transform data
transformed = []
for item in raw_data:
    ticker = item.get("Symbol", "")
    name = item.get("Security", "")
    gics_sector = item.get("GICS Sector", "Technology")
    industry = item.get("GICS Sub-Industry", "Unknown")
    
    # Map sector
    sector = sector_mapping.get(gics_sector, "Technology")
    
    # Rough market cap estimate (you can refine this later with API)
    # For now, set reasonable defaults based on typical S&P 500 sizes
    marketCap = 100.0  # Default to $100B
    
    # Default scores (can be enriched later)
    transformed.append({
        "ticker": ticker,
        "name": name,
        "sector": sector,
        "industry": industry,
        "marketCap": marketCap,
        "qualityScore": 70,
        "momentumScore": 60,
        "valueScore": 55,
        "sentimentScore": 65
    })

# Write to sp500.json
with open('sp500.json', 'w') as f:
    json.dump(transformed, f, indent=2)

print(f"✅ Transformed {len(transformed)} stocks and saved to data/sp500.json")
