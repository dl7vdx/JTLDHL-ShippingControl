"""
db.py – SQLite Datenbankschicht
Speichert Sendungen, Status-Events und Kundeninformationen
"""

import sqlite3
import os
from config import DB_PATH


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Erstellt alle Tabellen beim ersten Start."""
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS shipments (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_number  TEXT UNIQUE NOT NULL,
            order_number     TEXT,
            customer_name    TEXT,
            customer_email   TEXT,
            recipient_city   TEXT,
            created_at       TEXT DEFAULT (datetime('now','localtime')),
            last_checked     TEXT,
            current_status   TEXT DEFAULT 'unknown',
            is_problematic   INTEGER DEFAULT 0,
            is_delivered     INTEGER DEFAULT 0,
            is_packstation   INTEGER DEFAULT 0,
            is_filiale       INTEGER DEFAULT 0,
            pdf_filename     TEXT,
            notes            TEXT
        );



        CREATE TABLE IF NOT EXISTS tracking_events (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_number  TEXT NOT NULL,
            event_time       TEXT,
            location         TEXT,
            status_code      TEXT,
            description      TEXT,
            recorded_at      TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (tracking_number) REFERENCES shipments(tracking_number)
        );

        CREATE TABLE IF NOT EXISTS mail_log (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_number  TEXT,
            recipient        TEXT,
            subject          TEXT,
            sent_at          TEXT DEFAULT (datetime('now','localtime')),
            status           TEXT
        );
        """)
        # Migration: Spalte für bestehende DBs nachrüsten
        cols = {row[1] for row in conn.execute("PRAGMA table_info(shipments)")}
        if "is_filiale" not in cols:
            conn.execute("ALTER TABLE shipments ADD COLUMN is_filiale INTEGER DEFAULT 0")


# --- Sendungen ---

