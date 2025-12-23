# Data Pipeline and Workflow Technical Documentation

This document provides a technical overview of the data pipeline, from raw data sources to the final database.

## High-Level Data Flow

The data pipeline is designed to be **incremental, auditable, and safe**. It uses a staging area to verify data before committing it to the main database.

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
|                                  STAGING AREA                                         |
|                                                                                       |
|   +-------------------------------------------------------------------------------+   |
|   |                          transactions_staging (Table)                         |   |
|   |   (All new, un-reviewed data is held here with a unique 'batch_id')           |   |
|   +-------------------------------------------------------------------------------+   |
|                                                                                       |
|            ^                                |   ^                                     |
|            | (CLEAR)                        |   | (COMMIT)                              |
|            +--------------------------------+   +-------------------------------------+
|                                                                                       |
|                             +-----------------------------+                             |
|                             | scripts/db/review_staging.py| (User reviews and decides)  |
|                             +-----------------------------+                             |
+---------------------------------------------------------------------------------------+
                                                  |
                                                  v (On 'commit')
+---------------------------------------------------------------------------------------+
|                                  MAIN DATABASE                                        |
|                                                                                       |
|   +-------------------------------------------------------------------------------+   |
|   |                            transactions (Table)                               |   |
|   |             (Contains all historical and committed transactions)              |   |
|   +-------------------------------------------------------------------------------+   |
+---------------------------------------------------------------------------------------+
```

## Core Components

### 1. Data Ingestion & Deduplication

#### `scripts/pipeline/process_new_transactions.py`
This script is the entry point for file-based imports.
*   **Input:** Reads raw `.csv` (Nordnet) and `.xlsx` (Saxo) files from `data/new_raw_transactions/`.
*   **Logging:** Generates a detailed, row-level audit log in `data/logs/import_log_<timestamp>.txt`.
*   **Deduplication:**
    *   Generates a unique hash for every incoming transaction based on: `Date | Account | Type | Symbol | Amount`.
    *   Checks this hash against the entire existing database.
    *   **SKIPS** any transaction that already exists (preventing duplicates).
    *   **STAGES** only truly new transactions.
*   **Output:** Inserts new records into `transactions_staging` and archives source files to `data/new_raw_transactions/archive/`.

### 2. Staging and Committing

#### `transactions_staging` (Table)
*   **Purpose:** A temporary holding area. Data here is **not** yet in your reports.
*   **Review:** Use `scripts/db/review_staging.py` to inspect this data.

#### `scripts/db/review_staging.py`
*   **Functionality:**
    *   **`commit`**: Moves data to the main table. **Automatically creates a database backup** in `database/backups/` before modifying anything.
    *   **`clear`**: Wipes the staging area if you want to discard the batch.

### 3. Traceability

*   **Batch IDs:** Every transaction has a `batch_id` (e.g., `file_import_20251223_164050`). This allows you to identify exactly when and how a transaction entered the system.
*   **Logs:** Every import run creates a permanent text log in `data/logs/` detailing the decision made for every single row in the source file.