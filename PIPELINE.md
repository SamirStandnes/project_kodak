# Data Pipeline and Workflow Technical Documentation

This document provides a technical overview of the data pipeline, from raw data sources to the final database, and the scripts that manage this process.

## High-Level Data Flow

The data pipeline is designed to be incremental and safe, using a staging area before committing any new data to the main database.

```
                                  +---------------------------------+
[Raw Data Files] --------------> | scripts/pipeline/                 |
(Saxo, Nordnet)                   |   process_new_transactions.py   |
                                  +---------------------------------+
                                                  |
                                                  v
                                  +---------------------------------+
[Manual User Input] ----------> | scripts/db/                     |
(DNB, etc.)                       |   add_manual_transaction.py     |
                                  +---------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------+
|                                                                                       |
|                                  DATABASE (portfolio.db)                                |
|                                                                                       |
|   +-------------------------------------------------------------------------------+   |
|   |                                                                               |   |
|   |                          transactions_staging (Table)                         |   |
|   |   (All new, un-reviewed data is held here with a unique 'batch_id')           |   |
|   |                                                                               |   |
|   +-------------------------------------------------------------------------------+   |
|                                                                                       |
|            ^                                |   ^                                     |
|            | (CLEAR)                        |   | (COMMIT)                              |
|            |                                |   |                                     |
|            +--------------------------------+   +-------------------------------------+
|                                                                                       |
|                             +-----------------------------+                             |
|                             | scripts/db/review_staging.py| (User reviews and decides)  |
|                             +-----------------------------+                             |
|                                                                                       |
+---------------------------------------------------------------------------------------+
                                                  |
                                                  v (On 'commit')
+---------------------------------------------------------------------------------------+
|                                                                                       |
|                                  DATABASE (portfolio.db)                                |
|                                                                                       |
|   +-------------------------------------------------------------------------------+   |
|   |                                                                               |   |
|   |                            transactions (Main Table)                          |   |
|   |             (Contains all historical and committed transactions)              |   |
|   |                                                                               |   |
|   +-------------------------------------------------------------------------------+   |
|                                                                                       |
+---------------------------------------------------------------------------------------+
                                                  |
                                                  v
                                      +-------------------------+
                                      | scripts/analysis/       |
                                      | (All reporting scripts) |
                                      +-------------------------+

```

## Core Components

### 1. Data Ingestion & Processing

#### `scripts/pipeline/process_new_transactions.py`
-   **Trigger:** Manually run by the user.
-   **Input:** Reads raw `.csv` (Nordnet) and `.xlsx` (Saxo) files from the `data/new_raw_transactions/` directory.
-   **Processing:**
    -   Detects the source of each file based on its extension.
    -   Uses internal functions (`_clean_nordnet_data`, `_clean_saxo_data`) to parse and clean the specific formats. These functions are adaptations of the original, standalone cleaning scripts.
    -   Handles complex transformations, including fee splitting and transaction type classification.
    -   Unifies the cleaned data from all processed files into a single DataFrame.
    -   Assigns a single, unique `batch_id` (e.g., `file_import_20251214_193000`) to all transactions in the current run.
    -   Maps `AccountID` to `AccountType` and standardizes symbol names.
-   **Output:** Appends the final, processed DataFrame to the `transactions_staging` table in `database/portfolio.db`.
-   **Post-processing:** Moves the processed raw files to `data/new_raw_transactions/archive/` to prevent re-processing.

#### `scripts/db/add_manual_transaction.py`
-   **Trigger:** Manually run by the user for individual transaction entries.
-   **Processing:**
    -   Provides an interactive command-line interface to prompt the user for transaction details (Symbol, Quantity, Price, etc.).
    -   Generates a unique `batch_id` for each individual transaction (e.g., `manual_20251214_193500`).
-   **Output:** Inserts the single transaction record into the `transactions_staging` table.

### 2. Staging and Committing

#### `transactions_staging` (Table in `portfolio.db`)
-   **Purpose:** Acts as a temporary holding area for all new data before it is permanently saved. This allows for a crucial review step, preventing the corruption of historical data.
-   **Schema:** The schema is identical to the main `transactions` table.

#### `scripts/db/review_staging.py`
-   **Trigger:** Manually run by the user after data has been loaded into the staging area.
-   **Functionality:**
    1.  Displays all records currently in `transactions_staging`.
    2.  Prompts the user for an action:
        -   **`commit`**:
            -   First, it automatically creates a timestamped backup of the entire `portfolio.db` file as a final safety measure.
            -   It then inserts all records from `transactions_staging` into the main `transactions` table.
            -   Finally, it deletes all records from `transactions_staging`, clearing it for the next update.
        -   **`clear`**: Deletes all records from `transactions_staging`. This is a destructive action for the staging table only and is used to discard a bad batch.
        -   **`exit`**: Exits the script, leaving the staging area untouched for later review.

### 3. Main Data Table

#### `transactions` (Table in `portfolio.db`)
-   **Purpose:** This is the primary data table for the entire application. It is the single source of truth for all reporting and analysis.
-   **Key Columns:**
    -   `GlobalID`: A unique UUID for every transaction record, including split-out fees.
    -   `batch_id`: A string identifier that links a transaction to its import batch (e.g., `'historical'`, `'file_import_...'`, `'manual_...'`). This is **critical for traceability and potential rollbacks**.
    -   `ParentID`: Used to link child transactions (like a `FEE`) to their parent transaction (like a `BUY` or `SELL`).
    -   `Type`: The standardized transaction type (e.g., `BUY`, `SELL`, `DIVIDEND`, `FEE`).
    -   `Amount_Base`: The transaction's value in the portfolio's base currency (NOK).
    -   `Amount_Local`: The transaction's value in the asset's local currency (e.g., USD for US stocks).

### 4. Analysis and Reporting

#### `scripts/analysis/*`
-   All scripts within this directory (e.g., `generate_summary_report.py`, `generate_detailed_report.py`) read directly from the main `transactions` table in `portfolio.db` to perform their calculations and generate reports.
-   They are consumers of the cleaned, unified, and committed data.
