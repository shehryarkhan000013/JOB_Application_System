"""
sync_sent.py — Gmail IMAP synchronisation for sent-email deduplication.

Connects to the Gmail Sent folder via IMAP SSL and retrieves the set of
recipient email addresses from messages sent within a configurable window.
This is used by sender.py to prevent re-sending applications to businesses
that were already contacted in a previous run.

Only the 'To' header is fetched (not message bodies), making this
significantly faster than downloading full emails.
"""

import imaplib
import email
import re
import datetime
from typing import Optional


def get_sent_emails(
    username: str,
    password: str,
    days_back: int = 7
) -> set[str]:
    """Retrieves recipient addresses from the Gmail Sent folder.

    Connects via IMAP SSL, locates the Sent folder (supporting both
    English 'Sent Mail' and German 'Gesendet' folder names), and fetches
    only the 'To' headers of messages sent in the last `days_back` days.

    Args:
        username:  The Gmail address to authenticate with.
        password:  A valid Gmail App Password (not the account password).
        days_back: How many days back to scan the Sent folder.

    Returns:
        A set of unique email addresses that were previously contacted.
        Returns an empty set if the IMAP connection fails.
    """
    print(f"  [SYNC] Checking Gmail Sent folder (last {days_back} days)...")
    sent_to: set[str] = set()

    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(username, password)

        # Locate the Sent folder — name differs by Gmail language setting
        _, folders = imap.list()
        sent_folder = '"[Gmail]/Sent Mail"'
        for folder_bytes in folders:
            folder_name = folder_bytes.decode()
            if 'sent' in folder_name.lower() or 'gesendet' in folder_name.lower():
                sent_folder = folder_name.split(' "/" ')[-1]
                break

        status, _ = imap.select(sent_folder)
        if status != 'OK':
            print("  [SYNC] Could not select Sent folder — skipping IMAP sync.")
            return sent_to

        past_date = datetime.date.today() - datetime.timedelta(days=days_back)
        date_str = past_date.strftime("%d-%b-%Y")
        _, messages = imap.search(None, f'SINCE "{date_str}"')

        if not messages[0]:
            print("  [SYNC] No emails found in the specified timeframe.")
            return sent_to

        email_ids = messages[0].split()
        for e_id in email_ids:
            # Fetch only the To header — avoids downloading PDF attachments
            _, msg_data = imap.fetch(e_id, "(BODY.PEEK[HEADER.FIELDS (TO)])")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    to_header: Optional[str] = msg.get("To")
                    if to_header:
                        addresses = re.findall(
                            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                            to_header
                        )
                        sent_to.update(addresses)

        print(f"  [SYNC] Found {len(sent_to)} previously contacted addresses.")
        return sent_to

    except Exception as e:
        print(f"  [SYNC] IMAP error: {e}. Falling back to local tracking only.")
        return sent_to
