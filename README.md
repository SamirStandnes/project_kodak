# Project Kodak

Portfolio tracking and analysis system.

## Setup

1.  **Initialize database:**
    ```bash
    python -m scripts.setup.initialize_database
    ```
2.  **Configuration:**
    

## Data Pipeline

Follow these steps to update your portfolio with new data:

1.  **Ingestion:** Place raw Nordnet (.csv) or Saxo (.xlsx) files in `data/new_raw_transactions/`.
    ```bash
    python -m scripts.pipeline.ingest
    ```
2.  **Review and Commit:** Verify the staged data and commit it to the master ledger. This automatically creates a database backup.
    ```bash
    python -m scripts.pipeline.review_commit
    ```
3. **Enrichment:** Update account and instrument mappings, fetch latest prices, and enrich exchange rates.
    ```bash
    python -m scripts.pipeline.map_accounts
    python -m scripts.pipeline.map_isins
    python -m scripts.pipeline.fetch_prices
    python -m scripts.pipeline.enrich_fx
    ```

## Dashboard & Reporting

Launch the interactive dashboard:
```bash
streamlit run scripts/dashboard/Home.py
```

Or run terminal-based analysis tools:
- **Portfolio Summary:** `python -m scripts.analysis.analyze_portfolio`
- **FX Analysis:** `python -m scripts.analysis.analyze_fx`
- **Other Tools:** Check `scripts/analysis/` for specialized scripts (Dividends, Fees, Interest).

## Features

- **Multi-Currency Support:** Handles NOK, USD, EUR, etc. with historical FX rates.
- **Automated Pipeline:** Ingestion -> Staging -> Review -> Production.
- **Dashboard:** Visual analysis of Holdings, Performance, Dividends, Interest, Fees, and FX P&L.