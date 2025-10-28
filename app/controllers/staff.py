from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import datetime, date
from os import abort
from typing import Dict, Iterable, List, Optional, Tuple
from urllib import request
from urllib.parse import urlparse

from flask import Blueprint, session

from ..models.store import Store
from ..utils.security import generate_hash
from flask import Blueprint, render_template
from flask import request, render_template, redirect, url_for, flash
import uuid

# ---- Flask blueprint (keep the name and URL prefix unchanged) ----
bp = Blueprint("staff", __name__, url_prefix="/staff")


def _require_staff():
    if session.get("role") != "staff":
        abort()


# ---- Constants & helpers -----------------------------------------------------

DATE_FMT = "%Y-%m-%d"

# Centralized strings to avoid typos
ROLE_INDIVIDUAL = "individual"
ROLE_CORPORATE = "corporate"
ROLE_STAFF = "staff"

RENTAL_RENTED = "rented"
RENTAL_OVERDUE = "overdue"
RENTAL_RETURNED = "returned"
RENTAL_CANCELLED = "cancelled"

VEHICLE_AVAILABLE = "available"
VEHICLE_RENTED = "rented"
VEHICLE_OVERDUE = "overdue"

ALLOWED_TYPES = {"car", "motorbike", "truck"}
PLACEHOLDER = "/static/images/placeholder.png"


@bp.get("/users")
def staff_users():
    store = Service._store()
    users = list(store.users.values())
    return render_template("staff_users.html", users=users)


@bp.get("/vehicles")
def staff_vehicles():
    """List all vehicles with optional filters."""
    vtype = request.args.get("type")
    brand = request.args.get("brand")
    min_rate = request.args.get("min_rate")
    max_rate = request.args.get("max_rate")

    vehicles = Service.filter_vehicles(vtype=vtype, brand=brand,
                                       min_rate=min_rate, max_rate=max_rate)
    return render_template("staff_vehicles.html",
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

    ok, msg = Service.admin_create_vehicle(data)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("staff.staff_vehicles"))


@bp.post("/vehicles/delete")
def staff_delete_vehicle():
    """Delete a vehicle using POST /staff/vehicles/delete with form field 'vehicle_id'."""
    vid = (request.form.get("vehicle_id") or "").strip()
    if not vid:
        flash("Missing vehicle id", "danger")
        return redirect(url_for("staff.staff_vehicles"))  # or admin.admin_vehicles
    ok, msg = Service.delete_vehicle(vid)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("staff.staff_vehicles"))


@bp.post("/users/delete")
def staff_delete_user():
    """Delete a user (staff only)."""
    renter_id = (request.form.get("renter_id") or "").strip()
    if not renter_id:
        flash("Missing user id", "danger")
        return redirect(url_for("staff.users"))

    ok, msg = Service.admin_delete_user(renter_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("staff.users"))


@bp.post("/users/add")
def staff_add_user():
    """Staff: add an individual/corporate user."""
    username = (request.form.get("username") or "").strip()
    role = (request.form.get("role") or "").strip().lower()
    password = request.form.get("password") or ""

    # Basic validations
    if not username or not role or not password:
        flash("Username, role and password are required.", "danger")
        return redirect(url_for("staff.users"))

    if role not in ("individual", "corporate"):
        flash("Role must be 'individual' or 'corporate'.", "danger")
        return redirect(url_for("staff.users"))

    ok, msg = Service.admin_create_user(username, role, password)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("staff.users"))


# @bp.post("/vehicles/add")
# def staff_add_vehicle():
#     """Create a new vehicle (staff only)."""
#     _require_staff()
#
#     brand = (request.form.get("brand") or "").strip()
#     model = (request.form.get("model") or "").strip()
#     vtype = (request.form.get("type") or "").strip().lower()
#     image = (request.form.get("image_path") or "").strip()
#
#     # rate parse & validate
#     try:
#         rate = float(request.form.get("rate") or 0)
#     except Exception:
#         flash("Rate must be a number.", "danger")
#         return redirect(url_for("staff.staff_vehicles"))
#     if rate <= 0:
#         flash("Rate must be greater than 0.", "danger")
#         return redirect(url_for("staff.staff_vehicles"))
#
#     if not brand or not model or not vtype:
#         flash("Brand, model and type are required.", "danger")
#         return redirect(url_for("staff.staff_vehicles"))
#
#     data = {
#         "vehicle_id": uuid.uuid4().hex[:8],
#         "brand": brand,
#         "model": model,
#         "type": vtype,
#         "rate": rate,
#         "status": "available",
#         "image_path": image,
#     }
#
#     ok, msg = Service.admin_create_vehicle(data)
#     flash(msg, "success" if ok else "danger")
#     return redirect(url_for("staff.staff_vehicles"))

