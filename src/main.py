"""
main.py — Orchestrating entry point for the Auto-Bewerbung System.

Runs the full job-application pipeline in sequence:
  1. Discovery  — finds business leads via Google Places API
  2. Scraping   — extracts contact emails via Playwright
  3. Drafting   — generates personalised German application emails
  4. Reporting  — produces an Excel analytics dashboard

The email send step (sender.py) is intentionally kept separate and must
be triggered manually to allow human review before any emails are sent.

Usage:
    python -m src.main
"""

import sys
import sqlite3

import pandas as pd

import src.database as database
import src.discovery as discovery
import src.scraper as scraper
import src.email_drafter as email_drafter
import src.report_generator as report_generator
from src import config  # Triggers env validation — fails fast if .env is missing


def print_pipeline_summary() -> None:
    """Prints a terminal summary of the current leads database state."""
    print("\n" + "=" * 56)
    print("  PIPELINE SUMMARY")
    print("=" * 56)

    try:
        conn = database.get_connection()
        df = pd.read_sql_query("SELECT * FROM leads", conn)
        conn.close()

        if df.empty:
            print("  No leads in the database yet.")
            return

        print(f"  Total leads discovered : {len(df)}")
        print("\n  Status breakdown:")
        for status, count in df['status'].value_counts().items():
            print(f"    · {status:<25} {count}")

        drafted = df[df['status'] == 'Drafted']
        if not drafted.empty:
            print(f"\n  Ready to send ({len(drafted)} drafts):")
            print(drafted[['business_name', 'email']].to_string(index=False, justify='left'))

    except Exception as e:
        print(f"  [ERROR] Could not generate summary: {e}")

    print("=" * 56)


def main() -> None:
    """Runs the complete lead-generation and email-drafting pipeline.

    Phases:
    1. Initialise the SQLite database.
    2. Discover business leads via the Google Places API.
    3. Scrape each lead's website for a contact email address.
    4. Generate personalised German application email drafts.
    5. Print a pipeline summary to the terminal.
    6. Export an Excel analytics report.
    """
    print("╔══════════════════════════════════════╗")
    print("║    Auto-Bewerbung System — v2.0      ║")
    print("╚══════════════════════════════════════╝\n")

    # ── Phase 1: Initialise ─────────────────────────────────────────────────
    print("Phase 0 │ Initialising database...")
    database.init_db()

    # ── Phase 2: Discovery ──────────────────────────────────────────────────
    print(f"\nPhase 1 │ Discovery")
    print(f"  Keywords : {config.SEARCH_KEYWORDS}")
    print(f"  Districts: {config.SEARCH_DISTRICTS}\n")

    total_discovered = 0
    for keyword in config.SEARCH_KEYWORDS:
        for district in config.SEARCH_DISTRICTS:
            count = discovery.discover_leads(
                keyword=keyword,
                location=district,
                max_results=60  # Google Places API max per query
            )
            total_discovered += count

    print(f"\n  -> Discovery complete. {total_discovered} new leads added.")

    # ── Phase 3: Scraping ───────────────────────────────────────────────────
    print("\nPhase 2 │ Deep Scraping (Playwright)")
    scraper.run_scraper()

    # ── Phase 4: Email Drafting ─────────────────────────────────────────────
    print("\nPhase 3 │ Drafting Emails")
    draft_count = email_drafter.draft_emails()
    print(f"  -> {draft_count} drafts written to applications.json")

    # ── Phase 5: Summary & Report ───────────────────────────────────────────
    print_pipeline_summary()

    print("\nPhase 4 │ Generating Excel Report...")
    report_generator.generate_excel_report()

    print(
        "\n✓ Pipeline complete.\n"
        "  Review applications.json, then run:\n"
        "    python -m src.sender\n"
        "  to dispatch emails.\n"
    )


if __name__ == '__main__':
    main()
