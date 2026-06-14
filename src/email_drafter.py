"""
email_drafter.py — Generates personalised German application email drafts.

Categorises each lead by business type and applies the appropriate German
email template. All applicant personal details (name, address, phone, email)
are loaded securely from environment variables via config.py — no PII is
hardcoded in this file.

Outputs a structured JSON file (applications.json) consumed by sender.py.
"""

import json
import os
import shutil
from typing import TypedDict

import src.database as database
from src import config


class EmailTemplate(TypedDict):
    """Typed structure for an email template."""
    subject: str
    body: str


# ---------------------------------------------------------------------------
# Email Templates (German)
# All personal details are injected at runtime from config.py.
# ---------------------------------------------------------------------------

_SIGNATURE = (
    "Mit freundlichen Grüßen,\n"
    "{applicant_name}\n"
    "{applicant_address}\n"
    "Telefon: {applicant_phone}\n"
    "E-Mail: {applicant_email}\n"
)

_TEMPLATE_RESTAURANT: EmailTemplate = {
    "subject": "Initiativbewerbung als studentische Aushilfe (Küchenhilfe / Spülkraft) – {applicant_name}",
    "body": (
        "Sehr geehrte Damen und Herren bei {business_name},\n\n"
        "ich schreibe Ihnen, um mich initiativ nach einer offenen Stelle als studentische Aushilfe "
        "oder Werkstudent in Ihrem Betrieb zu erkundigen. Ich bin Masterstudent und suche eine "
        "flexible Nebentätigkeit, idealerweise als Küchenhilfe oder Spülkraft.\n\n"
        "Ich bin pünktlich, zuverlässig und körperlich belastbar. Ich kann ab sofort starten und "
        "bin bei den Arbeitszeiten flexibel (auch am Wochenende oder abends).\n\n"
        "Mein Deutsch ist auf A2-Niveau (ich lerne aktiv weiter) und ich spreche fließend Englisch (C1).\n\n"
        "Im Anhang finden Sie meinen Lebenslauf. Ich freue mich von Ihnen zu hören!\n\n"
        + _SIGNATURE
    ),
}

_TEMPLATE_WAREHOUSE: EmailTemplate = {
    "subject": "Initiativbewerbung als studentische Aushilfe (Lagerhelfer / Verpacker) – {applicant_name}",
    "body": (
        "Sehr geehrte Damen und Herren bei {business_name},\n\n"
        "ich schreibe Ihnen, um mich initiativ nach einer offenen Stelle als studentische Aushilfe "
        "oder Werkstudent in Ihrem Betrieb zu erkundigen. Ich bin Masterstudent und suche eine "
        "flexible Nebentätigkeit, idealerweise als Lagerhelfer oder Verpacker.\n\n"
        "Ich habe bereits Erfahrung in der Logistik gesammelt. Ich bin pünktlich, zuverlässig und "
        "körperlich belastbar. Ich kann ab sofort starten und bin bei den Arbeitszeiten flexibel "
        "(auch nachts oder am Wochenende).\n\n"
        "Mein Deutsch ist auf A2-Niveau (ich lerne aktiv weiter) und ich spreche fließend Englisch (C1).\n\n"
        "Im Anhang finden Sie meinen Lebenslauf. Ich freue mich von Ihnen zu hören!\n\n"
        + _SIGNATURE
    ),
}

_TEMPLATE_CLEANING: EmailTemplate = {
    "subject": "Initiativbewerbung als studentische Aushilfe (Reinigungskraft) – {applicant_name}",
    "body": (
        "Sehr geehrte Damen und Herren bei {business_name},\n\n"
        "ich schreibe Ihnen, um mich initiativ nach einer offenen Stelle als studentische Aushilfe "
        "oder Werkstudent in Ihrem Betrieb zu erkundigen. Ich bin Masterstudent und suche eine "
        "flexible Nebentätigkeit, idealerweise als Reinigungskraft.\n\n"
        "Ich habe bereits Erfahrung in der Reinigung. Ich bin pünktlich, zuverlässig und arbeite "
        "sehr gründlich. Ich kann ab sofort starten und bin bei den Arbeitszeiten flexibel.\n\n"
        "Mein Deutsch ist auf A2-Niveau (ich lerne aktiv weiter) und ich spreche fließend Englisch (C1).\n\n"
        "Im Anhang finden Sie meinen Lebenslauf. Ich freue mich von Ihnen zu hören!\n\n"
        + _SIGNATURE
    ),
}

