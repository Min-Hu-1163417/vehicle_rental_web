from datetime import date

from flask import Blueprint, render_template, session, redirect, url_for

from ..models.service import Service
from ..utils.decorators import login_required, role_required

bp = Blueprint("views", __name__)


@bp.get("/")
@login_required
def home():
    role = session.get("role")
    if role == "staff":
        return redirect("/dashboard/staff")
    elif role == "corporate":
        return redirect("/dashboard/corporate")
    elif role == "individual":
        return redirect("/dashboard/individual")
    else:
        return render_template("login.html")


@bp.get("/dashboard/individual")
@login_required
@role_required("individual")
def individual_dashboard():
    Service.refresh_overdue_flags()

    uid = session.get("uid")
    if not uid:
        return redirect(url_for("auth.login"))
    rentals = Service.rentals_for_user(uid)

    return render_template("dashboard/dash_individual.html", rentals=rentals, current_date=date.today().strftime("%Y-%m-%d"))


@bp.get("/dashboard/corporate")
@login_required
@role_required("corporate")
def corporate_dashboard():
    Service.refresh_overdue_flags()

    return render_template("dashboard/dash_corporate.html")


@bp.get("/dashboard/staff")
@login_required
@role_required("staff")
def staff_dashboard():
    Service.refresh_overdue_flags()

    return render_template("dashboard/dash_staff.html")