def upsert_shipment(tracking_number, order_number, customer_name, customer_email, recipient_city=""):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO shipments (tracking_number, order_number, customer_name, customer_email, recipient_city)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(tracking_number) DO UPDATE SET
                order_number   = excluded.order_number,
                customer_name  = excluded.customer_name,
                customer_email = excluded.customer_email
        """, (tracking_number, order_number, customer_name, customer_email, recipient_city))


def update_shipment_status(tracking_number, status, is_problematic, is_delivered, is_packstation, is_filiale=0):
    with get_conn() as conn:
        conn.execute("""
            UPDATE shipments SET
                current_status  = ?,
                is_problematic  = ?,
                is_delivered    = ?,
                is_packstation  = ?,
                is_filiale      = ?,
                last_checked    = datetime('now','localtime')
            WHERE tracking_number = ?
        """, (status, is_problematic, is_delivered, is_packstation, is_filiale, tracking_number))


def set_pdf_filename(tracking_number, filename):
    with get_conn() as conn:
        conn.execute("UPDATE shipments SET pdf_filename = ? WHERE tracking_number = ?",
                     (filename, tracking_number))


ALL_STATUSES = ["problematic", "packstation", "filiale", "transit", "pre-transit", "unknown", "delivered"]
DEFAULT_STATUSES = ["problematic", "packstation", "filiale", "transit", "pre-transit"]

STATUS_SQL = {
    "problematic": "is_problematic = 1",
    "packstation":  "is_packstation = 1 AND is_delivered = 0",
    "filiale":      "is_filiale = 1 AND is_delivered = 0",
    "delivered":    "is_delivered = 1",
    "transit":      "current_status = 'transit'",
    "pre-transit":  "current_status = 'pre-transit'",
    "unknown":      "current_status = 'unknown'",
}

def get_all_shipments(show_statuses=None, period=None, search=None):
    conditions = []
    params = []

    # Multi-Status-Filter: OR-Verknüpfung der gewählten Statii
    if show_statuses and set(show_statuses) != set(ALL_STATUSES):
        status_parts = [STATUS_SQL[s] for s in show_statuses if s in STATUS_SQL]
        if status_parts:
            conditions.append("(" + " OR ".join(status_parts) + ")")

    # Zeitraum-Filter
    period_conditions = {
        "today":     "DATE(created_at) = DATE('now','localtime')",
        "yesterday": "DATE(created_at) = DATE('now','localtime','-1 day')",
        "this_week": "DATE(created_at) >= DATE('now','localtime','weekday 0','-7 days')",
        "last_7":    "DATE(created_at) >= DATE('now','localtime','-7 days')",
        "last_30":   "DATE(created_at) >= DATE('now','localtime','-30 days')",
    }
    if period in period_conditions:
        conditions.append(period_conditions[period])

    # Suche
    if search:
        conditions.append("(tracking_number LIKE ? OR order_number LIKE ? OR customer_name LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term, term])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    with get_conn() as conn:
        return conn.execute(
            f"SELECT * FROM shipments {where} ORDER BY created_at DESC", params
        ).fetchall()


def get_shipment(tracking_number):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM shipments WHERE tracking_number = ?", (tracking_number,)
        ).fetchone()


def get_active_tracking_numbers():
    """
    Nicht zugestellte Sendungen, die laut Status-Intervall jetzt abgefragt werden sollen.
    Intervalle (Stunden): Probleme/Packstation/Filiale=2, Transit=8, Unbekannt=12, Pre-Transit=24
    Reihenfolge: zeitkritische Statii zuerst, dann älteste Prüfung.
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT tracking_number FROM shipments
            WHERE is_delivered = 0
              AND (
                last_checked IS NULL
                OR CASE
                    WHEN is_problematic = 1                  THEN last_checked < datetime('now','localtime','-2 hours')
                    WHEN is_packstation = 1                  THEN last_checked < datetime('now','localtime','-2 hours')
                    WHEN is_filiale = 1                      THEN last_checked < datetime('now','localtime','-2 hours')
                    WHEN current_status = 'transit'          THEN last_checked < datetime('now','localtime','-8 hours')
                    WHEN current_status = 'unknown'          THEN last_checked < datetime('now','localtime','-12 hours')
                    WHEN current_status = 'pre-transit'      THEN last_checked < datetime('now','localtime','-24 hours')
                    ELSE last_checked < datetime('now','localtime','-12 hours')
                END
              )
            ORDER BY
              CASE
                WHEN is_problematic = 1             THEN 1
                WHEN is_packstation = 1             THEN 2
                WHEN is_filiale = 1                 THEN 3
                WHEN current_status = 'transit'     THEN 4
                WHEN current_status = 'unknown'     THEN 5
                WHEN current_status = 'pre-transit' THEN 6
                ELSE 7
              END,
              last_checked ASC
        """).fetchall()
    return [r["tracking_number"] for r in rows]


# --- Events ---

def insert_event(tracking_number, event_time, location, status_code, description):
    with get_conn() as conn:
        # Duplikate vermeiden
        exists = conn.execute("""
            SELECT 1 FROM tracking_events
            WHERE tracking_number = ? AND event_time = ? AND status_code = ?
        """, (tracking_number, event_time, status_code)).fetchone()
        if not exists:
            conn.execute("""
                INSERT INTO tracking_events (tracking_number, event_time, location, status_code, description)
                VALUES (?, ?, ?, ?, ?)
            """, (tracking_number, event_time, location, status_code, description))


def get_transit_since(tracking_number):
    """Erster Transit-Event – Startpunkt für die Unterwegs-Ampel."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT event_time FROM tracking_events
            WHERE tracking_number = ? AND status_code = 'transit'
            ORDER BY event_time ASC
            LIMIT 1
        """, (tracking_number,)).fetchone()
    return row["event_time"] if row else None


def get_last_event_time(tracking_number):
    """Zeitpunkt des letzten bekannten Events – für Stillstand-Erkennung."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT event_time FROM tracking_events
            WHERE tracking_number = ?
            ORDER BY event_time DESC
            LIMIT 1
        """, (tracking_number,)).fetchone()
    return row["event_time"] if row else None


def get_station_location(tracking_number):
    """Adresse der Packstation oder Filiale aus dem relevanten Event."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT location FROM tracking_events
            WHERE tracking_number = ?
              AND location IS NOT NULL AND location != ''
              AND (description LIKE '%Packstation%'
                   OR description LIKE '%Filiale%'
                   OR description LIKE '%Postfiliale%'
                   OR description LIKE '%Paketshop%'
                   OR description LIKE '%Abholung%')
            ORDER BY event_time DESC
            LIMIT 1
        """, (tracking_number,)).fetchone()
    return row["location"] if row else None


def get_packstation_arrival(tracking_number):
    """Gibt den Zeitpunkt zurück, ab dem die Sendung in der Packstation liegt."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT event_time FROM tracking_events
            WHERE tracking_number = ?
              AND (description LIKE '%ready for collection from PACKSTATION%'
                   OR description LIKE '%zur Abholung in der Packstation%')
            ORDER BY event_time ASC
            LIMIT 1
        """, (tracking_number,)).fetchone()
    return row["event_time"] if row else None


def get_events(tracking_number):
    with get_conn() as conn:
        return conn.execute("""
            SELECT * FROM tracking_events
            WHERE tracking_number = ?
            ORDER BY event_time DESC
        """, (tracking_number,)).fetchall()


# --- Mail-Log ---

def log_mail(tracking_number, recipient, subject, status):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO mail_log (tracking_number, recipient, subject, status)
            VALUES (?, ?, ?, ?)
        """, (tracking_number, recipient, subject, status))


def get_mail_log(tracking_number):
    with get_conn() as conn:
        return conn.execute("""
            SELECT * FROM mail_log WHERE tracking_number = ? ORDER BY sent_at DESC
        """, (tracking_number,)).fetchall()
