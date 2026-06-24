"""
scheduler.py – Haupt-Polling-Loop
Wird per Windows Task Scheduler alle 2h ausgeführt (oder läuft dauerhaft)
"""

import logging
import sys
import os

# Projekt-Root zum Pfad hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import (
    init_db, upsert_shipment, update_shipment_status,
    insert_event, get_active_tracking_numbers
)
from app.dhl_tracker import fetch_tracking, parse_tracking_response
from app.wawi_reader import fetch_recent_shipments

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/tracker.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def sync_from_wawi():
    """Neue Sendungen aus JTL-Wawi in die lokale DB übernehmen."""
    logger.info("Synchronisiere Sendungen aus JTL-Wawi...")
    shipments = fetch_recent_shipments(days_back=30)
    for s in shipments:
        if s.get("tracking_number"):
            upsert_shipment(
                tracking_number=s["tracking_number"],
                order_number=s.get("order_number", ""),
                customer_name=s.get("customer_name", ""),
                customer_email=s.get("customer_email", ""),
                recipient_city=s.get("recipient_city", ""),
            )
    logger.info(f"Wawi-Sync abgeschlossen: {len(shipments)} Sendungen")


def poll_dhl():
    """DHL-Status für alle aktiven Sendungen abrufen."""
    tracking_numbers = get_active_tracking_numbers()
    logger.info(f"Starte DHL-Polling für {len(tracking_numbers)} aktive Sendungen...")

    updated = 0
    problematic = 0

    for tn in tracking_numbers:
        raw = fetch_tracking(tn)
        if raw == "RATE_LIMIT":
            logger.warning("Rate Limit erreicht – Polling abgebrochen, Rest beim nächsten Lauf")
            break
        if raw is None:
            logger.warning(f"Kein DHL-Response für {tn}")
            continue

        parsed = parse_tracking_response(raw)

        # Status in DB schreiben
        update_shipment_status(
            tracking_number=tn,
            status=parsed["status"],
            is_problematic=int(parsed["is_problematic"]),
            is_delivered=int(parsed["is_delivered"]),
            is_packstation=int(parsed["is_packstation"]),
            is_filiale=int(parsed["is_filiale"]),
        )

        # Events speichern
        for ev in parsed["events"]:
            insert_event(
                tracking_number=tn,
                event_time=ev["event_time"],
                location=ev["location"],
                status_code=ev["status_code"],
                description=ev["description"],
            )

        updated += 1
        if parsed["is_problematic"]:
            problematic += 1
            logger.warning(
                f"⚠️  PROBLEM: {tn} – Status: {parsed['status']} | {parsed['latest_description']}"
            )
        elif parsed["is_packstation"]:
            logger.info(f"📦 Packstation: {tn} – {parsed['latest_location']}")
        elif parsed["is_delivered"]:
            logger.info(f"✅ Zugestellt: {tn}")

    logger.info(f"Polling abgeschlossen: {updated} aktualisiert, {problematic} problematisch")


def run():
    """Einmaliger Durchlauf: Wawi-Sync + DHL-Polling."""
    logger.info("=" * 50)
    logger.info("JTL ShippingTracker – Polling-Lauf gestartet")
    logger.info("=" * 50)

    init_db()
    sync_from_wawi()
    poll_dhl()

    logger.info("Polling-Lauf beendet")


if __name__ == "__main__":
    run()
