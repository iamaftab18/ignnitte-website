"""
Ignnitte — Industry 4.0 Training Institute
Flask + Jinja + Tailwind + SQLite

Content is identical to ignnitte.com; the visual styling is redesigned in a
dark, minimalist NEURA-Robotics-inspired aesthetic.

Run:
    pip install -r requirements.txt
    python app.py
    open http://localhost:5000
"""

import csv
import hmac
import io
import os
import re
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    Response,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in production where env is set directly
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
# Reuse the original project's images / videos / logo instead of duplicating them.
ASSETS_DIR = PROJECT_ROOT / "public"
DB_PATH = BASE_DIR / "ignnitte.db"

if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env")

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# --------------------------------------------------------------------------- #
#  Admin credentials (secret login, not linked anywhere in the public nav)
# --------------------------------------------------------------------------- #
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "ignnitte01")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin@ignnitte")

# --------------------------------------------------------------------------- #
#  Reference data (kept in sync with the original React source in ../src)
# --------------------------------------------------------------------------- #
COURSE_NAME = "Industry 4.0 Career Program"
PROGRAM_TRACKS = [
    "IIoT",
    "Robotics",
    "AIoT",
    "PLC & HMI",
    "Industrial Automation",
    "Cloud & GenAI",
]
YEAR_OPTIONS = ["1st Year", "2nd Year", "3rd Year", "Final Year", "Recently Graduated"]
GENDER_OPTIONS = ["Female", "Male", "Other", "Prefer not to say"]


def _now():
    if ZoneInfo is not None:
        return datetime.now(ZoneInfo("Asia/Kolkata"))
    return datetime.now()


