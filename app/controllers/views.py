from datetime import date

from flask import Blueprint, render_template, session, redirect, url_for

from ..services.user_service import UserService
from ..services.vehicle_service import VehicleService
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
        return render_template("auth/login.html")


@bp.get("/dashboard/individual")
@login_required
@role_required("individual")
def individual_dashboard():
    VehicleService.refresh_overdue_flags()

    uid = session.get("uid")
    if not uid:
        return redirect(url_for("auth.login"))
    rentals = UserService.rentals_for_user(uid)

    return render_template("dashboards/dash_individual.html", rentals=rentals,
                           current_date=date.today().strftime("%Y-%m-%d"))


@bp.get("/dashboard/corporate")
@login_required
@role_required("corporate")
def corporate_dashboard():
    VehicleService.refresh_overdue_flags()

    uid = session.get("uid")
    if not uid:
        return redirect(url_for("auth.login"))
    rentals = UserService.rentals_for_user(uid)

    return render_template("dashboards/dash_corporate.html", rentals=rentals,
                           current_date=date.today().strftime("%Y-%m-%d"))


@bp.get("/dashboard/staff")
@login_required
@role_required("staff")
def staff_dashboard():
    VehicleService.refresh_overdue_flags()

    return render_template("dashboards/dash_staff.html")
