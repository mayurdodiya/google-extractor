# Batch Queue — Design (approved 2026-11-24, user: "do whatever best")

## Intent
Run many searches unattended: import an Excel list (or add rows manually) of
`Business type | Location`, extract each row in turn, auto-save each row's results to
the Downloads folder, and show per-row status (Pending / In progress / Completed …).

## Hard constraint
No existing flow changes: single search, Start/Stop/Continue, CAPTCHA auto-resume,
Extract to Excel, stat cards, filter, theme, log all behave exactly as before.

## Approach (chosen)
Reuse the existing `Scraper` unchanged, one run per queue row, driven from the UI thread:
when a run posts `("done", n)` in batch mode, the app saves that row's records and launches
the next pending row. Rejected: a new multi-search scraper sharing one browser (touches the
working scraper; a browser restart per row costs only a few seconds).

## Details
- `batch.py` (pure, tested): `read_jobs(path)` for .xlsx/.csv — col A business type, col B location,
  header row auto-skipped, blank rows skipped, a single cell like "garment shop 395006" split at a
  trailing 6-digit PIN; `downloads_dir()`; `unique_path(folder, filename)`.
- UI: new "Batch queue" tab beside "Results": Import Excel, Add current search, Remove, Clear,
  Start queue, Open Downloads; table #, Business type, Location, Status, Records, Saved file.
  Double-click a completed row opens its file.
- Save: `Downloads\<type>_<location>_<date>.xlsx` (existing `default_filename` + `export_to_excel`);
  name clash → `_HHMMSS` suffix. 0 rows → "No results", no file. Scraper error → "Failed", continue.
- Stop during batch: save partial as `…_partial.xlsx`, row "Stopped", batch halts; Start queue resumes
  remaining Pending rows.
