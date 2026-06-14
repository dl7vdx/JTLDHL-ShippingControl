"""
wawi_reader.py – Liest Sendungsnummern + Auftragsdaten aus JTL-Wawi (MSSQL)
Verbindung läuft über VPN, daher Timeout-Behandlung wichtig
"""
import logging
from config import WAWI_CONNECTION_STRING

logger = logging.getLogger(__name__)

# DHL Sendungsnummern-Präfixe
DHL_PREFIXES = (
    '00340',   # DHL Paket national
    '00345',   # DHL Paket international
    'JD',      # DHL Express
    '1Z',      # DHL (UPS-Format, selten)
)

def get_wawi_connection():
    try:
        import pyodbc
        conn = pyodbc.connect(WAWI_CONNECTION_STRING, timeout=10)
        return conn
    except Exception as e:
        logger.error(f"Wawi-Verbindung fehlgeschlagen: {e}")
        return None

def fetch_recent_shipments(days_back=30):
    """
    Holt alle DHL-Sendungen der letzten N Tage aus JTL-Wawi.
    Filtert nur DHL-Sendungsnummern (00340..., 00345..., JD...).
    """
    conn = get_wawi_connection()
    if not conn:
        logger.warning("Wawi nicht erreichbar – überspringe Synchronisation")
        return []

    query = """
        SELECT DISTINCT
            a.cAuftragsNr                                          AS order_number,
            aa.cVorname + ' ' + aa.cName                           AS customer_name,
            aa.cMail                                               AS customer_email,
            v.cIdentCode                                           AS tracking_number,
            aa.cOrt                                                AS recipient_city,
            v.dErstellt                                            AS dErstellt
        FROM dbo.tVersand v
        INNER JOIN dbo.tLieferschein ls          ON v.kLieferschein  = ls.kLieferschein
        INNER JOIN Verkauf.tAuftrag a            ON ls.kBestellung   = a.kAuftrag
        LEFT  JOIN Verkauf.tAuftragAdresse aa    ON a.kAuftrag       = aa.kAuftrag
                                                AND aa.nTyp          = 1
        WHERE v.cIdentCode IS NOT NULL
          AND v.cIdentCode <> ''
          AND v.dErstellt > DATEADD(day, ?, GETDATE())
          AND (
              v.cIdentCode LIKE '00340%'
           OR v.cIdentCode LIKE '00345%'
           OR v.cIdentCode LIKE 'JD%'
          )
        ORDER BY v.dErstellt DESC
    """

    try:
        cursor = conn.cursor()
        cursor.execute(query, (-abs(days_back),))
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"Wawi: {len(rows)} DHL-Sendungen geladen")
        return rows
    except Exception as e:
        logger.error(f"Wawi SQL-Fehler: {e}")
        return []
    finally:
        conn.close()

def test_connection():
    """Verbindungstest – nützlich für Setup-Diagnose."""
    conn = get_wawi_connection()
    if conn:
        conn.close()
        return True, "Verbindung erfolgreich"
    return False, "Verbindung fehlgeschlagen – VPN aktiv? Zugangsdaten prüfen"