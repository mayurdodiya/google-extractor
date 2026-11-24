"""Optional: look for an email address on a business's own website."""
import re
import urllib.parse

import requests

from parsing import find_emails

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
_CONTACT_RE = re.compile(r'href=["\']([^"\']*(?:contact|about)[^"\']*)["\']', re.I)


def _get(url: str, timeout: int) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.ok and "text/html" in r.headers.get("Content-Type", "text/html"):
            return r.text
    except requests.RequestException:
        pass
    return ""


def find_email_on_website(url: str, timeout: int = 8) -> str:
    """Return up to 3 emails ('; '-joined) found on the home page or a contact/about page."""
    html = _get(url, timeout)
    emails = find_emails(html)
    if not emails and html:
        host = urllib.parse.urlparse(url).netloc
        for link in _CONTACT_RE.findall(html)[:3]:
            full = urllib.parse.urljoin(url, link)
            if urllib.parse.urlparse(full).netloc != host:
                continue
            emails = find_emails(_get(full, timeout))
            if emails:
                break
    return "; ".join(emails[:3])
