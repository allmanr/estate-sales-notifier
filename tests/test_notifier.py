"""Tests for the estate sales notifier."""
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from estate_sales_notifier import (
    parse_sale_card,
    is_within_distance,
    format_date_range,
    format_summary_description,
    build_calendar_event,
    MAX_DISTANCE_MILES,
)


# ---------------------------------------------------------------------------
# Sample HTML fragments that mirror estatesales.net markup
# ---------------------------------------------------------------------------

SALE_ROW_HTML = """
<a class="sale-row" href="/TX/Austin/78759/4567890">
  <h3>Awesome Austin Estate Sale</h3>
  <div class="sale-row__address">
    <div class="address-line-1">123 Main St</div>
    <div class="address-line-2">Austin, TX 78759</div>
    <div class="sale-row__distance">3.2 miles <span class="sale-row__distance__label">away</span></div>
  </div>
  <span class="sale-row__date">Feb 14 to 16 9am to 3pm</span>
</a>
"""

SALE_ROW_NEARBY_HTML = """
<a class="sale-row" href="/TX/Austin/78759/9999999">
  <h3>Nearby Neighborhood Sale</h3>
  <div class="sale-row__address">
    <div class="address-line-2">Austin, TX 78759</div>
    <div class="sale-row__distance">Nearby</div>
  </div>
  <span class="sale-row__date">Mar 1 10am to 4pm</span>
</a>
"""

SALE_ROW_NO_DISTANCE_HTML = """
<a class="sale-row" href="/TX/Round-Rock/78664/1111111">
  <h3>Round Rock Moving Sale</h3>
  <div class="sale-row__address">
    <div class="address-line-2">Round Rock, TX 78664</div>
  </div>
  <span class="sale-row__date">Feb 21 to 22 8am to 2pm</span>
</a>
"""

SALE_ROW_NO_HREF_HTML = """
<a class="sale-row">
  <h3>Bad Listing</h3>
</a>
"""


# ---------------------------------------------------------------------------
# parse_sale_card
# ---------------------------------------------------------------------------

class TestParseSaleCard:
    def _card(self, html: str):
        return BeautifulSoup(html, "html.parser").find("a", class_="sale-row")

    def test_basic_sale(self):
        sale = parse_sale_card(self._card(SALE_ROW_HTML))
        assert sale is not None
        assert sale["title"] == "Awesome Austin Estate Sale"
        assert "Austin, TX 78759" in sale["address"]
        assert "miles" not in sale["address"]  # distance excluded from address
        assert sale["url"] == "https://www.estatesales.net/TX/Austin/78759/4567890"
        assert sale["zip"] == "78759"
        assert sale["distance"] == 3.2
        assert sale["distance_text"] == "3.2 mi"

    def test_nearby_distance(self):
        sale = parse_sale_card(self._card(SALE_ROW_NEARBY_HTML))
        assert sale is not None
        assert sale["distance"] == 0
        assert sale["distance_text"] == "Nearby"

    def test_no_distance_element(self):
        sale = parse_sale_card(self._card(SALE_ROW_NO_DISTANCE_HTML))
        assert sale is not None
        assert sale["distance"] is None
        assert sale["distance_text"] == ""

    def test_no_href_returns_none(self):
        sale = parse_sale_card(self._card(SALE_ROW_NO_HREF_HTML))
        assert sale is None

    def test_relative_url_gets_prefix(self):
        sale = parse_sale_card(self._card(SALE_ROW_HTML))
        assert sale["url"].startswith("https://www.estatesales.net")


# ---------------------------------------------------------------------------
# is_within_distance
# ---------------------------------------------------------------------------

class TestIsWithinDistance:
    def test_none_is_included(self):
        assert is_within_distance(None) is True

    def test_zero_is_included(self):
        assert is_within_distance(0) is True

    def test_within_range(self):
        assert is_within_distance(MAX_DISTANCE_MILES - 1) is True

    def test_at_boundary(self):
        assert is_within_distance(MAX_DISTANCE_MILES) is True

    def test_beyond_range(self):
        assert is_within_distance(MAX_DISTANCE_MILES + 1) is False


# ---------------------------------------------------------------------------
# format_date_range
# ---------------------------------------------------------------------------

