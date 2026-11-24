"""Batch queue helpers: read search jobs from Excel/CSV, pick where results are saved."""
import csv
import datetime
import os
import re

from openpyxl import load_workbook

_HEADER_WORDS = ("business", "type", "category", "keyword", "location", "pincode", "pin code", "area", "city")
_TRAILING_PIN = re.compile(r"^(.*?)[\s,]+(\d{6})$")


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)  # Excel stores 395006 as 395006.0
    return re.sub(r"\s+", " ", str(value)).strip()


def _is_header(a: str, b: str) -> bool:
    joined = f"{a} {b}".lower()
    return any(w in joined for w in _HEADER_WORDS) and not re.search(r"\d{6}", joined)


def _rows(path: str):
    if path.lower().endswith(".csv"):
        with open(path, newline="", encoding="utf-8-sig") as f:
            yield from csv.reader(f)
    else:
        wb = load_workbook(path, read_only=True, data_only=True)
        yield from wb.active.iter_rows(values_only=True)
        wb.close()


def read_jobs(path: str) -> list[tuple[str, str]]:
    """(business type, location) pairs from column A and B of the first sheet."""
    jobs = []
    for i, row in enumerate(_rows(path)):
        row = list(row) + [None, None]
        a, b = _text(row[0]), _text(row[1])
        if i == 0 and _is_header(a, b):
            continue
        if a and not b:
            m = _TRAILING_PIN.match(a)  # "garment shop 395006" in one cell
            if m:
                a, b = m.group(1).strip(), m.group(2)
        if a:
            jobs.append((a, b))
    return jobs


def downloads_dir() -> str:
    """The user's Downloads folder (honours a moved Downloads folder on Windows)."""
    try:
        import ctypes
        from ctypes import wintypes
        import uuid

        class GUID(ctypes.Structure):
            _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                        ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

        u = uuid.UUID("{374DE290-123F-4565-9164-39C4925E467B}")  # FOLDERID_Downloads
        guid = GUID(u.fields[0], u.fields[1], u.fields[2], (ctypes.c_ubyte * 8)(*u.bytes[8:]))
        out = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) == 0:
            path = out.value
            ctypes.windll.ole32.CoTaskMemFree(out)
            if path and os.path.isdir(path):
                return path
    except Exception:
        pass
    path = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(path, exist_ok=True)
    return path


def unique_path(folder: str, filename: str) -> str:
    """folder/filename, or with a time (and counter) suffix if that file already exists."""
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(filename)
    stamp = datetime.datetime.now().strftime("%H%M%S")
    n = 0
    while True:
        candidate = os.path.join(folder, f"{stem}_{stamp}{'' if not n else f'_{n}'}{ext}")
        if not os.path.exists(candidate):
            return candidate
        n += 1
