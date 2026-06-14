"""
web.py – Flask Web-Dashboard
Läuft auf dem lokalen Rechner, erreichbar von außen via Port-Freigabe oder VPN
"""

import os
import sys
import logging
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_from_directory, jsonify
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import (
    init_db, get_all_shipments, get_shipment, get_events,
    set_pdf_filename, upsert_shipment, get_mail_log, log_mail,
    get_packstation_arrival, get_transit_since, get_last_event_time
)
from app.mailer import send_mail, get_template
from app.wawi_reader import test_connection
from config import (
    SECRET_KEY, DASHBOARD_USER, DASHBOARD_PASSWORD,
    UPLOAD_FOLDER
)

app = Flask(__name__)
app.secret_key = SECRET_KEY


@app.template_filter("relative_time")
def relative_time(value):
    try:
        dt = datetime.fromisoformat(value)
        diff = datetime.now() - dt
        seconds = diff.total_seconds()
        if seconds < 3600:
            m = int(seconds / 60)
            return f"vor {m} Min." if m > 1 else "gerade eben"
        elif seconds < 86400:
            h = int(seconds / 3600)
            return f"vor {h} Std."
        else:
            d = int(seconds / 86400)
            return f"vor {d} Tag{'en' if d != 1 else ''}"
    except Exception:
        return value

ALLOWED_EXTENSIONS = {"pdf"}
logger = logging.getLogger(__name__)


