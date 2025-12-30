# update_portfolio.ps1
# A "tight pipeline" script to update the portfolio database with fresh data.

$ErrorActionPreference = "Stop"

Write-Host "--- Kodak Portfolio Update Pipeline (v2) ---" -ForegroundColor Cyan

# 1. Ingest New Transactions (File -> Staging)
Write-Host "`n[1/2] Ingesting new transaction files..." -ForegroundColor Yellow
python -m scripts.pipeline.ingest

# 2. Check Staging Status via Python
$StagingCount = python -c "from scripts.shared.db import execute_scalar; print(execute_scalar(\"SELECT COUNT(*) FROM transactions_staging\") or 0)"

if ($StagingCount -gt 0) {
    Write-Host "`n[ATTENTION] There are $StagingCount transactions in STAGING." -ForegroundColor Red
    Write-Host "Run the following command to review and commit them:"
    Write-Host "  python -m scripts.pipeline.review_commit" -ForegroundColor White
} else {
    Write-Host "`n[OK] No pending transactions in staging." -ForegroundColor Green
}

Write-Host "`n-------------------------------------------" -ForegroundColor Cyan
Write-Host "Pipeline Complete." -ForegroundColor Green