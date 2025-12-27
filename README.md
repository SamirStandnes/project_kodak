# Project Kodak

**Project Kodak** is a comprehensive portfolio management system designed to unify transaction data from multiple brokerages (Nordnet, Saxo, etc.), calculate advanced performance metrics (IRR, TWR), and track the valuation gap between market price and intrinsic value.

## 📂 Project Structure

*   **`data/`**: Stores raw transaction files, processed data, and import logs.
*   **`database/`**: Contains the SQLite database (`portfolio.db`) and automatic backups.
*   **`docs/`**: Detailed documentation.
    *   [**PIPELINE.md**](docs/PIPELINE.md): Technical deep-dive into the data flow, architecture, and safety mechanisms.
    *   [**TODO.md**](docs/TODO.md): Project roadmap.
*   **`scripts/`**: Python scripts for data processing (`pipeline`), analysis (`analysis`), and the dashboard (`dashboard`).

## 🚀 Getting Started

### 1. Configuration
Copy the template configuration file to create your local config:
```bash
cp docs/templates/config.ini.example config.ini
```
Edit `config.ini` with your specific settings.

### 2. Routine Workflow

**A. Import New Data (Monthly/Weekly)**
1.  Place brokerage export files in `data/new_raw_transactions/`.
2.  Run the ingestion pipeline:
    ```bash
    python -m scripts.pipeline.process_new_transactions
    ```
3.  Review and commit to the database:
    ```bash
    python -m scripts.db.review_staging
    ```

**B. Update Market Data (Daily/On-Demand)**
Before generating reports, fetch the latest prices to ensure accuracy:
```bash
python -m scripts.pipeline.fetch_prices
```

### 3. View Your Portfolio

**📊 Interactive Dashboard (Recommended)**
Launch the full web interface:
```bash
streamlit run scripts/dashboard/Home.py
```

**📄 Console Summaries**
*   **Summary:** `python -m scripts.analysis.generate_summary_report`
*   **Detailed:** `python -m scripts.analysis.generate_detailed_report`

## 🛠 Features
*   **Safe Staging:** Never corrupts your main database with bad imports.
*   **Unified Architecture:** All reports share the same logic and price data for 100% consistency.
*   **Automatic Deduplication:** Smart hashing prevents duplicate trades.
*   **Multi-Currency:** Robust handling of FX rates and cross-rates.