@bp.get("/analytics")
def staff_analytics():
    """Staff dashboards: system analytics summary."""
    data = Service.analytics()
    return render_template("staff_analytics.html", data=data)


def _parse_date(s: str) -> date:
    """Parse 'YYYY-MM-DD' into a date object; raise ValueError on bad input."""
    return datetime.strptime(s, DATE_FMT).date()


def _overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    """
    Check overlap between [a_start, a_end) and [b_start, b_end).
    End date is exclusive: booking 2025-10-22 -> 2025-10-23 occupies the night of 22 only.
    Overlap rule: a_start < b_end and b_start < a_end
    """
    return a_start < b_end and b_start < a_end


def _valid_image_path(s: Optional[str]) -> bool:
    """Accept '/static/...' or absolute http(s) URLs."""
    if not s:
        return False
    s = s.strip()
    if s.startswith("/static/"):
        return True
    try:
        u = urlparse(s)
        return u.scheme in ("http", "https") and bool(u.netloc)
    except Exception:
        return False


def _norm_type(value: Optional[str]) -> str:
    """Normalize vehicle type to lowercase; return '' if None."""
    return (value or "").strip().lower()


def _today() -> date:
    """Wrapper for easier testing/mocking."""
    return date.today()


def _round2(x: float) -> float:
    return round(float(x), 2)


# ---- Service layer -----------------------------------------------------------

