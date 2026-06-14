"""
scraper.py — Playwright-based web scraper for extracting business contact emails.

For each lead discovered, visits the business website and attempts to extract
a contact email address. If none is found on the main page, it follows any
'Impressum' or 'Kontakt' links to secondary pages.

Uses headless Chromium via Microsoft Playwright with randomised delays to
mimic human browsing patterns and avoid rate-limiting.
"""

import re
import time
import random
from urllib.parse import urlparse
from typing import Optional

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

import src.database as database

# Matches business email addresses ending in .de or .com
_EMAIL_REGEX = re.compile(
    r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.(?:de|com)',
    re.IGNORECASE
)


def extract_emails_from_html(html_content: str) -> list[str]:
    """Parses raw HTML and returns all unique email addresses found.

    Uses BeautifulSoup to get clean page text, then applies a regex to
    find addresses ending in .de or .com (typical for German businesses).

    Args:
        html_content: Raw HTML string from a web page.

    Returns:
        A list of unique email addresses found in the page text.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(separator=' ')
    return list(set(_EMAIL_REGEX.findall(text)))


def scrape_website_for_email(url: str, page: Page) -> Optional[str]:
    """Visits a URL and attempts to extract a business contact email.

    Strategy:
    1. Load the main page and scan for emails.
    2. If none found, search anchor links for 'Impressum' or 'Kontakt'.
    3. Navigate to that secondary page and scan again.

    Args:
        url:  The business website URL to scrape.
        page: An active Playwright Page instance.

    Returns:
        The first email address found, or None if none was discovered.
    """
    print(f"  Scraping: {url}")
    try:
        time.sleep(random.uniform(1.0, 3.0))
        page.goto(url, timeout=30_000, wait_until='domcontentloaded')

        emails = extract_emails_from_html(page.content())
        if emails:
            return emails[0]

        # Search for Impressum / Kontakt links
        target_href: Optional[str] = None
        for link in page.locator('a').all():
            try:
                text = link.inner_text().lower()
                if 'impressum' in text or 'kontakt' in text:
                    target_href = link.get_attribute('href')
                    if target_href:
                        break
            except Exception:
                continue

        if not target_href:
            return None

        # Resolve relative URLs
        if target_href.startswith('/'):
            parsed = urlparse(url)
            target_url = f"{parsed.scheme}://{parsed.netloc}{target_href}"
        elif not target_href.startswith('http'):
            target_url = url.rstrip('/') + '/' + target_href.lstrip('/')
        else:
            target_url = target_href

        print(f"    → Following: {target_url}")
        time.sleep(random.uniform(1.0, 2.0))
        page.goto(target_url, timeout=30_000, wait_until='domcontentloaded')
        emails = extract_emails_from_html(page.content())
        return emails[0] if emails else None

    except PlaywrightTimeoutError:
        print(f"    → Timeout: {url}")
    except Exception as e:
        print(f"    → Error on {url}: {e}")

    return None


def run_scraper(retry_count: int = 2) -> None:
    """Runs the email-scraping pipeline for all leads with status 'Found'.

    Launches a headless Chromium browser, iterates through unscraped leads,
    and updates the database with discovered email addresses. Leads where no
    email is found are marked 'No Contact Info'.

    Args:
        retry_count: Number of scraping attempts per lead before giving up.
    """
    leads = database.get_leads_by_status('Found')

    if not leads:
        print("No new leads to scrape.")
        return

    print(f"Starting scraper for {len(leads)} leads...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
        )
        page = context.new_page()

        for lead in leads:
            lead_id: int = lead['id']
            url: str = lead['website']
            business_name: str = lead['business_name']

            email: Optional[str] = None
            for attempt in range(retry_count):
                email = scrape_website_for_email(url, page)
                if email:
                    break
                if attempt < retry_count - 1:
                    print(f"    → Retry {attempt + 2} for {url}")
                    time.sleep(2.0)

            if email:
                print(f"  [SUCCESS] {business_name}: {email}")
                database.update_lead_email(lead_id, email)
            else:
                print(f"  [FAILED]  No email found for {business_name}")
                database.update_lead_status(lead_id, 'No Contact Info')

        browser.close()

    print("Scraping complete.")


if __name__ == '__main__':
    run_scraper()
