# Agent Instructions for Estate Sales Notifier

## Project Overview

Python tool that scrapes estatesales.net and creates Google Calendar events on a shared family calendar. Runs as a GitHub Action every Wednesday evening.

## Python Environment

- **Python Version**: Python 3.11+
- **Dependencies**: `pip install -r requirements.txt`
- **Test dependencies**: pytest (in requirements.txt)

## Running the Application

```bash
# Normal run (requires credentials.json or GOOGLE_CREDENTIALS_JSON env var)
python3 estate_sales_notifier.py

# Dry run — scrapes and authenticates but doesn't create events
DRY_RUN=true python3 estate_sales_notifier.py
```

## Key Files

- `estate_sales_notifier.py` — Main scraper and calendar event logic
- `tests/test_notifier.py` — Functional tests (pytest)
- `requirements.txt` — Python dependencies
- `credentials.json` — Google service account key (git-ignored, local only)
- `.github/workflows/notify.yml` — Production workflow (Wednesday 9 PM CT)
- `.github/workflows/ci.yml` — CI workflow (lint + test on PR)

## Configuration

Constants at the top of `estate_sales_notifier.py`:
- `BASE_URL` — estatesales.net search URL (default: Austin 78759)
- `MAX_DISTANCE_MILES` — Distance filter (default: 15 miles)
- `CALENDAR_ID` — Target Google Calendar ID
- `TIMEZONE` — Local timezone (default: America/Chicago)
- `CREDENTIALS_FILE` — Path to service account JSON (default: credentials.json)

## Testing

```bash
pytest tests/ -v
```

## Best Practices

- Keep dependencies minimal
- Follow existing code style (spaces, snake_case)
- All scraping logic is pure-function testable (pass HTML in, get dicts out)
- Calendar integration is isolated in `create_calendar_events()`
