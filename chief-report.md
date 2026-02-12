# Chief Engineer Review Report

## Executive Summary

I've completed a comprehensive review of the Estate Sales Notifier. The tool had evolved from an SMS-based notification system to a Google Calendar integration, but documentation, dead code, and several bugs hadn't caught up. This report covers what I found, what I fixed, and where I'd take this next.

---

## Issues Found

### 🔴 Critical

| # | Issue | Status |
|---|-------|--------|
| 1 | **`datetime.utcnow()` deprecated** — Python 3.12+ deprecates this; will emit warnings and eventually break | ✅ Fixed → `datetime.now(timezone.utc)` |
| 2 | **All-day event end date bug** — Google Calendar requires the end date to be *exclusive* (day after). Setting start=end=Friday created a zero-length event that sometimes didn't render | ✅ Fixed → summary event spans Fri–Mon (exclusive), individual events use start+1 |
| 3 | **Error handler re-sends errors as calendar events** — On failure, `main()` called `send_notification(error_msg)` which tried to push a garbage calendar event containing a stack trace | ✅ Fixed → errors are logged, not pushed to calendar |

### 🟡 Medium

| # | Issue | Status |
|---|-------|--------|
| 4 | **No sort order** — sales displayed in page-scrape order, not distance | ✅ Fixed → sorted by distance ascending, unknowns last |
| 5 | **SMS-style message formatting** — title truncated to 45 chars, numbered list crammed into a single event description, "ESTATE SALES THIS WEEKEND" header from SMS era | ✅ Fixed → individual calendar events per sale + clean summary event |
| 6 | **UTC timezone for notification events** — popup notification used UTC times, confusing for Central Time users | ✅ Fixed → added `TIMEZONE = "America/Chicago"` config |
| 7 | **Hardcoded to 10-sale limit** — old `format_message` capped at 10 with a "+ N more" note. Calendar events can handle more | ✅ Fixed → up to 15 individual events + unlimited in summary |
| 8 | **`CALENDAR_IDS` was a list for a single calendar** — unnecessary complexity, misleading name | ✅ Fixed → `CALENDAR_ID` singular string |
| 9 | **README entirely about SMS** — documented SMTP setup, carrier gateways, and app passwords for a tool that no longer sends SMS | ✅ Fixed → complete rewrite |

### 🟢 Low / Cleanup

| # | Issue | Status |
|---|-------|--------|
| 10 | **Dead code: `parse_distance()` function** — defined but never called | ✅ Removed |
| 11 | **Dead code: `test_email_output.py`** — email/ICS test script for the old SMS approach | ✅ Removed |
| 12 | **`print()` statements instead of logging** — no structured output, harder to debug in Actions | ✅ Fixed → `logging` module |
| 13 | **No tests** — zero automated test coverage | ✅ Fixed → 22 pytest tests |
| 14 | **No CI workflow** — PRs could merge broken code with no checks | ✅ Fixed → `.github/workflows/ci.yml` (lint + test) |
| 15 | **No linter configured** — no code quality baseline | ✅ Fixed → ruff added to requirements and CI |
| 16 | **`.gitignore` missing `*.eml`** — test output file could be committed | ✅ Fixed |
| 17 | **AGENTS.md referenced SMTP/SMS** — stale agent instructions | ✅ Fixed |

---

## Changes Made (This PR)

### Files Modified
- **`estate_sales_notifier.py`** — Bug fixes, sort order, individual events, logging, cleaned API
- **`README.md`** — Complete rewrite for calendar-based tool
- **`AGENTS.md`** — Updated to reflect current architecture
- **`requirements.txt`** — Added `pytest` and `ruff`
- **`.gitignore`** — Added `*.eml`
- **`.github/workflows/notify.yml`** — Production workflow (unchanged)

### Files Added
- **`tests/test_notifier.py`** — 22 functional tests covering parsing, formatting, sorting
- **`tests/__init__.py`** — Package marker
- **`.github/workflows/ci.yml`** — Lint + test on PR/push

### Files Removed
- **`test_email_output.py`** — Dead code from SMS era
- **`.github/workflows/test-notify.yml`** — Replaced by `ci.yml`

---

## Architecture Notes

The codebase follows a clean pipeline pattern:

```
Scrape → Parse → Filter → Sort → Format → Calendar API
```

Each stage is a pure function (except the Calendar API call), which makes testing straightforward. The `create_calendar_events()` function is the only side-effecting code and is isolated at the end of the pipeline.

---

## Enhancement Proposals

These are filed as GitHub issues for future work:

### 1. 🗺️ Deduplicate Across Runs
**Problem:** Running the notifier twice in a week creates duplicate events.
**Proposal:** Before creating events, query the calendar for existing events with matching titles in the target date range. Skip events that already exist. Alternatively, use a deterministic event ID derived from the sale URL so Google Calendar handles upserts.

### 2. 📸 Sale Photo Thumbnails in Event Descriptions
**Problem:** Calendar events are text-only; you can't tell what kind of sale it is without clicking through.
**Proposal:** Scrape the thumbnail image URL from each sale listing and embed it in the calendar event description using an HTML `<img>` tag (Google Calendar supports basic HTML in descriptions).

### 3. 🔍 Keyword Highlighting & Priority Sorting
**Problem:** Not all sales are equally interesting. A sale advertising "mid-century modern furniture" is more exciting than "general household items."
**Proposal:** Add a configurable list of priority keywords (e.g., "mid-century", "tools", "vinyl", "vintage"). Sales matching keywords sort first and get a ⭐ prefix in the calendar event title.

### 4. 📊 Historical Tracking & Trends
**Problem:** No way to know if a sale company consistently has good sales, or to see seasonal patterns.
**Proposal:** Log each run's results to a lightweight JSON file or SQLite database. Over time, surface insights like "this company has had 12 sales in your area" or "estate sales peak in March."

### 5. 🧹 Automatic Event Cleanup
**Problem:** Past estate sale events clutter the calendar forever.
**Proposal:** At the start of each run, delete events created by previous runs that are now in the past. Tag events with a custom extended property (e.g., `source: estate-sales-notifier`) to safely identify which events to clean up without touching manually-created events.
