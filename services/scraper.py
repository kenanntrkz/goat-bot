"""Apify scraper service — abstracts the Apify API for lead generation."""

import os
import time
import requests
from pathlib import Path

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")


def scrape_google_maps(query: str, location: str = "", max_results: int = 50, log=None) -> list:
    """Scrape Google Maps for businesses matching query + location.

    Returns list of lead dicts with: name, address, phone, website, email, etc.
    Falls back to empty list if Apify is unavailable.
    """
    if not APIFY_TOKEN:
        if log:
            log("No APIFY_TOKEN set — cannot scrape. Add it to .env")
        return []

    search_term = f"{query} {location}".strip() if location else query

    try:
        # Start Apify Google Maps Scraper run
        resp = requests.post(
            f"https://api.apify.com/v2/acts/compass~crawler-google-places/runs?token={APIFY_TOKEN}",
            json={
                "searchStringsArray": [search_term],
                "maxCrawledPlacesPerSearch": max_results,
                "language": "en",
                "deeperCityScrape": False,
            },
            timeout=30,
        )
        run_data = resp.json().get("data", {})
        run_id = run_data.get("id")

        if not run_id:
            if log:
                log(f"Apify failed to start: {resp.text[:200]}")
            return []

        if log:
            log(f"Apify run {run_id} started, polling for results...")

        # Poll for completion
        for i in range(60):
            time.sleep(10)
            sr = requests.get(
                f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}",
                timeout=15,
            )
            status = sr.json().get("data", {}).get("status")

            if log and i % 3 == 0:
                log(f"Poll {i+1}: status={status}")

            if status == "SUCCEEDED":
                dataset_id = sr.json().get("data", {}).get("defaultDatasetId")
                items_resp = requests.get(
                    f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}",
                    timeout=30,
                )
                raw_items = items_resp.json()

                # Normalize to our lead schema
                leads = []
                for item in raw_items:
                    lead = {
                        "name": item.get("title", ""),
                        "address": item.get("address", ""),
                        "phone": item.get("phone", ""),
                        "website": item.get("website", ""),
                        "email": _extract_email(item),
                        "rating": item.get("totalScore", 0),
                        "review_count": item.get("reviewsCount", 0),
                        "category": item.get("categoryName", ""),
                        "google_maps_url": item.get("url", ""),
                        "location": item.get("city", location),
                        "raw": item,
                    }
                    leads.append(lead)

                if log:
                    log(f"Got {len(leads)} results from Apify")
                return leads

            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                if log:
                    log(f"Apify run {status}")
                return []

        if log:
            log("Apify polling timeout (10 min)")
        return []

    except Exception as e:
        if log:
            log(f"Apify error: {e}")
        return []


def _extract_email(item: dict) -> str:
    """Try to extract email from Apify result."""
    # Some scrapers put email directly
    if item.get("email"):
        return item["email"]
    # Check contact info fields
    for field in ("emails", "contactEmail"):
        val = item.get(field)
        if val:
            if isinstance(val, list) and val:
                return val[0]
            if isinstance(val, str):
                return val
    return ""
