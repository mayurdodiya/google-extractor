"""Excel export."""
import datetime
import re

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

COLUMNS = ["Name", "Category", "Address", "Area", "Phone", "Phone 2", "Phone 3", "Website",
           "Email", "Instagram", "Facebook", "Pincode", "City", "State", "Maps Link", "Page"]


def _cell(col: str, value):
    # Store PIN codes as numbers so Excel doesn't flag "number stored as text".
    if col == "Pincode" and isinstance(value, str) and value.isdigit():
        return int(value)
    return value


def export_to_excel(records: list[dict], path: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Results"
    ws.append(COLUMNS)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F6FEB")
    for r in records:
        ws.append([_cell(c, r.get(c, "")) for c in COLUMNS])

    for i, col in enumerate(COLUMNS, start=1):
        width = max([len(str(col))] + [len(str(r.get(col, "") or "")) for r in records])
        ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 10), 60)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)


def default_filename(business_type: str, area: str, city: str, date: datetime.date | None = None) -> str:
    date = date or datetime.date.today()
    parts = []
    for p in (business_type, area, city):
        p = re.sub(r"[^A-Za-z0-9]+", "_", p or "").strip("_")
        if p:
            parts.append(p)
    return "_".join(parts + [date.isoformat()]) + ".xlsx"
