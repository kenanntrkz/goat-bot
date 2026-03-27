"""goat — Agency-in-a-Box Agent System"""

AGENTS = {
    "goat":     {"name": "goat",     "role": "Master orchestrator — runs the full pipeline",       "category": "master",      "icon": "🎯"},
    "scout":    {"name": "Scout",    "role": "Finds potential clients via Google Maps / Apify",     "category": "acquisition", "icon": "🔍"},
    "filter":   {"name": "Filter",   "role": "Scores and qualifies leads for outreach",            "category": "acquisition", "icon": "⚡"},
    "outreach": {"name": "Outreach", "role": "Email warmup + cold campaigns via Instantly.ai",     "category": "sales",       "icon": "📧"},
    "pitch":    {"name": "Pitch",    "role": "Generates service proposals and pitch decks",        "category": "sales",       "icon": "📋"},
    "mentor":   {"name": "Mentor",   "role": "Agency guide — answers any business question",       "category": "education",   "icon": "🎓"},
}

CATEGORIES = {
    "master":      {"name": "Orchestrator",  "color": "#00ff41"},
    "acquisition": {"name": "Acquisition",   "color": "#3b82f6"},
    "sales":       {"name": "Sales",         "color": "#ef4444"},
    "education":   {"name": "Education",     "color": "#8b5cf6"},
}
