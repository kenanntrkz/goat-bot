"""Website Analyzer — quick audit of a lead's website for proposal enrichment."""

import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

MAX_WORKERS = 15  # parallel site audits

TIMEOUT = 8

# Keywords by category
BOOKING_KEYWORDS = [
    "rezervasyon", "randevu", "booking", "appointment", "book now",
    "sipariş ver", "online order", "reserve", "rezerve et",
]
SOCIAL_DOMAINS = [
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "tiktok.com", "linkedin.com",
]
CHAT_SIGNALS = [
    "tawk.to", "intercom", "crisp.chat", "zendesk", "livechat",
    "freshchat", "drift.com", "hotjar",
]
ANALYTICS_SIGNALS = [
    "google-analytics.com", "gtag(", "googletagmanager.com",
    "fbq(", "_hjSettings",
]


def analyze_website(url: str) -> dict:
    """
    Fetch a lead's website and return a structured audit.
    Returns dict with: exists, issues (list), strengths (list), summary (str).
    Fast — single GET with 8s timeout, no JS rendering.
    """
    if not url:
        return {
            "exists": False,
            "issues": [],
            "strengths": [],
            "summary": "Web sitesi yok.",
        }

    if not url.startswith("http"):
        url = "https://" + url

    base = {
        "exists": True,
        "url": url,
        "issues": [],
        "strengths": [],
    }

    try:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; goat-audit/1.0)"})
        resp = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        html = resp.text
        html_lower = html.lower()

        # 1. SSL
        if resp.url.startswith("https"):
            base["strengths"].append("SSL sertifikası aktif (HTTPS)")
        else:
            base["issues"].append("SSL sertifikası yok — tarayıcılar 'Güvenli Değil' uyarısı gösteriyor")

        # 2. Mobile viewport
        if 'name="viewport"' in html_lower or "name='viewport'" in html_lower:
            base["strengths"].append("Mobil uyumlu (viewport etiketi var)")
        else:
            base["issues"].append("Mobil uyumlu değil — ziyaretçilerin %60–70'i mobil kullanıyor")

        # 3. Online booking / ordering
        if any(k in html_lower for k in BOOKING_KEYWORDS):
            base["strengths"].append("Online rezervasyon/sipariş sistemi mevcut")
        else:
            base["issues"].append("Online rezervasyon veya sipariş sistemi yok")

        # 4. Contact form
        if "<form" in html_lower:
            base["strengths"].append("İletişim formu var")
        else:
            base["issues"].append("İletişim formu yok — potansiyel müşteriler sizi bulamıyor")

        # 5. WhatsApp
        if "wa.me" in html or "whatsapp" in html_lower:
            base["strengths"].append("WhatsApp iletişim butonu var")
        else:
            base["issues"].append("WhatsApp butonu yok — hızlı iletişim fırsatı kaçıyor")

        # 6. Social media links
        if any(s in html_lower for s in SOCIAL_DOMAINS):
            base["strengths"].append("Sosyal medya hesapları bağlı")
        else:
            base["issues"].append("Sosyal medya linkleri yok")

        # 7. Analytics / tracking
        if any(s in html for s in ANALYTICS_SIGNALS):
            base["strengths"].append("Google Analytics / izleme kurulu")
        else:
            base["issues"].append("Google Analytics yok — ziyaretçi davranışı ölçülemiyor")

        # 8. Schema markup (SEO)
        if "schema.org" in html or '"@type"' in html:
            base["strengths"].append("Schema.org SEO markup var")
        else:
            base["issues"].append("SEO schema markup eksik — Google arama görünürlüğü düşük")

        # 9. Outdated copyright year
        years = re.findall(r"©\s*(\d{4})", html)
        if years:
            max_year = max(int(y) for y in years if 2000 <= int(y) <= 2035)
            current = datetime.now().year
            if max_year < current - 1:
                base["issues"].append(
                    f"Site görsel olarak eski (©{max_year}) — potansiyel müşterilere kötü izlenim bırakıyor"
                )

        # 10. Live chat
        if any(s in html_lower for s in CHAT_SIGNALS):
            base["strengths"].append("Canlı destek/sohbet widget mevcut")

    except requests.exceptions.SSLError:
        base["issues"].append("SSL sertifikası geçersiz veya süresi dolmuş")
    except requests.exceptions.ConnectionError:
        base["exists"] = False
        base["issues"].append("Web sitesine ulaşılamıyor (domain veya sunucu sorunu)")
    except requests.exceptions.Timeout:
        base["issues"].append("Web sitesi çok yavaş yükleniyor (8 saniyede yanıt vermedi)")
    except Exception:
        pass

    # Build summary
    n_issues = len(base["issues"])
    n_strengths = len(base["strengths"])
    if not base["exists"]:
        base["summary"] = "Web sitesine ulaşılamadı."
    elif n_issues == 0:
        base["summary"] = f"Web sitesi sağlıklı ({n_strengths} güçlü nokta tespit edildi)."
    else:
        base["summary"] = (
            f"Web sitesinde {n_issues} kritik eksiklik, {n_strengths} güçlü nokta tespit edildi."
        )

    return base


def enrich_leads_with_audits(leads: list, log=None) -> list:
    """
    Audit all lead websites in parallel and store results in lead["website_audit"].
    Only processes leads that have a website. Non-destructive for others.
    Same pattern as enrich_leads_with_emails — single pass, fast.
    """
    to_audit = [l for l in leads if l.get("website")]
    no_site = [l for l in leads if not l.get("website")]

    # Mark no-website leads immediately
    for lead in no_site:
        lead["website_audit"] = {"exists": False, "issues": [], "strengths": [],
                                  "summary": "Web sitesi yok."}

    if not to_audit:
        return leads

    if log:
        log(f"Web sitesi denetimi: {len(to_audit)} site paralel taranıyor...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_lead = {
            executor.submit(analyze_website, lead["website"]): lead
            for lead in to_audit
        }
        issues_total = 0
        for future in as_completed(future_to_lead):
            lead = future_to_lead[future]
            try:
                audit = future.result()
                lead["website_audit"] = audit
                issues_total += len(audit.get("issues", []))
            except Exception:
                lead["website_audit"] = {"exists": False, "issues": [], "strengths": [],
                                          "summary": "Analiz başarısız."}

    if log:
        log(f"Web denetimi tamamlandı: {len(to_audit)} sitede toplam {issues_total} eksiklik bulundu")

    return leads
