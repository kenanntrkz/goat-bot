"""Email Finder — scrapes website contact pages for email addresses (parallel)."""

import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

TIMEOUT = 3
MAX_WORKERS = 15  # parallel site requests
CONTACT_PATHS = ["/iletisim", "/contact", "/"]

SKIP_PREFIXES = ("noreply", "no-reply", "donotreply", "example", "test", "info@example",
                 "webmaster", "postmaster", "admin@example", "support@example")

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def _extract_emails(text: str) -> list:
    found = EMAIL_RE.findall(text)
    seen = set()
    result = []
    for email in found:
        e = email.lower()
        if e in seen:
            continue
        seen.add(e)
        if any(e.startswith(p) for p in SKIP_PREFIXES):
            continue
        if any(e.endswith(ext) for ext in (".png", ".jpg", ".gif", ".woff", ".svg")):
            continue
        result.append(e)
    return result


def find_email_on_website(url: str) -> str:
    """Check common contact pages on a website, return first email found."""
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    base = url.rstrip("/")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; goat-bot/1.0)"})

    for path in CONTACT_PATHS:
        try:
            resp = session.get(base + path, timeout=TIMEOUT, allow_redirects=True)
            if resp.status_code == 200:
                emails = _extract_emails(resp.text)
                if emails:
                    return emails[0]
        except Exception:
            continue
    return ""


def enrich_leads_with_emails(leads: list, log=None) -> list:
    """
    Enrich leads that have a website but no email by scraping contact pages.
    Uses parallel requests — all sites scraped simultaneously.
    Non-destructive: leads without websites are returned unchanged.
    """
    to_enrich = [l for l in leads if l.get("website") and not l.get("email")]

    if not to_enrich:
        return leads

    if log:
        log(f"Email aranıyor: {len(to_enrich)} site paralel taranıyor...")

    # Parallel scraping
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_lead = {
            executor.submit(find_email_on_website, lead["website"]): lead
            for lead in to_enrich
        }
        found_count = 0
        for future in as_completed(future_to_lead):
            lead = future_to_lead[future]
            try:
                email = future.result()
                if email:
                    lead["email"] = email
                    found_count += 1
            except Exception:
                pass

    if log:
        log(f"Email bulundu: {found_count}/{len(to_enrich)}")

    return leads
