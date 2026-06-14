"""
discovery.py — Lead discovery via the Google Places API.

Uses the Google Maps Places API to search for businesses matching
configured keywords and locations, then persists new leads to the
local database.
"""

import time
import googlemaps
import src.database as database
from src import config


def discover_leads(
    keyword: str = 'Restaurant',
    location: str = 'Berlin',
    max_results: int = 20
) -> int:
    """Discovers business leads using the Google Places API.

    Searches for businesses matching the given keyword and location,
    fetches website details for each result, and stores new leads in
    the database. Handles Google's pagination via next_page_token.

    Args:
        keyword:     The search term (e.g. 'Restaurant', 'Hotel').
        location:    The geographic area to search (e.g. 'Mitte, Berlin').
        max_results: Maximum number of new leads to add per call.

    Returns:
        The number of new leads added to the database.
    """
    print(f"Starting discovery for '{keyword}' in '{location}'...")
    gmaps = googlemaps.Client(key=config.GOOGLE_MAPS_API_KEY)

    leads_found = 0
    places_result = gmaps.places(query=f'{keyword} in {location}')

    if 'results' not in places_result:
        print("No results found or an error occurred with the Places API.")
        return 0

    database.init_db()

    while True:
        for place in places_result.get('results', []):
            if leads_found >= max_results:
                break

            place_id: str = place.get('place_id', '')
            name: str = place.get('name', 'Unknown')

            details = gmaps.place(place_id=place_id, fields=['name', 'website'])
            website: str | None = details.get('result', {}).get('website')

            if website:
                added = database.add_lead(name, website)
                if added:
                    print(f"  [+] New lead: {name} — {website}")
                    leads_found += 1
                else:
                    print(f"  [=] Already exists: {name}")

        if leads_found >= max_results:
            break

        next_page_token: str | None = places_result.get('next_page_token')
        if not next_page_token:
            break

        # Google requires a short delay before next_page_token becomes valid
        time.sleep(2)
        try:
            places_result = gmaps.places(page_token=next_page_token)
        except Exception as e:
            print(f"  [ERROR] Failed to fetch next page: {e}")
            break

    print(f"Discovery complete. Added {leads_found} new leads.")
    return leads_found


if __name__ == '__main__':
    discover_leads(keyword='Restaurant', location='Berlin', max_results=20)
