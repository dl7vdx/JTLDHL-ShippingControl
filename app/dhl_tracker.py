"""
dhl_tracker.py – DHL Shipment Tracking Unified API
Authentifizierung via API Key Header (DHL-API-Key)
"""

import requests
import logging
from datetime import datetime, timezone
from config import DHL_API_KEY, DHL_API_URL

logger = logging.getLogger(__name__)

PROBLEM_STATUSES = {
    "delivery-failure",
    "delivery-refused",
    "lost",
    "unknown",
}

PACKSTATION_KEYWORDS = [
    "packstation",
    "paketstation",
    "paketbox",
    "paket station",
]

NO_UPDATE_HOURS = 48


def fetch_tracking(tracking_number: str) -> dict | None:
    """
    Ruft den aktuellen Status einer Sendung von der DHL Unified Tracking API ab.
    Authentifizierung via DHL-API-Key Header.
    """
    headers = {
        "DHL-API-Key": DHL_API_KEY,
        "Accept": "application/json",
    }
    params = {
        "trackingNumber": tracking_number,
        "language": "de",
    }

    try:
        resp = requests.get(DHL_API_URL, headers=headers, params=params, timeout=15)

        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            logger.error(f"DHL API 401: API Key ungültig")
            return None
        elif resp.status_code == 404:
            logger.warning(f"Sendung {tracking_number} nicht gefunden")
            return None
        elif resp.status_code == 429:
            logger.warning("DHL API Rate Limit erreicht")
            return "RATE_LIMIT"
        else:
            logger.error(f"DHL API Fehler {resp.status_code}: {resp.text[:200]}")
            return None

    except requests.exceptions.Timeout:
        logger.error(f"DHL API Timeout für {tracking_number}")
        return None
    except Exception as e:
        logger.error(f"DHL API Ausnahme: {e}")
        return None


def parse_tracking_response(data: dict) -> dict:
    """
    Extrahiert relevante Informationen aus der DHL API-Antwort.
    """
    result = {
        "status": "unknown",
        "is_delivered": False,
        "is_problematic": False,
        "is_packstation": False,
        "events": [],
        "latest_location": "",
        "latest_description": "",
    }

    shipments = data.get("shipments", [])
    if not shipments:
        result["is_problematic"] = True
        return result

    shipment = shipments[0]
    status_obj = shipment.get("status", {})

    status_code = status_obj.get("statusCode", "unknown").lower()
    result["status"] = status_code
    result["latest_description"] = status_obj.get("description", "")
    result["latest_location"] = _extract_location(status_obj.get("location", {}))

    if status_code == "delivered":
        result["is_delivered"] = True

    loc_lower  = result["latest_location"].lower()
    desc_lower = result["latest_description"].lower()
    for kw in PACKSTATION_KEYWORDS:
        if kw in loc_lower or kw in desc_lower:
            result["is_packstation"] = True
            break

    if status_code in PROBLEM_STATUSES:
        result["is_problematic"] = True

    events_raw = shipment.get("events", [])
    for ev in events_raw:
        result["events"].append({
            "event_time":  ev.get("timestamp", ""),
            "location":    _extract_location(ev.get("location", {})),
            "status_code": ev.get("statusCode", ""),
            "description": ev.get("description", ""),
        })

    if not result["is_delivered"] and result["events"]:
        latest_ts = result["events"][0].get("event_time", "")
        if latest_ts:
            try:
                ts  = datetime.fromisoformat(latest_ts.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                hours_since = (now - ts).total_seconds() / 3600
                if hours_since > NO_UPDATE_HOURS:
                    result["is_problematic"] = True
                    result["status"] = f"no-update-{int(hours_since)}h"
            except Exception:
                pass

    return result


def _extract_location(loc: dict) -> str:
    if not loc:
        return ""
    parts = [
        loc.get("address", {}).get("addressLocality", ""),
        loc.get("address", {}).get("countryCode", ""),
    ]
    return ", ".join(p for p in parts if p)