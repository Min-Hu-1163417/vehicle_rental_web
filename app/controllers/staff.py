from __future__ import annotations

import uuid
from urllib import request

from flask import Blueprint
from flask import request, render_template, redirect, url_for, flash

from ..services.analytics_service import AnalyticsService
from ..services.common import _store
from ..services.user_service import UserService
from ..services.vehicle_service import VehicleService

bp = Blueprint("staff", __name__, url_prefix="/staff")


@bp.get("/users")
def staff_users():
    store = _store()
    users = list(store.users.values())
    return render_template("users/staff_users.html", users=users)


@bp.get("/vehicles")
def staff_vehicles():
    """List all vehicles with optional filters."""
    vtype = request.args.get("type")
    brand = request.args.get("brand")
    min_rate = request.args.get("min_rate")
    max_rate = request.args.get("max_rate")

    vehicles = VehicleService.filter_vehicles(vtype=vtype, brand=brand,
                                              min_rate=min_rate, max_rate=max_rate)
    return render_template("vehicles/staff_vehicles.html",
                           vehicles=vehicles,
                           vtype=vtype, brand=brand,
                           min_rate=min_rate, max_rate=max_rate)


@bp.post("/vehicles/add")
def staff_add_vehicle():
    """Add a new vehicle (staff only)."""
    data = {
        "vehicle_id": str(uuid.uuid4())[:8],
        "brand": request.form.get("brand", "").strip(),
        "model": request.form.get("model", "").strip(),
        "type": request.form.get("type", "").lower().strip(),
        "rate": float(request.form.get("rate") or 0),
        "status": "available",
        "image_path": request.form.get("image_path", "").strip(),
    }

    ok, msg = VehicleService.admin_create_vehicle(data)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("staff.staff_vehicles"))


@bp.post("/vehicles/delete")
def staff_delete_vehicle():
    """Delete a vehicle using POST /staff/vehicles/delete with form field 'vehicle_id'."""
    vid = (request.form.get("vehicle_id") or "").strip()
    if not vid:
        flash("Missing vehicle id", "danger")
        return redirect(url_for("staff.staff_vehicles"))  # or admin.admin_vehicles
    ok, msg = VehicleService.delete_vehicle(vid)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("staff.staff_vehicles"))


@bp.post("/users/delete")
def staff_delete_user():
    """Delete a user (staff only)."""
    renter_id = (request.form.get("renter_id") or "").strip()
    if not renter_id:
        flash("Missing user id", "danger")
        return redirect(url_for("staff.staff_users"))

    ok, msg = UserService.admin_delete_user(renter_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("staff.staff_users"))


@bp.post("/users/add")
def staff_add_user():
    """Staff: add an individual/corporate user."""
    username = (request.form.get("username") or "").strip()
    role = (request.form.get("role") or "").strip().lower()
    password = request.form.get("password") or ""

    # Basic validations
    if not username or not role or not password:
        flash("Username, role and password are required.", "danger")
        return redirect(url_for("staff.staff_users"))

    if role not in ("individual", "corporate"):
        flash("Role must be 'individual' or 'corporate'.", "danger")
        return redirect(url_for("staff.staff_users"))

    ok, msg = UserService.admin_create_user(username, role, password)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("staff.staff_users"))


@bp.get("/analytics")
def staff_analytics():
    """Staff dashboards: system analytics summary."""
    data = AnalyticsService.analytics()
    return render_template("users/staff_analytics.html", data=data)
