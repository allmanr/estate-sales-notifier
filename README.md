# Estate Sales Notifier

Scrapes [estatesales.net](https://www.estatesales.net/TX/Austin/78759) every Wednesday evening and pushes estate sale events directly to a shared Google Calendar.

## How It Works

1. **Scrapes** estatesales.net for sales within 15 miles of Austin 78759
2. **Sorts** results by distance (nearest first)
3. **Creates** individual Google Calendar events for each sale, plus a weekend summary event
4. Runs automatically via **GitHub Actions** every Wednesday at 9 PM CT

## Setup

### Google Service Account

1. Create a GCP project and enable the Google Calendar API
2. Create a service account and download the JSON key
3. Share your Google Calendar with the service account email (`client_email` in the JSON)
4. Store the JSON key contents as a GitHub Actions secret: `GOOGLE_CREDENTIALS_JSON`

### GitHub Actions Secrets

| Secret | Description |
|--------|-------------|
| `GOOGLE_CREDENTIALS_JSON` | Full JSON contents of the service account key file |

### Local Development

```bash
pip install -r requirements.txt

# Place your service account key at credentials.json (git-ignored)
python estate_sales_notifier.py

# Dry run (authenticate but don't create events)
DRY_RUN=true python estate_sales_notifier.py
```

## Configuration

Edit constants at the top of `estate_sales_notifier.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `BASE_URL` | Austin 78759 | estatesales.net search URL |
| `MAX_DISTANCE_MILES` | 15 | Radius filter |
| `CALENDAR_ID` | *(family calendar)* | Target Google Calendar ID |
| `TIMEZONE` | `America/Chicago` | Local timezone for events |

## Testing

```bash
pip install -r requirements.txt
pytest tests/ -v
```
