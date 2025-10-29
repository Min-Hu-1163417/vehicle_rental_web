from __future__ import annotations

from datetime import date, datetime

from app.models.store import Store
from app.services.common import (
    DATE_FMT,
    ACTIVE_RENTAL_STATES,
    parse_date,
    overlap,
    user_from_dict,
    vehicle_from_dict,
)


class RentalService:
    """
    Rent, return, cancel, and invoice operations.
    Uses polymorphic pricing (VehicleBase.price_for_days + UserBase.discount_for).
    """

    @staticmethod
    def rent(renter_id: str, vehicle_id: str, start: str, end: str):
        store = Store.instance()

        user_dict = store.get_user(renter_id)
        veh_dict = store.vehicles.get(vehicle_id)
        if not user_dict or not veh_dict:
            return False, "Invalid renter or vehicle", None

        # Validate dates
        try:
            d1 = parse_date(start)
            d2 = parse_date(end)
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
            s = parse_date(r["start_date"])
            e = parse_date(r["end_date"])
            if overlap(d1, d2, s, e):
                return False, "Selected dates overlap with existing bookings", None

        # Pricing via models
        user_obj = user_from_dict(user_dict)
        veh_obj = vehicle_from_dict(veh_dict)
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
            "rate": float(veh_dict.get("rate", 0)),  # keep listed rate for UI
            "discount": discount,
            "total": total,
            "status": "rented",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

        # Update vehicle snapshot (best-effort)
        if vehicle_id in store.vehicles:
            store.vehicles[vehicle_id]["status"] = "rented"

        store.save()
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
