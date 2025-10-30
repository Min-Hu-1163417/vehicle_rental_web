"""Rental-related service layer utilities."""

from datetime import date, datetime, timezone
from typing import Optional

from app.models.store import Store
from app.services.common import (
    DATE_FMT,
    ACTIVE_RENTAL_STATES,
    parse_date,
    overlap,
    user_from_dict,
    vehicle_from_dict,
)


def _as_date(x):
    """Coerce any date-like to a naive date (supports 'YYYY-MM-DD' or ISO with T)."""
    if isinstance(x, date) and not isinstance(x, datetime):
        return x
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, str):
        base = x.split("T", 1)[0].strip()
        return date.fromisoformat(base)
    raise ValueError(f"Unsupported date: {x!r}")


class RentalService:
    """
    Rent, return, cancel, and invoice operations.
    Uses polymorphic pricing (VehicleBase.price_for_days + UserBase.discount_for).
    """

    @staticmethod
    def rent(
            renter_id: str,
            vehicle_id: str,
            start: str,
            end: str,
            store: Optional["Store"] = None,
    ):
        """
        Create a rental if there is no active overlap for the same vehicle.
        Pricing includes role-based discounts:
          - corporate: flat 15% off
          - individual: 10% off when rental days >= 7
          - others: no discount

        Returns:
            (ok: bool, message: str, rental_id: Optional[str])
        """

        # --- resolve backing store (prefer injected store in tests) ---
        if store is not None:
            st = store
        else:
            # Try common accessor used by tests; fallback to singleton
            try:
                from app.services.common import _store as _common_store
                st = _common_store()
            except Exception:
                st = Store.instance()

        # --- vehicle lookup (support int/str keys) ---
        vid_raw = vehicle_id
        vid_str = str(vehicle_id)
        veh = st.vehicles.get(vid_raw) or st.vehicles.get(vid_str)
        if not veh:
            return False, "Invalid vehicle", None

        # --- parse & validate new interval (as pure dates; end is exclusive) ---
        try:
            d1 = _as_date(start)  # must return datetime.date
            d2 = _as_date(end)
        except Exception:
            return False, "Invalid dates (YYYY-MM-DD)", None

        if d1 < date.today():
            return False, "Start date cannot be in the past", None
        if d2 <= d1:
            return False, "End date must be after start date", None

        # --- resolve active rental states (fallback if constant missing) ---
        try:
            active_states = set(ACTIVE_RENTAL_STATES)  # e.g., {"rented", "overdue"}
        except Exception:
            active_states = {"rented", "overdue"}

        # --- conflict check on half-open intervals [d1, d2) ---
        for r in (st.rentals or {}).values():
            rv = r.get("vehicle_id")
            if not (rv == vid_raw or str(rv) == vid_str):
                continue
            status_lc = str(r.get("status") or "").lower()
            if status_lc not in {s.lower() for s in active_states}:
                continue

            # Support both start_date/end_date and start/end field names
            s_raw = r.get("start_date") or r.get("start")
            e_raw = r.get("end_date") or r.get("end")
            if not s_raw or not e_raw:
                # Skip malformed records to avoid false positives
                continue

            try:
                s = _as_date(s_raw)
                e = _as_date(e_raw)
            except Exception:
                # Skip malformed records
                continue

            # Overlap for half-open ranges: [d1, d2) intersects [s, e) iff (d1 < e) and (s < d2)
            if (d1 < e) and (s < d2):
                # print("DEBUG-OVERLAP:", {"new": [d1, d2], "old": [s, e], "status": r.get("status")})
                return False, "Date conflict with existing rental", None

        # --- pricing with role-based discount ---
        days = (d2 - d1).days
        try:
            rate = float(veh.get("rate", 0) or 0)
        except Exception:
            rate = 0.0

        # Look up renter to decide discount rules
        renter = st.users.get(renter_id) or st.users.get(str(renter_id)) or {}
        role = str(renter.get("role") or "").lower().strip()

        # Discount policy:
        # - corporate: flat 15% off
        # - individual: 10% off if rental is >= 7 days
        # - others (staff/unknown): no discount unless you define one
        discount_ratio = 0.0
        if role == "corporate":
            discount_ratio = 0.15
        elif role == "individual" and days >= 7:
            discount_ratio = 0.10

        base_total = rate * days
        total = round(base_total * (1.0 - discount_ratio), 2)

        # --- persist ---
        rid = st.create_rental({
            "renter_id": str(renter_id),
            "vehicle_id": vid_str,  # normalize to string ID
            "start_date": d1.isoformat(),
            "end_date": d2.isoformat(),
            "days": days,
            "rate": rate,
            "discount": discount_ratio,  # store discount ratio (e.g., 0.15)
            "total": total,  # final price after discount
            "status": "rented",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })

        # --- snapshot vehicle status ---
        if vid_str in st.vehicles:
            st.vehicles[vid_str]["status"] = "rented"
        elif vid_raw in st.vehicles:
            st.vehicles[vid_raw]["status"] = "rented"

        # --- optional save (fake stores in tests may not define save()) ---
        save_fn = getattr(st, "save", None)
        if callable(save_fn):
            save_fn()

        return True, "OK", rid

    @staticmethod
    def return_vehicle(rental_id: str):
        """
        Close a rental and free the vehicle.
        - today < start  -> cancel (no charge)
        - start <= today <= end -> charge used days (>=1)
        - today > end -> mark overdue_days; default charge only until end
        """
        store = Store.instance()
        r = store.rentals.get(rental_id)
        if not r:
            return False, "Rental not found"

        if (r.get("status") or "") in ("returned", "cancelled"):
            return False, "Rental already closed"

        start = parse_date(r["start_date"])
        end = parse_date(r["end_date"])
        today = date.today()

        rate = float(r.get("rate", 0))
        discount = float(r.get("discount", 0))
        used_days = 0
        overdue_days = 0
        total = 0.0
        new_status = "returned"

        if today < start:
            new_status = "cancelled"
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
        - Only owner or staff can cancel
        - Only 'rented' status
        - Must be today < start
        """
        store = Store.instance()
        r = store.rentals.get(rental_id)
        if not r:
            return False, "Rental not found"

        if (r.get("renter_id") != requester_id) and (not is_staff):
            return False, "Not allowed to cancel this rental"

        if r.get("status") != "rented":
            return False, "Only active rentals can be cancelled"

        start = parse_date(r["start_date"])
        if not (date.today() < start):
            return False, "Rental has already started, use return instead"

        r.update({
            "status": "cancelled",
            "cancelled_at": date.today().strftime(DATE_FMT),
            "used_days": 0,
            "overdue_days": 0,
            "total": 0.0,
        })
        store.save()
        return True, "Rental cancelled"

    @staticmethod
    def invoice(rid: str):
        return Store.instance().rentals.get(rid)
