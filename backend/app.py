"""
Mini CRM backend
-----------------
Flask + MySQL REST API for: Login, Lead Management, Dashboard stats,
Search, Notes, Lead Status, and one external API integration
(Clearbit Logo API - fetches a company's logo from its website domain).

Run locally:
    pip install -r requirements.txt
    set the env vars below (or create a .env file)
    python app.py
"""

import os
import re
from datetime import timedelta
from functools import wraps

from dotenv import load_dotenv
load_dotenv()

import requests
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
pymysql.install_as_MySQLdb()
from flask_sqlalchemy import SQLAlchemy

# ---------------------------------------------------------------------------
# App + DB config
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["SESSION_COOKIE_SAMESITE"] = "None"   # needed when frontend is on a different domain
app.config["SESSION_COOKIE_SECURE"] = True       # cookies only over HTTPS (required for SameSite=None)
app.permanent_session_lifetime = timedelta(days=1)

DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_NAME = os.environ.get("DB_NAME", "crm_db")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_recycle": 280, "pool_pre_ping": True}

db = SQLAlchemy(app)

# Allow the frontend (hosted elsewhere) to call this API with cookies
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")
CORS(app, supports_credentials=True, origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else "*")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Lead(db.Model):
    __tablename__ = "leads"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150))
    phone = db.Column(db.String(30))
    company = db.Column(db.String(150))
    website = db.Column(db.String(150))
    logo_url = db.Column(db.String(255))
    source = db.Column(db.String(80), default="Other")
    status = db.Column(db.String(20), default="New")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "company": self.company,
            "website": self.website,
            "logo_url": self.logo_url,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Note(db.Model):
    __tablename__ = "notes"
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=False)
    note_text = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "note_text": self.note_text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


VALID_STATUSES = ["New", "Contacted", "Qualified", "Proposal", "Won", "Lost"]


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# External API integration: Clearbit Logo API
# Given a company website, fetch a logo image URL. No API key required.
# Docs: https://clearbit.com/docs#logo-api
# ---------------------------------------------------------------------------
def fetch_company_logo(website: str):
    if not website:
        return None
    domain = re.sub(r"^https?://", "", website).split("/")[0].replace("www.", "")
    if not domain or "." not in domain:
        return None
    # Google's public favicon service - no API key required, still active.
    logo_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    try:
        resp = requests.get(logo_url, timeout=4, stream=True)
        if resp.status_code == 200:
            return logo_url
    except requests.RequestException:
        pass
    return None


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    """One-time helper to create your first user. You can disable/remove this
    route after creating your account."""
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username already exists"}), 409
    user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "user created"}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid username or password"}), 401
    session.permanent = True
    session["user_id"] = user.id
    session["username"] = user.username
    return jsonify({"message": "logged in", "username": user.username})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "logged out"})


@app.route("/api/me", methods=["GET"])
def me():
    if "user_id" not in session:
        return jsonify({"authenticated": False}), 200
    return jsonify({"authenticated": True, "username": session.get("username")})


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/api/dashboard/stats", methods=["GET"])
@login_required
def dashboard_stats():
    total = Lead.query.count()
    by_status = {s: Lead.query.filter_by(status=s).count() for s in VALID_STATUSES}
    recent = Lead.query.order_by(Lead.created_at.desc()).limit(5).all()
    return jsonify({
        "total_leads": total,
        "by_status": by_status,
        "recent_leads": [l.to_dict() for l in recent],
    })


# ---------------------------------------------------------------------------
# Leads: list + search, create
# ---------------------------------------------------------------------------
@app.route("/api/leads", methods=["GET"])
@login_required
def list_leads():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    query = Lead.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Lead.name.ilike(like),
                Lead.email.ilike(like),
                Lead.company.ilike(like),
                Lead.phone.ilike(like),
            )
        )
    if status and status in VALID_STATUSES:
        query = query.filter_by(status=status)

    leads = query.order_by(Lead.created_at.desc()).all()
    return jsonify([l.to_dict() for l in leads])


@app.route("/api/leads", methods=["POST"])
@login_required
def create_lead():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    website = (data.get("website") or "").strip()
    logo_url = fetch_company_logo(website) if website else None

    lead = Lead(
        name=name,
        email=data.get("email"),
        phone=data.get("phone"),
        company=data.get("company"),
        website=website or None,
        logo_url=logo_url,
        source=data.get("source") or "Other",
        status=data.get("status") if data.get("status") in VALID_STATUSES else "New",
        created_by=session["user_id"],
    )
    db.session.add(lead)
    db.session.commit()
    return jsonify(lead.to_dict()), 201


# ---------------------------------------------------------------------------
# Leads: get / update / delete one
# ---------------------------------------------------------------------------
@app.route("/api/leads/<int:lead_id>", methods=["GET"])
@login_required
def get_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    notes = Note.query.filter_by(lead_id=lead_id).order_by(Note.created_at.desc()).all()
    result = lead.to_dict()
    result["notes"] = [n.to_dict() for n in notes]
    return jsonify(result)


@app.route("/api/leads/<int:lead_id>", methods=["PUT"])
@login_required
def update_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    data = request.get_json(force=True)

    for field in ["name", "email", "phone", "company", "source"]:
        if field in data:
            setattr(lead, field, data[field])

    if "website" in data and data["website"] != lead.website:
        lead.website = data["website"]
        lead.logo_url = fetch_company_logo(lead.website)

    if "status" in data:
        if data["status"] not in VALID_STATUSES:
            return jsonify({"error": f"status must be one of {VALID_STATUSES}"}), 400
        lead.status = data["status"]

    db.session.commit()
    return jsonify(lead.to_dict())


@app.route("/api/leads/<int:lead_id>", methods=["DELETE"])
@login_required
def delete_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    db.session.delete(lead)
    db.session.commit()
    return jsonify({"message": "deleted"})


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------
@app.route("/api/leads/<int:lead_id>/notes", methods=["POST"])
@login_required
def add_note(lead_id):
    Lead.query.get_or_404(lead_id)  # 404 if lead doesn't exist
    data = request.get_json(force=True)
    text = (data.get("note_text") or "").strip()
    if not text:
        return jsonify({"error": "note_text is required"}), 400
    note = Note(lead_id=lead_id, note_text=text, created_by=session["user_id"])
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