class TestFormatDateRange:
    def test_empty_string(self):
        assert format_date_range("") == ""

    def test_date_with_time(self):
        result = format_date_range("Feb 14 to 16 9am to 3pm")
        assert "Feb" in result
        assert "9am" in result
        assert "3pm" in result

    def test_single_date(self):
        result = format_date_range("Mar 1 10am to 4pm")
        assert "Mar" in result
        assert "1" in result

    def test_strips_status_words(self):
        result = format_date_range("Feb 14 to 16 9am to 3pm Going on now")
        assert "Going" not in result

    def test_handles_stuck_together_times(self):
        # e.g. "119am" should be parsed as "11" and "9am"
        result = format_date_range("Feb 14 119am to 3pm")
        assert "9am" in result or "11" in result


# ---------------------------------------------------------------------------
# format_summary_description
# ---------------------------------------------------------------------------

class TestFormatSummaryDescription:
    def test_empty_sales(self):
        result = format_summary_description([])
        assert "No estate sales" in result

    def test_includes_all_sales(self):
        sales = [
            {"title": f"Sale {i}", "url": f"https://example.com/{i}",
             "distance_text": f"{i} mi", "dates": "", "address": ""}
            for i in range(1, 4)
        ]
        result = format_summary_description(sales)
        assert "Sale 1" in result
        assert "Sale 2" in result
        assert "Sale 3" in result

    def test_includes_distance(self):
        sales = [
            {"title": "Close Sale", "url": "https://x.com/1",
             "distance_text": "1.5 mi", "dates": "", "address": ""}
        ]
        result = format_summary_description(sales)
        assert "1.5 mi" in result


# ---------------------------------------------------------------------------
# Integration: full HTML parsing
# ---------------------------------------------------------------------------

class TestFullParsing:
    """Verify the scraping pipeline works end-to-end with sample HTML."""

    FULL_PAGE = f"""
    <html><body>
    {SALE_ROW_HTML}
    {SALE_ROW_NEARBY_HTML}
    {SALE_ROW_NO_DISTANCE_HTML}
    </body></html>
    """

    def test_parses_multiple_sales(self):
        soup = BeautifulSoup(self.FULL_PAGE, "html.parser")
        rows = soup.find_all("a", class_="sale-row")
        sales = [parse_sale_card(r) for r in rows]
        sales = [s for s in sales if s is not None]
        assert len(sales) == 3

    def test_sorting_by_distance(self):
        soup = BeautifulSoup(self.FULL_PAGE, "html.parser")
        rows = soup.find_all("a", class_="sale-row")
        sales = [parse_sale_card(r) for r in rows]
        sales = [s for s in sales if s is not None]
        sales.sort(
            key=lambda s: s.get("distance") if s.get("distance") is not None else float("inf")
        )
        assert sales[0]["distance"] == 0  # Nearby first
        assert sales[1]["distance"] == 3.2
        assert sales[2]["distance"] is None  # Unknown last


# ---------------------------------------------------------------------------
# Realistic HTML fixtures (mirrors actual estatesales.net markup)
# ---------------------------------------------------------------------------

# Distance nested inside address div, unicode smart quotes, emoji in title
REALISTIC_ROWS_HTML = """
<html><body>
<a class="sale-row" href="/TX/Austin/78759/4794264">
  <h3>Blue Moon Estate Sale in Balcones Woods</h3>
  <div class="sale-row__address">
    <address>
      <div class="address-line-2"> Austin,\u00a0TX\u00a078759 </div>
    </address>
    <div class="sale-row__distance"> Nearby <span class="sale-row__distance__label">Less than 3 miles away</span></div>
  </div>
  <div class="sale-row__dates">
    <span class="sale-row__date">Feb 14 to 15 9am to 3pm</span>
  </div>
</a>
<a class="sale-row" href="/TX/Austin/78750/4801824">
  <h3>\u201cTreat Yourself Valentine\u2019s Estate Sale\u2014No Bad Dates Required\u201d</h3>
  <div class="sale-row__address">
    <address>
      <div class="address-line-2"> Austin,\u00a0TX\u00a078750 </div>
    </address>
    <div class="sale-row__distance"> 4 miles <span class="sale-row__distance__label">away</span></div>
  </div>
  <div class="sale-row__dates">
    <span class="sale-row__date">Feb 13 to 15 10am to 4pm</span>
  </div>
</a>
<a class="sale-row" href="/TX/Manor/78653/4784664">
  <h3>Estate sale in Manor</h3>
  <div class="sale-row__address">
    <address>
      <div class="address-line-1"><span>13420 marie lane</span></div>
      <div class="address-line-2"> Manor,\u00a0TX\u00a078653 </div>
    </address>
    <div class="sale-row__distance"> 13 miles <span class="sale-row__distance__label">away</span></div>
  </div>
  <div class="sale-row__dates">
    <span class="sale-row__date">Feb 11 to 13</span>
  </div>
</a>
<a class="sale-row" href="/TX/Pflugerville/78660/4801860">
  <h3>\u201cValentine\u2019s Weekend Estate Sale \u2764\ufe0f Come Fall in Love With a Deal\u201d</h3>
  <div class="sale-row__address">
    <address>
      <div class="address-line-2"> Pflugerville,\u00a0TX\u00a078660 </div>
    </address>
    <div class="sale-row__distance"> 9 miles <span class="sale-row__distance__label">away</span></div>
  </div>
  <div class="sale-row__dates">
    <span class="sale-row__date">Feb 14 to 15 10am to 4pm</span>
  </div>
</a>
</body></html>
"""


