#!/usr/bin/env python3
"""
Estate Sales Notifier
Scrapes estatesales.net for sales within 15 miles of Austin 78759
and creates Google Calendar events with notifications.
"""

from __future__ import annotations

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build


# Configuration
BASE_URL = "https://www.estatesales.net/TX/Austin/78759"
MAX_DISTANCE_MILES = 15

# Calendar IDs (your Gmail addresses)
CALENDAR_IDS = [
    "richard.allman7@gmail.com",
    "Bschlapkohl13@gmail.com",
]

# Path to service account credentials
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")


def fetch_estate_sales() -> list[dict]:
    """Fetch and parse estate sales from the website."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(BASE_URL, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    sales = []

    # Find all sale listings - they use <a class="sale-row"> elements
    sale_rows = soup.find_all("a", class_="sale-row")

    for row in sale_rows:
        sale = parse_sale_card(row)
        if sale and is_within_distance(sale.get("distance")):
            sales.append(sale)

    return sales


def parse_sale_card(card) -> Optional[dict]:
    """Parse a single sale card element."""
    try:
        sale = {}

        # Get link - the card itself is an <a> tag
        href = card.get("href", "")
        if href.startswith("/"):
            sale["url"] = f"https://www.estatesales.net{href}"
        elif href:
            sale["url"] = href
        else:
            return None  # Skip if no link

        # Extract zip code from URL (e.g., /TX/Austin/78759/12345)
        zip_match = re.search(r"/(\d{5})/", href)
        sale["zip"] = zip_match.group(1) if zip_match else ""

        # Get title from h3
        title_elem = card.find("h3")
        sale["title"] = title_elem.get_text(strip=True) if title_elem else "Estate Sale"

        # Get address
        address_elem = card.find(class_=re.compile(r"sale-row__address"))
        sale["address"] = address_elem.get_text(strip=True) if address_elem else ""

        # Get dates
        date_elem = card.find(class_=re.compile(r"sale-row__date"))
        sale["dates"] = date_elem.get_text(strip=True) if date_elem else ""

        # Get distance
        distance_elem = card.find(class_=re.compile(r"sale-row__distance"))
        if distance_elem:
            distance_text = distance_elem.get_text(strip=True)

            # Handle "Nearby" or "Less than X miles"
            if "nearby" in distance_text.lower():
                sale["distance"] = 0
                sale["distance_text"] = "Nearby"
            elif "less than" in distance_text.lower():
                sale["distance"] = 0
                sale["distance_text"] = "Nearby"
            else:
                # Extract just the number and "mi" part
                match = re.search(r"(\d+(?:\.\d+)?)\s*mi", distance_text, re.IGNORECASE)
                if match:
                    sale["distance"] = float(match.group(1))
                    sale["distance_text"] = f"{match.group(1)} mi"
                else:
                    sale["distance"] = None
                    sale["distance_text"] = ""
        else:
            sale["distance"] = None
            sale["distance_text"] = ""

        return sale
    except Exception as e:
        print(f"Error parsing sale card: {e}")
        return None


def parse_distance(text: str) -> Optional[float]:
    """Extract numeric distance from text like '5.2 mi' or '12 miles'."""
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None


def is_within_distance(distance: Optional[float]) -> bool:
    """Check if distance is within the max range."""
    if distance is None:
        return True  # Include if we can't determine distance
    return distance <= MAX_DISTANCE_MILES


def format_date_range(date_text: str) -> str:
    """Clean up and format date ranges from the website."""
    if not date_text:
        return ""

    # Remove everything after status words and distance info
    clean_text = re.split(r"(Going|Starts|Started|Ongoing|Ended|Nearby|miles|away)", date_text, flags=re.IGNORECASE)[0]
    clean_text = clean_text.replace("\u200c", "").replace("\u200b", "")

    # Preprocess: split stuck-together numbers before am/pm
    # "119am" -> "11 9am", "1110am" -> "11 10am"
    def split_time(m):
        digits = m.group(1)
        ampm = m.group(2)
        # Try to extract valid hour (1-12) from the end
        if len(digits) >= 2 and digits[-2:] in ["10", "11", "12"]:
            hour = digits[-2:]
            prefix = digits[:-2]
        else:
            hour = digits[-1]
            prefix = digits[:-1]
        if prefix:
            return f"{prefix} {hour}{ampm}"
        return f"{hour}{ampm}"

    clean_text = re.sub(r"(\d{2,})(am|pm)", split_time, clean_text, flags=re.IGNORECASE)

    # Now match time pattern
    time_match = re.search(r"(1[0-2]|[1-9])\s*(am|pm)\s*to\s*(1[0-2]|[1-9])\s*(am|pm)", clean_text, re.IGNORECASE)
    time_str = ""
    time_pos = len(clean_text)

    if time_match:
        time_str = f"{time_match.group(1)}{time_match.group(2).lower()}-{time_match.group(3)}{time_match.group(4).lower()}"
        time_pos = time_match.start()

    # Get everything before the time for date parsing
    date_section = clean_text[:time_pos]

    # Find month and extract day numbers
    date_match = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", date_section)

    date_str = ""
    if date_match:
        month = date_match.group(1)
        after_month = date_section[date_match.end():]

        # Extract all numbers
        all_nums = re.findall(r"\d+", after_month)

        # Filter to valid day numbers (1-31)
        days = [n for n in all_nums if 1 <= int(n) <= 31]

        if len(days) == 1:
            date_str = f"{month} {days[0]}"
        elif len(days) >= 2:
            date_str = f"{month} {days[0]}-{days[-1]}"

    if date_str and time_str:
        return f"{date_str}, {time_str}"
    elif date_str:
        return date_str
    elif time_str:
        return time_str
    else:
        return ""


def format_message(sales: list[dict]) -> str:
    """Format the sales into a clean, readable message."""
    if not sales:
        return "No estate sales found within 15 miles this week."

    lines = ["ESTATE SALES THIS WEEKEND", "Near Austin 78759", ""]

    for i, sale in enumerate(sales[:10], 1):
        title = sale["title"][:45]
        distance = sale.get("distance_text", "")
        dates = format_date_range(sale.get("dates", ""))
        url = sale["url"]

        # Clean title line
        if distance:
            lines.append(f"{i}. {title} [{distance}]")
        else:
            lines.append(f"{i}. {title}")

        # Date/time on its own line
        if dates:
            lines.append(f"   {dates}")

        # Link
        lines.append(f"   {url}")
        lines.append("")

    if len(sales) > 10:
        lines.append(f"+ {len(sales) - 10} more at {BASE_URL}")

    return "\n".join(lines)


def get_calendar_service():
    """Get authenticated Google Calendar service."""
    # Check for credentials JSON in environment variable (for GitHub Actions)
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")

    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
    elif os.path.exists(CREDENTIALS_FILE):
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
    else:
        raise Exception("No Google credentials found. Set GOOGLE_CREDENTIALS_JSON or provide credentials.json")

    return build("calendar", "v3", credentials=creds)


def send_notification(message: str):
    """Create Google Calendar event with popup notification."""
    service = get_calendar_service()

    # Event starts in 2 minutes, triggers notification immediately
    now = datetime.utcnow()
    start_time = now + timedelta(minutes=2)
    end_time = start_time + timedelta(minutes=30)

    event = {
        "summary": "Estate Sales This Weekend",
        "description": message,
        "start": {
            "dateTime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "UTC",
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 1},
            ],
        },
    }

    for calendar_id in CALENDAR_IDS:
        try:
            created = service.events().insert(calendarId=calendar_id, body=event).execute()
            print(f"Calendar event created for {calendar_id}: {created.get('htmlLink')}")
        except Exception as e:
            print(f"Failed to create event for {calendar_id}: {e}")


def main():
    """Main entry point."""
    print(f"Fetching estate sales from {BASE_URL}...")

    try:
        sales = fetch_estate_sales()
        print(f"Found {len(sales)} sales within {MAX_DISTANCE_MILES} miles")

        message = format_message(sales)
        print(f"\nMessage ({len(message)} chars):")
        print(message)

        print("\nSending calendar invite notifications...")
        send_notification(message)

        print("\nDone!")
    except Exception as e:
        error_msg = f"Estate Sales Notifier Error: {e}"
        print(error_msg)
        send_notification(error_msg)
        raise


if __name__ == "__main__":
    main()
