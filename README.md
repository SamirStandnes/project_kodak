# Kodak Portfolio Tracker 📈

A robust, multi-currency investment portfolio tracking system with a serverless-ready architecture.

## 🧐 Why Project Kodak?

Most investors today struggle with fragmented data spread across multiple brokerage accounts (Nordnet, Saxo, Robinhood, etc.). Existing solutions often fall into two traps:
1.  **SaaS Platforms:** Services like Shareville or other portfolio trackers require you to upload your sensitive financial data to their servers, compromising your privacy.
2.  **Manual Spreadsheets:** Maintaining a manual spreadsheet with multi-currency historical FX rates and automatic price updates is a nightmare.

**Project Kodak** provides a "Third Way":
*   **Unified View:** Combine all your accounts into one source of truth.
*   **Privacy First:** Your data stays in a local SQLite database on *your* machine.
*   **Automated:** Automated ingestion, historical FX enrichment, and live market pricing.
*   **Extensible:** Add any broker in minutes using our AI-assisted plugin system.

---

## 🚀 Key Features

*   **Plugin-Based Ingestion:** Add support for new brokers just by dropping a Python script into the `parsers/` folder.
*   **Multi-Currency Engine:** Automatic historical FX rate enrichment using Yahoo Finance.
*   **Deep Performance Analysis:** Tracks Realized/Unrealized Gains, Dividend yields, Interest expenses, and FX P&L.
*   **Staging Workflow:** Review and verify transactions before they hit your master database.
*   **Modern Dashboard:** Interactive UI built with Streamlit and Plotly.

---

## 🛠 Setup

For a detailed, step-by-step walkthrough from scratch, see our **[Getting Started Guide](GETTING_STARTED.md)**.

### 1. Prerequisites
Ensure you have **Python 3.9+** installed.

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/SamirStandnes/project_kodak.git
cd project_kodak
pip install -r requirements.txt
```

### 3. Initialize Database
Create your local SQLite database and structure:
```bash
python -m scripts.setup.initialize_database
```

---

## 📂 Project Structure

```text
├── data/
│   ├── new_raw_transactions/  <-- Place broker exports here
│   │   ├── nordnet/
│   │   └── saxo/
│   └── reference/             <-- ISIN and Account mappings
├── scripts/
│   ├── analysis/              <-- Terminal-based analysis tools
│   ├── dashboard/             <-- Streamlit UI code
│   ├── pipeline/              <-- Core data processing
│   │   └── parsers/           <-- Broker plugins
│   └── shared/                <-- Reusable logic & DB helpers
└── database/                  <-- SQLite storage and backups
```

---

## 🔄 Daily Workflow

### Adding New Transactions
1.  **Export:** Download your transaction history from your broker (e.g., Nordnet CSV or Saxo Excel).
2.  **Place:** Move the files to the matching folder in `data/new_raw_transactions/`.
3.  **Run Pipeline:** 
    ```powershell
    .\workflows\add_transactions.ps1
    ```
    *This will ingest files, ask for confirmation to commit to the DB, and then automatically fetch prices and FX rates.*

### Refreshing Prices (No new trades)
To see how your portfolio is doing today without adding new data:
```powershell
.\workflows\refresh_market_data.ps1
```

### Launching the Dashboard
```bash
streamlit run scripts/dashboard/Home.py
```

---

## 🧩 Adding a New Broker (Plugin System)

Project Kodak is designed to be infinitely extensible. To add a new broker (e.g., "Robinhood"):

1.  **Create Folder:** `data/new_raw_transactions/robinhood/`
2.  **Inspect Sample:** Run our helper to see the file structure:
    ```bash
    python -m scripts.maintenance.inspect_file path/to/sample.csv
    ```
3.  **Create Parser:** Create `scripts/pipeline/parsers/robinhood.py`.
4.  **Implement:** Define a `parse(file_path)` function that returns the standard transaction schema. 

*(Tip: You can paste the output of the inspection tool into an AI like ChatGPT/Claude to have it write the parser for you in seconds!)*

---

## ⚖️ License
MIT License - feel free to use and modify!

---
👀 **Curious about what's next?** Check out our [ROADMAP](ROADMAP.md)!
