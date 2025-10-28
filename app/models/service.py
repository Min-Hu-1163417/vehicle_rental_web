from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, date
from urllib.parse import urlparse
from typing import Optional

from .store import Store
from .user import UserBase, IndividualUser, CorporateUser, StaffUser
from .vehicle import VehicleBase, Car, Motorbike, Truck
from ..utils.security import generate_hash

DATE_FMT = "%Y-%m-%d"
ALLOWED_TYPES = {"car", "motorbike", "truck"}
PLACEHOLDER = "/static/images/placeholder.png"
ACTIVE_RENTAL_STATES = {"rented", "overdue"}


# ------------------------- helpers -------------------------
def _parse_date(s: str) -> date:
    """Parse YYYY-MM-DD into a date object; raise ValueError on bad input."""
    return datetime.strptime(s, DATE_FMT).date()


def _overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    """
    Check overlap between [a_start, a_end) and [b_start, b_end).
    End date is exclusive: booking 2025-10-22 -> 2025-10-23 occupies the night of 22 only.
    Overlap rule: a_start < b_end and b_start < a_end
    """
    return a_start < b_end and b_start < a_end


def _valid_image_path(s: Optional[str]) -> bool:
    """Accept /static/... or an absolute http(s) URL."""
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
    """Normalize vehicle type to lowercase string; return '' for None."""
    return (value or "").strip().lower()


