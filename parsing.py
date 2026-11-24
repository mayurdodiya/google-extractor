"""Pure text helpers: pincode / city / state from address, phone cleanup, email search."""
import re
import urllib.parse

STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
    "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
    "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]

# Common cities -> state (used to fill State when the address doesn't contain it).
CITY_STATE = {
    "surat": "Gujarat", "ahmedabad": "Gujarat", "vadodara": "Gujarat", "baroda": "Gujarat",
    "rajkot": "Gujarat", "bhavnagar": "Gujarat", "jamnagar": "Gujarat", "gandhinagar": "Gujarat",
    "navsari": "Gujarat", "vapi": "Gujarat", "valsad": "Gujarat", "bharuch": "Gujarat",
    "anand": "Gujarat", "junagadh": "Gujarat", "mehsana": "Gujarat", "morbi": "Gujarat",
    "mumbai": "Maharashtra", "pune": "Maharashtra", "nagpur": "Maharashtra", "nashik": "Maharashtra",
    "thane": "Maharashtra", "aurangabad": "Maharashtra", "delhi": "Delhi", "new delhi": "Delhi",
    "bengaluru": "Karnataka", "bangalore": "Karnataka", "mysuru": "Karnataka", "mysore": "Karnataka",
    "chennai": "Tamil Nadu", "coimbatore": "Tamil Nadu", "madurai": "Tamil Nadu", "tiruppur": "Tamil Nadu",
    "hyderabad": "Telangana", "kolkata": "West Bengal", "jaipur": "Rajasthan", "jodhpur": "Rajasthan",
    "udaipur": "Rajasthan", "lucknow": "Uttar Pradesh", "kanpur": "Uttar Pradesh", "noida": "Uttar Pradesh",
    "agra": "Uttar Pradesh", "varanasi": "Uttar Pradesh", "indore": "Madhya Pradesh",
    "bhopal": "Madhya Pradesh", "patna": "Bihar", "ludhiana": "Punjab", "amritsar": "Punjab",
    "gurgaon": "Haryana", "gurugram": "Haryana", "chandigarh": "Chandigarh", "kochi": "Kerala",
    "thiruvananthapuram": "Kerala", "visakhapatnam": "Andhra Pradesh", "vijayawada": "Andhra Pradesh",
    "bhubaneswar": "Odisha", "raipur": "Chhattisgarh", "ranchi": "Jharkhand", "guwahati": "Assam",
    "dehradun": "Uttarakhand", "panaji": "Goa", "silvassa": "Dadra and Nagar Haveli and Daman and Diu",
    "daman": "Dadra and Nagar Haveli and Daman and Diu",
}

_PIN_RE = re.compile(r"(?<!\d)([1-9]\d{2})\s?(\d{3})(?!\d)")
_PHONE_RE = re.compile(r"(\+?\d[\d\s\-()]{7,}\d)")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_BAD_EMAIL_SUFFIX = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")


def extract_pincode(address: str) -> str:
    """Return the 6-digit Indian PIN code in the address, or ''."""
    for m in _PIN_RE.finditer(address or ""):
        return m.group(1) + m.group(2)
    return ""


def extract_city_state(address: str, fallback_city: str) -> tuple[str, str]:
    """Find city and state in the address; fall back to the user's city input."""
    address = address or ""
    low = address.lower()
    state = next((s for s in STATES if s.lower() in low), "")

    city = ""
    parts = [p.strip() for p in address.split(",") if p.strip()]
    # Typical Google format: "..., City, State 395006" -> the part before the state
    if state:
        for i, p in enumerate(parts):
            if state.lower() in p.lower() and i > 0:
                city = re.sub(r"\d", "", parts[i - 1]).strip()
                break
    if not city:
        # A comma-separated part that is exactly a known city (not "baroda pristage")
        for p in reversed(parts):
            if p.lower() in CITY_STATE:
                city = p.title()
                break
    if not city:
        city = (fallback_city or "").strip()
    if not state:
        state = CITY_STATE.get(city.lower(), "") or CITY_STATE.get((fallback_city or "").strip().lower(), "")
    return city, state


