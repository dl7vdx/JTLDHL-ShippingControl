# JTL ShippingTracker – Projektübergabe

## Ziel
Custom Python/Flask Tool das JTL-Wawi (MSSQL) mit der DHL Tracking API verbindet und ein Web-Dashboard bereitstellt. Ersetzt JTL Track & Trace + JTL REST API (zu teuer).

## Was das Tool macht
- Liest DHL-Sendungsnummern aus JTL-Wawi (MSSQL)
- Pollt DHL Tracking API für Statusupdates
- Erkennt Probleme (Zustellfehler, Packstation, kein Update >48h)
- Zeigt Web-Dashboard (Flask, port 5000)
- Erlaubt manuellen PDF-Upload von Liefernachweisen
- Sendet Kunden-E-Mails via 3 Templates

## Projektstruktur
```
C:\Users\admin\Downloads\jtl_dhl_tracker\jtl-tracker\
├── config.py              ← Alle Einstellungen
├── requirements.txt
├── start.bat              ← Startet Flask + Scheduler
├── app/
│   ├── web.py             ← Flask App
│   ├── scheduler.py       ← Polling Loop (alle 2h)
│   ├── dhl_tracker.py     ← DHL API Client
│   ├── wawi_reader.py     ← MSSQL Reader
│   ├── mailer.py          ← SMTP + Templates
│   ├── db.py              ← SQLite Layer
│   └── templates/         ← HTML Templates
├── data/
│   ├── tracker.db         ← SQLite Datenbank
│   └── tracker.log
└── uploads/               ← PDF Liefernachweise
```

## Wichtige Konfiguration (config.py)

### DHL API
```python
DHL_API_KEY = "xwjqiS3MuWfgZH1Tf38i6LPQGop5Lcr8"
DHL_API_URL = "https://api-eu.dhl.com/track/shipments"
```
**WICHTIG:** Authentifizierung läuft NUR über den Header `DHL-API-Key`. 
Kein OAuth2, kein Basic Auth, kein GKP-Benutzer nötig!
Verwendete API: **Shipment Tracking Unified** (nicht Parcel DE Tracking!)

### JTL-Wawi (MSSQL)
```python
WAWI_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.178.73\\jtlwawi;"
    "DATABASE=eazybusiness;"
    "UID=sa;PWD=...;TrustServerCertificate=yes;"
)
```
- Server über VPN erreichbar
- Datenbank: `eazybusiness` (nicht Mandant_1/2/3 – die sind leer!)
- Relevante Tabellen:
  - `dbo.tVersand` – Sendungsnummern (cIdentCode)
  - `dbo.tLieferschein` – Lieferscheine
  - `Verkauf.tAuftrag` – Aufträge
  - `Verkauf.tAuftragAdresse` – Adressen (nTyp=2 = Lieferadresse)

## DHL API – Authentifizierung (ENDGÜLTIGE LÖSUNG)
```python
headers = {
    "DHL-API-Key": DHL_API_KEY,
    "Accept": "application/json",
}
params = {"trackingNumber": tracking_number}
resp = requests.get(DHL_API_URL, headers=headers, params=params)
```
Das war nach wochenlangem Debugging die Lösung – ein einziger Header.
Vorher wurden OAuth2, Basic Auth, GKP-Benutzer etc. versucht – alles falsch.

## DHL Rate Limit
- Aktuell: **250 requests/Tag** (Shipment Tracking Unified, Production Europe)
- Problem: Bei 155 Sendungen wird das Limit schnell erreicht
- **Rate Limit Upgrade wurde bereits beantragt** im Developer Portal
- Bis dahin: Nur DHL-Sendungen laden (Filter in wawi_reader.py)

## Offene Aufgaben / Bekannte Probleme

### 1. Unknown-Einträge im Dashboard (PRIORITÄT)
Im Dashboard werden noch Aufträge mit Status "unknown" angezeigt.
Diese stammen aus der Zeit vor dem DHL-Filter und sind in der SQLite DB gespeichert.
**Lösung:** Alte Einträge mit nicht-DHL-Sendungsnummern aus `tracker.db` löschen.
```sql
-- In tracker.db ausführen:
DELETE FROM shipments 
WHERE tracking_number NOT LIKE '00340%' 
AND tracking_number NOT LIKE '00345%' 
AND tracking_number NOT LIKE 'JD%';
```

### 2. DHL-Filter in wawi_reader.py
Bereits implementiert – nur Sendungsnummern mit Präfix `00340`, `00345`, `JD` werden geladen.
Prüfen ob das alle DHL-Formate abdeckt.

### 3. Rate Limit Handling
Beim Polling werden viele "Rate Limit erreicht" Warnungen geloggt.
Verbesserung: Bereits zugestellte Sendungen (`status = 'delivered'`) beim Polling überspringen
um API-Anfragen zu sparen.

### 4. Windows Task Scheduler
Scheduler noch nicht als automatischer Windows-Task eingerichtet.
Aktuell muss `scheduler.py` manuell gestartet werden.

### 5. SMTP noch nicht konfiguriert
E-Mail-Versand ist implementiert aber SMTP-Zugangsdaten in config.py noch leer.

## Technischer Stack
- Python 3.x
- Flask (Web-Dashboard)
- pyodbc (MSSQL-Verbindung)
- requests (DHL API)
- SQLite (lokale Datenbank)
- Windows 10/11, läuft auf lokalem Rechner
- VPN für MSSQL-Zugriff erforderlich

## Was bereits funktioniert
- ✅ MSSQL-Verbindung zu JTL-Wawi (155 Sendungen geladen)
- ✅ DHL Tracking API (Shipment Tracking Unified mit API Key)
- ✅ Web-Dashboard (Flask)
- ✅ PDF-Upload und Download
- ✅ E-Mail-Templates (3 Typen)
- ✅ SQLite Datenbank
- ✅ DHL-Filter in wawi_reader.py
- ⏳ Rate Limit Upgrade beantragt
- ❌ Unknown-Einträge noch im Dashboard
- ❌ Windows Task Scheduler nicht eingerichtet
- ❌ SMTP nicht konfiguriert