# --------------------------------------------------------------------------- #
#  SQLite helpers
# --------------------------------------------------------------------------- #
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS contact_submissions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            email        TEXT NOT NULL,
            phone        TEXT NOT NULL,
            inquiry      TEXT NOT NULL,
            submitted_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS student_registrations (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            name              TEXT NOT NULL,
            email             TEXT NOT NULL UNIQUE,
            contact           TEXT NOT NULL,
            gender            TEXT,
            college           TEXT NOT NULL,
            department        TEXT NOT NULL,
            year_of_study     TEXT,
            cgpa              TEXT,
            program_interest  TEXT,
            consent           INTEGER NOT NULL DEFAULT 0,
            registered_at     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS site_visits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            path        TEXT NOT NULL,
            visitor_id  TEXT NOT NULL,
            visited_at  TEXT NOT NULL
        );
        """
    )
    con.commit()
    con.close()


init_db()


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_phone(phone):
    return "".join(c for c in phone if c.isdigit() or c == "+")


# --------------------------------------------------------------------------- #
#  Visitor tracking (lightweight, cookie-based, no personal data stored)
# --------------------------------------------------------------------------- #
TRACKED_PREFIXES_EXCLUDED = ("/static", "/assets", "/admin", "/api")
VISITOR_COOKIE = "ignnitte_vid"


@app.before_request
def track_visit():
    path = request.path
    if request.method != "GET" or path.startswith(TRACKED_PREFIXES_EXCLUDED):
        return
    visitor_id = request.cookies.get(VISITOR_COOKIE)
    g.new_visitor_id = None if visitor_id else str(uuid.uuid4())
    g.visitor_id = visitor_id or g.new_visitor_id
    db = get_db()
    db.execute(
        "INSERT INTO site_visits (path, visitor_id, visited_at) VALUES (?, ?, ?)",
        (path, g.visitor_id, _now().isoformat()),
    )
    db.commit()


@app.after_request
def set_visitor_cookie(response):
    new_id = g.get("new_visitor_id", None)
    if new_id:
        response.set_cookie(
            VISITOR_COOKIE, new_id, max_age=60 * 60 * 24 * 365, samesite="Lax"
        )
    return response


# --------------------------------------------------------------------------- #
#  Admin auth
# --------------------------------------------------------------------------- #
def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


# --------------------------------------------------------------------------- #
#  Template context
# --------------------------------------------------------------------------- #
@app.context_processor
def inject_globals():
    return {
        "current_year": _now().year,
        "nav_links": [
            {"label": "Home", "path": "/"},
            {"label": "Programs", "path": "/programs"},
            {"label": "Internships", "path": "/internship"},
            {"label": "About Us", "path": "/about"},
            {"label": "Events", "path": "/events"},
            {"label": "Lab Tour", "path": "/lab-tour"},
            {"label": "Contact", "path": "/contact"},
        ],
    }


# --------------------------------------------------------------------------- #
#  Asset route  (serves the original project's images / videos / logo)
# --------------------------------------------------------------------------- #
@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(ASSETS_DIR, filename)


# --------------------------------------------------------------------------- #
#  Page routes
# --------------------------------------------------------------------------- #
@app.route("/")
def home():
    return render_template("home.html", active="/")


@app.route("/programs")
def programs():
    return render_template("programs.html", active="/programs")


@app.route("/internship")
def internship():
    return render_template("internship.html", active="/internship")


@app.route("/about")
def about():
    return render_template("about.html", active="/about")


@app.route("/events")
def events():
    return render_template("events.html", active="/events")


@app.route("/lab-tour")
def lab_tour():
    return render_template("lab_tour.html", active="/lab-tour")


@app.route("/contact")
def contact():
    return render_template("contact.html", active="/contact")


@app.route("/register")
def register():
    return render_template(
        "register.html",
        active="/register",
        course_name=COURSE_NAME,
        program_tracks=PROGRAM_TRACKS,
        year_options=YEAR_OPTIONS,
        gender_options=GENDER_OPTIONS,
    )


# --------------------------------------------------------------------------- #
#  API routes
# --------------------------------------------------------------------------- #
@app.post("/api/contact")
def api_contact():
    data = request.get_json(silent=True) or request.form
    fields = {k: str(data.get(k, "")).strip() for k in ("name", "email", "phone", "inquiry")}

    if any(not v for v in fields.values()):
        return jsonify({"message": "All fields are required."}), 400
    if not EMAIL_RE.match(fields["email"]):
        return jsonify({"message": "Please enter a valid email address."}), 400

    db = get_db()
    db.execute(
        "INSERT INTO contact_submissions (name, email, phone, inquiry, submitted_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (fields["name"], fields["email"], fields["phone"], fields["inquiry"], _now().isoformat()),
    )
    db.commit()
    return jsonify(
        {
            "success": True,
            "message": "Thank you for your inquiry! Our team will reach out to you shortly.",
        }
    )


@app.post("/api/register")
def api_register():
    data = request.get_json(silent=True) or request.form

    fields = {
        "name": str(data.get("name", "")).strip(),
        "email": str(data.get("email", "")).strip().lower(),
        "contact": clean_phone(str(data.get("contact", "")).strip()),
        "gender": str(data.get("gender", "")).strip(),
        "college": str(data.get("college", "")).strip(),
        "department": str(data.get("department", "")).strip(),
        "year_of_study": str(data.get("year_of_study", "")).strip(),
        "cgpa": str(data.get("cgpa", "")).strip(),
        "program_interest": str(data.get("program_interest", "")).strip(),
    }
    consent = str(data.get("consent", "")).lower() in ("true", "on", "1", "yes")

    required = ["name", "email", "contact", "college", "department"]
    if any(not fields[f] for f in required):
        return jsonify({"message": "Name, email, contact, college and department are required."}), 400
    if not EMAIL_RE.match(fields["email"]):
        return jsonify({"message": "Please enter a valid email address."}), 400
    if not consent:
        return jsonify({"message": "Please provide consent to receive updates via mail or WhatsApp."}), 400

    if fields["cgpa"]:
        try:
            cgpa_value = float(fields["cgpa"])
            if not (0 <= cgpa_value <= 10):
                raise ValueError
        except ValueError:
            return jsonify({"message": "CGPA must be a number between 0 and 10."}), 400

    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO student_registrations
              (name, email, contact, gender, college, department, year_of_study,
               cgpa, program_interest, consent, registered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fields["name"],
                fields["email"],
                fields["contact"],
                fields["gender"],
                fields["college"],
                fields["department"],
                fields["year_of_study"],
                fields["cgpa"],
                fields["program_interest"],
                1 if consent else 0,
                _now().isoformat(),
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "This email is already registered."}), 409

    return jsonify(
        {
            "success": True,
            "message": "You're registered! You'll receive further updates regarding the institute via mail or WhatsApp.",
        }
    )


@app.get("/api/health")
def health():
    return jsonify({"status": "Server is running"})


# --------------------------------------------------------------------------- #
#  Admin routes (secret login — not linked from the public site)
# --------------------------------------------------------------------------- #
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))

    error = None
    if request.method == "POST":
        username = str(request.form.get("username", "")).strip()
        password = str(request.form.get("password", ""))
        valid = hmac.compare_digest(username, ADMIN_USERNAME) and hmac.compare_digest(
            password, ADMIN_PASSWORD
        )
        if valid:
            session.clear()
            session["is_admin"] = True
            session.permanent = True
            app.permanent_session_lifetime = timedelta(hours=8)
            next_path = request.args.get("next")
            if next_path and next_path.startswith("/admin"):
                return redirect(next_path)
            return redirect(url_for("admin_dashboard"))
        error = "Invalid username or password."

    return render_template("admin_login.html", error=error)


@app.post("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.get("/admin/dashboard")
@admin_required
def admin_dashboard():
    db = get_db()

    registrations = [dict(r) for r in db.execute(
        "SELECT * FROM student_registrations ORDER BY registered_at DESC"
    ).fetchall()]
    contacts = [dict(r) for r in db.execute(
        "SELECT * FROM contact_submissions ORDER BY submitted_at DESC"
    ).fetchall()]

    total_visits = db.execute("SELECT COUNT(*) AS c FROM site_visits").fetchone()["c"]
    unique_visitors = db.execute(
        "SELECT COUNT(DISTINCT visitor_id) AS c FROM site_visits"
    ).fetchone()["c"]
    today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    visits_today = db.execute(
        "SELECT COUNT(*) AS c FROM site_visits WHERE visited_at >= ?", (today_start,)
    ).fetchone()["c"]

    daily_rows = db.execute(
        """
        SELECT substr(visited_at, 1, 10) AS day, COUNT(*) AS visits,
               COUNT(DISTINCT visitor_id) AS visitors
        FROM site_visits
        GROUP BY day
        ORDER BY day DESC
        LIMIT 14
        """
    ).fetchall()
    daily_stats = list(reversed([dict(r) for r in daily_rows]))

    top_pages = [dict(r) for r in db.execute(
        """
        SELECT path, COUNT(*) AS visits
        FROM site_visits
        GROUP BY path
        ORDER BY visits DESC
        LIMIT 8
        """
    ).fetchall()]

    gender_rows = [dict(r) for r in db.execute(
        """
        SELECT COALESCE(NULLIF(gender, ''), 'Not specified') AS gender, COUNT(*) AS count
        FROM student_registrations
        GROUP BY gender
        """
    ).fetchall()]

    program_rows = [dict(r) for r in db.execute(
        """
        SELECT COALESCE(NULLIF(program_interest, ''), 'Not specified') AS program, COUNT(*) AS count
        FROM student_registrations
        GROUP BY program
        ORDER BY count DESC
        """
    ).fetchall()]

    stats = {
        "total_visits": total_visits,
        "unique_visitors": unique_visitors,
        "visits_today": visits_today,
        "total_registrations": len(registrations),
        "total_contacts": len(contacts),
        "consented_count": sum(1 for r in registrations if r["consent"]),
    }

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        registrations=registrations,
        contacts=contacts,
        daily_stats=daily_stats,
        top_pages=top_pages,
        gender_rows=gender_rows,
        program_rows=program_rows,
    )


def _csv_response(rows, fieldnames, filename):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/admin/export/registrations.csv")
@admin_required
def export_registrations():
    db = get_db()
    rows = [dict(r) for r in db.execute(
        "SELECT * FROM student_registrations ORDER BY registered_at DESC"
    ).fetchall()]
    fieldnames = [
        "id", "name", "email", "contact", "gender", "college", "department",
        "year_of_study", "cgpa", "program_interest", "consent", "registered_at",
    ]
    return _csv_response(rows, fieldnames, "registrations.csv")


@app.get("/admin/export/contacts.csv")
@admin_required
def export_contacts():
    db = get_db()
    rows = [dict(r) for r in db.execute(
        "SELECT * FROM contact_submissions ORDER BY submitted_at DESC"
    ).fetchall()]
    fieldnames = ["id", "name", "email", "phone", "inquiry", "submitted_at"]
    return _csv_response(rows, fieldnames, "contacts.csv")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG") == "1")