class Service:
    """
    Thin domain service layer around the Store (pickle-backed repository).
    All methods keep the original signatures for drop-in compatibility.
    """

    # ------------- utilities --------------

    @staticmethod
    def _store() -> Store:
        """Get the singleton store instance."""
        return Store.instance()

    @staticmethod
    def _discount_for(role: str, days: int) -> float:
        """
        Centralized discount rule:
        - corporate: 15% on all rentals
        - individual: 10% if days >= 7
        """
        if role == ROLE_CORPORATE:
            return 0.15
        if role == ROLE_INDIVIDUAL and days >= 7:
            return 0.10
        return 0.0

    # ------------- vehicle browsing -------------

    @staticmethod
    def filter_vehicles(vtype=None, brand=None, min_rate=None, max_rate=None):
        store = Service._store()
        vehicles = list(store.vehicles.values())

        if vtype:
            vt = _norm_type(vtype)
            vehicles = [v for v in vehicles if _norm_type(v.get("type")) == vt]

        if brand:
            vehicles = [v for v in vehicles if v.get("brand") == brand]

        if min_rate is not None:
            lo = float(min_rate)
            vehicles = [v for v in vehicles if float(v.get("rate", 0)) >= lo]

        if max_rate is not None:
            hi = float(max_rate)
            vehicles = [v for v in vehicles if float(v.get("rate", 0)) <= hi]

        return vehicles

    @staticmethod
    def get_vehicle(vid):
        return Service._store().vehicles.get(vid)

    @staticmethod
    def availability_calendar(vehicle_id: str):
        """
        Return a list of (start, end) strings for active rentals (rented/overdue).
        Used by the UI to disable booked date ranges.
        """
        store = Service._store()
        ranges: List[Tuple[str, str]] = []
        for r in store.rentals.values():
            if r.get("vehicle_id") != vehicle_id:
                continue
            if r.get("status") in (RENTAL_RENTED, RENTAL_OVERDUE):
                ranges.append((r["start_date"], r["end_date"]))
        ranges.sort(key=lambda t: t[0])  # stable for UI
        return ranges

    # ------------- rental core -------------

    @staticmethod
    def rent(renter_id: str, vehicle_id: str, start: str, end: str):
        """
        Validate and create a rental.
        Constraints:
          - start must be today or later
          - end must be strictly after start
          - must not overlap with existing active rentals of the same vehicle
          - compute total with discount by role and length
        """
        store = Service._store()
        user = store.get_user(renter_id)
        vehicle = store.vehicles.get(vehicle_id)

        if not user or not vehicle:
            return False, "Invalid renter or vehicle", None

        try:
            d1 = _parse_date(start)
            d2 = _parse_date(end)
        except Exception:
            return False, "Invalid dates (YYYY-MM-DD)", None

        today = _today()
        if d1 < today:
            return False, "Start date cannot be in the past", None
        if d2 <= d1:
            return False, "End must be after start", None

        # Overlap check vs. active rentals for this vehicle
        for r in store.rentals.values():
            if r.get("vehicle_id") != vehicle_id:
                continue
            if r.get("status") not in (RENTAL_RENTED, RENTAL_OVERDUE):
                continue
            s = _parse_date(r["start_date"])
            e = _parse_date(r["end_date"])
            if _overlap(d1, d2, s, e):
                return False, "Selected dates overlap with existing bookings", None

        days = (d2 - d1).days
        rate = float(vehicle.get("rate", 0))
        discount = Service._discount_for(user.get("role", ""), days)

        base = rate * days
        total = _round2(base * (1 - discount))

        rid = store.create_rental({
            "renter_id": renter_id,
            "vehicle_id": vehicle_id,
            "start_date": start,
            "end_date": end,
            "days": days,
            "rate": rate,
            "discount": discount,
            "total": total,
            "status": RENTAL_RENTED,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

        # reflect vehicle status immediately
        if vehicle_id in store.vehicles:
            store.vehicles[vehicle_id]["status"] = VEHICLE_RENTED

        store.save()
        return True, "OK", rid

    @staticmethod
    def return_vehicle(rental_id: str):
        """
        Close a rental and free the vehicle.
        Rules:
        - If today < start: treat as cancellation (no charge).
        - If start <= today <= end: charge used days (>=1), early return is allowed.
        - If today > end: record overdue_days; default charge up to end (common approach).
          (If you need to bill overdue days as well, change 'used_days' to (today - start).days.)
        Vehicle becomes 'available' after success.
        """
        store = Service._store()
        r = store.rentals.get(rental_id)
        if not r:
            return False, "Rental not found"

        status = r.get("status", "")
        if status in (RENTAL_RETURNED, RENTAL_CANCELLED):
            return False, "Rental already closed"

        start = _parse_date(r["start_date"])
        end = _parse_date(r["end_date"])
        today = _today()

        rate = float(r.get("rate", 0))
        discount = float(r.get("discount", 0.0))

        used_days = 0
        overdue_days = 0
        new_status = RENTAL_RETURNED
        total = 0.0

        if today < start:
            # Not started yet -> cancel
            new_status = RENTAL_CANCELLED
            total = 0.0
        elif today <= end:
            # Charge for used days; at least 1 day
            effective_end = today
            used_days = max(1, (effective_end - start).days)
            base = rate * used_days
            total = _round2(base * (1 - discount))
        else:
            # Overdue: record overdue_days; by default we charge only up to 'end'
            used_days = max(1, (end - start).days)
            overdue_days = (today - end).days
            base = rate * used_days
            total = _round2(base * (1 - discount))

        # Persist rental changes
        r.update({
            "returned_at": today.strftime(DATE_FMT),
            "status": new_status,
            "used_days": used_days,
            "overdue_days": overdue_days,
            "total": total,
        })

        # Free the vehicle
        vid = r.get("vehicle_id")
        if vid in store.vehicles:
            store.vehicles[vid]["status"] = VEHICLE_AVAILABLE

        store.save()
        msg = "Rental cancelled" if new_status == RENTAL_CANCELLED else "Vehicle returned"
        return True, msg

    @staticmethod
    def cancel_rental(rental_id: str, requester_id: str, is_staff: bool = False):
        """
        Cancel a rental strictly before it starts.
        Permissions:
          - the renter themself OR a staff user
        Constraints:
          - current status must be 'rented'
          - today < start_date
        Effect:
          - mark cancelled, zero out total, keep audit fields, persist to pickle
        """
        store = Service._store()
        r = store.rentals.get(rental_id)
        if not r:
            return False, "Rental not found"

        is_owner = (r.get("renter_id") == requester_id)
        if not (is_owner or is_staff):
            return False, "Not allowed to cancel this rental"

        if r.get("status") != RENTAL_RENTED:
            return False, "Only active rentals can be cancelled"

        start = _parse_date(r["start_date"])
        if not (_today() < start):
            return False, "Rental has already started, use return instead"

        r.update({
            "status": RENTAL_CANCELLED,
            "cancelled_at": _today().strftime(DATE_FMT),
            "used_days": 0,
            "overdue_days": 0,
            "total": 0.0,
        })
        store.save()
        return True, "Rental cancelled"

    @staticmethod
    def invoice(rid):
        """Return raw rental dict for invoice rendering."""
        return Service._store().rentals.get(rid)

    # ------------- admin: users & vehicles -------------

    @staticmethod
    def admin_create_user(username, role, password):
        store = Service._store()
        if role not in (ROLE_INDIVIDUAL, ROLE_CORPORATE):
            return False, "Role must be individual/corporate"
        if store.user_exists(username):
            return False, "Username exists"
        store.create_user(username, generate_hash(password), role)
        return True, "User created"

    @staticmethod
    def admin_delete_user(renter_id):
        ok = Service._store().delete_user(renter_id)
        return ok, "User deleted" if ok else "User not found"

    @staticmethod
    def all_vehicles():
        return list(Service._store().vehicles.values())

    @staticmethod
    def admin_create_vehicle(data):
        """
        Basic validation + normalization.
        Accept '/static/...' or absolute http(s) as image_path; fallback to PLACEHOLDER.
        """
        t = _norm_type(data.get("type"))
        if t not in ALLOWED_TYPES:
            return False, "Invalid vehicle type"

        img = (data.get("image_path") or "").strip()
        if not _valid_image_path(img):
            img = PLACEHOLDER  # fallback quietly (or return error if you prefer)

        data = dict(data)
        data["type"] = t
        data["image_path"] = img

        Service._store().create_vehicle(data)
        return True, "Vehicle created"

    @staticmethod
    def delete_vehicle(vehicle_id: str):
        """Delete a vehicle only if it has no active rentals."""
        store = Service._store()
        v = store.vehicles.get(vehicle_id)
        if not v:
            return False, "Vehicle not found"

        # Check active rentals (rented or overdue) instead of relying on vehicle['status']
        has_active_rental = any(
            (r.get("vehicle_id") == vehicle_id)
            and (r.get("status") in (RENTAL_RENTED, RENTAL_OVERDUE))
            for r in store.rentals.values()
        )
        if has_active_rental:
            return False, "Vehicle is currently rented or overdue"

        # Optional: normalize status just for reference (not enforced)
        status = (v.get("status") or "").strip().lower()
        if status and status not in (VEHICLE_AVAILABLE,):
            # Only a soft check; not blocking deletion
            pass

        del store.vehicles[vehicle_id]
        store.save()
        return True, "Vehicle deleted"

    # ------------- analytics & dashboards -------------

    @staticmethod
    def analytics_summary():
        store = Service._store()
        veh_counts: Dict[str, int] = Counter(r.get("vehicle_id") for r in store.rentals.values())
        revenue = _round2(sum(float(r.get("total") or 0.0) for r in store.rentals.values()))
        top = sorted(veh_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        bottom = sorted(veh_counts.items(), key=lambda x: x[1])[:5]
        return {
            "total_vehicles": len(store.vehicles),
            "total_users": len(store.users),
            "total_rentals": len(store.rentals),
            "revenue": revenue,
            "most_rented": top,
            "least_rented": bottom,
        }

    @staticmethod
    def rentals_for_user(renter_id: str):
        """
        Compose user's rentals joined with vehicle label fields.
        Sorted by start_date desc (string ISO works as lexicographic).
        """
        store = Service._store()
        out: List[Dict] = []
        for r in store.rentals.values():
            if r.get("renter_id") != renter_id:
                continue
            v = store.vehicles.get(r.get("vehicle_id"), {})
            out.append({
                "rental_id": r.get("rental_id"),
                "vehicle_id": r.get("vehicle_id"),
                "brand": v.get("brand", ""),
                "model": v.get("model", ""),
                "type": v.get("type", ""),
                "start_date": r.get("start_date"),
                "end_date": r.get("end_date"),
                "days": r.get("days"),
                "rate": r.get("rate"),
                "discount": r.get("discount"),
                "total": r.get("total"),
                "status": r.get("status", RENTAL_RENTED),
            })
        out.sort(key=lambda x: x.get("start_date") or "", reverse=True)
        return out

    @staticmethod
    def analytics():
        """
        Provide rich analytics for staff dashboards:
          - totals
          - rentals per vehicle (top-down)
          - revenue by start_date
          - users by role
        """
        store = Service._store()

        # Totals
        totals_users = len(store.users)
        totals_vehicles = len(store.vehicles)
        totals_rentals = len(store.rentals)
        totals_revenue = _round2(sum((float(r.get("total") or 0.0)) for r in store.rentals.values()))

        # Rentals per vehicle
        cnt = Counter(r.get("vehicle_id") for r in store.rentals.values())
        rentals_by_vehicle = []
        for vid, v in store.vehicles.items():
            label = f"{v.get('brand', '')} {v.get('model', '')}".strip() or vid[:6]
            rentals_by_vehicle.append({
                "vehicle_id": vid,
                "label": label,
                "count": cnt.get(vid, 0),
            })
        rentals_by_vehicle.sort(key=lambda x: x["count"], reverse=True)

        # Revenue by date (grouped by rental start_date)
        rev_by_date: Dict[str, float] = defaultdict(float)
        for r in store.rentals.values():
            d = r.get("start_date")
            if d:
                rev_by_date[d] += float(r.get("total") or 0.0)
        revenue_by_date = [{"date": k, "total": _round2(v)} for k, v in sorted(rev_by_date.items())]

        # Users by role
        role_cnt = Counter(u.get("role", "") for u in store.users.values())
        users_by_role = [{"role": k or "unknown", "count": v} for k, v in role_cnt.items()]

        return {
            "totals": {
                "users": totals_users,
                "vehicles": totals_vehicles,
                "rentals": totals_rentals,
                "revenue": totals_revenue,
            },
            "rentals_by_vehicle": rentals_by_vehicle,
            "revenue_by_date": revenue_by_date,
            "users_by_role": users_by_role,
        }

    # ------------- background reconciliation -------------

    @staticmethod
    def refresh_overdue_flags():
        """
        If a rental end_date < today and status is still 'rented' -> mark rental 'overdue'
        and set the vehicle to 'overdue'.
        """
        store = Service._store()
        today = _today()

        for rental in store.rentals.values():
            if rental.get("status") == RENTAL_RENTED:
                end = _parse_date(rental["end_date"])
                if end < today:
                    rental["status"] = RENTAL_OVERDUE
                    vid = rental.get("vehicle_id")
                    if vid in store.vehicles:
                        store.vehicles[vid]["status"] = VEHICLE_OVERDUE
        store.save()

    @staticmethod
    def reconcile_vehicle_statuses():
        """
        Re-derive vehicle status from rentals (idempotent):
        - initialize all vehicles to 'available'
        - if any rental is 'overdue' -> vehicle 'overdue'
        - else if a rental is 'rented' and today within [start, end) -> vehicle 'rented'
        """
        store = Service._store()
        today = _today()

        # Initialize
        for v in store.vehicles.values():
            v["status"] = VEHICLE_AVAILABLE

        # Derive from rentals
        for r in store.rentals.values():
            vid = r.get("vehicle_id")
            if vid not in store.vehicles:
                continue
            status = r.get("status")

            if status == RENTAL_OVERDUE:
                store.vehicles[vid]["status"] = VEHICLE_OVERDUE
            elif status == RENTAL_RENTED:
                start = _parse_date(r["start_date"])
                end = _parse_date(r["end_date"])
                if start <= today < end:
                    # only upgrade to 'rented' if it's not already 'overdue'
                    if store.vehicles[vid]["status"] != VEHICLE_OVERDUE:
                        store.vehicles[vid]["status"] = VEHICLE_RENTED

        store.save()
