# Changelog

Alle wichtigen Änderungen werden in dieser Datei dokumentiert.

---

## [1.1.0] – 2026-06-24

### Neu

- **Status „In Filiale"** – Sendungen, die zur Abholung in einer DHL-Filiale oder einem Paketshop bereitstehen, werden als eigenständiger Status erkannt, gefiltert und im Dashboard angezeigt (🏪)
- **Adresse der Packstation / Filiale** – Sofern von der DHL-API geliefert, wird die genaue Adresse der Abholstation direkt unter dem Status-Badge im Dashboard angezeigt
- **Abholort-Symbol bei zugestellten Sendungen** – Zugestellte Pakete zeigen, ob die Übergabe an eine Packstation (📦) oder Filiale (🏪) erfolgte
- **Sendungsnummer kopieren & GKP-Link** – In der Detailansicht kann die Sendungsnummer per Klick in die Zwischenablage kopiert werden; daneben öffnet ein Button direkt das DHL Geschäftskundenportal
- **Priorisiertes API-Polling** – DHL-Abfragen werden nach Dringlichkeit des Status gestaffelt, um das Tageskontingent von 250 Calls optimal zu nutzen:
  - Probleme / Packstation / Filiale → alle 2 Stunden
  - Unterwegs → alle 8 Stunden
  - Unbekannt → alle 12 Stunden
  - Vorbereitung → alle 24 Stunden

### Verbesserungen

- **Lesbareres Zeitformat im Sendungsverlauf** – Das ISO-Trennzeichen `T` wird als Leerzeichen dargestellt (`2026-06-15 17:50` statt `2026-06-15T17:50`)
- **Straße in Standortanzeige** – Die Straße wird jetzt aus der DHL-API-Antwort mitgespeichert und angezeigt (bisher nur Stadt)
- **Status-Toggle-Filter** – Die Statusfilter im Dashboard wurden von einfachen Tabs auf unabhängig schaltbare Chips umgestellt; mehrere Statii können gleichzeitig ein- und ausgeblendet werden

### Technisch

- Neue Datenbankspalte `is_filiale` mit automatischer Migration für bestehende Installationen (kein manueller DB-Eingriff nötig)
- `get_active_tracking_numbers()` berücksichtigt jetzt Status-abhängige Mindestabstände zwischen Abfragen

---

## [1.0.0] – 2026-06-17

Erste öffentliche Version.

- Automatische Synchronisation neuer Sendungen aus JTL-Wawi (MSSQL)
- DHL Shipment Tracking Unified API (Authentifizierung via `DHL-API-Key`)
- Web-Dashboard mit Status-Übersicht, Ampelsystem und Zeitraumfiltern
- Erkennung von Problemen, Packstation-Sendungen und Zustellfehlern
- Ampel für Packstation (Tage bis Rücksendung) und Transit (Tage unterwegs)
- Stillstand-Warnung bei Sendungen ohne Update seit >48 Stunden (🕐)
- E-Mail-Versand an Kunden direkt aus dem Dashboard (HTML-Templates)
- PDF-Upload für Liefernachweise pro Sendung
- Passwortgeschütztes Web-Login
- Automatisches Polling via Windows Task Scheduler
