# Extra fields + single record count — Design (short)

Date: 2026-11-24

## Intent
Collect more contact details per business, **from Google's listing panel only** (no website visits),
and simplify the stats area to a single "how many records extracted" count.

## Goals
- **All phone numbers** of a business. `Phone` stays as today (the first number); extra numbers go in
  new columns **Phone 2** and **Phone 3**. If Google shows more than 3, the rest are added to Phone 3,
  comma-separated, so nothing is lost.
- **Area** (e.g. "Varachha") from the address: the part just before the city. Blank if not found.
- **Instagram** link: any `instagram.com` link in the detail panel (usually under "Profiles").
- **Email** from the panel text (regex). Usually blank, because Google rarely shows emails.
- Address, Pincode and Website keep working exactly as now.
- **All pages**: the tool already follows "Next" until there are no more pages. The 50-page cap is
  raised to 200 so a long result set is never cut short.
- **Stats:** the 4 cards (Pages scraped / Rows collected / Rows from last page / Working time)
  are replaced by one card, **Records extracted**. The status text and progress bar stay.

## Non-goals / anti-goals
- No website visits for the new fields.
- The existing "check website for email" toggle, CAPTCHA handling, Stop/Continue, duplicate skipping,
  filter, copy-cell and Excel export stay unchanged. With the toggle on, the website email
  overrides the panel email only when the panel had none.
- A selector failure must never lose a record: every new field is best-effort and blank on failure.

## Approaches
- **Chosen:** read every phone element in the panel, then scan the panel text for extra numbers and
  emails, de-duplicated by digits. Instagram comes from panel links.
- Rejected: panel text only (misses numbers held in attributes); elements only (misses
  "Phone: a, b" text).
- Phone layout: the user picked **separate columns** over one comma-separated cell.

## Column order (table + Excel)
Name, Category, Address, Area, Phone, Phone 2, Phone 3, Website, Email, Instagram,
Pincode, City, State, Maps Link, Page

## Builder's calls
- Phone de-duplication compares the last 10 digits, so `+91 98250 12345` equals `098250 12345`.
- Area stays blank when the address doesn't contain one (no guessing from the search input).
- Unit tests cover the new parsing helpers and exporter columns. The scraper is verified by a live run.
