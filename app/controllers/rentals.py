from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..exceptions import VehicleNotFoundError, RentalNotFoundError

from ..services.rental_service import RentalService
from ..services.vehicle_service import VehicleService
from ..utils.decorators import login_required
from app.services.common import Store  # <-- make sure this import path is correct

bp = Blueprint("rentals", __name__, url_prefix="/")


@bp.get("/vehicles")
@login_required
def list_vehicles():
    """Vehicles list with filters. Strip empty query params and redirect to a clean URL."""
    q = {k: (v or "").strip() for k, v in request.args.items()}
    nonempty = {k: v for k, v in q.items() if v}

    # If URL has only empty params, redirect to /vehicles without ?brand=&type=...
    if request.args and not nonempty:
        return redirect(url_for("rentals.list_vehicles"))

    vehicles = VehicleService.filter_vehicles(
        vtype=nonempty.get("type"),
        brand=nonempty.get("brand"),
        min_rate=nonempty.get("min"),
        max_rate=nonempty.get("max"),
    )
    return render_template("vehicles/vehicles.html", vehicles=vehicles)


@bp.get("/vehicles/<vid>")
@login_required
def vehicle_detail(vid):
    """
    Vehicle detail page.
    - Staff users see all booked periods plus who rented them.
    - Non-staff users see only their own bookings.
    """
    # 1) Load the vehicle
    v = VehicleService.get_vehicle(vid)
    if not v:
        flash("Vehicle not found", "danger")
        return redirect(url_for("rentals.list_vehicles"))

    # 2) Who is the current user?
    is_staff = session.get("role") == "staff"
    me_id = session.get("renter_id") or session.get("user_id")

    # 3) Access the shared store
    store = Store.instance()

    # 4) Collect rentals for this vehicle (adjust statuses if needed)
    rentals = []
    for r in store.rentals.values():
        if r.get("vehicle_id") != vid:
            continue
        if r.get("status") not in ("rented", "reserved", "overdue", "returned"):
            continue
        rentals.append(r)

    # 5) Enrich with renter username
    calendar = []
    for r in sorted(rentals, key=lambda x: (x.get("start_date") or "")):
        rid = r.get("renter_id")
        rname = r.get("renter_username")
        if not rname and rid in store.users:
            rname = store.users[rid].get("username")

        item = {
            "start": (r.get("start_date") or "")[:10],
            "end": (r.get("end_date") or "")[:10],
            "renter_id": rid,
            "renter_username": rname,
        }

        # Staff see all; non-staff see only their own
        if is_staff or (me_id and rid == me_id):
            calendar.append(item)

    # 6) Fallback to service calendar if nothing enriched (keeps JS blocking working)
    if not calendar:
        simple = VehicleService.availability_calendar(vid) or []
        calendar = [{"start": s[:10], "end": e[:10], "renter_id": None, "renter_username": None}
                    for (s, e) in simple]

    return render_template("vehicles/vehicle_detail.html", v=v, calendar=calendar)


@bp.post("/rent")
@login_required
def rent_vehicle():
    """Create a rental for current user if dates are valid and non-overlapping."""
    form = request.form
    ok, msg, rid = RentalService.rent(
        renter_id=session.get("uid"),
        vehicle_id=form.get("vehicle_id"),
        start=form.get("start_date"),
        end=form.get("end_date"),
    )
    if not ok:
        flash(msg)
        return redirect(url_for("rentals.vehicle_detail", vid=form.get("vehicle_id")))
    flash("Rental created")
    return redirect(url_for("rentals.invoice", rid=rid))


@bp.post("/cancel")
@login_required
def cancel_rental():
    """Cancel a rental before it starts. Only renter or staff can do this."""
    rid = request.form.get("rental_id")
    uid = session.get("uid")
    role = session.get("role")
    is_staff = (role == "staff")

    ok, msg = RentalService.cancel_rental(rid, requester_id=uid, is_staff=is_staff)
    flash(msg)

    return redirect(url_for("rentals.list_vehicles"))


@bp.get("/invoice/<rid>")
@login_required
def invoice(rid):
    """Show invoice for a rental id."""
    inv = RentalService.invoice(rid)
    if not inv:
        flash("Invoice not found")
        return redirect(url_for("rentals.list_vehicles"))
    return render_template("users/invoice.html", inv=inv)


@bp.post("/return")
@login_required
def return_submit():
    """Handle vehicle return from dashboards form."""
    rid = (request.form.get("rental_id") or "").strip()
    if not rid:
        flash("Missing rental id", "danger")
        # Return to the corresponding dashboard of the current user
        role = session.get("role")
        dest = {
            "staff": "views.staff_dashboard",
            "corporate": "views.corporate_dashboard",
            "individual": "views.individual_dashboard",
        }.get(role, "views.individual_dashboard")
        return redirect(url_for(dest))

    ok, msg = RentalService.return_vehicle(rid)
    flash(msg, "success" if ok else "danger")

    # Return to the corresponding dashboard of the current user
    role = session.get("role")
    dest = {
        "staff": "views.staff_dashboard",
        "corporate": "views.corporate_dashboard",
        "individual": "views.individual_dashboard",
    }.get(role, "views.individual_dashboard")
    return redirect(url_for(dest))
