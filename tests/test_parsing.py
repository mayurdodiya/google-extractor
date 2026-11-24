import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsing import extract_pincode, extract_city_state, clean_phone, find_emails, city_from_location


def test_pincode_found():
    assert extract_pincode("Shop 5, Varachha Rd, Surat, Gujarat 395006") == "395006"


def test_pincode_with_space():
    assert extract_pincode("Ring Rd, Surat, Gujarat 395 002, India") == "395002"


def test_pincode_missing():
    assert extract_pincode("Dabholi Char Rasta") == ""


def test_pincode_ignores_phone_digits():
    assert extract_pincode("Near bank 9876543210") == ""


def test_city_state_from_address():
    assert extract_city_state("Mini Bazar, Varachha, Surat, Gujarat 395006", "Surat") == ("Surat", "Gujarat")


def test_city_state_fallback_to_input():
    assert extract_city_state("Dabholi Char Rasta", "Surat") == ("Surat", "Gujarat")


def test_city_state_unknown_city():
    assert extract_city_state("Somewhere", "Atlantis") == ("Atlantis", "")


def test_city_not_fooled_by_word_in_street():
    # "baroda pristage" is a building name, not the city
    assert extract_city_state("6V64+VQ5 baroda pristage, shri krishna cloth stores, Varachha", "Surat") == ("Surat", "Gujarat")


def test_city_from_full_google_address():
    addr = "20-21, Lambe Hanuman Rd, near Maruti Chok, Varachha, Surat, Gujarat 395006"
    assert extract_city_state(addr, "Ahmedabad") == ("Surat", "Gujarat")
    assert extract_pincode(addr) == "395006"


def test_city_from_location():
    assert city_from_location("Varachha, Surat") == "Surat"
    assert city_from_location("395006, Surat") == "Surat"
    assert city_from_location("Varachha surat") == "Surat"
    assert city_from_location("Andheri, Mumbai, Maharashtra") == "Mumbai"
    assert city_from_location("Some Village") == "Some Village"
    assert city_from_location("395006") == ""


def test_clean_phone():
    assert clean_phone("Phone: 092653 46365") == "092653 46365"
    assert clean_phone("+91 98765 43210") == "+91 98765 43210"
    assert clean_phone("no phone") == ""


def test_find_emails():
    text = "Mail us: Info@Shop.com or sales@shop.in. logo@2x.png info@shop.com"
    assert find_emails(text) == ["info@shop.com", "sales@shop.in"]


from parsing import find_phones, split_phones, extract_area, social_url


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
    assert extract_area("Surat, Gujarat 395006", "Surat") == ""


def test_instagram_unwraps_google_redirect():
    hrefs = ["/url?q=https://www.instagram.com/shop_x/%3Figsh%3Dabc&sa=U"]
    assert social_url(hrefs, "instagram.com") == "https://www.instagram.com/shop_x/"
    assert social_url(["https://facebook.com/x"], "instagram.com") == ""


def test_facebook_url():
    assert social_url(["https://www.google.com/x", "https://m.facebook.com/shopx?ref=1"],
                      "facebook.com") == "https://m.facebook.com/shopx"


def test_social_prefers_profile_over_post():
    hrefs = ["https://www.instagram.com/reel/DfmXf03In8c/", "https://www.instagram.com/beyond_temptation_surat/"]
    assert social_url(hrefs, "instagram.com") == "https://www.instagram.com/beyond_temptation_surat/"
    assert social_url(hrefs[:1], "instagram.com") == "https://www.instagram.com/reel/DfmXf03In8c/"


def test_facebook_post_trimmed_to_page():
    href = "https://www.facebook.com/cafewhiteeye/posts/no-words-needed/1151581187833834/"
    assert social_url([href], "facebook.com") == "https://www.facebook.com/cafewhiteeye"


def test_facebook_profile_php_keeps_id():
    assert social_url(["https://www.facebook.com/profile.php?id=1000"], "facebook.com") == \
        "https://www.facebook.com/profile.php?id=1000"


from parsing import last_page_number


def test_last_page_number():
    assert last_page_number(["2", "3", "10", "Next", ""], 1) == 10
    assert last_page_number([], 4) == 4
    assert last_page_number(["Page 7", "5"], 6) == 7


def test_area_ignores_number_only_part():
    assert extract_area("12, Ankur Shopping Centre, 12, Surat, Gujarat 395006", "Surat") == ""
