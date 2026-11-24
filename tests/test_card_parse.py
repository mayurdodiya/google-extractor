import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper import Scraper


def test_card_with_phone():
    text = ("KULDEVI GARMENT\n3.5\n(41) · Clothing store\nDabholi Char Rasta · 092653 46365\n"
            "Open · Closes 9 PM\n\"Very good quality of clothes\"")
    rec = Scraper.parse_card_text(text)
    assert rec["Name"] == "KULDEVI GARMENT"
    assert rec["Rating"] == "3.5"
    assert rec["Reviews"] == "41"
    assert rec["Category"] == "Clothing store"
    assert rec["Address"] == "Dabholi Char Rasta"
    assert rec["Phone"] == "092653 46365"
    assert rec["Hours"] == "Open · Closes 9 PM"


def test_card_rating_inline():
    text = "Sai Dresses\n4.6 ★★★★★ (1K) · Clothing store\n5th Floor, Auditorium Hall, Ring Rd\nOpen · Closes 9 PM"
    rec = Scraper.parse_card_text(text)
    assert rec["Rating"] == "4.6"
    assert rec["Reviews"] == "1K"
    assert rec["Category"] == "Clothing store"
    assert rec["Address"] == "5th Floor, Auditorium Hall, Ring Rd"
    assert "Phone" not in rec
