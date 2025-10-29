from __future__ import annotations

from app.models.store import Store
from app.utils.security import generate_hash


class UserService:
    """User admin operations (create/delete) and per-user rentals view."""

    @staticmethod
    def admin_create_user(username: str, role: str, password: str):
        store = Store.instance()
        role = (role or "").lower().strip()
        if role not in ("individual", "corporate", "staff"):
            return False, "Role must be individual/corporate/staff"
        if store.user_exists(username):
            return False, "Username exists"
        store.create_user(username, generate_hash(password), role)
        return True, "User created"

    @staticmethod
    def admin_delete_user(renter_id: str):
        ok = Store.instance().delete_user(renter_id)
        return ok, "User deleted" if ok else "User not found"

    @staticmethod
    def rentals_for_user(renter_id: str):
        """Return this user's rentals with vehicle info attached."""
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
                "created_at": r.get("created_at"),
            })
        out.sort(key=lambda x: x.get("start_date") or "", reverse=True)
        return out
