"""
industry_resolver.py — Google Places API (New/V2) integration
for detecting industry/category of subscription providers.

Uses Places API V2 (searchText endpoint) to query a provider name
and map the returned 'types' array to subscription categories.
Results are cached in a local file to avoid redundant API calls.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("industry_resolver")

# ── Google Place types -> our categories ────────────────────

TYPE_TO_CATEGORY = {
    # Cloud / Infrastructure
    "cloud_computing": "cloud",
    "data_center": "cloud",
    "data_storage": "cloud",
    "hosting": "cloud",
    "internet_service_provider": "cloud",
    "computer_technical_support": "cloud",
    # Software / Dev Tools
    "software_company": "dev_tools",
    "developer": "dev_tools",
    "computer_software": "dev_tools",
    "technology": "dev_tools",
    "information_technology": "dev_tools",
    "electronics": "dev_tools",
    # Streaming / Media
    "movie_streaming": "streaming",
    "movie_rental": "streaming",
    "tv_network": "streaming",
    "video_streaming": "streaming",
    "broadcasting": "streaming",
    "media_company": "streaming",
    "entertainment": "streaming",
    "film_production": "streaming",
    # Music
    "music_producer": "music",
    "record_label": "music",
    "radio_station": "music",
    "music": "music",
    "music_instrument_store": "music_tools",
    "recording_studio": "music_tools",
    "audio_visual_equipment": "music_tools",
    # AI
    "artificial_intelligence": "ai",
    "research_institute": "ai",
    "machine_learning": "ai",
    "research_organization": "ai",
    # Gaming
    "video_game": "gaming",
    "game_console": "gaming",
    "video_game_developer": "gaming",
    "gaming": "gaming",
    # Design
    "design": "design",
    "graphic_design": "design",
    "web_design": "design",
    # Productivity / Business
    "productivity": "productivity",
    "business": "productivity",
    "communication": "productivity",
    "collaboration": "productivity",
    # Security
    "security": "security",
    "cybersecurity": "security",
    "data_protection": "security",
    "privacy": "security",
    # Fitness / Health
    "fitness": "fitness",
    "gym": "fitness",
    "health": "fitness",
    "wellness": "fitness",
    # Education
    "education": "education",
    "online_learning": "education",
    "e_learning": "education",
    # News / Publishing
    "news": "news",
    "publishing": "news",
    "newspaper": "news",
    "journalism": "news",
    # Other
    "hosting": "hosting",
    "domain_registration": "hosting",
    "web_hosting": "hosting",
    "payment_processor": "payment_processor",
    "financial": "payment_processor",
    "bank": "payment_processor",
}

DEFAULT_CATEGORY = "other"

# ── Cache ───────────────────────────────────────────────────

CACHE_FILE = Path(__file__).parent / ".industry_cache.json"
CACHE_TTL_DAYS = 30


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


# ── API Call ────────────────────────────────────────────────

def resolve_industry(provider_name: str) -> str:
    """
    Resolve the industry/category for a provider name using Google Places API V2.
    Results are cached to avoid redundant API calls.

    Returns one of: cloud, dev_tools, streaming, music, music_tools, ai,
                    gaming, design, productivity, security, fitness,
                    education, news, hosting, payment_processor, other
    """
    if not provider_name or provider_name == "Unknown Service":
        return DEFAULT_CATEGORY

    cache = _load_cache()
    key = provider_name.lower().strip()

    # Check cache
    if key in cache:
        entry = cache[key]
        cached_time = datetime.fromisoformat(entry["cached_at"])
        if datetime.now() - cached_time < timedelta(days=CACHE_TTL_DAYS):
            return entry["category"]

    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_PLACES_API_KEY not set — skipping Places API lookup")
        return DEFAULT_CATEGORY

    try:
        import requests
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.types,places.displayName",
            "Content-Type": "application/json",
        }
        body = {
            "textQuery": f"{provider_name} subscription service",
            "maxResultCount": 3,
        }
        resp = requests.post(url, headers=headers, json=body, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"Places API error {resp.status_code} for {provider_name}: {resp.text[:200]}")
            cache[key] = {"category": DEFAULT_CATEGORY, "cached_at": datetime.now().isoformat()}
            _save_cache(cache)
            return DEFAULT_CATEGORY

        data = resp.json()
        places = data.get("places", [])
        if not places:
            cache[key] = {"category": DEFAULT_CATEGORY, "cached_at": datetime.now().isoformat()}
            _save_cache(cache)
            return DEFAULT_CATEGORY

        # Collect all types from returned places
        all_types = []
        for place in places:
            all_types.extend(place.get("types", []))

        # Match to our categories
        for t in all_types:
            if t.lower() in TYPE_TO_CATEGORY:
                category = TYPE_TO_CATEGORY[t.lower()]
                cache[key] = {"category": category, "cached_at": datetime.now().isoformat()}
                _save_cache(cache)
                return category

        # No match found
        cache[key] = {"category": DEFAULT_CATEGORY, "cached_at": datetime.now().isoformat()}
        _save_cache(cache)
        return DEFAULT_CATEGORY

    except ImportError:
        logger.warning("requests not installed — skipping Places API")
        return DEFAULT_CATEGORY
    except Exception as e:
        logger.error(f"Places API error for {provider_name}: {e}")
        return DEFAULT_CATEGORY


if __name__ == "__main__":
    # Quick test
    test_names = ["Netflix", "GitHub", "Spotify", "DigitalOcean", "OpenAI", "Adobe"]
    for name in test_names:
        cat = resolve_industry(name)
        print(f"{name:20s} -> {cat}")
