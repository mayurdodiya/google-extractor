import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openpyxl import load_workbook

from exporter import COLUMNS, export_to_excel, default_filename


def test_columns_order():
    assert COLUMNS == ["Name", "Category", "Address", "Area", "Phone", "Phone 2", "Phone 3",
                       "Website", "Email", "Instagram", "Facebook", "Pincode", "City", "State",
                       "Maps Link", "Page"]


def test_pincode_saved_as_number(tmp_path):
    path = tmp_path / "out.xlsx"
    export_to_excel([{"Name": "A", "Pincode": "395006", "Rating": "4.5", "Hours": "Open"}], str(path))
    ws = load_workbook(path).active
    assert ws["L2"].value == 395006
    assert ws.max_column == len(COLUMNS)


def test_export(tmp_path):
    path = tmp_path / "out.xlsx"
    export_to_excel([{"Name": "Punit Garments", "Phone": "123"}, {"Name": "Sai Dresses"}], str(path))
    ws = load_workbook(path).active
    assert [c.value for c in ws[1]] == COLUMNS
    assert ws.max_row == 3
    assert ws["A2"].value == "Punit Garments"
    assert ws["E2"].value == "123"


def test_default_filename_sanitized():
    name = default_filename("garment shop", "Varachha/East", "Surat?", datetime.date(2026, 11, 24))
    assert name == "garment_shop_Varachha_East_Surat_2026-11-24.xlsx"
