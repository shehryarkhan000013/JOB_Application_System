"""
database.py — SQLite persistence layer for the Auto-Bewerbung System.

Manages all reads and writes to the local leads.db SQLite database.
All other modules must interact with the database exclusively through
the functions defined here.
"""

import os
import sqlite3
from typing import Optional

# Database file stored in the project root
DB_PATH: str = os.path.join(os.path.dirname(__file__), '..', 'leads.db')


def get_connection() -> sqlite3.Connection:
    """Opens and returns a connection to the SQLite database.

    Returns:
        sqlite3.Connection: An active database connection with a 30-second
                            busy-timeout to handle concurrent access gracefully.
    """
    return sqlite3.connect(DB_PATH, timeout=30.0)


def init_db() -> None:
    """Creates the leads table if it does not already exist.

    This is idempotent and safe to call on every startup.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT    NOT NULL,
            website       TEXT,
            email         TEXT,
            status        TEXT    DEFAULT 'Found'
        )
    ''')
    conn.commit()
    conn.close()


def add_lead(business_name: str, website: str) -> bool:
    """Inserts a new lead if one with the same name or website does not exist.

    Args:
        business_name: The name of the business.
        website:       The URL of the business website.

    Returns:
        True if the lead was newly inserted, False if it already existed.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id FROM leads WHERE business_name = ? OR website = ?',
        (business_name, website)
    )
    if cursor.fetchone():
        conn.close()
        return False

    cursor.execute(
        'INSERT INTO leads (business_name, website, status) VALUES (?, ?, ?)',
        (business_name, website, 'Found')
    )
    conn.commit()
    conn.close()
    return True


def update_lead_email(lead_id: int, email: str) -> None:
    """Sets the email address for a lead and marks its status as found.

    Args:
        lead_id: The primary key of the lead to update.
        email:   The discovered contact email address.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE leads SET email = ?, status = ? WHERE id = ?',
        (email, 'Contact Info Found', lead_id)
    )
    conn.commit()
    conn.close()


def update_lead_status(lead_id: int, status: str) -> None:
    """Updates the pipeline status of a lead by its primary key.

    Args:
        lead_id: The primary key of the lead to update.
        status:  The new status string (e.g. 'Drafted', 'No Contact Info').
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE leads SET status = ? WHERE id = ?',
        (status, lead_id)
    )
    conn.commit()
    conn.close()


def update_lead_status_by_email(email: str, status: str) -> None:
    """Updates the pipeline status of a lead identified by its email address.

    Args:
        email:  The email address of the lead to update.
        status: The new status string (e.g. 'Contacted').
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE leads SET status = ? WHERE email = ?',
            (status, email)
        )
        conn.commit()
    finally:
        conn.close()


def get_leads_by_status(status: str) -> list[dict]:
    """Fetches all leads that match a given pipeline status.

    Args:
        status: The status string to filter by.

    Returns:
        A list of lead dictionaries with keys:
        id, business_name, website, email, status.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, business_name, website, email, status FROM leads WHERE status = ?',
        (status,)
    )
    leads = cursor.fetchall()
    conn.close()
    return [
        {'id': r[0], 'business_name': r[1], 'website': r[2], 'email': r[3], 'status': r[4]}
        for r in leads
    ]


def get_all_leads() -> list[dict]:
    """Fetches every lead in the database, regardless of status.

    Returns:
        A list of all lead dictionaries.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, business_name, website, email, status FROM leads')
    leads = cursor.fetchall()
    conn.close()
    return [
        {'id': r[0], 'business_name': r[1], 'website': r[2], 'email': r[3], 'status': r[4]}
        for r in leads
    ]


if __name__ == '__main__':
    init_db()
    print(f"Database initialised successfully at: {DB_PATH}")
