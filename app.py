import os
import re
import secrets
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
from flask import (Flask, abort, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash

from db import get_db, close_db

load_dotenv()  # read .env into os.environ

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
app.teardown_appcontext(close_db)  # close the connection at the end of every request

FIELDS = ["full_name", "phone", "organisation", "host_name", "purpose"]
PHONE_RE = re.compile(r"\+?[0-9]{9,15}")


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- CSRF protection ----------

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(32)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token  # usable as {{ csrf_token() }} in templates


@app.before_request
def verify_csrf():
    if request.method == "POST":
        expected = session.get("csrf")
        sent = request.form.get("csrf", "")
        if not expected or not secrets.compare_digest(expected, sent):
            abort(400, "Invalid form submission. Go back and try again.")


# ---------- Login check ----------

def login_required(view):
    """Decorator: send anyone who is not logged in to the login page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ---------- Routes ----------

@app.route("/health")
@login_required
def health():
    with get_db().cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM visits")
        return f"Database OK, {cur.fetchone()['n']} visits"


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        with get_db().cursor() as cur:
            cur.execute("SELECT id, name, password_hash FROM users WHERE email = %s", (email,))
            user = cur.fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()  # start a fresh session on login
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("index"))
        error = "Email or password is incorrect."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    start_of_today = datetime.now().strftime("%Y-%m-%d 00:00:00")
    with get_db().cursor() as cur:
        cur.execute(
            "SELECT * FROM visits WHERE time_in >= %s ORDER BY time_in DESC",
            (start_of_today,),
        )
        visits = cur.fetchall()
    inside = sum(1 for v in visits if v["time_out"] is None)
    return render_template("index.html", visits=visits, inside=inside)


@app.route("/checkin", methods=["GET", "POST"])
@login_required
def checkin():
    errors = {}
    old = {field: "" for field in FIELDS}

    if request.method == "POST":
        old = {field: request.form.get(field, "").strip() for field in FIELDS}

        if not old["full_name"]:
            errors["full_name"] = "Full name is required."
        elif len(old["full_name"]) > 150:
            errors["full_name"] = "Full name must be 150 characters or fewer."
        if not PHONE_RE.fullmatch(old["phone"]):
            errors["phone"] = "Enter a valid phone number, e.g. 0772123456 or +256772123456."
        if not old["host_name"]:
            errors["host_name"] = "Who is the visitor here to see?"
        if not old["purpose"]:
            errors["purpose"] = "Purpose of visit is required."

        if not errors:
            db = get_db()
            with db.cursor() as cur:
                cur.execute(
                    """INSERT INTO visits
                       (full_name, phone, organisation, host_name, purpose, time_in, recorded_by)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (old["full_name"], old["phone"], old["organisation"] or None,
                     old["host_name"], old["purpose"], now(), session["user_id"]),
                )
            db.commit()
            flash(f"{old['full_name']} checked in.")
            return redirect(url_for("index"))

    return render_template("checkin.html", old=old, errors=errors)


@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    visit_id = request.form.get("id", type=int, default=0)
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "UPDATE visits SET time_out = %s WHERE id = %s AND time_out IS NULL",
            (now(), visit_id),
        )
        changed = cur.rowcount
    db.commit()
    flash("Visitor checked out." if changed else "That visitor was already checked out.")
    return redirect(url_for("index"))


@app.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    date_from = request.args.get("from", "")
    date_to = request.args.get("to", "")

    where, params, errors = [], [], []

    if q:
        where.append("(full_name LIKE %s OR phone LIKE %s)")
        params += [f"%{q}%", f"%{q}%"]

    for label, value, time_part, op in (("From", date_from, "00:00:00", ">="),
                                        ("To", date_to, "23:59:59", "<=")):
        if not value:
            continue
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            errors.append(f"{label} date is not a valid date.")
            continue
        where.append(f"time_in {op} %s")
        params.append(f"{value} {time_part}")

    sql = "SELECT * FROM visits"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY time_in DESC LIMIT 100"

    with get_db().cursor() as cur:
        cur.execute(sql, params)
        results = cur.fetchall()

    return render_template("search.html", results=results, q=q,
                           date_from=date_from, date_to=date_to, errors=errors)