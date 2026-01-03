# refresh_market_data.ps1
# Quick update for market prices and metadata only (no new transactions).

$ErrorActionPreference = "Stop"
Write-Host "--- Kodak Portfolio: Refresh Market Data ---" -ForegroundColor Cyan

# 1. Map ISINs (Ensure metadata is up to date)
Write-Host "`n[1/2] Checking for missing ISIN mappings..." -ForegroundColor Yellow
python -m kodak.pipeline.map_isins

# 2. Fetch Prices
Write-Host "`n[2/2] Fetching latest market prices..." -ForegroundColor Yellow
python -m kodak.pipeline.fetch_prices

Write-Host "`n[SUCCESS] Market data refreshed." -ForegroundColor Green
