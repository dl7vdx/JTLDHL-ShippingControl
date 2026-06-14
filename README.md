# JTLDHL-ShippingControl

Web-Dashboard zur DHL-Sendungsverfolgung für JTL-Wawi Nutzer – ohne JTL Track & Trace und ohne JTL REST-API.

Das Tool liest Sendungsnummern direkt aus der JTL-Wawi Datenbank (MSSQL), fragt den Status über die DHL Shipment Tracking API ab und zeigt alles in einem übersichtlichen Web-Dashboard an.

---

## Voraussetzungen

- Windows 10/11 oder Windows Server
- Python 3.11+
- ODBC Driver 17 for SQL Server
- VPN-Verbindung zum JTL-Wawi Server
- DHL API Key (Shipment Tracking Unified, Production Europe) aus dem [DHL Developer Portal](https://developer.dhl.com)

---

## Installation

**1. Python-Pakete installieren**

```cmd
pip install -r requirements.txt
```

**2. Konfiguration anlegen**

```cmd
copy config.example.py config.py
```

Dann `config.py` öffnen und ausfüllen:

| Einstellung | Beschreibung |
|---|---|
| `DHL_API_KEY` | API Key aus dem DHL Developer Portal |
| `WAWI_CONNECTION_STRING` | MSSQL Verbindungsstring zur JTL-Wawi |
| `SMTP_*` | Zugangsdaten für E-Mail-Versand |
| `DASHBOARD_USER` / `DASHBOARD_PASSWORD` | Login für das Web-Dashboard |
| `SECRET_KEY` | Zufälliger String (mind. 32 Zeichen) |

> **Wichtig:** Die DHL Authentifizierung läuft ausschließlich über den Header `DHL-API-Key`. Kein OAuth2, kein Basic Auth.

**3. Dashboard starten**

```cmd
start.bat
```

Erreichbar unter: **http://localhost:5000**

---

## Features

### Dashboard
- Sendungsübersicht mit Echtzeit-Status aus der DHL API
- **Status-Filter**: Alle, Aktiv, Probleme, Packstation, Unterwegs, Vorbereitung, Zugestellt, Unbekannt
- **Zeitraum-Filter**: Heute, Gestern, Diese Woche, 7 Tage, 30 Tage
- **Suche** nach Sendungsnummer, Auftragsnummer oder Kundenname
- Klickbare Tabellenzeilen für schnellen Zugriff auf die Detailansicht

### Ampel-System
- **Unterwegs**: Grün (1–2 Tage) → Gelb (3 Tage) → Rot (ab 4 Tage)
- **Packstation**: Grün (1–2 Tage) → Gelb (3–4 Tage) → Rot (ab 5 Tage)
- **Stillstand-Warnung** 🕐: Sendung nicht zugestellt, kein neues Event seit 48h

### Automatisierung
- Synchronisiert neue Sendungen automatisch aus der JTL-Wawi Datenbank
- Pollt DHL-Status für alle offenen Sendungen (empfohlen: alle 2h per Windows Task Scheduler)
- Ungecheckte Sendungen werden bevorzugt abgefragt
- Bei Rate Limit wird das Polling sauber abgebrochen und beim nächsten Lauf fortgesetzt

### Weitere Funktionen
- Sendungsverlauf auf Deutsch (via DHL API Sprachparameter)
- PDF-Upload für manuelle Liefernachweise pro Sendung
- E-Mail-Versand an Kunden mit vorausgefüllten Templates (Zustellfehler, Packstation, Verzögerung)
- Mail-Log pro Sendung
- Relatives Zeitformat ("vor 2 Std." statt rohem Datum)

---

## Automatisches Polling (Windows Task Scheduler)

```cmd
schtasks /create /tn "JTLDHL-ShippingControl-Poll" /tr "python C:\Pfad\zum\Projekt\app\scheduler.py" /sc hourly /mo 2 /f
```

---

## Projektstruktur

```
jtl-trackerNG/
├── config.py              ← Zugangsdaten (nicht in Git!)
├── config.example.py      ← Vorlage für config.py
├── requirements.txt
├── start.bat              ← Web-Dashboard starten
├── app/
│   ├── web.py             ← Flask Web-App
│   ├── scheduler.py       ← Polling-Lauf
│   ├── dhl_tracker.py     ← DHL API Client
│   ├── wawi_reader.py     ← JTL-Wawi MSSQL Anbindung
│   ├── mailer.py          ← E-Mail-Versand
│   ├── db.py              ← SQLite Datenbankschicht
│   └── templates/         ← HTML-Templates
├── data/                  ← SQLite DB + Logs (nicht in Git)
└── uploads/               ← PDF-Liefernachweise (nicht in Git)
```

---

## Hinweise

- **DHL Rate Limit**: Der kostenlose API-Zugang erlaubt 250 Anfragen/Tag. Bereits zugestellte Sendungen werden nicht erneut abgefragt.
- **config.py** enthält sensible Zugangsdaten – niemals in Git einchecken (ist in `.gitignore` ausgeschlossen).
- Für externen Zugriff empfiehlt sich ein Reverse-Proxy (nginx/Caddy) mit HTTPS.
- Regelmäßige Backups des `data/`-Ordners empfohlen.
