from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..exceptions import VehicleNotFoundError, RentalNotFoundError

from ..models.store import Store
from ..utils.security import generate_hash, check_hash

bp = Blueprint("auth", __name__, url_prefix="/")


@bp.get("register")
def register_form():
    return render_template("auth/register.html")


@bp.post("register")
def register_submit():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "individual")
    if not username or not password or role not in ("corporate", "individual"):
        flash("Invalid input")
        return redirect(url_for("auth.register_form"))
    store = Store.instance()
    if store.user_exists(username):
        flash("Username already exists")
        return redirect(url_for("auth.register_form"))
    store.create_user(username=username, password_hash=generate_hash(password), role=role)
    flash("Registration successful. Please login.")
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
