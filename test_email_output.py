#!/usr/bin/env python3
"""Test script to generate and display email structure without sending."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import uuid

SMTP_EMAIL = "richard.allman7@gmail.com"

def create_ics_event(summary: str, description: str, organizer: str, attendee: str) -> str:
    """Create an ICS calendar invite."""
    uid = str(uuid.uuid4())
    now = datetime.utcnow()
    start_time = now + timedelta(minutes=2)
    dtstart = start_time.strftime("%Y%m%dT%H%M%SZ")
    dtend = (start_time + timedelta(minutes=30)).strftime("%Y%m%dT%H%M%SZ")
    dtstamp = now.strftime("%Y%m%dT%H%M%SZ")
    description = description.replace("\n", "\\n").replace(",", "\\,")
    
    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Estate Sales Notifier//EN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{dtstamp}
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:{summary}
DESCRIPTION:{description}
LOCATION:Austin, TX 78759
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
    return ics

# Create test message
message = "Test Estate Sales\n\n1. Sale 1 - 3 miles\n   Some dates\n   URL"
summary = "Estate Sales This Weekend"
recipient = SMTP_EMAIL

ics_content = create_ics_event(summary, message, SMTP_EMAIL, recipient)

msg = MIMEMultipart("mixed")
msg["Subject"] = summary
msg["From"] = SMTP_EMAIL
msg["To"] = recipient

# Create multipart/alternative for text and HTML
msg_alternative = MIMEMultipart("alternative")
msg.attach(msg_alternative)

# Add plain text version with quoted-printable encoding
text_part = MIMEText(message, "plain", "utf-8")
encoders.encode_quopri(text_part)
msg_alternative.attach(text_part)

# Add HTML version with quoted-printable encoding
html_message = message.replace("\n", "<br>")
html_part = MIMEText(f"<html><body><pre>{html_message}</pre></body></html>", "html", "utf-8")
encoders.encode_quopri(html_part)
msg_alternative.attach(html_part)

# Add calendar part
cal_part = MIMEBase("text", "calendar")
cal_part.set_payload(ics_content)
encoders.encode_base64(cal_part)
cal_part.add_header("Content-Disposition", "attachment", filename="Invitation")
msg.attach(cal_part)

# Save to file
with open("/home/rallman/estate-sales-notifier/test_output.eml", "w") as f:
    f.write(msg.as_string())

print("Email structure saved to test_output.eml")
print("\nFirst 100 lines:")
with open("/home/rallman/estate-sales-notifier/test_output.eml", "r") as f:
    lines = f.readlines()
    for i, line in enumerate(lines[:100], 1):
        print(f"{i}: {line}", end="")
