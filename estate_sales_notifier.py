#!/usr/bin/env python3
"""
Estate Sales Notifier
Scrapes estatesales.net for sales within 15 miles of Austin 78759
and sends SMS notifications via Twilio.
"""

from __future__ import annotations

import os
import re
import requests
from bs4 import BeautifulSoup
from twilio.rest import Client
from datetime import datetime
from typing import Optional


# Configuration
BASE_URL = "https://www.estatesales.net/TX/Austin/78759"
MAX_DISTANCE_MILES = 15
PHONE_NUMBERS = ["+19259844951", "+15126530151"]

# Twilio credentials (set as environment variables)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")


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
            # Clean up the text (remove "Nearby", extra labels)
            distance_text = re.sub(r"(Nearby|Less than|away)", "", distance_text).strip()
            sale["distance"] = parse_distance(distance_text)
            sale["distance_text"] = distance_text if distance_text else ""
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


def format_message(sales: list[dict]) -> str:
    """Format the sales into an SMS-friendly message."""
    if not sales:
        return "No estate sales found within 15 miles this week."

    today = datetime.now().strftime("%m/%d")
    lines = [f"Estate Sales Near Austin 78759 ({today}):", ""]

    for i, sale in enumerate(sales[:8], 1):  # Limit to 8 sales for SMS length
        title = sale["title"][:40]
        distance = sale.get("distance_text", "")
        dates = sale.get("dates", "")[:30]
        url = sale["url"]

        entry = f"{i}. {title}"
        if distance:
            entry += f" ({distance})"
        if dates:
            entry += f"\n   {dates}"
        entry += f"\n   {url}"

        lines.append(entry)
        lines.append("")

    if len(sales) > 8:
        lines.append(f"+ {len(sales) - 8} more sales. Visit {BASE_URL}")

    return "\n".join(lines)


def send_sms(message: str):
    """Send SMS to all configured phone numbers."""
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        print("Twilio credentials not configured. Message would be:")
        print("-" * 40)
        print(message)
        print("-" * 40)
        return

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    # Split message if too long for single SMS (1600 char limit for concatenated SMS)
    max_length = 1500
    messages = []

    if len(message) <= max_length:
        messages = [message]
    else:
        # Split into multiple messages
        lines = message.split("\n")
        current_msg = ""
        for line in lines:
            if len(current_msg) + len(line) + 1 > max_length:
                if current_msg:
                    messages.append(current_msg.strip())
                current_msg = line + "\n"
            else:
                current_msg += line + "\n"
        if current_msg.strip():
            messages.append(current_msg.strip())

    for phone in PHONE_NUMBERS:
        for i, msg in enumerate(messages):
            if len(messages) > 1:
                msg = f"({i+1}/{len(messages)}) {msg}"

            try:
                result = client.messages.create(
                    body=msg,
                    from_=TWILIO_PHONE_NUMBER,
                    to=phone
                )
                print(f"SMS sent to {phone}: {result.sid}")
            except Exception as e:
                print(f"Failed to send SMS to {phone}: {e}")


def main():
    """Main entry point."""
    print(f"Fetching estate sales from {BASE_URL}...")

    try:
        sales = fetch_estate_sales()
        print(f"Found {len(sales)} sales within {MAX_DISTANCE_MILES} miles")

        message = format_message(sales)
        print(f"\nMessage ({len(message)} chars):")
        print(message)

        print("\nSending SMS notifications...")
        send_sms(message)

        print("\nDone!")
    except Exception as e:
        error_msg = f"Estate Sales Notifier Error: {e}"
        print(error_msg)
        send_sms(error_msg)
        raise


if __name__ == "__main__":
    main()