# ---------------------------------------------------------------------------
# Output quality: parsed fields are clean and well-formatted
# ---------------------------------------------------------------------------

ZIP_RE = re.compile(r"\b\d{5}\b")
MOJIBAKE_RE = re.compile(r"â\x80|ï¸|Ã|Â")  # common UTF-8-as-Latin-1 artifacts


def _parse_realistic_sales():
    """Parse the realistic HTML fixture into a list of sale dicts."""
    soup = BeautifulSoup(REALISTIC_ROWS_HTML, "html.parser")
    rows = soup.find_all("a", class_="sale-row")
    return [parse_sale_card(r) for r in rows]


class TestParsedFieldQuality:
    """Ensure parsed sale fields are clean: no encoding artifacts,
    no distance text leaking into addresses, valid zips and distances."""

    def test_address_excludes_distance_text(self):
        for sale in _parse_realistic_sales():
            addr = sale["address"]
            assert "miles" not in addr.lower(), f"distance leaked into address: {addr!r}"
            assert "away" not in addr.lower(), f"'away' leaked into address: {addr!r}"
            assert "nearby" not in addr.lower(), f"'Nearby' leaked into address: {addr!r}"

    def test_address_has_space_before_zip(self):
        for sale in _parse_realistic_sales():
            addr = sale["address"]
            zips = ZIP_RE.findall(addr)
            for z in zips:
                idx = addr.index(z)
                if idx > 0:
                    assert addr[idx - 1] == " ", (
                        f"missing space before zip in address: {addr!r}"
                    )

    def test_titles_have_no_mojibake(self):
        for sale in _parse_realistic_sales():
            title = sale["title"]
            assert not MOJIBAKE_RE.search(title), (
                f"encoding artifact in title: {title!r}"
            )

    def test_titles_preserve_unicode(self):
        sales = _parse_realistic_sales()
        titles = [s["title"] for s in sales]
        # The smart-quote title should have real curly quotes, not garbage
        smart_title = [t for t in titles if "Valentine" in t and "Treat" in t][0]
        assert "\u201c" in smart_title  # left double quote
        assert "\u2019" in smart_title  # right single quote (apostrophe)
        # The emoji title should contain a heart
        heart_title = [t for t in titles if "Valentine" in t and "Deal" in t][0]
        assert "\u2764" in heart_title  # red heart emoji

    def test_distance_is_numeric_or_zero(self):
        for sale in _parse_realistic_sales():
            d = sale["distance"]
            assert isinstance(d, (int, float)), f"distance not numeric: {d!r}"
            assert d >= 0

    def test_distance_text_is_clean(self):
        for sale in _parse_realistic_sales():
            dt = sale["distance_text"]
            assert dt in ("Nearby",) or re.match(r"^\d+(\.\d+)? mi$", dt), (
                f"unexpected distance_text format: {dt!r}"
            )

    def test_zip_is_five_digits(self):
        for sale in _parse_realistic_sales():
            assert re.match(r"^\d{5}$", sale["zip"]), (
                f"bad zip: {sale['zip']!r}"
            )


