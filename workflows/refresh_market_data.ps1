# refresh_market_data.ps1
# Quick update for market prices and metadata only (no new transactions).

$ErrorActionPreference = "Stop"
Write-Host "--- Kodak Portfolio: Refresh Market Data ---" -ForegroundColor Cyan

# 1. Map ISINs (Ensure metadata is up to date)
Write-Host "`n[1/3] Checking for missing ISIN mappings..." -ForegroundColor Yellow
python -m kodak.pipeline.map_isins

# 2. Fetch Prices
Write-Host "`n[2/3] Fetching latest market prices..." -ForegroundColor Yellow
python -m kodak.pipeline.fetch_prices

# 3. Export Performance & Holdings JSON
Write-Host "`n[3/3] Exporting performance and holdings data..." -ForegroundColor Yellow
python -m kodak.cli.performance_report --json data/performance.json
python -m kodak.cli.analyze_portfolio --json data/holdings.json

Write-Host "`n[SUCCESS] Market data refreshed." -ForegroundColor Green