def _to_float_safe(value: Optional[str | float | int]) -> Optional[float]:
    """Safely convert to float, returning None on invalid input."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


# ----------------- rich object mappers (dict -> model) -----------------
def _user_from_dict(d: Optional[dict]) -> Optional[UserBase]:
    """Map a stored user dict to a rich user object."""
    if not d:
        return None
    role = (d.get("role") or "").lower()
    base = dict(
        user_id=d.get("user_id") or d.get("id"),
        username=d.get("username"),
        role=role,
    )
    if role == "corporate":
        return CorporateUser(**base)
    if role == "staff":
        return StaffUser(**base)
    # default to individual
    return IndividualUser(**base)


def _vehicle_from_dict(d: Optional[dict]) -> Optional[VehicleBase]:
    """Map a stored vehicle dict to a rich vehicle object."""
    if not d:
        return None
    vtype = (d.get("type") or "").lower()
    base = dict(
        vehicle_id=d.get("vehicle_id") or d.get("id"),
        brand=d.get("brand"),
        model=d.get("model"),
        type=vtype,
        rate=float(d.get("rate") or 0.0),
    )
    if vtype == "motorbike":
        return Motorbike(**base)
    if vtype == "truck":
        return Truck(**base)
    return Car(**base)


# ============================ Service ============================
class Service:
    """
    Thin application service that:
    - Validates inputs
    - Translates Store dicts into model objects
    - Delegates pricing/discount logic to model classes
    - Persists back to Store
    """

    # --------------- Queries ---------------
    @staticmethod
    def filter_vehicles(vtype=None, brand=None, min_rate=None, max_rate=None):
        store = Store.instance()
        res = list(store.vehicles.values())

        if vtype:
            vt = _norm_type(vtype)
            res = [v for v in res if _norm_type(v.get("type")) == vt]

        if brand:
            res = [v for v in res if v.get("brand") == brand]

        min_val = _to_float_safe(min_rate)
        max_val = _to_float_safe(max_rate)

        if min_val is not None:
            res = [v for v in res if
                   _to_float_safe(v.get("rate", 0)) is not None and float(v.get("rate", 0)) >= min_val]
        if max_val is not None:
            res = [v for v in res if
                   _to_float_safe(v.get("rate", 0)) is not None and float(v.get("rate", 0)) <= max_val]

        return res

    @staticmethod
    def get_vehicle(vid):
        return Store.instance().vehicles.get(vid)

    @staticmethod
    def availability_calendar(vehicle_id: str):
        """
        Return a list of (start, end) strings for current active rentals (rented/overdue).
        Used by UI to disable booked dates.
        """
        store = Store.instance()
        ranges = []
        for r in store.rentals.values():
            if r.get("vehicle_id") != vehicle_id:
                continue
            if (r.get("status") or "") in ACTIVE_RENTAL_STATES:
                ranges.append((r["start_date"], r["end_date"]))
        ranges.sort(key=lambda t: t[0])
        return ranges

    # --------------- Commands ---------------
    @staticmethod
    def rent(renter_id: str, vehicle_id: str, start: str, end: str):
        """
        Validate and create a rental using polymorphic pricing:
        - Vehicle subclass decides the pre-discount base price
        - User subclass decides the discount ratio
        """
        store = Store.instance()

        user_dict = store.get_user(renter_id)
        veh_dict = store.vehicles.get(vehicle_id)
        if not user_dict or not veh_dict:
            return False, "Invalid renter or vehicle", None

        try:
            d1 = _parse_date(start)
            d2 = _parse_date(end)
        except Exception:
            return False, "Invalid dates (YYYY-MM-DD)", None

        today = date.today()
        if d1 < today:
            return False, "Start date cannot be in the past", None
        if d2 <= d1:
            return False, "End must be after start", None

        # Overlap check against active rentals of the same vehicle
        for r in store.rentals.values():
            if r.get("vehicle_id") != vehicle_id:
                continue
            if (r.get("status") or "") not in ACTIVE_RENTAL_STATES:
                continue
            s = _parse_date(r["start_date"])
            e = _parse_date(r["end_date"])
            if _overlap(d1, d2, s, e):
                return False, "Selected dates overlap with existing bookings", None

        # Pricing via model classes
        user_obj = _user_from_dict(user_dict)
        veh_obj = _vehicle_from_dict(veh_dict)
        if not user_obj or not veh_obj:
            return False, "Failed to construct models", None

        days = (d2 - d1).days
        base = veh_obj.price_for_days(days)
        discount = user_obj.discount_for(days)
        total = round(base * (1 - discount), 2)

        rid = store.create_rental({
            "renter_id": renter_id,
            "vehicle_id": vehicle_id,
            "start_date": start,
            "end_date": end,
            "days": days,
            "rate": float(veh_dict.get("rate", 0)),  # keep listed per-day rate for UI
            "discount": discount,
            "total": total,
            "status": "rented",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

        # Update vehicle snapshot status (best-effort)
        if vehicle_id in store.vehicles:
            store.vehicles[vehicle_id]["status"] = "rented"

        store.save()
        return True, "OK", rid

    @staticmethod
    def return_vehicle(rental_id: str):
        """
        Close a rental and free the vehicle.
        - If today < start: treat as cancellation (no charge)
        - If start <= today <= end: charge used days (>=1)
        - If today > end: mark overdue_days; default charge only until end
        """
        store = Store.instance()
        r = store.rentals.get(rental_id)
        if not r:
            return False, "Rental not found"

        if (r.get("status") or "") in ("returned", "cancelled"):
            return False, "Rental already closed"

        start = _parse_date(r["start_date"])
        end = _parse_date(r["end_date"])
        today = date.today()

        rate = float(r.get("rate", 0))
        discount = float(r.get("discount", 0))
        used_days = 0
        overdue_days = 0
        total = 0.0
        new_status = "returned"

        if today < start:
            # Not started yet -> cancel
            new_status = "cancelled"
            used_days = 0
            overdue_days = 0
            total = 0.0
        else:
            if today <= end:
                effective_end = today
                used_days = max(1, (effective_end - start).days)
                base = rate * used_days
                total = round(base * (1 - discount), 2)
            else:
                used_days = max(1, (end - start).days)
                overdue_days = (today - end).days
                base = rate * used_days
                total = round(base * (1 - discount), 2)

        r.update({
            "returned_at": today.strftime(DATE_FMT),
            "status": new_status,
            "used_days": used_days,
            "overdue_days": overdue_days,
            "total": total,
        })

        vid = r.get("vehicle_id")
        if vid in store.vehicles:
            store.vehicles[vid]["status"] = "available"

        store.save()
        msg = "Rental cancelled" if new_status == "cancelled" else "Vehicle returned"
        return True, msg

    @staticmethod
    def cancel_rental(rental_id: str, requester_id: str, is_staff: bool = False):
        """
        Cancel a rental before it starts.
        Rules:
        - Only the renter themself or a staff member can cancel.
        - Only rentals with status 'rented' are cancellable.
        - Must be strictly before start_date (today < start_date).
        - No fee by default (set total=0 and mark status='cancelled').
        """
        store = Store.instance()
        r = store.rentals.get(rental_id)
        if not r:
            return False, "Rental not found"

        if (r.get("renter_id") != requester_id) and (not is_staff):
            return False, "Not allowed to cancel this rental"

        if r.get("status") != "rented":
            return False, "Only active rentals can be cancelled"

        start = _parse_date(r["start_date"])
        today = date.today()
        if not (today < start):
            return False, "Rental has already started, use return instead"

        r.update({
            "status": "cancelled",
            "cancelled_at": today.strftime(DATE_FMT),
            "used_days": 0,
            "overdue_days": 0,
            "total": 0.0,
        })
        store.save()
        return True, "Rental cancelled"

    @staticmethod
    def invoice(rid):
        return Store.instance().rentals.get(rid)

    # --------------- Admin ---------------
    @staticmethod
    def admin_create_user(username, role, password):
        store = Store.instance()
        role = (role or "").lower().strip()
        if role not in ("individual", "corporate", "staff"):
            return False, "Role must be individual/corporate/staff"
        if store.user_exists(username):
            return False, "Username exists"
        store.create_user(username, generate_hash(password), role)
        return True, "User created"

    @staticmethod
    def admin_delete_user(renter_id):
        ok = Store.instance().delete_user(renter_id)
        return ok, "User deleted" if ok else "User not found"

    @staticmethod
    def all_vehicles():
        return list(Store.instance().vehicles.values())

    @staticmethod
    def admin_create_vehicle(data):
        """
        Minimal validation when creating vehicles via staff UI.
        Fallback to a placeholder image if a valid path/URL is not provided.
        """
        t = (data.get("type") or "").lower().strip()
        if t not in ALLOWED_TYPES:
            return False, "Invalid vehicle type"
        img = (data.get("image_path") or "").strip()
        if not _valid_image_path(img):
            img = PLACEHOLDER
        data["image_path"] = img
        Store.instance().create_vehicle(data)
        return True, "Vehicle created"

    @staticmethod
    def delete_vehicle(vehicle_id: str):
        """
        Delete a vehicle if it has no active rentals.
        We check rentals as the single source of truth instead of trusting the
        vehicle's snapshot 'status'.
        """
        store = Store.instance()
        v = store.vehicles.get(vehicle_id)
        if not v:
            return False, "Vehicle not found"

        has_active = any(
            (r.get("vehicle_id") == vehicle_id) and ((r.get("status") or "") in ACTIVE_RENTAL_STATES)
            for r in store.rentals.values()
        )
        if has_active:
            return False, "Vehicle is currently rented/overdue"

        del store.vehicles[vehicle_id]
        store.save()
        return True, "Vehicle deleted"

    # --------------- Analytics / Dashboards ---------------
    @staticmethod
    def analytics_summary():
        store = Store.instance()
        veh_counts: dict[str, int] = {}
        revenue = 0.0
        for r in store.rentals.values():
            veh_counts[r["vehicle_id"]] = veh_counts.get(r["vehicle_id"], 0) + 1
            revenue += float(r.get("total", 0))
        top = sorted(veh_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        bottom = sorted(veh_counts.items(), key=lambda x: x[1])[:5]
        return {
            "total_vehicles": len(store.vehicles),
            "total_users": len(store.users),
            "total_rentals": len(store.rentals),
            "revenue": round(revenue, 2),
            "most_rented": top,
            "least_rented": bottom,
        }

    @staticmethod
    def rentals_for_user(renter_id: str):
        """
        Return this user's rentals with vehicle info attached.
        """
        store = Store.instance()
        out = []
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
                "status": r.get("status", "rented"),
                "overdue_days": r.get("overdue_days"),
            })
        out.sort(key=lambda x: x.get("start_date") or "", reverse=True)
        return out

    @staticmethod
    def analytics():
        store = Store.instance()

        # Totals
        total_users = len(store.users)
        total_vehicles = len(store.vehicles)
        total_rentals = len(store.rentals)
        revenue = round(sum((r.get("total") or 0) for r in store.rentals.values()), 2)

        # Rentals per vehicle
        cnt = Counter([r.get("vehicle_id") for r in store.rentals.values()])
        rentals_by_vehicle = []
        for vid, v in store.vehicles.items():
            label = f"{v.get('brand', '')} {v.get('model', '')}".strip()
            rentals_by_vehicle.append({
                "vehicle_id": vid,
                "label": label or vid[:6],
                "count": cnt.get(vid, 0),
            })
        rentals_by_vehicle.sort(key=lambda x: x["count"], reverse=True)

        # Revenue by date (group by rental start_date)
        rev_by_date = defaultdict(float)
        for r in store.rentals.values():
            d = r.get("start_date")
            if not d:
                continue
            rev_by_date[d] += float(r.get("total") or 0)
        revenue_by_date = [{"date": k, "total": round(v, 2)} for k, v in sorted(rev_by_date.items())]

        # Users by role (quick donut)
        role_cnt = Counter([u.get("role", "") for u in store.users.values()])
        users_by_role = [{"role": k or "unknown", "count": v} for k, v in role_cnt.items()]

        return {
            "totals": {
                "users": total_users,
                "vehicles": total_vehicles,
                "rentals": total_rentals,
                "revenue": revenue,
            },
            "rentals_by_vehicle": rentals_by_vehicle,
            "revenue_by_date": revenue_by_date,
            "users_by_role": users_by_role,
        }

    @staticmethod
    def refresh_overdue_flags():
        """
        If rental end < today and still 'rented' -> mark rental 'overdue'
        and mark the vehicle 'overdue'.
        """
        store = Store.instance()
        today = date.today()

        for rid, rental in store.rentals.items():
            if rental.get("status") == "rented":
                end = _parse_date(rental["end_date"])
                if end < today:
                    rental["status"] = "overdue"
                    vid = rental.get("vehicle_id")
                    if vid in store.vehicles:
                        store.vehicles[vid]["status"] = "overdue"
        store.save()

    @staticmethod
    def reconcile_vehicle_statuses():
        """
        Rebuild vehicle snapshot statuses from rentals.
        Overdue has higher priority than rented; otherwise available.
        """
        store = Store.instance()
        today = date.today()

        # Start from 'available'
        for v in store.vehicles.values():
            v["status"] = "available"

        for r in store.rentals.values():
            vid = r.get("vehicle_id")
            if vid not in store.vehicles:
                continue

            status = (r.get("status") or "").lower()
            if status == "overdue":
                store.vehicles[vid]["status"] = "overdue"
                continue

            if status == "rented":
                start = _parse_date(r["start_date"])
                end = _parse_date(r["end_date"])
                if start <= today < end:
                    if store.vehicles[vid]["status"] != "overdue":
                        store.vehicles[vid]["status"] = "rented"

        store.save()
