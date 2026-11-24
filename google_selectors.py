"""All Google page selectors in one place. Google changes its HTML often —
if extraction breaks, update the lists here (first match wins)."""

SEARCH_BOX = ["textarea[name=q]", "input[name=q]"]

# One result card in the Places (local) results list.
RESULT_CARDS = [
    "div.VkpGBb",
    "div[jscontroller][data-cid]",
    "#search div[role=heading]:not([aria-level]) >> xpath=ancestor::a[1]",
]

# Clickable element inside a card that opens the detail panel.
CARD_CLICK = ["a.vwVdIc", "a[role=link]", "div[role=heading]", "a"]

CARD_NAME = ["div[role=heading] span", "div[role=heading]", ".OSrXXb", ".dbg0pd"]

DETAIL_MAPS_LINK = ["a.PWtZJ", "a[href*='ftid=']"]

# Detail panel that opens on the right after clicking a card.
# (the visible role=dialog is the listing's detail panel; #rhs is often just the map)
DETAIL_PANEL = ["div.xpdopen", "div[jsname=xQjRM]", "div.immersive-container", "div[role=dialog]", "#rhs"]
DETAIL_NAME = ["h2.RjvGlb", "h2[data-attrid=title]", "div[data-attrid=title]", "h2 span", "[role=heading][aria-level='2']"]
DETAIL_ADDRESS = ["a.PWtZJ span.C1cKff", "span.C1cKff",
                  "[data-attrid='kc:/location/location:address'] span.LrzXr",
                  "[data-attrid='kc:/location/location:address']", "span.LrzXr"]
DETAIL_PHONE = ["a[data-phone-number]",
                "[data-attrid='kc:/local:alt phone'] span[aria-label]",
                "[data-attrid='kc:/collection/knowledge_panels/has_phone:phone'] span[aria-label]",
                "span[aria-label^='Call phone number']", "a[data-dtype=d3ph] span",
                "[data-attrid*='phone']"]
DETAIL_WEBSITE = ["a:has(span.aSAiSd)", "a.cevG5:has-text('Website')", "a[aria-label='Website']", "a.dHS6jb", "a:has-text('Website')"]
DETAIL_CATEGORY = ["span.YhemCb", "[data-attrid='subtitle']", "span.E5BaQ"]
DETAIL_RATING = ["span.Aq14fc", "span.yi40Hd", "span[aria-hidden=true].z3HNkc + span"]
DETAIL_REVIEWS = ["span.hqzQac a span", "a[data-async-trigger=reviewDialog] span", "span.RDApEe"]
DETAIL_HOURS = ["[data-attrid='kc:/location/location:hours'] span.TLou0b",
                "[data-attrid='kc:/location/location:hours']", "span.JjSWRd"]

# Social profile links in the detail panel (usually under "Profiles").
DETAIL_SOCIAL = ["a[href*='instagram.com']", "a[href*='facebook.com']"]

# Numbered links in the pagination bar ("2", "3", … / aria-label "Page 2").
PAGE_NUMBERS = ["a[aria-label^='Page ']", "table.AaVjTc td a", "td.d6cvqb ~ td a", "#botstuff td a"]

NEXT_PAGE = ["a#pnnext", "a[aria-label='Next page']", "a[aria-label='Next']", "td.d6cvqb:last-child a"]

CAPTCHA_MARKERS = ["/sorry/", "unusual traffic"]
CONSENT_BUTTONS = ["button:has-text('Accept all')", "button:has-text('I agree')", "button:has-text('Reject all')"]
