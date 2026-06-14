"""
sender.py — SMTP email dispatch with anti-spam and deduplication logic.

Reads drafted applications from applications.json, cross-references both
the local SQLite database and the live Gmail Sent folder (via IMAP) to
prevent duplicate sends, attaches the applicant's CV, and sends each
email via Gmail SMTP SSL.

All credentials and personal details are loaded from environment variables
via config.py — no sensitive data is hardcoded in this file.
"""

import json
import os
import smtplib
import time
import random
from email.message import EmailMessage
from typing import Optional

import src.database as database
import src.sync_sent as sync_sent
from src import config


def send_emails() -> None:
    """Executes the email dispatch pipeline for all drafted applications.

    Pipeline:
    1. Loads drafted applications from applications.json.
    2. Syncs the Gmail Sent folder to build a master deduplication list.
    3. For each application: checks for duplicates, constructs the email
       with CV attachment, sends via SMTP SSL, and updates the database.
    4. Enforces a configurable daily send limit and anti-spam delays.

    All credentials and applicant info are sourced from config.py.
    """
    # --- Load drafted applications ---
    apps_path = os.path.join(os.path.dirname(__file__), '..', 'applications.json')
    try:
        with open(apps_path, 'r', encoding='utf-8') as f:
            applications = json.load(f)
    except FileNotFoundError:
        print("[ERROR] applications.json not found. Run email_drafter.py first.")
        return

    if not applications:
        print("[INFO] No applications to send.")
        return

    # --- Validate CV attachment exists ---
    cv_path = os.path.join(os.path.dirname(__file__), '..', config.CV_FILENAME)
    if not os.path.exists(cv_path):
        print(
            f"[ERROR] CV file '{config.CV_FILENAME}' not found in project root.\n"
            f"  -> Ensure CV_FILENAME in your .env matches the actual filename."
        )
        return

    print(f"Starting send run. {len(applications)} applications queued. "
          f"Daily limit: {config.DAILY_EMAIL_LIMIT}.")

    # --- Build deduplication set ---
    backup_path = os.path.join(os.path.dirname(__file__), '..', 'backup_contacted.txt')
    backup_contacted: set[str] = set()
    if os.path.exists(backup_path):
        with open(backup_path, 'r') as b:
            backup_contacted = {line.strip() for line in b if line.strip()}

    # Merge with live Gmail Sent folder for robust deduplication
    live_sent = sync_sent.get_sent_emails(
        config.GMAIL_USER, config.GMAIL_APP_PASSWORD, days_back=7
    )
    backup_contacted.update(live_sent)

    emails_sent_today = 0

    try:
        for index, app in enumerate(applications, start=1):
            if emails_sent_today >= config.DAILY_EMAIL_LIMIT:
                print(f"\n[LIMIT] Daily limit of {config.DAILY_EMAIL_LIMIT} reached. Stopping.")
                break

            business_name: str = app['business_name']
            recipient_email: str = app['email']
            subject: str = app['subject']
            body: str = app['body']

            print(f"[{index}/{len(applications)}] -> {business_name} ({recipient_email})")

            # --- Deduplication check ---
            if recipient_email in backup_contacted:
                print(f"  [SKIP] Already contacted.")
                continue

            conn = database.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT status FROM leads WHERE email = ?", (recipient_email,)
                )
                row = cursor.fetchone()
                if row and row[0] == 'Contacted':
                    print(f"  [SKIP] DB status is 'Contacted'.")
                    continue
            finally:
                conn.close()

            # --- Compose email ---
            msg = EmailMessage()
            msg['From'] = config.GMAIL_USER
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.set_content(body)

            try:
                with open(cv_path, 'rb') as pdf_file:
                    msg.add_attachment(
                        pdf_file.read(),
                        maintype='application',
                        subtype='pdf',
                        filename=config.CV_FILENAME
                    )
            except Exception as e:
                print(f"  [ERROR] Could not read CV: {e}")
                continue

            # --- Send via SMTP SSL ---
            email_sent = False
            try:
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                    smtp.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
                    smtp.send_message(msg)
                print("  [OK] Sent.")
                email_sent = True
                emails_sent_today += 1
            except Exception as e:
                print(f"  [FAILED] SMTP error: {e}")
                time.sleep(10)
                continue

            # --- Update database (separate try block — DB failure must not skip delay) ---
            if email_sent:
                try:
                    database.update_lead_status_by_email(recipient_email, 'Contacted')
                    backup_contacted.add(recipient_email)
                except Exception as e:
                    print(f"  [WARN] DB update failed: {e}. Writing to backup file.")
                    with open(backup_path, 'a') as b:
                        b.write(f"{recipient_email}\n")
                    backup_contacted.add(recipient_email)

            # --- Anti-spam delay ---
            if index < len(applications) and emails_sent_today < config.DAILY_EMAIL_LIMIT:
                delay = random.randint(175, 440)
                print(f"  [WAIT] Pausing {delay}s to avoid spam filters...")
                time.sleep(delay)

    except Exception as e:
        print(f"[CRITICAL] Unexpected error: {e}")

    print(f"\nRun complete. {emails_sent_today} email(s) sent today.")


if __name__ == '__main__':
    send_emails()
