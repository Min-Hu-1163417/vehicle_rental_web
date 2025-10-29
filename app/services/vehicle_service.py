from __future__ import annotations

from typing import List, Tuple

from app.models.store import Store
from app.services.common import (
    ALLOWED_TYPES,
    PLACEHOLDER,
    ACTIVE_RENTAL_STATES,
    norm_type,
    valid_image_path,
    to_float_safe, _today, _parse_date, _lc,
)
from app.utils.constants import RentalStatus, VehicleStatus


class VehicleService:
    """Vehicle catalogue: filter, create, delete."""

    @staticmethod
    def filter_vehicles(vtype=None, brand=None, min_rate=None, max_rate=None):
        store = Store.instance()
        res = list(store.vehicles.values())  # Retrieve all vehicles from the Store singleton

        # Filter by vehicle type: exact match (normalized for consistency)
        if vtype:
            vt = norm_type(vtype)
            res = [v for v in res if norm_type(v.get("type")) == vt]

        # Filter by brand/model: case-insensitive fuzzy match
        if brand:
            kw = _lc(brand).strip()  # Convert to lowercase and trim spaces
            if kw:
                res = [
                    v for v in res
                    if (kw in _lc(v.get("brand")) or kw in _lc(v.get("model")))
                ]

        # Convert rate filters safely to float (avoid type errors)
        min_val = to_float_safe(min_rate)
        max_val = to_float_safe(max_rate)

        # Apply minimum rate filter (greater than or equal)
        if min_val is not None:
            res = [
                v for v in res
                if to_float_safe(v.get("rate", 0)) is not None and float(v.get("rate", 0)) >= min_val
            ]

        # Apply maximum rate filter (less than or equal)
        if max_val is not None:
            res = [
                v for v in res
                if to_float_safe(v.get("rate", 0)) is not None and float(v.get("rate", 0)) <= max_val
            ]

        # Return the filtered vehicle list
        return res

    @staticmethod
    def get_vehicle(vid: str):
        return Store.instance().vehicles.get(vid)

    @staticmethod
    def admin_create_vehicle(data: dict):
        """
        Minimal validation for staff add-vehicle form.
        Fallback to placeholder image when invalid path is provided.
        """
        t = (data.get("type") or "").lower().strip()
        if t not in ALLOWED_TYPES:
            return False, "Invalid vehicle type"
        img = (data.get("image_path") or "").strip()
        if not valid_image_path(img):
            img = PLACEHOLDER
        data["image_path"] = img
        Store.instance().create_vehicle(data)
        return True, "Vehicle created"

    @staticmethod
    def delete_vehicle(vehicle_id: str):
        """
        Delete only when there is NO active rental referencing the vehicle.
        Source of truth is rentals, not snapshot 'status'.
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

    @staticmethod
    def all_vehicles():
        return list(Store.instance().vehicles.values())

    @staticmethod
    def availability_calendar(vehicle_id: str):
        """
        Return a list of (start, end) strings for active rentals (rented/overdue).
        Used by the UI to disable booked date ranges.
        """
        store = Store.instance()
        ranges: List[Tuple[str, str]] = []
        for r in store.rentals.values():
            if r.get("vehicle_id") != vehicle_id:
                continue
            if r.get("status") in (RentalStatus.RENTED, RentalStatus.OVERDUE):
                ranges.append((r["start_date"], r["end_date"]))
        ranges.sort(key=lambda t: t[0])  # stable for UI
        return ranges

    @staticmethod
    def refresh_overdue_flags():
        """
        If a rental end_date < today and status is still 'rented' -> mark rental 'overdue'
        and set the vehicle to 'overdue'.
        """
        store = Store.instance()
        today = _today()

        for rental in store.rentals.values():
            if rental.get("status") == RentalStatus.RENTED:
                end = _parse_date(rental["end_date"])
                if end < today:
                    rental["status"] = RentalStatus.OVERDUE
                    vid = rental.get("vehicle_id")
                    if vid in store.vehicles:
                        store.vehicles[vid]["status"] = VehicleStatus.OVERDUE
        store.save()
