# Estate Sales Notifier

Automatically checks [estatesales.net](https://www.estatesales.net/TX/Austin/78759) every Wednesday evening and sends SMS notifications with estate sales within 15 miles of Austin 78759.

Uses free email-to-SMS gateways (no Twilio costs).

## Setup

### 1. Create a Gmail App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification if not already enabled
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Create a new app password (select "Mail" and "Other")
5. Copy the 16-character password

### 2. Create GitHub Repository

```bash
cd estate-sales-notifier
git init
git add .
git commit -m "Initial commit"
gh repo create estate-sales-notifier --private --push
```

### 3. Add GitHub Secrets

Go to your repository **Settings** → **Secrets and variables** → **Actions** and add:

| Secret Name | Value |
|-------------|-------|
| `SMTP_EMAIL` | Your Gmail address |
| `SMTP_PASSWORD` | Your Gmail app password (16 chars) |

### 4. Enable GitHub Actions

The workflow will run:
- **Automatically**: Every Wednesday at 8 PM Central Time
- **Manually**: Click "Run workflow" in the Actions tab to test

## Configuration

Edit `estate_sales_notifier.py` to customize:

```python
# Change the search location
BASE_URL = "https://www.estatesales.net/TX/Austin/78759"

# Change the distance filter
MAX_DISTANCE_MILES = 15

# Change recipients (use carrier gateway)
SMS_RECIPIENTS = [
    "9259844951@tmomail.net",  # T-Mobile
    "5126530151@tmomail.net",
]
```

### Email-to-SMS Gateways by Carrier

| Carrier | Gateway |
|---------|---------|
| T-Mobile | `number@tmomail.net` |
| AT&T | `number@txt.att.net` |
| Verizon | `number@vtext.com` |
| Sprint | `number@messaging.sprintpcs.com` |

## Local Testing

```bash
pip install -r requirements.txt

export SMTP_EMAIL="your.email@gmail.com"
export SMTP_PASSWORD="your_app_password"

python estate_sales_notifier.py
```

Without credentials, the script prints the message instead of sending.

## Cost

**Free!** Uses Gmail SMTP and carrier email-to-SMS gateways.
