from __future__ import annotations

import sqlite3
from functools import wraps

import requests
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from requests_oauthlib import OAuth2Session

from config import settings


AUTH_BASE = "https://discord.com/api/oauth2/authorize"
TOKEN_URL = "https://discord.com/api/oauth2/token"
API_BASE = "https://discord.com/api"


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def is_staff(user_roles: list[str]) -> bool:
    allowed = {role.lower() for role in settings.dmv_staff_roles + settings.admin_roles}
    return any(role.lower() in allowed for role in user_roles)


def is_admin(user_roles: list[str]) -> bool:
    allowed = {role.lower() for role in settings.admin_roles}
    return any(role.lower() in allowed for role in user_roles)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "discord_user" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = settings.web_secret_key

    @app.route("/")
    def home():
        return render_template("login.html", web_base_url=settings.web_base_url)

    @app.route("/login")
    def login():
        discord = OAuth2Session(settings.discord_client_id, redirect_uri=settings.discord_redirect_uri, scope=["identify", "guilds"])
        auth_url, state = discord.authorization_url(AUTH_BASE)
        session["oauth_state"] = state
        return redirect(auth_url)

    @app.route("/callback")
    def callback():
        discord = OAuth2Session(settings.discord_client_id, state=session.get("oauth_state"), redirect_uri=settings.discord_redirect_uri)
        token = discord.fetch_token(
            TOKEN_URL,
            client_secret=settings.discord_client_secret,
            authorization_response=request.url,
        )
        user = discord.get(f"{API_BASE}/users/@me").json()
        session["oauth_token"] = token
        session["discord_user"] = user
        session["role_names"] = settings.admin_roles + settings.dmv_staff_roles
        return redirect(url_for("dashboard"))

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("home"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        conn = db_conn()
        uid = int(session["discord_user"]["id"])
        user = conn.execute("SELECT * FROM users WHERE user_id = ?", (uid,)).fetchone()
        licenses = conn.execute("SELECT * FROM licenses WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall()
        return render_template("dashboard.html", user=user, licenses=licenses, viewer=session["discord_user"])

    @app.route("/staff")
    @login_required
    def staff():
        roles = session.get("role_names", [])
        if not is_staff(roles):
            return redirect(url_for("dashboard"))
        conn = db_conn()
        applications = conn.execute("SELECT * FROM applications ORDER BY id DESC LIMIT 20").fetchall()
        bookings = conn.execute("SELECT * FROM bookings WHERE status = 'queued' ORDER BY id ASC").fetchall()
        tickets = conn.execute("SELECT * FROM tickets WHERE status = 'open' ORDER BY id DESC").fetchall()
        return render_template("staff.html", applications=applications, bookings=bookings, tickets=tickets)

    @app.route("/admin")
    @login_required
    def admin():
        roles = session.get("role_names", [])
        if not is_admin(roles):
            return redirect(url_for("dashboard"))
        conn = db_conn()
        transactions = conn.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 25").fetchall()
        staff_stats = conn.execute("SELECT * FROM staff_stats ORDER BY actions_completed DESC LIMIT 20").fetchall()
        return render_template("admin.html", transactions=transactions, staff_stats=staff_stats)

    @app.route("/verify-license/<int:license_id>")
    def verify_license(license_id: int):
        conn = db_conn()
        lic = conn.execute("SELECT * FROM licenses WHERE id = ?", (license_id,)).fetchone()
        if not lic:
            return jsonify({"valid": False, "message": "License not found"}), 404
        return jsonify({
            "valid": lic["status"] == "active",
            "license_type": lic["license_type"],
            "issued_at": lic["issued_at"],
            "status": lic["status"],
            "user_id": lic["user_id"],
        })

    @app.route("/api/live")
    def live():
        conn = db_conn()
        payload = {
            "tracked_users": conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"],
            "active_shifts": conn.execute("SELECT COUNT(*) AS count FROM active_shifts").fetchone()["count"],
            "queued_bookings": conn.execute("SELECT COUNT(*) AS count FROM bookings WHERE status = 'queued'").fetchone()["count"],
            "open_tickets": conn.execute("SELECT COUNT(*) AS count FROM tickets WHERE status = 'open'").fetchone()["count"],
            "applications_pending": conn.execute("SELECT COUNT(*) AS count FROM applications WHERE status = 'pending'").fetchone()["count"],
        }
        return jsonify(payload)

    return app


app = create_app()
