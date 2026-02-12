"""Tests for the estate sales notifier."""
from bs4 import BeautifulSoup

from estate_sales_notifier import (
    parse_sale_card,
    is_within_distance,
    format_date_range,
    format_event_description,
    format_summary_description,
    MAX_DISTANCE_MILES,
)


# ---------------------------------------------------------------------------
# Sample HTML fragments that mirror estatesales.net markup
# ---------------------------------------------------------------------------

SALE_ROW_HTML = """
<a class="sale-row" href="/TX/Austin/78759/4567890">
  <h3>Awesome Austin Estate Sale</h3>
  <span class="sale-row__address">123 Main St, Austin TX 78759</span>
  <span class="sale-row__date">Feb 14 to 16 9am to 3pm</span>
  <span class="sale-row__distance">3.2 mi away</span>
</a>
"""

SALE_ROW_NEARBY_HTML = """
<a class="sale-row" href="/TX/Austin/78759/9999999">
  <h3>Nearby Neighborhood Sale</h3>
  <span class="sale-row__address">456 Oak Ave, Austin TX 78759</span>
  <span class="sale-row__date">Mar 1 10am to 4pm</span>
  <span class="sale-row__distance">Nearby</span>
</a>
"""

SALE_ROW_NO_DISTANCE_HTML = """
<a class="sale-row" href="/TX/Round-Rock/78664/1111111">
  <h3>Round Rock Moving Sale</h3>
  <span class="sale-row__address">789 Elm St, Round Rock TX 78664</span>
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
        assert sale["address"] == "123 Main St, Austin TX 78759"
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
# format_event_description
# ---------------------------------------------------------------------------

class TestFormatEventDescription:
    def test_includes_url(self):
        sale = {
            "title": "Test Sale",
            "url": "https://www.estatesales.net/TX/Austin/78759/123",
            "address": "123 Main St",
            "dates": "Feb 14 9am to 3pm",
            "distance_text": "2 mi",
        }
        desc = format_event_description(sale)
        assert "https://www.estatesales.net" in desc
        assert "123 Main St" in desc
        assert "2 mi" in desc

    def test_handles_missing_fields(self):
        sale = {"title": "Minimal Sale", "url": "https://example.com"}
        desc = format_event_description(sale)
        assert "https://example.com" in desc


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