def city_from_location(location: str) -> str:
    """Best guess of the city in the user's location input ('Varachha, Surat' -> 'Surat')."""
    location = (location or "").strip()
    low = location.lower()
    for c in sorted(CITY_STATE, key=len, reverse=True):
        if re.search(r"\b" + re.escape(c) + r"\b", low):
            return c.title()
    parts = [p.strip() for p in location.split(",") if p.strip() and not p.strip().isdigit()]
    parts = [p for p in parts if p.lower() not in (s.lower() for s in STATES)]
    return parts[-1] if parts else ""


def clean_phone(text: str) -> str:
    """Extract the first phone-number-looking string from text."""
    m = _PHONE_RE.search(text or "")
    if not m:
        return ""
    phone = m.group(1).strip()
    digits = re.sub(r"\D", "", phone)
    return phone if 8 <= len(digits) <= 15 else ""


def find_emails(text: str) -> list[str]:
    """All unique email addresses in text, lowercased, in order of appearance."""
    seen: list[str] = []
    for e in _EMAIL_RE.findall(text or ""):
        e = e.lower().rstrip(".")
        if e.endswith(_BAD_EMAIL_SUFFIX) or e in seen:
            continue
        seen.append(e)
    return seen


def find_phones(text: str) -> list[str]:
    """Every phone-number-looking string (8-15 digits) in text, deduped by last 10 digits."""
    phones, seen = [], set()
    for m in _PHONE_RE.finditer(text or ""):
        phone = m.group(1).strip()
        digits = re.sub(r"\D", "", phone)
        if not 8 <= len(digits) <= 15 or digits[-10:] in seen:
            continue
        seen.add(digits[-10:])
        phones.append(phone)
    return phones


def split_phones(phones: list[str]) -> dict:
    """{'Phone': 1st, 'Phone 2': 2nd, 'Phone 3': rest comma-joined} - only non-empty keys."""
    out = {}
    for key, value in (("Phone", phones[:1]), ("Phone 2", phones[1:2]), ("Phone 3", phones[2:])):
        if value:
            out[key] = ", ".join(value)
    return out


def extract_area(address: str, city: str) -> str:
    """The address part just before the city ('Mini Bazar, Varachha, Surat, ...' -> 'Varachha')."""
    city = (city or "").strip().lower()
    if not city:
        return ""
    parts = [p.strip() for p in (address or "").split(",") if p.strip()]
    for i, p in enumerate(parts):
        if re.sub(r"\d", "", p).strip().lower() == city:
            area = parts[i - 1] if i > 0 else ""
            return area if re.search(r"[A-Za-z]", area) else ""  # "12" is a shop no., not an area
    return ""


_POST_PATHS = ("p", "reel", "reels", "tv", "stories", "explore", "share", "watch", "photo.php", "story.php")


def social_url(hrefs: list[str], domain: str) -> str:
    """Best link to `domain` (e.g. 'instagram.com'): a profile/page link is preferred over a
    single post. Facebook post links are trimmed to the page. Unwraps Google's /url?q= redirect."""
    post = ""
    for href in hrefs:
        href = href or ""
        if href.startswith("/url?") or "google." in urllib.parse.urlparse(href).netloc:
            href = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("q", [href])[0]
        u = urllib.parse.urlparse(href)
        if not (u.scheme.startswith("http") and (u.netloc == domain or u.netloc.endswith("." + domain))):
            continue
        path = u.path
        segs = [x for x in path.split("/") if x]
        if domain == "facebook.com" and len(segs) > 1 and segs[1] in ("posts", "photos", "videos", "reels"):
            path = "/" + segs[0]
            segs = segs[:1]
        query = u.query if path.endswith("profile.php") else ""  # profile.php?id=... needs its id
        url = urllib.parse.urlunparse((u.scheme, u.netloc, path, "", query, ""))
        if segs and segs[0].lower() not in _POST_PATHS:
            return url
        post = post or url
    return post


def last_page_number(texts: list[str], current: int) -> int:
    """Highest page number among pagination link texts/labels ('10', 'Page 10'), at least `current`."""
    nums = [int(m.group(1)) for t in texts for m in [re.fullmatch(r"(?:Page\s*)?(\d{1,3})", (t or "").strip())] if m]
    return max(nums + [current])
