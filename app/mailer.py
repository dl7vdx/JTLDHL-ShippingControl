"""
mailer.py – E-Mail-Versand an Kunden
Unterstützt HTML-Templates für verschiedene Problemfälle
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

logger = logging.getLogger(__name__)


# ── Mail-Templates ──────────────────────────────────────────────────────────

TEMPLATES = {
    "delivery_failure": {
        "subject": "Ihr Paket konnte nicht zugestellt werden – Auftrag {order_number}",
        "body": """
<p>Sehr geehrte/r {customer_name},</p>

<p>leider konnten wir Ihr Paket mit der Sendungsnummer <strong>{tracking_number}</strong>
(Auftrag: {order_number}) nicht erfolgreich zustellen.</p>

<p>Aktueller Status: <strong>{status_description}</strong></p>

<p>Sie können den Sendungsverlauf jederzeit hier einsehen:<br>
<a href="https://www.dhl.de/de/privatkunden/pakete-empfangen/verfolgen.html?piececode={tracking_number}">
Sendung verfolgen
</a></p>

<p>Bitte nehmen Sie Kontakt mit Ihrer DHL-Filiale auf oder antworten Sie auf diese E-Mail,
falls Sie Fragen haben.</p>

<p>Mit freundlichen Grüßen<br>
Ihr Shop-Team</p>
""",
    },
    "packstation": {
        "subject": "Ihr Paket liegt in der Packstation – Auftrag {order_number}",
        "body": """
<p>Sehr geehrte/r {customer_name},</p>

<p>Ihr Paket mit der Sendungsnummer <strong>{tracking_number}</strong>
(Auftrag: {order_number}) wurde in einer Packstation hinterlegt.</p>

<p>Standort: <strong>{location}</strong></p>

<p>Bitte holen Sie Ihr Paket zeitnah ab – Packstationen haben eine begrenzte Lagerzeit.</p>

<p>Den genauen Standort und Ihren Abholcode finden Sie in der DHL-App oder unter:<br>
<a href="https://www.dhl.de/de/privatkunden/pakete-empfangen/verfolgen.html?piececode={tracking_number}">
Sendung verfolgen
</a></p>

<p>Mit freundlichen Grüßen<br>
Ihr Shop-Team</p>
""",
    },
    "no_update": {
        "subject": "Verzögerung bei Ihrer Lieferung – Auftrag {order_number}",
        "body": """
<p>Sehr geehrte/r {customer_name},</p>

<p>bei Ihrem Paket (Sendungsnummer: <strong>{tracking_number}</strong>, Auftrag: {order_number})
gibt es derzeit leider keine neuen Tracking-Updates von DHL.</p>

<p>Wir sind bereits dabei, den Status Ihrer Sendung zu klären und melden uns schnellstmöglich
bei Ihnen.</p>

<p>Mit freundlichen Grüßen<br>
Ihr Shop-Team</p>
""",
    },
    "custom": {
        "subject": "{subject}",
        "body": "{body}",
    },
}


def get_template(template_key: str, **kwargs) -> dict:
    """
    Gibt ein vorausgefülltes Mail-Dict zurück.
    kwargs: tracking_number, order_number, customer_name, status_description, location, ...
    """
    tpl = TEMPLATES.get(template_key, TEMPLATES["custom"])
    return {
        "subject": tpl["subject"].format(**kwargs),
        "body":    tpl["body"].format(**kwargs),
    }


def send_mail(to_address: str, subject: str, html_body: str) -> tuple[bool, str]:
    """
    Sendet eine HTML-Mail via SMTP.
    Gibt (True, "") bei Erfolg zurück, (False, Fehlermeldung) bei Fehler.
    """
    msg = MIMEMultipart("alternative")
    msg["From"]    = SMTP_FROM
    msg["To"]      = to_address
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_address, msg.as_string())
        logger.info(f"Mail gesendet an {to_address}: {subject}")
        return True, ""
    except smtplib.SMTPAuthenticationError:
        msg = "SMTP-Authentifizierung fehlgeschlagen – Zugangsdaten prüfen"
        logger.error(msg)
        return False, msg
    except smtplib.SMTPException as e:
        logger.error(f"SMTP-Fehler: {e}")
        return False, str(e)
    except Exception as e:
        logger.error(f"Mail-Fehler: {e}")
        return False, str(e)
