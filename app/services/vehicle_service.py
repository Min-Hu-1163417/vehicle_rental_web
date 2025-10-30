from __future__ import annotations
from typing import List, Tuple, Optional, TYPE_CHECKING, Any
from app.services.common import norm_type, to_float_safe, _today, _parse_date, _lc, _store
from app.utils.constants import VehicleStatus, RentalStatus

if TYPE_CHECKING:
    # Only for type hints; won't execute at runtime
    from app.models.store import Store  # noqa: F401


class VehicleService:
    """Vehicle catalogue: filter, create, delete."""

    # tests can inject: VehicleService.store = fake_store
    store: Any = None

    @staticmethod
    def _get_store():
        """
        Prefer injected store (for tests). Otherwise try common import paths.
        Includes app.models.store (most likely correct in your project).
        """
        if VehicleService.store is not None:
            return VehicleService.store

        # Lazy import with robust fallbacks
        StoreCls = None
        # A) the most likely layout in your project
        try:
            from app.models.store import Store as _Store  # type: ignore
            StoreCls = _Store
        except ModuleNotFoundError:
            pass

        # B) fallback: app.store
        if StoreCls is None:
            try:
                from app.store import Store as _Store  # type: ignore
                StoreCls = _Store
            except ModuleNotFoundError:
                pass

        # C) fallback: relative to services/ (..models.store)
        if StoreCls is None:
            try:
                from ..models.store import Store as _Store  # type: ignore
                StoreCls = _Store
            except Exception:
                pass

        # D) flat fallback: store.py at sys.path root
        if StoreCls is None:
            from store import Store as _Store  # type: ignore
            StoreCls = _Store

        return StoreCls.instance()

    @staticmethod
    def filter_vehicles(vtype=None, brand=None, min_rate=None, max_rate=None, *, store=None):
        """
        Filter vehicles by type, brand/model, and price range.
        - If `store` is provided, use it (for tests).
        - Otherwise call app.services.common._store() (tests monkeypatch this).
        """
        # 1. Resolve data source
        st = store or _store()
        res = list(getattr(st, "vehicles", {}).values())

        # 2. Type filter
        if vtype:
            vt = norm_type(vtype)
            res = [v for v in res if norm_type(v.get("type")) == vt]

        # 3. Brand/model filter (case-insensitive, partial match)
        if brand:
            kw = _lc(brand).strip()
            if kw:
                def match(v):
                    b = _lc(v.get("brand") or "")
                    m = _lc(v.get("model") or "")
                    return (kw in b) or (kw in m)

                res = [v for v in res if match(v)]

        # 4. Price range filter (invalid min/max ignored)
        min_val = to_float_safe(min_rate)
        max_val = to_float_safe(max_rate)
        if (min_val is not None) and (max_val is not None) and (min_val > max_val):
            min_val, max_val = max_val, min_val

        if (min_val is not None) or (max_val is not None):
            def within(v):
                r = to_float_safe(v.get("rate"))
                if r is None:
                    return False
                if (min_val is not None) and (r < min_val):
                    return False
                if (max_val is not None) and (r > max_val):
                    return False
                return True

            res = [v for v in res if within(v)]

        return res

    @staticmethod
    def get_vehicle(vid: str):
        """Return a vehicle dict by ID or raise VehicleNotFoundError."""
        store = VehicleService._get_store()
        v = store.vehicles.get(vid)
        if v is None:
            raise VehicleNotFoundError(f"Error: vehicle with ID '{vid}' not found")
        return v

    @staticmethod
    def admin_create_vehicle(payload: dict, store: Optional["Store"] = None):
        """
        Create a vehicle record into the given store (for testing)
        or the active store by default.
        """
        st = store or VehicleService._get_store()  # use fake_store if provided

        brand = (payload.get("brand") or "").strip()
        model = (payload.get("model") or "").strip()
        vtype = (payload.get("type") or "").lower().strip()
        rate = float(payload.get("rate") or 0)

        if not brand or not model or vtype not in ("car", "motorbike", "truck"):
            return False, "Invalid vehicle data", None

        vid = st.create_vehicle({
            "brand": brand,
            "model": model,
            "type": vtype,
            "rate": rate,
            "status": "available",
            "image_path": payload.get("image_path") or "/static/images/placeholder.png",
        })

        return True, "Vehicle created", vid

    @staticmethod
    def delete_vehicle(vehicle_id: str, store: Optional["Store"] = None):
        """
        Delete a vehicle if and only if:
        - the vehicle exists,
        - the vehicle itself is not in an active state (rented/overdue),
        - there are no active rentals referencing this vehicle.
        The persistence layer's `save()` is optional (no-op if missing).
        """
        st = store or VehicleService._get_store()

        veh = getattr(st, "vehicles", {}).get(vehicle_id)
        if not veh:
            return False, "Vehicle not found"

        # Guard 1: vehicle status must not be active
        active_vehicle_states = {"rented", "overdue"}
        if (veh.get("status") or "").lower() in active_vehicle_states:
            return False, f"Cannot delete while {veh.get('status')}"

        # Guard 2: no active rentals referencing this vehicle
        # Adjust the set if your project defines ACTIVE_RENTAL_STATES elsewhere.
        active_rental_states = {"rented", "overdue"}
        rentals = getattr(st, "rentals", {}) or {}
        for r in rentals.values():
            if r.get("vehicle_id") == vehicle_id and (r.get("status") or "").lower() in active_rental_states:
                return False, "Cannot delete: active rentals exist"

        # Perform deletion
        del st.vehicles[vehicle_id]

        # Optional save: do nothing if the store has no save()
        save = getattr(st, "save", None)
        if callable(save):
            save()

        return True, "Vehicle deleted"

    @staticmethod
    def all_vehicles():
        return list(VehicleService._get_store().vehicles.values())

    @staticmethod
    def availability_calendar(vehicle_id: str):
        """
        Return a list of (start, end) strings for active rentals (rented/overdue).
        Used by the UI to disable booked date ranges.
        """
        store = VehicleService._get_store()
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
        store = VehicleService._get_store()
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
