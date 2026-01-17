# 🗺️ Project Roadmap

This document outlines the future direction of Project Kodak. We aim to make portfolio tracking accessible to everyone, regardless of their coding skills.

---

## ✅ Completed Features

### 🌐 Cloud Deployment (Web App)
**Status:** Complete

Access your portfolio dashboard from your phone or any browser via Heroku deployment.

**What's Included:**
- PostgreSQL database adapter (replaces SQLite for cloud)
- SQL translation layer (SQLite → PostgreSQL syntax)
- Password-protected dashboard
- Daily automatic price updates via Heroku Scheduler
- One-command data migration from local SQLite to cloud PostgreSQL

**See:** [Heroku Deployment Guide](../heroku/README.md)

---

## 🚀 Upcoming Features

### 1. 🤖 AI-Powered Auto-Onboarding (Magic Parsers)
**Goal:** Allow users to add *any* broker without writing a single line of code.

**The Vision:**
1.  User drops a file into a new folder (e.g., `data/new_raw_transactions/coinbase/`).
2.  User runs a wizard command: `.\add_broker.ps1`
3.  **The System takes over:**
    *   Detects the new file.
    *   Reads the header and sample data.
    *   Sends this context to an LLM (ChatGPT/Gemini).
    *   *AI writes the Python parser code automatically.*
    *   System saves the code to `kodak/pipeline/parsers/coinbase.py`.
    *   System runs a test ingestion to verify it works.
4.  **Result:** The user is ready to go in under 30 seconds.

**Requirements:**
*   Integration with OpenAI/Gemini API.
*   Secure handling of API keys.
*   Robust error checking (AI code verification).

---

### 2. 📊 Advanced Analytics
*   **Benchmarking:** Compare portfolio performance against indices (S&P 500, OSEBX).
*   **Tax Estimation:** Rough estimation of tax liabilities based on realized gains (Norwegian rules).
*   ~~**Dividend Calendar:** Forecast future dividend income based on historical data.~~ ✅ Done

### 3. ☁️ Optional Cloud Sync
*   Ability to securely backup the SQLite database to Google Drive or Dropbox.

---

## 💡 Have an idea?
Open an issue or submit a pull request!