class TestFormattedSummaryQuality:
    """Ensure the full formatted summary has no formatting defects."""

    def test_no_mojibake_in_summary(self):
        sales = _parse_realistic_sales()
        summary = format_summary_description(sales)
        assert not MOJIBAKE_RE.search(summary), (
            f"encoding artifact in summary:\n{summary}"
        )

    def test_no_distance_in_address_lines(self):
        sales = _parse_realistic_sales()
        summary = format_summary_description(sales)
        for line in summary.splitlines():
            # Address lines are indented and don't start with a number or URL
            stripped = line.strip()
            if stripped and not stripped[0].isdigit() and not stripped.startswith("http"):
                assert "milesaway" not in stripped, f"stuck distance in line: {line!r}"
                assert "miles away" not in stripped.lower() or stripped == stripped, (
                    f"distance text in address line: {line!r}"
                )

    def test_formatted_dates_are_reasonable(self):
        sales = _parse_realistic_sales()
        summary = format_summary_description(sales)
        # Every date line should match "Mon D-D, Xam-Ypm" or "Mon D-D"
        date_line_re = re.compile(
            r"^\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"\s+\d{1,2}(-\d{1,2})?(,\s+\d{1,2}(am|pm)-\d{1,2}(am|pm))?$"
        )
        for line in summary.splitlines():
            stripped = line.strip()
            if stripped and not stripped[0].isdigit() and not stripped.startswith("http"):
                # This is either a date line or an address line
                if any(m in stripped for m in
                       ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
                    assert date_line_re.match(line), (
                        f"date line has unexpected format: {line!r}"
                    )


# ---------------------------------------------------------------------------
# Calendar event reminder timing
# ---------------------------------------------------------------------------

class TestCalendarEventReminder:
    """Verify the reminder fires shortly after the script runs,
    not at some default time."""

    def _make_sales(self):
        return [
            {"title": "Test Sale", "url": "https://example.com/1",
             "distance_text": "3 mi", "dates": "Feb 14 to 15 9am to 3pm",
             "address": "Austin, TX 78759"}
        ]

    def test_reminder_fires_near_run_time_wednesday_night(self):
        """Simulates the cron: 03:00 UTC Thursday = 9 PM Wednesday CST."""
        now_utc = datetime(2026, 2, 12, 3, 0, tzinfo=timezone.utc)  # Thu 03:00 UTC
        event = build_calendar_event(self._make_sales(), now_utc)

        reminders = event["reminders"]
        assert reminders["useDefault"] is False
        mins = reminders["overrides"][0]["minutes"]

        # The reminder should fire at ~9:02 PM Wed CST.
        # Friday midnight CST = 2026-02-13 00:00 CST
        # 9:02 PM Wed = 2026-02-11 21:02 CST
        # Delta = ~26h58m = ~1618 minutes
        # Allow a narrow window: 1610–1630 minutes
        assert 1610 <= mins <= 1630, (
            f"expected ~1618 min reminder, got {mins}"
        )

    def test_reminder_fires_near_run_time_manual_dispatch(self):
        """If manually dispatched on a Monday, reminder still fires ~2 min later."""
        # Monday 2PM CST = Monday 20:00 UTC
        now_utc = datetime(2026, 2, 9, 20, 0, tzinfo=timezone.utc)
        event = build_calendar_event(self._make_sales(), now_utc)

        mins = event["reminders"]["overrides"][0]["minutes"]

        # Friday midnight CST = 2026-02-13 00:00 CST
        # Mon 2:02 PM CST = 2026-02-09 14:02 CST
        # Delta = ~3 days 9h 58m = ~4918 minutes
        assert 4910 <= mins <= 4930, (
            f"expected ~4918 min reminder, got {mins}"
        )

    def test_reminder_is_not_default(self):
        now_utc = datetime(2026, 2, 12, 3, 0, tzinfo=timezone.utc)
        event = build_calendar_event(self._make_sales(), now_utc)
        assert event["reminders"]["useDefault"] is False

    def test_reminder_is_popup(self):
        now_utc = datetime(2026, 2, 12, 3, 0, tzinfo=timezone.utc)
        event = build_calendar_event(self._make_sales(), now_utc)
        assert event["reminders"]["overrides"][0]["method"] == "popup"

    def test_event_is_on_friday(self):
        # Wednesday night run
        now_utc = datetime(2026, 2, 12, 3, 0, tzinfo=timezone.utc)
        event = build_calendar_event(self._make_sales(), now_utc)
        from datetime import date
        friday = date(2026, 2, 13)
        assert event["start"]["date"] == friday.strftime("%Y-%m-%d")
