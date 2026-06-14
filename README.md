# JTLDHL-ShippingControl

Wer täglich Pakete versendet, kennt das Problem: Sendungen verschwinden im Nirgendwo, Kunden melden sich wegen ausbleibender Lieferungen, Pakete verstauben wochenlang in Packstationen – und man bemerkt es zu spät.

**JTLDHL-ShippingControl** löst genau das. Das Tool synchronisiert sich automatisch mit der JTL-Wawi Datenbank, ruft für jede Sendung den aktuellen DHL-Status ab und zeigt alles in einem übersichtlichen Web-Dashboard an – mit Ampelsystem, Frühwarnung und direktem Kundenkontakt aus dem Browser heraus.

Kein manuelles Tracking mehr. Kein Wechsel zwischen DHL-Portal und Warenwirtschaft. Alles an einem Ort.

---

## Voraussetzungen

- Windows 10/11 oder Windows Server
- Python 3.11+
- ODBC Driver 17 for SQL Server
- Netzwerkzugriff auf den JTL-Wawi Datenbankserver (lokal oder per VPN)
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

> **Sicherheitsempfehlung:** Das Tool führt ausschließlich lesende `SELECT`-Abfragen auf der JTL-Wawi Datenbank aus – es werden keine Daten verändert. Empfohlen wird dennoch ein dedizierter SQL-Benutzer mit reinen Leserechten (`db_datareader`) statt des `sa`-Kontos:
> ```sql
> CREATE LOGIN jtl_tracking_reader WITH PASSWORD = 'SicheresPasswort';
> USE eazybusiness;
> CREATE USER jtl_tracking_reader FOR LOGIN jtl_tracking_reader;
> EXEC sp_addrolemember 'db_datareader', 'jtl_tracking_reader';
> ```

**3. Dashboard starten**

```cmd
start.bat
```

Erreichbar unter: **http://localhost:5000**

---

## Was das Tool leistet

### Frühwarnsystem mit Ampel

Jede Sendung bekommt eine farbliche Bewertung – direkt im Dashboard sichtbar, ohne in Details klicken zu müssen:

**Sendungen unterwegs:**
- 🟢 1–2 Tage → alles normal
- 🟡 3 Tage → Aufmerksamkeit empfohlen
- 🔴 ab 4 Tage → Handlungsbedarf, möglicherweise Lieferproblem

**Sendungen in der Packstation:**
- 🟢 1–2 Tage → Kunde hat noch Zeit
- 🟡 3–4 Tage → Kunde sollte erinnert werden
- 🔴 ab 5 Tage → dringend, Paket wird bald retourniert

Zusätzlich: Sendungen ohne jede Statusänderung seit mehr als 48 Stunden werden mit einem ⏰-Symbol markiert – ein frühes Zeichen für Zustellprobleme, bevor der Kunde sich meldet.

### Direkte Kundenkommunikation

Aus der Detailansicht jeder Sendung kann direkt eine E-Mail an den Kunden verfasst und versendet werden – mit vorausgefüllten Templates für die häufigsten Szenarien:

- **Zustellfehler** – Paket konnte nicht zugestellt werden
- **Packstation** – Erinnerung zur Abholung mit Fristhinweis
- **Verzögerung** – proaktive Information bei ausbleibenden Updates

Der Kundenname wird automatisch aus JTL-Wawi übernommen, sodass jede Mail persönlich adressiert ist. Alle versendeten Mails werden pro Sendung protokolliert.

### Übersicht und Filterung

- **Status-Filter**: Alle · Aktiv · Probleme · Packstation · Unterwegs · Vorbereitung · Zugestellt · Unbekannt
- **Zeitraum-Filter**: Heute · Gestern · Diese Woche · 7 Tage · 30 Tage
- **Volltextsuche** nach Sendungsnummer, Auftragsnummer oder Kundenname
- Alle Filter sind kombinierbar
- Relative Zeitangaben ("vor 2 Std.", "vor 3 Tagen") statt roher Datumsstempel

### Automatische Synchronisation

Das Tool läuft im Hintergrund und hält sich selbst aktuell:

- Neue Sendungen werden automatisch aus der JTL-Wawi Datenbank (MSSQL) geladen
- DHL-Status wird regelmäßig per Windows Task Scheduler abgerufen (empfohlen: alle 2h)
- Bereits zugestellte Sendungen werden nicht erneut abgefragt – spart API-Kontingent
- Ungecheckte Sendungen haben Vorrang beim Polling
- Bei Erreichen des API-Tageslimits wird sauber abgebrochen und beim nächsten Lauf fortgesetzt

### Weitere Funktionen

- Sendungsverlauf auf Deutsch direkt aus der DHL API
- PDF-Upload für manuelle Liefernachweise, pro Sendung abrufbar
- Passwortgeschütztes Web-Login
- Läuft lokal auf dem eigenen Rechner oder Server – keine Cloud, keine externen Dienste

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

---

## Kompatibilität

Getestet mit **JTL-Wawi 1.11.11** und der **DHL Shipment Tracking Unified API** (Production Europe).

---

## Rechtlicher Hinweis

Dieses Projekt ist ein unabhängiges Open-Source-Tool und steht in keiner Verbindung zur JTL-Software GmbH oder der Deutsche Post DHL Group.

„JTL" und „JTL-Wawi" sind eingetragene Marken der JTL-Software GmbH. „DHL" ist eine eingetragene Marke der Deutsche Post DHL Group. Alle Markennamen werden ausschließlich zur sachlichen Beschreibung der Kompatibilität verwendet.

Die Nutzung erfolgt auf eigene Verantwortung. Es wird keine Haftung für Schäden übernommen, die durch den Einsatz dieses Tools entstehen.

---

## Lizenz

Dieses Projekt steht unter der [CC BY-NC-ND 4.0 Lizenz](https://creativecommons.org/licenses/by-nc-nd/4.0/).

- ✅ Nutzung und Weitergabe erlaubt
- ❌ Keine kommerzielle Nutzung
- ❌ Keine Veränderung oder Weiterveröffentlichung von Abwandlungen

© 2026 Ron – [u238.de](https://u238.de)

---

## Unterstützung

Wenn dir dieses Tool nützlich ist, freue ich mich über einen Kaffee ☕

[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/scavenger6)
