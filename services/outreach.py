"""Turkoz Outreach service — campaigns and leads via outreach.kenanturkoz.cloud"""

import os
import requests


def _base_url():
    return os.getenv("OUTREACH_URL", "https://outreach.kenanturkoz.cloud")


def _headers():
    return {
        "Content-Type": "application/json",
        "x-internal-key": os.getenv("OUTREACH_API_KEY", ""),
    }


def get_api_key():
    return os.getenv("OUTREACH_API_KEY", "")


def test_connection(api_key=None):
    """Test connection by calling GET /api/campaigns."""
    try:
        resp = requests.get(
            f"{_base_url()}/api/campaigns",
            headers=_headers(),
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def create_campaign(name, subject_template="", body_template="", api_key=None):
    """Create a campaign. Returns campaign ID or None."""
    try:
        resp = requests.post(
            f"{_base_url()}/api/campaigns",
            headers=_headers(),
            json={
                "name": name,
                "subject_template": subject_template,
                "body_template": body_template,
            },
            timeout=15,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            return data.get("id")
        return None
    except Exception:
        return None


def import_leads(leads, api_key=None):
    """
    Import leads into outreach system. Returns imported count or None.
    leads = list of dicts with keys: email, first_name, company, sector, phone, website, source
    """
    try:
        resp = requests.post(
            f"{_base_url()}/api/leads/import",
            headers=_headers(),
            json=leads,
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("imported", 0)
        return None
    except Exception:
        return None


def list_campaigns(api_key=None):
    """List all campaigns."""
    try:
        resp = requests.get(
            f"{_base_url()}/api/campaigns",
            headers=_headers(),
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception:
        return []
