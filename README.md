# Estate Sales Notifier

Automatically checks [estatesales.net](https://www.estatesales.net/TX/Austin/78759) every Wednesday evening and sends SMS notifications with estate sales within 15 miles of Austin 78759.

## Setup

### 1. Create a Twilio Account

1. Sign up at [twilio.com](https://www.twilio.com/try-twilio)
2. Get your **Account SID** and **Auth Token** from the [Twilio Console](https://console.twilio.com/)
3. Get a phone number from the [Phone Numbers page](https://console.twilio.com/us1/develop/phone-numbers/manage/incoming)

### 2. Create GitHub Repository

1. Create a new repository on GitHub
2. Push this code to the repository:

```bash
cd estate-sales-notifier
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/estate-sales-notifier.git
git push -u origin main
```

### 3. Add GitHub Secrets

Go to your repository **Settings** → **Secrets and variables** → **Actions** and add:

| Secret Name | Value |
|-------------|-------|
| `TWILIO_ACCOUNT_SID` | Your Twilio Account SID (starts with `AC`) |
| `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token |
| `TWILIO_PHONE_NUMBER` | Your Twilio phone number (format: `+1XXXXXXXXXX`) |

### 4. Enable GitHub Actions

GitHub Actions should be enabled by default. The workflow will run:
- **Automatically**: Every Wednesday at 8 PM Central Time
- **Manually**: Click "Run workflow" in the Actions tab to test

## Configuration

Edit `estate_sales_notifier.py` to customize:

```python
# Change the search location
BASE_URL = "https://www.estatesales.net/TX/Austin/78759"

# Change the distance filter
MAX_DISTANCE_MILES = 15

# Change recipient phone numbers (E.164 format)
PHONE_NUMBERS = ["+19259844951", "+15126530151"]
```

## Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TWILIO_ACCOUNT_SID="your_account_sid"
export TWILIO_AUTH_TOKEN="your_auth_token"
export TWILIO_PHONE_NUMBER="+1234567890"

# Run the script
python estate_sales_notifier.py
```

Without Twilio credentials, the script will print the message instead of sending SMS.

## Cost

- **GitHub Actions**: Free for public repos, 2000 minutes/month for private repos
- **Twilio SMS**: ~$0.0079/message sent + ~$1/month for phone number

## Troubleshooting

- **No sales found**: The website structure may have changed. Check the scraping selectors.
- **SMS not received**: Verify Twilio credentials and phone number format.
- **Action not running**: Check that Actions are enabled in repository settings.