# ── Auth ─────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (request.form.get("username") == DASHBOARD_USER and
                request.form.get("password") == DASHBOARD_PASSWORD):
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        flash("Falscher Benutzername oder Passwort", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def dashboard():
    status_filter = request.args.get("filter", "all")
    valid_filters = {"all", "active", "problematic", "packstation", "delivered", "transit", "pre-transit", "unknown"}
    if status_filter not in valid_filters:
        status_filter = "all"

    valid_periods = {"today", "yesterday", "this_week", "last_7", "last_30"}
    period = request.args.get("period", "")
    if period not in valid_periods:
        period = ""

    search = request.args.get("search", "").strip()

    shipments = get_all_shipments(
        filter_status=None if status_filter == "all" else status_filter,
        period=period or None,
        search=search or None,
    )

    # Zähler immer ohne Zeitraum/Suche (Gesamtübersicht)
    all_ships = get_all_shipments()
    counts = {
        "all":          len(all_ships),
        "active":       sum(1 for s in all_ships if not s["is_delivered"]),
        "problematic":  sum(1 for s in all_ships if s["is_problematic"]),
        "packstation":  sum(1 for s in all_ships if s["is_packstation"] and not s["is_delivered"]),
        "delivered":    sum(1 for s in all_ships if s["is_delivered"]),
        "transit":      sum(1 for s in all_ships if s["current_status"] == "transit"),
        "pre-transit":  sum(1 for s in all_ships if s["current_status"] == "pre-transit"),
        "unknown":      sum(1 for s in all_ships if s["current_status"] == "unknown"),
    }

    # Packstation-Tage berechnen
    packstation_days = {}
    transit_days = {}
    stale_hours = {}   # Sendungen ohne Update seit >48h

    for s in shipments:
        tn = s["tracking_number"]
        now = datetime.now()

        if s["is_packstation"] and not s["is_delivered"]:
            arrival = get_packstation_arrival(tn)
            if arrival:
                try:
                    packstation_days[tn] = (now - datetime.fromisoformat(arrival)).days
                except Exception:
                    pass

        if s["current_status"] == "transit" and not s["is_delivered"]:
            since = get_transit_since(tn)
            if since:
                try:
                    transit_days[tn] = (now - datetime.fromisoformat(since)).days
                except Exception:
                    pass

        if not s["is_delivered"]:
            last_event = get_last_event_time(tn)
            if last_event:
                try:
                    hours = (now - datetime.fromisoformat(last_event)).total_seconds() / 3600
                    if hours >= 48:
                        stale_hours[tn] = int(hours)
                except Exception:
                    pass

    return render_template("dashboard.html",
                           shipments=shipments,
                           current_filter=status_filter,
                           current_period=period,
                           current_search=search,
                           counts=counts,
                           packstation_days=packstation_days,
                           transit_days=transit_days,
                           stale_hours=stale_hours)


# ── Sendungs-Detail ───────────────────────────────────────────────────────────

@app.route("/shipment/<tracking_number>")
@login_required
def shipment_detail(tracking_number):
    shipment = get_shipment(tracking_number)
    if not shipment:
        flash("Sendung nicht gefunden", "error")
        return redirect(url_for("dashboard"))

    events   = get_events(tracking_number)
    mail_log = get_mail_log(tracking_number)

    # Vorausgefüllte Mail-Templates
    templates = {}
    kwargs = dict(
        tracking_number    = tracking_number,
        order_number       = shipment["order_number"] or "",
        customer_name      = shipment["customer_name"] or "",
        status_description = shipment["current_status"] or "",
        location           = shipment["recipient_city"] or "",
        subject            = "",
        body               = "",
    )
    for key in ("delivery_failure", "packstation", "no_update"):
        templates[key] = get_template(key, **kwargs)

    return render_template("detail.html",
                           shipment=shipment,
                           events=events,
                           mail_log=mail_log,
                           templates=templates)


# ── Sendung manuell hinzufügen ────────────────────────────────────────────────

@app.route("/add", methods=["GET", "POST"])
@login_required
def add_shipment():
    if request.method == "POST":
        tn = request.form.get("tracking_number", "").strip()
        if not tn:
            flash("Sendungsnummer darf nicht leer sein", "error")
            return redirect(url_for("add_shipment"))
        upsert_shipment(
            tracking_number = tn,
            order_number    = request.form.get("order_number", "").strip(),
            customer_name   = request.form.get("customer_name", "").strip(),
            customer_email  = request.form.get("customer_email", "").strip(),
            recipient_city  = request.form.get("recipient_city", "").strip(),
        )
        flash(f"Sendung {tn} hinzugefügt", "success")
        return redirect(url_for("shipment_detail", tracking_number=tn))
    return render_template("add.html")


# ── PDF Upload ────────────────────────────────────────────────────────────────

@app.route("/shipment/<tracking_number>/upload_pdf", methods=["POST"])
@login_required
def upload_pdf(tracking_number):
    file = request.files.get("pdf_file")
    if not file or file.filename == "":
        flash("Keine Datei ausgewählt", "error")
        return redirect(url_for("shipment_detail", tracking_number=tracking_number))

    if not file.filename.lower().endswith(".pdf"):
        flash("Nur PDF-Dateien erlaubt", "error")
        return redirect(url_for("shipment_detail", tracking_number=tracking_number))

    filename = secure_filename(f"{tracking_number}.pdf")
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    set_pdf_filename(tracking_number, filename)
    flash("PDF erfolgreich hochgeladen", "success")
    return redirect(url_for("shipment_detail", tracking_number=tracking_number))


@app.route("/pdf/<filename>")
@login_required
def download_pdf(filename):
    return send_from_directory(
        os.path.abspath(UPLOAD_FOLDER),
        filename,
        as_attachment=True
    )


# ── Mail senden ───────────────────────────────────────────────────────────────

@app.route("/shipment/<tracking_number>/send_mail", methods=["POST"])
@login_required
def send_customer_mail(tracking_number):
    shipment = get_shipment(tracking_number)
    if not shipment:
        flash("Sendung nicht gefunden", "error")
        return redirect(url_for("dashboard"))

    to_address = request.form.get("to_address", "").strip()
    subject    = request.form.get("subject", "").strip()
    body       = request.form.get("body", "").strip()

    if not to_address or not subject or not body:
        flash("Empfänger, Betreff und Text sind erforderlich", "error")
        return redirect(url_for("shipment_detail", tracking_number=tracking_number))

    # Einfaches HTML-Wrapping falls nötig
    if not body.strip().startswith("<"):
        body = f"<p>{body.replace(chr(10), '</p><p>')}</p>"

    success, error_msg = send_mail(to_address, subject, body)
    status = "sent" if success else f"failed: {error_msg}"
    log_mail(tracking_number, to_address, subject, status)

    if success:
        flash(f"E-Mail erfolgreich gesendet an {to_address}", "success")
    else:
        flash(f"Fehler beim Senden: {error_msg}", "error")

    return redirect(url_for("shipment_detail", tracking_number=tracking_number))


# ── System ────────────────────────────────────────────────────────────────────

@app.route("/system")
@login_required
def system_status():
    wawi_ok, wawi_msg = test_connection()
    return render_template("system.html", wawi_ok=wawi_ok, wawi_msg=wawi_msg)


@app.route("/api/trigger_poll", methods=["POST"])
@login_required
def trigger_poll():
    """Manuellen Polling-Lauf anstoßen (AJAX)."""
    try:
        from app.scheduler import run as run_poll
        import threading
        t = threading.Thread(target=run_poll, daemon=True)
        t.start()
        return jsonify({"status": "started"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
