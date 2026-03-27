"""Email Finder — scrapes website contact pages for email addresses."""

import re
import requests

TIMEOUT = 4
CONTACT_PATHS = ["/iletisim", "/contact", "/hakkimizda", "/about", "/bize-ulasin", "/"]

# Emails to skip
SKIP_PREFIXES = ("noreply", "no-reply", "donotreply", "example", "test", "info@example",
                 "webmaster", "postmaster", "admin@example", "support@example")

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

_session = requests.Session()
_session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; bot/1.0)"})


def _extract_emails(text: str) -> list[str]:
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
        # Skip image/font file false positives
        if any(e.endswith(ext) for ext in (".png", ".jpg", ".gif", ".woff", ".svg")):
            continue
        result.append(e)
    return result


def find_email_on_website(url: str) -> str:
    """
    Try to find an email on a website by checking common contact pages.
    Returns the first email found, or empty string.
    """
    if not url:
        return ""

    # Normalize URL
    if not url.startswith("http"):
        url = "https://" + url
    base = url.rstrip("/")

    for path in CONTACT_PATHS:
        try:
            resp = _session.get(base + path, timeout=TIMEOUT, allow_redirects=True)
            if resp.status_code == 200:
                emails = _extract_emails(resp.text)
                if emails:
                    return emails[0]
        except Exception:
            continue

    return ""


def enrich_leads_with_emails(leads: list, log=None) -> list:
    """
    For leads that have a website but no email, try to find their email.
    Returns the same list with emails filled in where found.
    Non-destructive — leads without websites are returned unchanged.
    """
    to_enrich = [l for l in leads if l.get("website") and not l.get("email")]

    if not to_enrich:
        return leads

    if log:
        log(f"Email aranıyor: {len(to_enrich)} websiteli lead...")

    found_count = 0
    for lead in to_enrich:
        email = find_email_on_website(lead["website"])
        if email:
            lead["email"] = email
            found_count += 1
            if log:
                log(f"  ✓ {lead.get('name', '')[:30]} → {email}")

    if log:
        log(f"Email bulundu: {found_count}/{len(to_enrich)}")

    return leads
