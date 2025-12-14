# Project Kodak

## A. Primary Goals (Revised and Reordered)
- **Unify Data & Performance:** Create a centralized, standardized database (portfolio.db) capable of consolidating all transaction data from disparate brokerage sources and calculating Unified Performance Metrics (e.g., Internal Rate of Return (IRR), Time-Weighted Return (TWR)) across all brokerage accounts.

- **Quantify Valuation Gap:** Develop a reliable method to calculate and track the percentage difference between the portfolio's aggregate Intrinsic Value and its Market Value daily.

- **Establish Modeling Capability:** Implement and operationalize at least one core intrinsic valuation model.

- **Enable Seamless Data Entry:** Provide a simple, structured method (terminal interface) for ongoing manual input of new trades after the initial historical data load.

## Workflow for Incremental Transaction Updates

To ensure data integrity and traceability, a new workflow has been implemented for adding new transactions. This workflow uses a staging area and unique batch IDs.

### 1. Adding Manual Transactions

For individual trades (e.g., from DNB or other sporadic entries):
*   **Script:** `scripts/db/add_manual_transaction.py`
*   **How to use:**
    1.  Run `python -m scripts.db.add_manual_transaction`.
    2.  The script will interactively prompt you for transaction details.
    3.  Each transaction entered will be assigned a unique `batch_id` (e.g., `manual_YYYYMMDD_HHMMSS`) and stored in the `transactions_staging` table.
    4.  You can add multiple transactions in one session.

### 2. Adding File-Based Transactions (e.g., Quarterly Brokerage Exports)

For importing new batches of transactions from brokerage export files:
*   **Input Directory:** `data/new_raw_transactions/`
*   **Script:** `scripts/pipeline/process_new_transactions.py`
*   **How to use:**
    1.  Place your new raw transaction files (e.g., Nordnet CSVs, Saxo XLSX files) into the `data/new_raw_transactions/` directory.
    2.  Run `python -m scripts.pipeline.process_new_transactions`.
    3.  The script will automatically detect the file type, clean the data, unify it, assign a unique `batch_id` (e.g., `file_import_YYYYMMDD_HHMMSS`), and load all processed transactions into the `transactions_staging` table.
    4.  Processed files will be moved to `data/new_raw_transactions/archive/`.

### 3. Reviewing and Committing Staged Transactions

Before any new transactions are permanently added to your main `transactions` database, they go through a review process:
*   **Script:** `scripts/db/review_staging.py`
*   **How to use:**
    1.  Run `python -m scripts.db.review_staging`.
    2.  The script will display all transactions currently held in the `transactions_staging` table.
    3.  You will be presented with three options:
        *   **`commit`**: Moves all transactions from `transactions_staging` to your main `transactions` table. **This action automatically creates a timestamped backup of your `database/portfolio.db` before committing, ensuring data safety.** The staging area is then cleared.
        *   **`clear`**: Deletes all transactions from the `transactions_staging` table without affecting your main database. Use this if you've made errors and want to discard the current staged batch.
        *   **`exit`**: Exits the script without making any changes to either the staging or main tables.

### Data Traceability (`batch_id`)
Every transaction in the `transactions` table now includes a `batch_id` column.
*   Existing historical data is marked with `batch_id = 'historical'`.
*   New manual entries and file imports receive unique, timestamped `batch_id`s.
This allows for precise identification and easy reversal of any batch of imported transactions if issues are discovered.