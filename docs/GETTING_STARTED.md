# 🏁 Getting Started: A-Z Guide

Welcome to Project Kodak! This guide will take you from a fresh computer to a fully functioning investment dashboard in minutes. No advanced coding skills required.

---

## 🛠 Phase 1: Preparation

1.  **Install Python:** Download and install [Python 3.9+](https://www.python.org/downloads/). 
    *   **CRITICAL:** During installation, check the box that says **"Add Python to PATH"**.
2.  **Install Git:** Download and install [Git](https://git-scm.com/downloads).
3.  **Download Project:** Open a terminal (PowerShell on Windows) and run:
    ```powershell
    git clone https://github.com/SamirStandnes/kodak-portfolio.git
    cd kodak-portfolio
    ```
4.  **Install Dependencies:**
    ```powershell
    pip install -r requirements.txt
    ```
5.  **Create Database:**
    ```powershell
    python -m kodak.setup.initialize_database
    ```

---

## 🤖 Phase 2: Adding a Broker (The "AI Magic" Way)

If you use a broker we haven't supported yet (e.g., "Coinbase"), follow this 2-minute workflow:

1.  **Create Folder:** Inside `data/new_raw_transactions/`, create a folder named `coinbase`.
2.  **Place File:** Put your exported transaction file (CSV or Excel) into that folder.
3.  **Get AI Context:** Run this command to analyze the file:
    ```powershell
    python -m kodak.maintenance.inspect_file data/new_raw_transactions/coinbase/your_file.csv
    ```
4.  **Generate Parser:**
    *   Copy the output from the terminal.
    *   Go to ChatGPT or Claude.
    *   Paste the output and add this prompt:
    > "Write a Python parser function `def parse(file_path):` for this data. It must return a list of dictionaries following the standard schema [See Schema Below]."
5.  **Save:** Create a file named `kodak/pipeline/parsers/coinbase.py` and paste the AI's code inside.

---

## 📈 Phase 3: Run the Pipeline

Once your files are in their folders:

1.  **Process Data:**
    ```powershell
    .\workflows\add_transactions.ps1
    ```
    *   Follow the prompts. Type `y` when asked to commit transactions.
2.  **Open Dashboard:**
    ```powershell
    streamlit run kodak/dashboard/Home.py
    ```

---

## 📋 Standard Transaction Schema (For AI)

When asking an AI to write a parser, provide this schema:

```python
{
    'external_id': str(uuid.uuid4()),
    'account_external_id': 'Unique ID of the account',
    'isin': 'ISIN code',
    'symbol': 'Ticker Symbol',
    'date': 'YYYY-MM-DD',
    'type': 'BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAWAL, INTEREST, or FEE',
    'quantity': float,
    'price': float,
    'amount': float (original currency),
    'currency': 'USD, EUR, etc.',
    'amount_local': float (value in BASE_CURRENCY),
    'exchange_rate': float (Rate to convert amount -> amount_local),
    'description': 'Transaction notes',
    'source_file': os.path.basename(file_path),
    'fee': float,
    'fee_currency': 'Currency code',
    'fee_local': float (fee in BASE_CURRENCY)
}
```

---

## 🔄 Daily Maintenance

*   **Got new trades?** Drop the files in and run `.\workflows\add_transactions.ps1`.
*   **Just want latest prices?** Run `.\workflows\refresh_market_data.ps1`.
