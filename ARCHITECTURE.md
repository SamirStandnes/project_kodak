# System Architecture & Logic Documentation

This document serves as the technical reference for **Project Kodak**. It details the database schema, data pipeline, and the mathematical logic used to calculate portfolio performance.

---

## 1. High-Level Design

Project Kodak follows a **ELT (Extract, Load, Transform)** pattern tailored for personal finance:
1.  **Extract:** Python "parsers" read raw broker exports (CSV/Excel).
2.  **Load:** Data is normalized and loaded into a local SQLite database (`portfolio.db`).
3.  **Transform (On-Demand):** Reporting scripts calculate holdings, performance, and taxes dynamically from the raw ledger at runtime. We do *not* store calculated daily balances; we re-derive them to ensure accuracy.

---

## 2. Database Schema (`portfolio.db`)

The database is a normalized relational schema centered around a "Double-Entry-ish" Ledger.

### 2.1 Core Ledger (`transactions`)
The single source of truth for every event (trade, dividend, deposit, fee).

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | Primary Key. |
| `date` | TEXT | Transaction date (ISO 8601: `YYYY-MM-DD`). |
| `type` | TEXT | Standardized Type: `BUY`, `SELL`, `DIVIDEND`, `DEPOSIT`, `WITHDRAWAL`, `INTEREST`, `FEE`, `TAX`. |
| `account_id` | INT | Foreign Key to `accounts`. |
| `instrument_id` | INT | Foreign Key to `instruments` (NULL for Cash/Interest). |
| `quantity` | REAL | Number of shares. Positive for inflows, Negative for outflows. |
| `amount` | REAL | Raw transaction value in the asset's currency (e.g., USD). |
| `currency` | TEXT | The currency of the asset (e.g., 'USD'). |
| `amount_local` | REAL | **CRITICAL:** The value converted to the portfolio's base currency (e.g., NOK, USD). This is the "Book Value" used for accounting. |
| `exchange_rate` | REAL | The FX rate applied at the time of transaction. |
| `fee_local` | REAL | Fees incurred, normalized to base currency. |

### 2.2 Reference Data

#### `accounts`
Containers for assets (e.g., "Nordnet ASK", "Saxo Trader").
*   `currency`: The "Home" currency of the account (defaults to Base Currency).

#### `instruments`
Tradable assets.
*   `isin`: Unique International Securities Identification Number (Primary Identifier).
*   `symbol`: Ticker symbol (e.g., `AAPL`, `NHY.OL`) used for fetching market data.

### 2.3 Market Data

#### `market_prices`
Historical EOD (End of Day) close prices.
*   `source`: Usually 'yahoo' or 'manual'.

#### `exchange_rates`
Historical FX rates (e.g., USD -> Base Currency).

---

## 3. Data Pipeline (Ingestion)

The ingestion process is automated by `scripts/pipeline/ingest.py`.

### Step 1: Parser Routing
The system scans `data/new_raw_transactions/`. If a file is found in `nordnet/`, it dynamically loads `scripts/pipeline/parsers/nordnet.py`.
*   **Parsers** are "dumb" translation layers. They convert proprietary broker formats (headers, number formats) into a standard Python dictionary.

### Step 2: Deduplication
We generate a **Content Hash** for every transaction:
`Hash = SHA256(date + account + type + symbol + amount)`
New transactions are compared against existing hashes in the DB. Duplicates are silently skipped.

### Step 3: Staging
New, non-duplicate records are pushed to a temporary table (`transactions_staging`).
*   **User Review:** The user verifies these records before they are "Committed" to the permanent `transactions` table.

---

## 4. Performance & Calculation Logic

This is the core "Brain" of the system, located in `scripts/shared/calculations.py`.

### 4.1 "Accounting View" vs. "Performance View"

*   **Accounting View:** "How many shares do I own?"
    *   **Logic:** `Sum(quantity)` from the ledger.
    *   **Truth:** Accurate for tax and current ownership.
*   **Performance View:** "How has my investment grown?"
    *   **Problem:** Historical prices from providers (Yahoo) are "Split-Adjusted".
    *   **Solution:** We must adjust historical *quantities* to match the adjusted prices.

### 4.2 Share Split Logic (`get_adjusted_qty`)
We discover splits by looking for `BYTTE` (Exchange) transactions in the ledger.
*   **Formula:** `Adjusted Qty = Raw Qty * Cumulative Split Ratio`
*   **Usage:** When calculating the value of a holding on a historical date (e.g., for a chart), we scale the quantity up/down so it aligns with Yahoo's adjusted price history.

### 4.3 Cost Basis (Average Cost Method)
We use a weighted **Average Cost** basis.
*   **Buy:** Increases Total Cost and Quantity.
*   **Sell:** Reduces Quantity and reduces Total Cost *proportionally* to the shares sold.
    *   `Cost Removed = (Current Total Cost / Current Total Qty) * Qty Sold`
*   **Realized Gain:** `Proceeds - Cost Removed`.

### 4.4 XIRR (Money-Weighted Return)
We use the **XIRR (Extended Internal Rate of Return)** algorithm to calculate performance. This accounts for the timing of cash flows (deposits/withdrawals).
*   **Inputs:**
    1.  Initial Value (Negative Flow)
    2.  All Deposits/Withdrawals (Negative/Positive Flows) at their specific dates.
    3.  Final Value (Positive Flow)
*   **Why?** A simple percentage gain `(End / Start) - 1` is invalid if you added fresh cash halfway through the year. XIRR solves this.

### 4.5 FX Handling
*   **Transactions:** Converted to Base Currency using the *actual* exchange rate at the moment of the trade (stored in `exchange_rate` column).
*   **Current Value:** `(Qty * Live Price * Live FX Rate)`.
*   **FX Impact:** The system distinguishes between "Stock Performance" (Asset price change) and "FX Performance" (Currency fluctuation) in the Detailed Reports.
