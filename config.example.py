# config.example.py – Vorlage für config.py
# Kopiere diese Datei als config.py und trage deine Zugangsdaten ein

# ── DHL Tracking API ─────────────────────────────────────────────────────────
DHL_API_KEY = "DEIN_DHL_API_KEY"
DHL_API_URL = "https://api-eu.dhl.com/track/shipments"

# ── JTL-Wawi (MSSQL) ─────────────────────────────────────────────────────────
WAWI_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=IP_ODER_HOSTNAME\\jtlwawi;"
    "DATABASE=eazybusiness;"
    "UID=sa;PWD=DEIN_PASSWORT;TrustServerCertificate=yes;"
)

# ── Flask / Dashboard ─────────────────────────────────────────────────────────
SECRET_KEY        = "aendern-vor-produktiveinsatz"
DASHBOARD_USER    = "admin"
DASHBOARD_PASSWORD = "aendern"

# ── Dateipfade ────────────────────────────────────────────────────────────────
DB_PATH      = "data/tracker.db"
UPLOAD_FOLDER = "uploads"

# ── SMTP (E-Mail-Versand) ─────────────────────────────────────────────────────
SMTP_HOST     = "smtp.dein-anbieter.de"
SMTP_PORT     = 587
SMTP_USER     = "deine@email.de"
SMTP_PASSWORD = "DEIN_SMTP_PASSWORT"
SMTP_FROM     = "versand@dein-shop.de"
