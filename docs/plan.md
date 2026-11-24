# Google Places Extractor Implementation Plan

> Executed natively (user asked to implement directly).

**Goal:** Tkinter desktop app that scrapes Google Places results (all pages) into Excel.
**Architecture:** UI thread (Tkinter) + scraper worker thread (Playwright sync API) talking via `queue.Queue`. Pure logic (parsing, export) is unit tested.
**Tech Stack:** Python 3.11+, playwright, openpyxl, requests, pytest, pyinstaller.
**Spec:** docs/design.md

## Global Constraints
- Work only inside `D:\SMX\Google extractor`.
- Browser: `channel="chrome"`, fallback `channel="msedge"`; headful; dedicated profile dir `%LOCALAPPDATA%\GoogleExtractor\profile`.
- Delays: random 1–3 s between listings/pages.
- Columns (exact order): Name, Category, Rating, Reviews, Address, Phone, Website, Email, Hours, Pincode, City, State, Maps Link, Page.

## Review Focus
1. Address without PIN / state → blank pincode, fall back to input city + its state.
2. CAPTCHA page (`/sorry/` URL or "unusual traffic") → pause, wait for Continue.
3. Stop mid-run → records so far still exportable.
4. Listing click that fails / panel missing fields → record kept with blanks, run continues.
5. Filenames with spaces/special chars from inputs → sanitized default filename.

### Task 1: parsing.py (TDD)
- `extract_pincode(address: str) -> str`
- `extract_city_state(address: str, fallback_city: str) -> tuple[str, str]`
- `clean_phone(text: str) -> str`
- `find_emails(text: str) -> list[str]` (dedup, lowercase, ignore image filenames like `x@2x.png`)
- Tests: `tests/test_parsing.py`.

### Task 2: exporter.py (TDD)
- `COLUMNS: list[str]`; `export_to_excel(records: list[dict], path: str) -> None`; `default_filename(type, area, city, date) -> str`.
- Tests: header row == COLUMNS, row count, sanitized filename.

### Task 3: google_selectors.py + scraper.py
- `Scraper(query, fetch_emails, out_queue, stop_event, continue_event)`, `run()`; posts `("log", str)`, `("record", dict)`, `("status", str)`, `("captcha", None)`, `("done", int)`.
- Verified by a live run.

### Task 4: email_finder.py
- `find_email_on_website(url: str, timeout=8) -> str`.

### Task 5: app.py + build.bat + README
- Manual live run verification; PyInstaller build.
