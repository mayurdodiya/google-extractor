# Google Places Extractor — Design

Date: 2026-11-24

## Intent
A Windows desktop tool that anyone can run on any PC. The user enters a business type, an area and a city. The tool opens its own Chrome window, searches Google, opens the **Places** results, clicks every listing on every result page and collects whatever business details Google shows. When the run finishes, the user clicks **Extract** and gets an Excel file.

## Goals
- 3 inputs: **Business type** (e.g. "garment shop"), **Area** (e.g. "Varachha"), **City** (e.g. "Surat").
  The search query is `"<type> in <area>, <city>"`.
- The tool opens a **separate, visible Chrome window** (its own profile, not the user's).
- It opens Google's Places tab (`udm=1` local results), clicks each listing and reads the detail panel.
- It follows the "Next >" arrow until no more pages are left.
- Fields (any missing field stays blank): Name, Category, Rating, Reviews count, Address, Phone, Website, Email, Hours/Status, Pincode, City, State, Google Maps link, Search page #.
- Pincode is parsed from the address (6-digit Indian PIN). City and State are parsed from the address against a list of Indian states; if they can't be found, the City input and its state are used.
- Optional checkbox **"Also check websites for email"** (default off). When it's on, the tool visits each listing's website (home page plus /contact if present) and picks out emails with a pattern match.
- A live status shows the page number, listings found, and a log. A **Stop** button ends the run early and keeps the data collected so far.
- When a run ends, the tool shows a "Completed — N records" message. **Extract to Excel** opens a Save dialog; the default filename is `<type>_<area>_<city>_<date>.xlsx`.
- Duplicates (same name + address) are skipped.
- Ships as a single `.exe` for Windows; Python is not needed on the target PC.

## Non-goals
- No Google Maps API (paid) and no proxies or CAPTCHA-solving services.
- No scheduling and no database. One search per run (the user can run again).

## Anti-goals
- It must not crash and lose collected data. Every listing is kept in memory as it's scraped, so Stop or an error still allows Extract.
- It must not touch the user's personal Chrome profile.

## Constraints
- Google changes its HTML often. Selectors live in one module (`google_selectors.py`) with several fallbacks each, so they're easy to fix.
- CAPTCHA: if the "unusual traffic" page is detected, the tool pauses, shows "Solve the CAPTCHA in the Chrome window, then click Continue", and resumes after that.
- Random human-like delays (1–3 s) between clicks and pages.
- Uses the installed Chrome (`channel="chrome"`), so no 150 MB browser download is needed. If Chrome is missing, it falls back to Edge (`msedge`), which every Windows 10/11 PC has.

## Approaches considered
| Approach | Trade-off | Decision |
|---|---|---|
| **A. Python + Playwright + Tkinter, packaged with PyInstaller** | Single `.exe` (~60–80 MB); plain-looking UI | **Chosen**: simplest way to "copy to any PC and run" |
| B. Electron + Puppeteer | Nicer UI; 150 MB+ install, more parts | Rejected |
| C. Chrome extension | No install; runs in the user's own Chrome, fragile pagination, manual load | Rejected: doesn't match "separate Chrome" |

## Structure (`Google extractor/`)
```
app.py            Tkinter UI (inputs, Start/Stop, status, log, Extract)
scraper.py        Playwright worker thread: search → places → listings → pages
google_selectors.py      All Google CSS/XPath selectors + fallbacks
parsing.py        Address → pincode/city/state; phone cleanup; email regex
email_finder.py   Optional website email lookup (requests, short timeout)
exporter.py       openpyxl Excel writer (bold header, autosized columns, autofilter)
requirements.txt
build.bat         PyInstaller one-file build → dist/GoogleExtractor.exe
tests/            pytest for parsing.py and exporter.py
README.md         How to run / build
```
The scraper runs in a background thread and talks to the UI through a queue, so the window never freezes.

## Calls made by Claude (user said "do whatever is best")
- Third input = City.
- Email-from-website is optional and off by default.
- Edge fallback when Chrome isn't installed.
- Pure-logic parts (parsing, export) get unit tests; the live scraper is verified by a real run.
