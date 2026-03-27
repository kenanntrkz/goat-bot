"""Instantly.ai email service — creates campaigns, adds leads, tracks analytics."""

import os
import requests

API_BASE = "https://api.instantly.ai/api/v2"


def get_api_key():
    """Get Instantly API key from env or config."""
    return os.getenv("INSTANTLY_API_KEY", "")


def _headers(api_key=None):
    key = api_key or get_api_key()
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def test_connection(api_key=None):
    """Test if the API key works."""
    try:
        resp = requests.get(
            f"{API_BASE}/campaigns",
            headers=_headers(api_key),
            params={"limit": 1},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def create_campaign(name, api_key=None):
    """Create a new campaign. Returns campaign ID or None."""
    try:
        resp = requests.post(
            f"{API_BASE}/campaigns",
            headers=_headers(api_key),
            json={"name": name},
            timeout=15,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            return data.get("id")
        return None
    except Exception:
        return None


def add_leads_to_campaign(campaign_id, leads, api_key=None):
    """Add leads to a campaign. leads = list of dicts with email, first_name, company_name, etc."""
    try:
        resp = requests.post(
            f"{API_BASE}/leads",
            headers=_headers(api_key),
            json={
                "campaign_id": campaign_id,
                "leads": leads,
            },
            timeout=30,
        )
        return resp.status_code in (200, 201)
    except Exception:
        return False


def activate_campaign(campaign_id, api_key=None):
    """Activate (launch) a campaign."""
    try:
        resp = requests.post(
            f"{API_BASE}/campaigns/{campaign_id}/activate",
            headers=_headers(api_key),
            timeout=15,
        )
        return resp.status_code in (200, 201)
    except Exception:
        return False


def get_campaign_analytics(campaign_id, api_key=None):
    """Get campaign analytics."""
    try:
        resp = requests.get(
            f"{API_BASE}/campaigns/{campaign_id}/analytics",
            headers=_headers(api_key),
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def list_campaigns(api_key=None):
    """List all campaigns."""
    try:
        resp = requests.get(
            f"{API_BASE}/campaigns",
            headers=_headers(api_key),
            params={"limit": 20},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception:
        return []
