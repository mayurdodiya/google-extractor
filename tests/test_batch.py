import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openpyxl import Workbook

from batch import read_jobs, unique_path


def _xlsx(path, rows):
    wb = Workbook()
    for r in rows:
        wb.active.append(r)
    wb.save(path)


def test_read_xlsx_two_columns_with_header(tmp_path):
    p = tmp_path / "jobs.xlsx"
    _xlsx(p, [["Business type", "Location"], ["garment shop", 395006], ["electric shop", "395010"],
              [None, None], ["  hardware shop ", "Varachha, Surat"]])
    assert read_jobs(str(p)) == [("garment shop", "395006"), ("electric shop", "395010"),
                                 ("hardware shop", "Varachha, Surat")]


def test_read_xlsx_without_header(tmp_path):
    p = tmp_path / "jobs.xlsx"
    _xlsx(p, [["garment shop", "395006"]])
    assert read_jobs(str(p)) == [("garment shop", "395006")]


def test_read_single_cell_split_at_pincode(tmp_path):
    p = tmp_path / "jobs.xlsx"
    _xlsx(p, [["garment shop  395006"], ["electric shop 395010"]])
    assert read_jobs(str(p)) == [("garment shop", "395006"), ("electric shop", "395010")]


def test_read_csv(tmp_path):
    p = tmp_path / "jobs.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([["Business", "Pincode"], ["garment shop", "395006"]])
    assert read_jobs(str(p)) == [("garment shop", "395006")]


def test_float_pincode_from_excel(tmp_path):
    p = tmp_path / "jobs.xlsx"
    _xlsx(p, [["garment shop", 395006.0]])
    assert read_jobs(str(p)) == [("garment shop", "395006")]


def test_unique_path(tmp_path):
    first = unique_path(str(tmp_path), "a.xlsx")
    assert first == os.path.join(str(tmp_path), "a.xlsx")
    open(first, "w").close()
    second = unique_path(str(tmp_path), "a.xlsx")
    assert second != first and second.endswith(".xlsx") and not os.path.exists(second)
