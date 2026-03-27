"""Scout — Lead Finder Agent

Scrapes Google Maps via Apify to find potential clients
for the user's automation agency.
Supports multi-niche × multi-city with daily lead limit.
"""

import json
from datetime import date, datetime
from pathlib import Path

from agents.base import BaseAgent, DATA_DIR
from services.scraper import scrape_google_maps
from services.email_finder import enrich_leads_with_emails
from services.website_analyzer import enrich_leads_with_audits


class ScoutAgent(BaseAgent):
    agent_id = "scout"
    name = "Scout"
    role = "Finds potential clients via Google Maps / Apify"
    category = "acquisition"

    def run(self, query: str = "", location: str = "", limit: int = 0) -> dict:
        config = self.load_config()
        daily_limit = limit or config.get("daily_lead_limit", 30)

        # Build niche-city pairs
        if query:
            # Manual single-query run
            pairs = [(query, location or "")]
        else:
            industries = config.get("target_industries", []) or ["restaurants"]
            cities = config.get("target_cities", []) or [""]
            pairs = [(n, c) for n in industries for c in cities]

        # Rotate starting pair daily so each day hits a different niche/city first
        start = date.today().toordinal() % len(pairs)
        pairs = pairs[start:] + pairs[:start]

        all_leads = []
        seen_keys: set = set()

        for niche, city in pairs:
            remaining = daily_limit - len(all_leads)
            if remaining <= 0:
                break

            self.log(f"Aranıyor: '{niche}' / '{city}' (kalan: {remaining})...")
            batch = scrape_google_maps(
                query=niche,
                location=city,
                max_results=remaining * 2,  # fetch extra to account for dupes
                log=self.log,
            )

            for lead in batch:
                if len(all_leads) >= daily_limit:
                    break
                # Dedup by website URL, then by name+address
                key = lead.get("website") or (lead.get("name", "") + "|" + lead.get("address", ""))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                all_leads.append(lead)

        leads = all_leads

        # Enrich — emails + website audits in parallel
        leads = enrich_leads_with_emails(leads, log=self.log)
        leads = enrich_leads_with_audits(leads, log=self.log)

        if not leads:
            # Check for cached data
            cached = self._load_latest_raw()
            if cached:
                self.log(f"Using cached data: {len(cached)} leads")
                leads = cached
            else:
                return {
                    "status": "error",
                    "summary": "No leads found. Check your APIFY_TOKEN in .env",
                    "metrics": {},
                    "leads": [],
                    "recommendations": [
                        "Make sure APIFY_TOKEN is set in your .env file",
                        "Get a free token at https://console.apify.com/account/integrations",
                    ],
                }

        # Save raw results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        niches_label = query or "+".join(config.get("target_industries", []))[:30]
        slug = niches_label.lower().replace(" ", "_")[:30]
        filename = f"leads/raw/{timestamp}_{slug}.json"
        self.save_data(filename, {
            "query": niches_label,
            "location": location or ", ".join(config.get("target_cities", [])),
            "scraped_at": datetime.now().isoformat(),
            "count": len(leads),
            "leads": leads,
        })

        # Strip raw field for the report
        clean_leads = [{k: v for k, v in l.items() if k != "raw"} for l in leads]

        # Stats
        with_email = sum(1 for l in leads if l.get("email"))
        with_website = sum(1 for l in leads if l.get("website"))
        with_phone = sum(1 for l in leads if l.get("phone"))
        avg_rating = sum(l.get("rating", 0) for l in leads) / len(leads) if leads else 0
        niches_used = query or ", ".join(config.get("target_industries", []))
        cities_used = location or ", ".join(config.get("target_cities", []))

        results = {
            "status": "ok",
            "summary": f"{len(leads)} işletme bulundu — {niches_used} / {cities_used or 'tüm şehirler'}",
            "metrics": {
                "total_found": len(leads),
                "with_email": with_email,
                "with_website": with_website,
                "with_phone": with_phone,
                "avg_rating": round(avg_rating, 1),
                "niches": niches_used,
                "cities": cities_used,
                "daily_limit": daily_limit,
                "scraped_at": datetime.now().isoformat(),
            },
            "leads": clean_leads[:20],  # Top 20 in report
            "recommendations": [
                f"Found {with_email} leads with email — ready for outreach",
                f"{with_website} have websites — check for automation opportunities",
                "Run Filter agent next to score and rank these leads",
            ],
        }

        self.save_output("scout_leads_report.json", results)
        self.log(f"Done: {len(leads)} leads found, {with_email} with email")
        return results

    def _load_latest_raw(self) -> list:
        """Load the most recent raw scrape file."""
        raw_dir = DATA_DIR / "leads" / "raw"
        if not raw_dir.exists():
            return []
        files = sorted(raw_dir.glob("*.json"), reverse=True)
        if files:
            with open(files[0]) as f:
                data = json.load(f)
                return data.get("leads", [])
        return []
