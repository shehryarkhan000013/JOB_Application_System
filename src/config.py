"""
config.py — Central configuration loader for the Auto-Bewerbung System.

All environment variables are loaded here from the project's .env file.
Any other module that needs configuration imports from this module —
never reads from os.getenv() directly.

Raises:
    ValueError: On startup if any required environment variable is missing,
                providing a clear, actionable error message.
"""

import os
from dotenv import load_dotenv

# Load .env file from the project root (one level above src/)
_ENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=_ENV_PATH)


def _require(key: str) -> str:
    """Fetches a required environment variable, raising an error if absent."""
    value = os.getenv(key)
    if not value:
        raise ValueError(
            f"\n[CONFIG ERROR] Required environment variable '{key}' is not set.\n"
            f"  -> Copy .env.example to .env and fill in all required values.\n"
        )
    return value


# --- Google Maps Platform ---
GOOGLE_MAPS_API_KEY: str = _require("GOOGLE_MAPS_API_KEY")

# --- Gmail Credentials ---
GMAIL_USER: str = _require("GMAIL_USER")
GMAIL_APP_PASSWORD: str = _require("GMAIL_APP_PASSWORD")

# --- Applicant Details (populates email templates) ---
APPLICANT_NAME: str = _require("APPLICANT_NAME")
APPLICANT_ADDRESS: str = _require("APPLICANT_ADDRESS")
APPLICANT_PHONE: str = _require("APPLICANT_PHONE")
APPLICANT_EMAIL: str = _require("APPLICANT_EMAIL")

# --- CV Configuration ---
CV_FILENAME: str = os.getenv("CV_FILENAME", "CV.pdf")

# --- Campaign Settings ---
DAILY_EMAIL_LIMIT: int = int(os.getenv("DAILY_EMAIL_LIMIT", "20"))

# --- Search Configuration ---
_DEFAULT_KEYWORDS = [
    "Restaurant", "Hotel", "Cafe", "Logistik", "Lager",
    "Supermarkt", "Fast Food", "Catering", "Reinigung"
]
_DEFAULT_DISTRICTS = [
    "Mitte, Berlin", "Kreuzberg, Berlin", "Neukölln, Berlin",
    "Friedrichshain, Berlin", "Charlottenburg, Berlin", "Schöneberg, Berlin"
]

_keywords_env = os.getenv("SEARCH_KEYWORDS")
SEARCH_KEYWORDS: list[str] = (
    [k.strip() for k in _keywords_env.split(",")]
    if _keywords_env
    else _DEFAULT_KEYWORDS
)

_districts_env = os.getenv("SEARCH_DISTRICTS")
SEARCH_DISTRICTS: list[str] = (
    [d.strip() for d in _districts_env.split(",")]
    if _districts_env
    else _DEFAULT_DISTRICTS
)
