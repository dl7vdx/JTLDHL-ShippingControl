# JTL ShippingTracker

DHL Sendungsverfolgung für JTL-Wawi Geschäftskunden – als eigenständiges Web-Tool,
ohne JTL-REST-API und ohne DHL-Versandkosten für die Tracking-API.

---

## Voraussetzungen

- Windows 10/11 oder Windows Server
- Python 3.11+ (https://python.org)
- ODBC Driver 17 for SQL Server (https://aka.ms/odbc17)
- VPN-Verbindung zum JTL-Wawi-Server muss aktiv sein
- DHL API Key (Production Europe) aus dem DHL Developer Portal

---

## Installation

### 1. Python-Pakete installieren

```cmd
cd C:\jtl-tracker
pip install -r requirements.txt
```

### 2. Konfiguration anpassen

Öffne `config.py` und trage ein:

| Einstellung | Beschreibung |
|---|---|
| `DHL_API_KEY` | Dein DHL API Key aus dem Developer Portal |
| `DHL_API_SECRET` | Dein DHL API Secret |
| `WAWI_CONNECTION_STRING` | IP/Hostname des MSSQL-Servers + Zugangsdaten |
| `SMTP_*` | Zugangsdaten deines E-Mail-Providers |
| `DASHBOARD_PASSWORD` | Sicheres Passwort für das Web-Login |
| `SECRET_KEY` | Zufälliger String (mind. 32 Zeichen) |

### 3. Ersten Start durchführen

```cmd
start.bat
```

Das Dashboard ist dann erreichbar unter: **http://localhost:5000**

Von außen/unterwegs: Port 5000 in der Windows Firewall freigeben und
die externe IP deines Rechners verwenden. Für Produktionsbetrieb
empfiehlt sich ein Reverse-Proxy (nginx) mit HTTPS.

---

## Automatisches Polling einrichten (Windows Task Scheduler)

Damit DHL-Status automatisch alle 2 Stunden abgerufen wird,
öffne eine Kommandozeile **als Administrator** und führe aus:

```cmd
schtasks /create /tn "JTL-ShippingTracker-Poll" /tr "python C:\jtl-tracker\app\scheduler.py" /sc hourly /mo 2 /f
```

---

## Projektstruktur

```
jtl-tracker/
├── config.py              ← Alle Einstellungen hier
├── requirements.txt
├── start.bat              ← Web-Dashboard starten
├── app/
│   ├── web.py             ← Flask Web-App (Dashboard)
│   ├── scheduler.py       ← Polling-Lauf (Task Scheduler)
│   ├── dhl_tracker.py     ← DHL Tracking API Client
│   ├── wawi_reader.py     ← JTL-Wawi MSSQL Anbindung
│   ├── mailer.py          ← E-Mail-Versand + Templates
│   ├── db.py              ← SQLite Datenbank
│   └── templates/         ← HTML-Templates
├── data/
│   ├── tracker.db         ← SQLite Datenbank (auto-erstellt)
│   └── tracker.log        ← Log-Datei
└── uploads/               ← PDF-Sendungsnachweise
```

---

## Features

- **Sendungsübersicht** mit Ampel-Status (OK / Problem / Packstation)
- **Automatische Problemerkennung**: Zustellfehler, Packstation, keine Updates > 48h
- **JTL-Wawi Sync**: Neue Sendungen werden automatisch aus der Wawi-DB geladen
- **PDF-Upload**: Sendungsnachweise manuell hochladen und pro Sendung abrufbar
- **E-Mail-Templates**: Vorausgefüllte Mails für Zustellfehler, Packstation, Verzögerung
- **Mail-Log**: Übersicht aller gesendeten Kunden-Mails
- **Manueller Polling-Trigger**: Direkt im Dashboard per Knopfdruck

---

## Bekannte Einschränkungen

- PDF-Sendungsnachweise müssen manuell aus dem DHL-Portal heruntergeladen
  und über den Upload-Button im Dashboard hinzugefügt werden.
  Eine automatische API-Abholung bietet DHL nicht an.

- Die DHL Tracking API hat nach Registrierung zunächst Status `pending`.
  Die Freischaltung dauert meist einige Stunden bis 1 Werktag.

---

## Sicherheitshinweise

- `config.py` enthält sensible Zugangsdaten – niemals in Git einchecken
- Für Zugriff von außen: HTTPS via nginx/Caddy einrichten
- Regelmäßige Backups der `data/`-Ordners empfohlen
