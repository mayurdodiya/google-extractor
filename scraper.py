"""Browser worker: searches Google Places, opens each listing, follows pages.

Runs in a background thread. Communicates with the UI only through `out_queue`:
    ("log", str) ("status", str) ("record", dict) ("captcha", None) ("done", int)
    ("progress", (page_no, listing_index, listings_on_page))
    ("page_done", (page_no, rows_added_from_that_page))
    ("pages_total", highest_page_number_google_shows_so_far)
    ("last_page", page_no)  - no "Next" link after this page
"""
import os
import random
import re
import time
import traceback
import urllib.parse

from playwright.sync_api import sync_playwright, Error as PWError, TimeoutError as PWTimeout

import google_selectors as S
from email_finder import find_email_on_website
from parsing import (extract_pincode, extract_city_state, clean_phone, city_from_location,
                     find_phones, split_phones, extract_area, social_url, find_emails,
                     last_page_number)

APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "GoogleExtractor")
PROFILE_DIR = os.path.join(APP_DIR, "profile")
DEBUG_DIR = os.path.join(APP_DIR, "debug")
MAX_PAGES = 200


class StopRequested(Exception):
    pass


class Scraper:
    def __init__(self, business_type, location, fetch_emails, out_queue, stop_event, continue_event):
        self.business_type = business_type.strip()
        self.location = location.strip()
        self.city = city_from_location(self.location)  # fallback when an address has no city
        self.fetch_emails = fetch_emails
        self.q = out_queue
        self.stop_event = stop_event
        self.continue_event = continue_event
        self.seen = set()
        self.count = 0

    # ---------- helpers ----------
    @property
    def query(self):
        return f"{self.business_type} in {self.location}" if self.location else self.business_type

    def log(self, msg):
        self.q.put(("log", msg))

    def status(self, msg):
        self.q.put(("status", msg))

    def check_stop(self):
        if self.stop_event.is_set():
            raise StopRequested()

    def pause(self, lo=1.0, hi=3.0):
        end = time.time() + random.uniform(lo, hi)
        while time.time() < end:
            self.check_stop()
            time.sleep(0.1)

    @staticmethod
    def first(root, selectors, timeout=0):
        """First visible locator among fallbacks, or None."""
        # Google keeps old (hidden) detail panels in the page, so only consider visible matches.
        for sel in selectors:
            try:
                loc = root.locator(sel).filter(visible=True).first
                if timeout:
                    loc.wait_for(state="visible", timeout=timeout)
                if loc.count():
                    return loc
            except (PWError, PWTimeout):
                continue
        return None

    def text_of(self, root, selectors):
        loc = self.first(root, selectors)
        if not loc:
            return ""
        try:
            return loc.inner_text(timeout=2000).strip()
        except PWError:
            return ""

    # ---------- browser ----------
    def launch(self, p):
        os.makedirs(PROFILE_DIR, exist_ok=True)
        last_err = None
        for channel in ("chrome", "msedge"):
            try:
                ctx = p.chromium.launch_persistent_context(
                    PROFILE_DIR, channel=channel, headless=False, no_viewport=True,
                    locale="en-IN", args=["--start-maximized"])
                self.log(f"Opened {'Chrome' if channel == 'chrome' else 'Edge'} browser.")
                return ctx
            except PWError as e:
                last_err = e
        raise RuntimeError(f"Could not open Chrome or Edge. Please install Google Chrome.\n{last_err}")

    def is_captcha(self, page):
        try:
            if "/sorry/" in page.url:
                return True
            return "unusual traffic" in page.locator("body").inner_text(timeout=3000).lower()
        except PWError:
            return False

    def wait_if_captcha(self, page):
        if not self.is_captcha(page):
            return
        self.log("Google is asking for a CAPTCHA. Solve it in the browser window — "
                 "extraction resumes automatically (or click Continue).")
        self.continue_event.clear()
        self.q.put(("captcha", None))
        # Resume as soon as the CAPTCHA page is gone, or when the user clicks Continue.
        while True:
            self.check_stop()
            time.sleep(2)
            if self.continue_event.is_set() or not self.is_captcha(page):
                self.continue_event.clear()
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                except PWError:
                    pass
                self.pause(1, 2)
                if not self.is_captcha(page):
                    break
        self.log("CAPTCHA cleared — continuing.")
        self.q.put(("status", "Continuing after CAPTCHA…"))

    def accept_consent(self, page):
        btn = self.first(page, S.CONSENT_BUTTONS)
        if btn:
            try:
                btn.click(timeout=3000)
                self.pause(1, 2)
            except PWError:
                pass

    def save_debug(self, page, name):
        try:
            os.makedirs(DEBUG_DIR, exist_ok=True)
            path = os.path.join(DEBUG_DIR, name)
            with open(path + ".html", "w", encoding="utf-8") as f:
                f.write(page.content())
            page.screenshot(path=path + ".png", full_page=True)
            self.log(f"Saved page snapshot for troubleshooting: {path}.html")
        except Exception:
            pass

    # ---------- extraction ----------
    def get_cards(self, page):
        for sel in S.RESULT_CARDS:
            try:
                cards = page.locator(sel)
                n = cards.count()
                if n:
                    return [cards.nth(i) for i in range(n)]
            except PWError:
                continue
        return []

    @staticmethod
    def parse_card_text(text):
        """Fallback: pull fields from the list card's visible text."""
        rec = {}
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            return rec
        rec["Name"] = lines[0]
        for line in lines[1:]:
            m = re.match(r"^(\d[.,]\d)\b", line)
            if m and "Rating" not in rec:
                rec["Rating"] = m.group(1).replace(",", ".")
            m = re.search(r"\(([\d.,]+\s*[Kk]?)\)", line)
            if m and "Reviews" not in rec:
                rec["Reviews"] = m.group(1)
            if "·" in line and ("Rating" in rec or "Reviews" in rec) and "Category" not in rec and "(" in line:
                rec["Category"] = line.split("·")[-1].strip()
                continue
            if re.match(r"^(Open|Closed|Opens|Closes|Open 24)", line):
                rec.setdefault("Hours", line)
                continue
            if re.match(r"^\d[.,]\d$|^\([\d.,]+[Kk]?\)$", line):
                continue
            if "Category" in rec and "Address" not in rec and not line.startswith('"'):
                parts = [p.strip() for p in line.split("·")]
                for part in parts:
                    ph = clean_phone(part)
                    if ph and len(re.sub(r"\D", "", part)) >= 8 and not re.search(r"[A-Za-z]{3,}", part):
                        rec.setdefault("Phone", ph)
                    elif "Address" not in rec and part and not re.match(r"^\d+\+? years? in business", part):
                        rec["Address"] = part
        return rec

    def read_detail(self, page):
        rec = {}
        rec["Name"] = self.text_of(page, S.DETAIL_NAME)
        rec["Address"] = self.text_of(page, S.DETAIL_ADDRESS).replace("⁦", "").replace("⁩", "")
        phone_loc = self.first(page, S.DETAIL_PHONE)
        if phone_loc:
            try:
                rec["Phone"] = clean_phone(phone_loc.get_attribute("aria-label") or phone_loc.inner_text())
            except PWError:
                pass
        maps = self.first(page, S.DETAIL_MAPS_LINK)
        if maps:
            try:
                href = maps.get_attribute("href") or ""
                m = re.search(r"ftid=(0x[0-9a-f]+:0x[0-9a-f]+)", href)
                if m:
                    rec["Maps Link"] = f"https://www.google.com/maps?ftid={m.group(1)}"
                elif href.startswith("http"):
                    rec["Maps Link"] = href
            except PWError:
                pass
        site = self.first(page, S.DETAIL_WEBSITE)
        if site:
            try:
                href = site.get_attribute("href") or ""
                if href.startswith("/url?"):
                    href = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("q", [""])[0]
                if href.startswith("http") and "google." not in href:
                    rec["Website"] = href
            except PWError:
                pass

        # Text fallback: knowledge panels label fields as "Address: ...", "Phone: ..."
        panel = self.first(page, S.DETAIL_PANEL)
        try:
            body = (panel or page.locator("body")).inner_text(timeout=3000)
        except PWError:
            body = ""
        for label, key in (("Address", "Address"), ("Phone", "Phone")):
            if not rec.get(key):
                m = re.search(rf"^{label}:\s*(.+)$", body, re.M)
                if m:
                    rec[key] = clean_phone(m.group(1)) if key == "Phone" else m.group(1).strip()

        # Extra details (best effort): all phone numbers, email, Instagram / Facebook links.
        # Only read inside the detail panel, so other shops in the result list never leak in.
        if panel:
            rec["_phones"] = self.all_phones(panel, body, rec.get("Phone", ""))
            emails = find_emails(body)
            if emails:
                rec["Email"] = emails[0]
            hrefs = self.social_hrefs(panel)
            rec["Instagram"] = social_url(hrefs, "instagram.com")
            rec["Facebook"] = social_url(hrefs, "facebook.com")
        return {k: v for k, v in rec.items() if v}

    def all_phones(self, panel, body, first_phone):
        """Every phone number shown in the detail panel (first one first)."""
        texts = [first_phone]
        for sel in S.DETAIL_PHONE:
            try:
                locs = panel.locator(sel).filter(visible=True)
                for i in range(min(locs.count(), 10)):
                    loc = locs.nth(i)
                    texts.append(loc.get_attribute("aria-label", timeout=1000) or loc.inner_text(timeout=1000))
            except PWError:
                continue
        # Only "Phone: ..." lines of the text — other lines hold ratings, hours, pincodes.
        texts += re.findall(r"^Phones?:\s*(.+)$", body, re.M)
        return find_phones(", ".join(t for t in texts if t))

    def social_hrefs(self, root):
        hrefs = []
        for sel in S.DETAIL_SOCIAL:
            try:
                locs = root.locator(sel)
                for i in range(min(locs.count(), 10)):
                    hrefs.append(locs.nth(i).get_attribute("href", timeout=1000) or "")
            except PWError:
                continue
        return hrefs

    def maps_link(self, card, name, address):
        try:
            cid = card.get_attribute("data-cid") or card.locator("[data-cid]").first.get_attribute("data-cid", timeout=500)
        except PWError:
            cid = None
        if cid:
            return f"https://maps.google.com/?cid={cid}"
        return "https://www.google.com/maps/search/" + urllib.parse.quote_plus(f"{name} {address}".strip())

    def scrape_card(self, page, card, page_no):
        try:
            card.scroll_into_view_if_needed(timeout=3000)
            card_text = card.inner_text(timeout=3000)
        except PWError:
            return
        rec = self.parse_card_text(card_text)
        name = rec.get("Name", "")
        if not name:
            return

        click_target = self.first(card, S.CARD_CLICK) or card
        try:
            click_target.click(timeout=5000)
            # wait until the detail panel shows this listing
            end = time.time() + 6
            while time.time() < end:
                self.check_stop()
                title = self.text_of(page, S.DETAIL_NAME)
                if title and title.lower()[:15] == name.lower()[:15]:
                    break
                time.sleep(0.3)
            self.pause(0.8, 1.8)
            self.wait_if_captcha(page)
            detail = self.read_detail(page)
            if detail.get("Name", "").lower()[:15] == name.lower()[:15]:
                card_phone = rec.get("Phone", "")
                phones = detail.pop("_phones", [])
                rec.update(detail)  # detail panel is richer; card values are fallback
                rec["_phones"] = phones + [card_phone]
            else:
                for k, v in detail.items():  # panel may be stale: only fill gaps
                    if k not in ("Name", "Website", "_phones", "Email", "Instagram", "Facebook"):
                        rec.setdefault(k, v)
        except StopRequested:
            raise
        except PWError as e:
            self.log(f"  (could not open details for '{name}', using list info) {str(e).splitlines()[0]}")

        key = (rec.get("Name", "").lower(), rec.get("Address", "").lower()[:40])
        if key in self.seen:
            return
        self.seen.add(key)

        phones = rec.pop("_phones", None) or [rec.get("Phone", "")]
        rec.pop("Phone", None)
        rec.update(split_phones(find_phones(", ".join(p for p in phones if p))))

        address = rec.get("Address", "")
        rec["Pincode"] = extract_pincode(address)
        rec["City"], rec["State"] = extract_city_state(address, self.city)
        rec["Area"] = extract_area(address, rec["City"])
        if not rec.get("Maps Link"):
            rec["Maps Link"] = self.maps_link(card, rec["Name"], address)
        rec["Page"] = page_no
        if self.fetch_emails and rec.get("Website") and not rec.get("Email"):
            self.status(f"Page {page_no} — checking website for email: {rec['Website']}")
            rec["Email"] = find_email_on_website(rec["Website"])

        self.count += 1
        self.q.put(("record", rec))
        self.log(f"  {self.count}. {rec['Name']} | {rec.get('Phone', '-')} | {address[:60]}")

    def last_page(self, page, page_no):
        """Highest page number shown in Google's pagination bar (best effort)."""
        texts = []
        for sel in S.PAGE_NUMBERS:
            try:
                locs = page.locator(sel)
                for i in range(min(locs.count(), 30)):
                    loc = locs.nth(i)
                    texts += [loc.get_attribute("aria-label", timeout=500) or "", loc.inner_text(timeout=500)]
            except PWError:
                continue
        return last_page_number(texts, page_no)

    def go_next(self, page):
        # Open the "Next" link's URL directly: clicking it often fails because the
        # open detail panel sits on top of the pagination arrows.
        for sel in S.NEXT_PAGE:
            try:
                loc = page.locator(sel).first
                if not loc.count():
                    continue
                href = loc.get_attribute("href")
                if href:
                    page.goto(urllib.parse.urljoin(page.url, href), wait_until="domcontentloaded")
                else:
                    loc.click(timeout=5000, force=True)
                    page.wait_for_load_state("domcontentloaded")
                return True
            except PWError as e:
                self.log(f"  (next page failed: {str(e).splitlines()[0]})")
        return False

    # ---------- main ----------
    def run(self):
        try:
            with sync_playwright() as p:
                ctx = self.launch(p)
                try:
                    self._run(ctx)
                finally:
                    try:
                        ctx.close()
                    except Exception:
                        pass
        except StopRequested:
            self.log("Stopped by user.")
        except Exception as e:
            self.log(f"ERROR: {e}")
            self.log(traceback.format_exc())
        finally:
            self.q.put(("done", self.count))

    def _run(self, ctx):
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        url = "https://www.google.com/search?" + urllib.parse.urlencode({"q": self.query, "tbm": "lcl", "hl": "en"})
        self.log(f"Searching: {self.query}")
        self.status("Opening Google…")
        page.goto(url, wait_until="domcontentloaded")
        self.pause(1.5, 3)
        self.accept_consent(page)
        self.wait_if_captcha(page)

        page_no = 1
        while page_no <= MAX_PAGES:
            self.check_stop()
            cards = self.get_cards(page)
            if not cards:
                if page_no == 1:
                    self.log("No listings found on the page.")
                    self.save_debug(page, "no_results")
                break
            self.log(f"Page {page_no}: {len(cards)} listings")
            self.q.put(("pages_total", self.last_page(page, page_no)))
            before = self.count
            for i, card in enumerate(cards, 1):
                self.check_stop()
                self.status(f"Page {page_no} — listing {i}/{len(cards)} — {self.count} saved")
                self.q.put(("progress", (page_no, i, len(cards))))
                self.scrape_card(page, card, page_no)
                self.pause(1, 2.5)
            self.q.put(("page_done", (page_no, self.count - before)))
            self.status(f"Page {page_no} done — {self.count} saved. Looking for next page…")
            if not self.go_next(page):
                self.log("No more pages.")
                self.q.put(("last_page", page_no))
                break
            page_no += 1
            self.pause(2, 4)
            self.wait_if_captcha(page)
        self.log(f"Finished. {self.count} businesses collected.")
