# Auto-Bewerbung System 🤖

> **A fully automated job application pipeline** that discovers local businesses via the Google Places API, extracts contact emails using Playwright, generates personalised German application emails from configurable templates, and dispatches them via Gmail SMTP — all while persisting state to a local SQLite database to prevent duplicate sends.

Built as a portfolio project to demonstrate applied Python engineering, web automation, and secure system design.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        src/main.py                              │
│                  (Orchestration Entry Point)                     │
└──────┬──────────────┬──────────────┬───────────────┬────────────┘
       │              │              │               │
       ▼              ▼              ▼               ▼
 discovery.py    scraper.py   email_drafter.py   report_generator.py
 Google Places   Playwright   Template Engine    Excel Dashboard
 API → leads.db  → leads.db   → applications.json → .xlsx
       │              │              │
       └──────────────┴──────────────┘
                      │
               database.py (SQLite)
                      │
              ┌───────┴────────┐
          config.py        sync_sent.py
        (env loader)     (IMAP dedup)
                              │
                         sender.py
                       (SMTP dispatch)
```

**Pipeline Stages:**

| Stage        | Module                | Input                | Output                                    |
| ------------ | --------------------- | -------------------- | ----------------------------------------- |
| 1. Discovery | `discovery.py`        | Keywords + Districts | `leads.db` (status: `Found`)              |
| 2. Scraping  | `scraper.py`          | Leads with websites  | `leads.db` (status: `Contact Info Found`) |
| 3. Drafting  | `email_drafter.py`    | Leads with emails    | `applications.json`                       |
| 4. Review    | _Manual step_         | `applications.json`  | Human approval                            |
| 5. Sending   | `sender.py`           | `applications.json`  | Emails sent + DB updated                  |
| 6. Reporting | `report_generator.py` | `leads.db`           | `Campaign_Report.xlsx`                    |

---

## Key Technical Features

- **🌐 Google Places API Integration** — Paginated business discovery across multiple keywords and geographic districts with automatic deduplication.
- **🎭 Playwright Web Automation** — Headless Chromium scraping with randomised delays, human-mimicking User-Agent headers, and intelligent Impressum/Kontakt page discovery for German business websites.
- **📧 Secure SMTP Email Dispatch** — Gmail SMTP SSL with App Password authentication. Anti-spam delays (175–440s) between sends. Configurable daily send limit.
- **🔄 IMAP Deduplication** — Syncs with the live Gmail Sent folder before each run to prevent re-sending to already-contacted businesses, even across multiple runs.
- **🗄️ SQLite State Persistence** — Full pipeline state tracked in a local database. Resumable — restart at any phase without reprocessing completed steps.
- **🔒 Secure Configuration** — Zero hardcoded credentials. All secrets and personal details loaded from environment variables via `python-dotenv`. Startup fails fast with clear error messages if any required variable is missing.
- **📊 Excel Analytics Dashboard** — Auto-generated XlsxWriter report with a formatted data table and a pie chart of pipeline status distribution.

---

## Project Structure

```
Auto-Bewerbung System/
├── src/
│   ├── __init__.py
│   ├── main.py            # Pipeline orchestrator
│   ├── config.py          # Environment variable loader (single source of truth)
│   ├── database.py        # SQLite persistence layer
│   ├── discovery.py       # Google Places API lead discovery
│   ├── scraper.py         # Playwright email scraper
│   ├── email_drafter.py   # German email template engine
│   ├── sender.py          # Gmail SMTP dispatcher
│   ├── sync_sent.py       # Gmail IMAP deduplication
│   └── report_generator.py# Excel analytics report
├── .env.example           # Safe-to-commit environment template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Installation

### 1. Prerequisites

- Python 3.11+
- A Google Cloud account with the **Places API** enabled
- A Gmail account with a [Gmail App Password](https://myaccount.google.com/apppasswords) generated

### 2. Clone and set up the environment

```bash
git clone https://github.com/your-username/auto-bewerbung-system.git
cd auto-bewerbung-system

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt

# Install the Playwright browser engine
playwright install chromium
```

### 3. Configure environment variables

```bash
# Copy the template
cp .env.example .env
```

Open `.env` and fill in **all** required values:

```dotenv
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password_here

APPLICANT_NAME=Your Full Name
APPLICANT_ADDRESS=Your Street, 12345 Your City
APPLICANT_PHONE=+49 000 00000000
APPLICANT_EMAIL=your.email@example.com

CV_FILENAME=Your_CV.pdf         # must exist in the project root
DAILY_EMAIL_LIMIT=20
```

### 4. Add your CV

Place your CV PDF file in the **project root directory**. The filename must exactly match the `CV_FILENAME` value in your `.env`.

---

## How to Run

### Full pipeline (Discovery → Scraping → Drafting → Report)

```bash
python -m src.main
```

### Send emails (manual step — run after reviewing `applications.json`)

```bash
python -m src.sender
```

### Run individual modules

```bash
python -m src.discovery     # Discover new leads only
python -m src.scraper       # Scrape emails only
python -m src.email_drafter # Draft emails only
python -m src.report_generator  # Regenerate Excel report
```

---

## Safety & Ethics

- **Anti-spam delays** (175–440 seconds) are enforced between every email send.
- **Daily send limits** are configurable and enforced before each run.
- **IMAP deduplication** prevents any business from receiving more than one application.
- **Database deduplication** prevents re-processing leads that have already been scraped or contacted.
- This tool is intended for **personal job seeking** only. Respect robots.txt and website terms of service when scraping.

---

## Tech Stack

| Technology             | Role                            |
| ---------------------- | ------------------------------- |
| Python 3.11+           | Core language                   |
| Playwright             | Headless browser automation     |
| Google Maps Places API | Business lead discovery         |
| BeautifulSoup4         | HTML parsing                    |
| smtplib / imaplib      | Email dispatch and IMAP sync    |
| SQLite3                | Local state persistence         |
| Pandas + XlsxWriter    | Analytics report generation     |
| python-dotenv          | Secure configuration management |

---
