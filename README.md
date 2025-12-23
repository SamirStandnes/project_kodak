# Project Kodak

**Project Kodak** is a comprehensive portfolio management system designed to unify transaction data from multiple brokerages (Nordnet, Saxo, etc.), calculate advanced performance metrics (IRR, TWR), and track the valuation gap between market price and intrinsic value.

## 📂 Project Structure

*   **`data/`**: Stores raw transaction files, processed data, and import logs.
    *   `new_raw_transactions/`: Drop your new CSV/Excel exports here.
    *   `logs/`: Detailed audit logs of every import operation.
*   **`database/`**: Contains the SQLite database (`portfolio.db`) and automatic backups.
*   **`docs/`**: Detailed documentation.
    *   [**PIPELINE.md**](docs/PIPELINE.md): Technical details on data ingestion, deduplication, and the safety staging workflow.
    *   [**TODO.md**](docs/TODO.md): Project roadmap and tasks.
*   **`scripts/`**: Python scripts for data processing, database management, and reporting.

## 🚀 Getting Started

### 1. Configuration
Copy the template configuration file to create your local config:
```bash
cp docs/templates/config.ini.example config.ini
```
Edit `config.ini` with your specific settings (email server, API keys, etc.).

### 2. Adding New Transactions
The project uses a safe, two-step process for adding data:

1.  **Ingest:**
    Place your brokerage export files in `data/new_raw_transactions/` and run:
    ```bash
    python -m scripts.pipeline.process_new_transactions
    ```
    *Check `data/logs/` to see exactly what was imported vs. skipped as duplicate.*

2.  **Review & Commit:**
    Inspect the staged data and commit it to the database:
    ```bash
    python -m scripts.db.review_staging
    ```
    *This automatically creates a backup of your database before saving.*

### 3. Reporting
Generate a summary of your portfolio:
```bash
python -m scripts.analysis.generate_summary_report
```
Or send a daily email report:
```bash
python -m scripts.messaging.send_daily_report
```

## 🛠 Features
*   **Automatic Deduplication:** Smart hashing ensures you never import the same trade twice, even if your brokerage export overlaps with previous dates.
*   **Audit Logging:** Every file import generates a detailed log file in `data/logs/` for full transparency.
*   **Unified Schema:** Consolidates different broker formats (Nordnet, Saxo) into a single, standardized data model.