# Data Pipeline and Workflow Technical Documentation

This document provides a technical overview of the Project Kodak data pipeline, covering the entire lifecycle from raw data ingestion to final reporting and dashboards.

## High-Level Data Flow

The architecture is split into three phases: **Ingestion (Safe Staging)**, **Enrichment (Market Data)**, and **Reporting (Unified Output)**.

```
[Phase 1: Ingestion]             [Phase 2: Enrichment]              [Phase 3: Reporting]

Raw Files (CSV/XLSX)
       |
       v
process_new_transactions.py  -->  fetch_prices.py (Yahoo API)
       |                                  |
       v                                  v
+----------------------+         +----------------------+
| transactions_staging |         |    current_prices    |
+----------------------+         +----------------------+
       |                                  |
       v (review & commit)                |
+----------------------+                  |
|     transactions     | <----------------+
+----------------------+                  |
          |                               |
          +---------------+---------------+
                          |
                          v
               +----------------------+
               |   scripts/shared/    |  <-- Single Source of Truth
               | (db, market_data)    |
               +----------------------+
                          |
          +---------------+---------------+
          |               |               |
          v               v               v
    [Dashboard]     [Summary Rpt]   [Detailed Rpt]
   (Interactive)      (Console)        (Audit)
```

## Phase 1: Ingestion & Safety

The ingestion pipeline is designed to be **incremental, auditable, and idempotent**.

### 1. `scripts/pipeline/process_new_transactions.py`
*   **Input:** Reads raw export files from `data/new_raw_transactions/`.
*   **Deduplication:** Generates a unique hash (`Date|Account|Type|Symbol|Amount`) for every row and checks against the database. Skips duplicates automatically.
*   **Output:** Inserts *only* new records into `transactions_staging` and archives source files.
*   **Logging:** Generates a detailed audit log in `data/logs/`.

### 2. `scripts/db/review_staging.py`
*   **Purpose:** Human verification gate.
*   **Actions:**
    *   **Commit:** Moves data from staging to the main `transactions` table. **Automatically creates a DB backup** first.
    *   **Clear:** Discards the staged batch if errors are found.

## Phase 2: Enrichment & Market Data

To ensure all reports (Dashboard, Email, CLI) show consistent numbers, we use a **Snapshot Model** for prices.

### `scripts/pipeline/fetch_prices.py`
*   **Function:** Fetches the latest closing price for every held security from Yahoo Finance.
*   **Storage:** Updates the `current_prices` table in the database.
*   **Why?** This decouples reporting from API limits and latency. You run this script *once* to update the "state of the world," and then generate as many reports as you want instantly.

## Phase 3: Analysis & Reporting

All reports rely on a shared kernel located in `scripts/shared/` and `scripts/analysis/calculations.py`.

### Shared Core (`scripts/shared/`)
*   **`market_data.py`**: The centralized logic for retrieving prices. It first checks the `current_prices` DB snapshot. If a historical price is needed (for graphs), it falls back to caching via Yahoo Finance.
*   **`db.py`**: Centralized database connection management.

### The Reports

#### 1. 📈 The Dashboard
*   **Command:** `streamlit run scripts/dashboard/Home.py`
*   **Purpose:** Interactive exploration. Visualizes sector allocation, performance charts, and activity.
*   **Tech:** Streamlit + Plotly.

#### 2. 📊 Summary Report
*   **Command:** `python -m scripts.analysis.generate_summary_report`
*   **Purpose:** High-level executive summary. Shows total Market Value (M NOK), XIRR, and top-level gains.
*   **Used By:** The Daily Email script also uses this module to generate its HTML body.

#### 3. 📝 Detailed Report
*   **Command:** `python -m scripts.analysis.generate_detailed_report`
*   **Purpose:** Audit-level granularity. Breaks down holdings **by Account**. Useful for reconciling against specific bank statements.

## Key Database Tables

*   **`transactions`**: The immutable ledger of all buys, sells, dividends, and fees.
*   **`transactions_staging`**: Temporary holding area for new imports.
*   **`isin_symbol_map`**: Maps ISINs (e.g., `US0378331005`) to Tickers (e.g., `AAPL`) and metadata (Sector, Region).
*   **`current_prices`**: The latest price snapshot for all active holdings.
