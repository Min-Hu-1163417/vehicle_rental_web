from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..exceptions import VehicleNotFoundError, RentalNotFoundError

from ..models.store import Store
from ..utils.security import generate_hash, check_hash
import re

bp = Blueprint("auth", __name__, url_prefix="/")

# Compile once at module import
PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{6,}$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,10}$")  # tweak as needed


@bp.get("register")
def register_form():
    return render_template("auth/register.html")


@bp.post("/register")
def register_submit():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    role = request.form.get("role") or "individual"

    # Basic input validation
    if not username or not password:
        flash("Username and password are required.", "danger")
        return redirect(url_for("auth.register_form"))

    if role not in ("corporate", "individual"):
        flash("Invalid role.", "danger")
        return redirect(url_for("auth.register_form"))

    # Username policy
    if not USERNAME_PATTERN.match(username):
        flash("Username must be 3–30 chars (letters, digits, ., _, -).", "danger")
        return redirect(url_for("auth.register_form"))

    # Password policy (server-side enforcement)
    if not PASSWORD_PATTERN.match(password):
        flash("Password must have at least 6 characters, including A-Z, a-z, and 0-9.", "danger")
        return redirect(url_for("auth.register_form"))

    # Extra guard: disallow password equal to username
    if password.lower() == username.lower():
        flash("Password cannot be the same as username.", "danger")
        return redirect(url_for("auth.register_form"))

    store = Store.instance()
    if store.user_exists(username):
        flash("Username already exists.", "warning")
        return redirect(url_for("auth.register_form"))

    store.create_user(username=username, password_hash=generate_hash(password), role=role)
    flash("Registration successful. Please login.", "success")
    return redirect(url_for("auth.login_form"))


@bp.get("login")
def login_form():
    return render_template("auth/login.html")


@bp.post("login")
def login_submit():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    store = Store.instance()
    user = store.find_user(username)

    if not user or not check_hash(password, user["password_hash"]):
        flash("Invalid credentials")
        return redirect(url_for("auth.login_form"))

    session["user_id"] = user["renter_id"]
    session["_user_id"] = user["renter_id"]
    session["uid"] = user["renter_id"]
    session["role"] = user["role"]
    session["username"] = user["username"]

    dest = {
        "staff": "views.staff_dashboard",
        "corporate": "views.corporate_dashboard",
        "individual": "views.individual_dashboard",
    }.get(user["role"], "views.individual_dashboard")

    try:
        return redirect(url_for(dest))
    except Exception:
        return redirect(url_for("home"))


@bp.get("logout")
def logout():
    session.clear()
    flash("Logged out")
    return redirect(url_for("auth.login_form"))
