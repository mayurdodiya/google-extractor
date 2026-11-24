# Extra Fields + Single Count Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collect all phones (Phone / Phone 2 / Phone 3), Area, Instagram and panel Email from Google only, and show one "Records extracted" stat card.

**Architecture:** Pure helpers in `parsing.py` (unit-tested); `scraper.py` reads the extra data from the already-open detail panel; `exporter.COLUMNS` drives both the Excel file and the UI table; `app.py` loses three stat cards.

**Tech Stack:** Python 3, Playwright (sync), ttkbootstrap, openpyxl, pytest.

**Spec:** `docs/superpowers/specs/2026-11-24-extra-fields-design.md`

## Global Constraints
- Google only for the new fields — no website requests added.
- Existing toggle, CAPTCHA, Stop/Continue, dedupe, filter, copy-cell, export flow unchanged.
- Column order: Name, Category, Address, Area, Phone, Phone 2, Phone 3, Website, Email, Instagram, Pincode, City, State, Maps Link, Page.
- `MAX_PAGES = 200`.
- Every new field is best-effort: any Playwright error → field blank, record still saved.
- Not a git repo: skip commit steps; run `.venv\Scripts\python -m pytest -q` instead.

## Review Focus
- Panel text contains digits that are not phones (ratings, review counts, pincodes, hours) → must not become phones. Pinned by `test_find_phones_ignores_non_phone_digits` (Task 1); scraper text scan only reads lines starting with `Phone`.
- Same number in two formats (`+91 98250 12345` / `098250 12345`) → one phone. `test_find_phones_dedupes_by_last_10_digits` (Task 1).
- More than 3 phones → extras kept in Phone 3, comma-separated. `test_split_phones_overflow` (Task 1).
- Address without the city → Area blank, not a guess. `test_area_blank_without_city` (Task 1).
- Instagram link wrapped in Google's `/url?q=` redirect → real instagram URL. `test_instagram_unwraps_google_redirect` (Task 1).

---

### Task 1: Parsing helpers

**Files:** Modify `parsing.py`; Test `tests/test_parsing.py`

**Interfaces — Produces:**
- `find_phones(text: str) -> list[str]` — every 8–15 digit phone in text, in order, deduped by last 10 digits.
- `split_phones(phones: list[str]) -> dict` — `{"Phone": p1, "Phone 2": p2, "Phone 3": ", ".join(rest)}`, keys only for non-empty values.
- `extract_area(address: str, city: str) -> str` — comma part immediately before the part equal (case-insensitive, digits stripped) to `city`; `""` if city absent or first part.
- `instagram_url(hrefs: list[str]) -> str` — first href containing `instagram.com` after unwrapping `/url?q=`; query string dropped; `""` if none.

- [ ] **Step 1: Write failing tests**
```python
def test_find_phones_multiple():
    assert find_phones("098250 12345, 0261 234 5678") == ["098250 12345", "0261 234 5678"]
def test_find_phones_dedupes_by_last_10_digits():
    assert find_phones("+91 98250 12345 / 098250 12345") == ["+91 98250 12345"]
def test_find_phones_ignores_non_phone_digits():
    assert find_phones("4.5 (1,234) Surat 395006 Open 9 AM") == []
def test_split_phones_overflow():
    assert split_phones(["1", "2", "3", "4"]) == {"Phone": "1", "Phone 2": "2", "Phone 3": "3, 4"}
    assert split_phones([]) == {}
def test_area_before_city():
    assert extract_area("Mini Bazar, Varachha, Surat, Gujarat 395006", "Surat") == "Varachha"
def test_area_blank_without_city():
    assert extract_area("Dabholi Char Rasta", "Surat") == ""
def test_instagram_unwraps_google_redirect():
    assert instagram_url(["/url?q=https://www.instagram.com/shop_x/%3Figsh%3Dabc&sa=U"]) == "https://www.instagram.com/shop_x/"
    assert instagram_url(["https://facebook.com/x"]) == ""
```
- [ ] **Step 2:** `pytest tests/test_parsing.py -q` → FAIL (ImportError).
- [ ] **Step 3:** Implement the four functions in `parsing.py` (reuse `_PHONE_RE`; unwrap with `urllib.parse`).
- [ ] **Step 4:** `pytest -q` → all pass.

### Task 2: Exporter columns

**Files:** Modify `exporter.py`, `tests/test_exporter.py`

**Interfaces — Produces:** `COLUMNS` in the Global Constraints order (15 columns).

- [ ] **Step 1:** Update `test_columns_order` to the new list; in `test_pincode_saved_as_number` the pincode cell becomes `K2`; in `test_export` the phone cell becomes `E2`.
- [ ] **Step 2:** `pytest tests/test_exporter.py -q` → FAIL.
- [ ] **Step 3:** Change `COLUMNS`.
- [ ] **Step 4:** `pytest -q` → all pass.

### Task 3: Scraper reads extra fields

**Files:** Modify `scraper.py`, `google_selectors.py`

**Interfaces — Consumes:** Task 1 helpers. **Produces:** records may contain `Area`, `Phone 2`, `Phone 3`, `Instagram`, `Email`.

- [ ] **Step 1:** `MAX_PAGES = 200`. Add `S.DETAIL_LINKS = ["a[href*='instagram.com']"]`.
- [ ] **Step 2:** In `read_detail`: collect phones from **all** visible matches of every `S.DETAIL_PHONE` selector (aria-label or text, via `find_phones`), then from panel-text lines matching `^Phone:` ; store as `rec["_phones"]` (list). Instagram: hrefs of all `S.DETAIL_LINKS` inside panel → `instagram_url`. Email: first of `find_emails(body)` → `rec["Email"]`. Wrap each in `try/except PWError`.
- [ ] **Step 3:** In `scrape_card`, after the merge: phones = detail `_phones` (if panel matched this listing) + card `Phone`, re-deduped via `find_phones(", ".join(...))`; pop `_phones`; `rec.update(split_phones(phones))`. When the panel is stale, do not copy `_phones`/`Instagram`/`Email` from it (same rule as Website). Set `rec["Area"] = extract_area(address, rec["City"])`. Website email: run only `if self.fetch_emails and rec.get("Website") and not rec.get("Email")`.
- [ ] **Step 4:** `pytest -q` → all pass (card-parse tests unchanged).

### Task 4: UI single count + new columns

**Files:** Modify `app.py`

- [ ] **Step 1:** Replace the 4-card loop with one card: key `"rows"`, label `"Records extracted"`, style `"primary"`. Remove `pages/last/time` resets in `start()`, `page_done` handler body (keep the message consumed, no-op), and `_tick` / its call.
- [ ] **Step 2:** `COL_WIDTHS` add `"Area": 110, "Phone 2": 130, "Phone 3": 160, "Instagram": 220`.
- [ ] **Step 3:** `python -c "import app"` → no error; `pytest -q` → pass.

### Task 5: Build and live check

- [ ] **Step 1:** Run `build.bat` → "Build complete", `dist\GoogleExtractor.exe` timestamp updated.
- [ ] **Step 2:** Live run from source on "garment shop" / "Varachha, Surat"; stop after ~1 page; confirm the single count increments, Area/Phone 2/Instagram populate where Google shows them, and Excel has the 15 columns.
