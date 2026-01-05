#!/bin/bash
# refresh_market_data.sh
# Quick update for market prices and metadata only (no new transactions).

set -e

echo "--- Kodak Portfolio: Refresh Market Data ---"

# 1. Map ISINs (Ensure metadata is up to date)
echo ""
echo "[1/2] Checking for missing ISIN mappings..."
python -m kodak.pipeline.map_isins

# 2. Fetch Prices
echo ""
echo "[2/2] Fetching latest market prices..."
python -m kodak.pipeline.fetch_prices

echo ""
echo "[SUCCESS] Market data refreshed."