_TEMPLATE_HOTEL: EmailTemplate = {
    "subject": "Initiativbewerbung als studentische Aushilfe (Service / Housekeeping) – {applicant_name}",
    "body": (
        "Sehr geehrte Damen und Herren bei {business_name},\n\n"
        "ich schreibe Ihnen, um mich initiativ nach einer offenen Stelle als studentische Aushilfe "
        "oder Werkstudent in Ihrem Hotel zu erkundigen. Ich bin Masterstudent und suche eine "
        "flexible Nebentätigkeit, idealerweise als Aushilfe im Service oder im Housekeeping.\n\n"
        "Ich bin pünktlich, zuverlässig und habe ein gepflegtes Auftreten. Ich kann ab sofort "
        "starten und bin bei den Arbeitszeiten flexibel (auch an Wochenenden und Feiertagen).\n\n"
        "Mein Deutsch ist auf A2-Niveau (ich lerne aktiv weiter) und ich spreche fließend Englisch (C1).\n\n"
        "Im Anhang finden Sie meinen Lebenslauf. Ich freue mich von Ihnen zu hören!\n\n"
        + _SIGNATURE
    ),
}


def _categorise_business(name: str) -> EmailTemplate:
    """Selects the appropriate email template based on business name keywords.

    Args:
        name: The name of the business.

    Returns:
        The matching EmailTemplate dictionary.
    """
    name_lower = name.lower()

    if any(kw in name_lower for kw in ['hotel', 'hostel', 'pension', 'motel', 'resort', 'inn']):
        return _TEMPLATE_HOTEL
    if any(kw in name_lower for kw in ['reinigung', 'cleaning', 'putz', 'sauber', 'facility']):
        return _TEMPLATE_CLEANING
    if any(kw in name_lower for kw in [
        'logistik', 'lager', 'transport', 'liefer', 'spediti',
        'versand', 'cargo', 'handel', 'wholesale', 'großhandel', 'supply'
    ]):
        return _TEMPLATE_WAREHOUSE

    # Default: food/restaurant roles (most common search target)
    return _TEMPLATE_RESTAURANT


def draft_emails() -> int:
    """Generates personalised email drafts for all leads with contact info.

    Fetches leads in 'Contact Info Found' and 'Drafted' states, selects the
    appropriate German template for each, injects applicant details from
    config.py, and serialises all drafts to applications.json.

    Returns:
        The number of email drafts generated.
    """
    leads = database.get_leads_by_status('Contact Info Found')
    leads.extend(database.get_leads_by_status('Drafted'))

    if not leads:
        print("No leads with contact info to draft emails for.")
        return 0

    json_output = []
    drafts_created = 0

    # Applicant details sourced exclusively from environment variables
    applicant_vars = {
        "applicant_name":    config.APPLICANT_NAME,
        "applicant_address": config.APPLICANT_ADDRESS,
        "applicant_phone":   config.APPLICANT_PHONE,
        "applicant_email":   config.APPLICANT_EMAIL,
    }

    for lead in leads:
        lead_id: int = lead['id']
        business_name: str = lead['business_name']
        email: str = lead['email']

        template = _categorise_business(business_name)

        subject = template['subject'].format(**applicant_vars)
        body = template['body'].format(business_name=business_name, **applicant_vars)

        json_output.append({
            "business_name": business_name,
            "email":         email,
            "subject":       subject,
            "body":          body,
        })

        database.update_lead_status(lead_id, 'Drafted')
        drafts_created += 1

    output_path = os.path.join(os.path.dirname(__file__), '..', 'applications.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, indent=4, ensure_ascii=False)

    print(f"Generated {drafts_created} email drafts -> applications.json")
    return drafts_created


if __name__ == '__main__':
    # Clean old text draft directories if present
    old_dir = os.path.join(os.path.dirname(__file__), '..', 'email_drafts')
    if os.path.exists(old_dir):
        shutil.rmtree(old_dir)
        print("Cleared legacy email_drafts/ directory.")

    draft_emails()
