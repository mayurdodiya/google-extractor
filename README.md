# Google Places Extractor

Desktop tool: enter **Business type** and **Location** (e.g. "Varachha, Surat" or "395006, Surat") → it opens its own Chrome window,
searches Google Places, opens every listing on every result page, and collects
Name, Category, Address, Area, Phone, Phone 2, Phone 3 (all numbers Google shows), Website,
Email, Instagram, Facebook (when Google shows them), Pincode, City, State, Maps link, Page.
When finished click **Extract to Excel**.

## Use (any Windows PC)
1. Copy `dist\GoogleExtractor.exe` to the PC. Google Chrome should be installed (Edge is used if not).
2. Double-click it, fill Business type + Location, click **Start**.
3. Don't use the opened browser window while it works (you can minimise the app).
4. If Google shows a CAPTCHA, solve it in that browser window — extraction continues automatically.
5. When "Completed" appears, click **Extract to Excel** and choose where to save.

**Stop** ends early — everything collected so far can still be exported.
Tick *"Also check each shop's website for email"* to visit each shop's website looking for an email (slower).
Google rarely shows emails on listings itself.

## Run from source
```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py
```
Tests: `.venv\Scripts\python -m pytest -q`

## Build the .exe
Run `build.bat` → `dist\GoogleExtractor.exe`.

## If extraction stops working
Google changes its page layout from time to time. All page selectors are in
`google_selectors.py`. When no listings are found, a snapshot of the page is saved to
`%LOCALAPPDATA%\GoogleExtractor\debug\` to help update them.

## Notes
- Browser profile is kept in `%LOCALAPPDATA%\GoogleExtractor\profile` (separate from your normal Chrome).
- Automated scraping is against Google's Terms of Service; keep volumes reasonable. Heavy use triggers CAPTCHAs.
