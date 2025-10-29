from __future__ import annotations

from app.models.store import Store
from app.services.common import (
    ALLOWED_TYPES,
    PLACEHOLDER,
    ACTIVE_RENTAL_STATES,
    norm_type,
    valid_image_path,
    to_float_safe,
)


class VehicleService:
    """Vehicle catalogue: filter, create, delete."""

    @staticmethod
    def filter_vehicles(vtype=None, brand=None, min_rate=None, max_rate=None):
        store = Store.instance()
        res = list(store.vehicles.values())

        if vtype:
            vt = norm_type(vtype)
            res = [v for v in res if norm_type(v.get("type")) == vt]

        if brand:
            res = [v for v in res if v.get("brand") == brand]

        min_val = to_float_safe(min_rate)
        max_val = to_float_safe(max_rate)

        if min_val is not None:
            res = [v for v in res if to_float_safe(v.get("rate", 0)) is not None and float(v.get("rate", 0)) >= min_val]
        if max_val is not None:
            res = [v for v in res if to_float_safe(v.get("rate", 0)) is not None and float(v.get("rate", 0)) <= max_val]

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
