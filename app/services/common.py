"""Shared service helpers and factories."""

from datetime import datetime, date
from typing import Optional
from urllib.parse import urlparse

from app.models.store import Store
from app.models.user import UserBase, IndividualUser, CorporateUser, StaffUser
from app.models.vehicle import VehicleBase, Car, Motorbike, Truck

DATE_FMT = "%Y-%m-%d"
ALLOWED_TYPES = {"car", "motorbike", "truck"}
PLACEHOLDER = "/static/images/placeholder.png"
ACTIVE_RENTAL_STATES = {"rented", "overdue"}


def _store() -> Store:
    """Get the singleton store instance."""
    return Store.instance()


def _parse_date(s: str) -> date:
    """Parse 'YYYY-MM-DD' into a date object; raise ValueError on bad input."""
    return datetime.strptime(s, DATE_FMT).date()


# -------- date & math helpers --------
def parse_date(s: str) -> date:
    """Parse YYYY-MM-DD string to date."""
    return datetime.strptime(s, DATE_FMT).date()


def _today() -> date:
    """Wrapper for easier testing/mocking."""
    return date.today()


def round2(x: float) -> float:
    return round(float(x), 2)


def norm_type(value: Optional[str]) -> str:
    """Normalize vehicle type to lowercase; return '' if None."""
    return (value or "").strip().lower()


def overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    """
    Check overlap between [a_start, a_end) and [b_start, b_end).
    End date is exclusive: booking 2025-10-22 -> 2025-10-23 occupies the night of 22 only.
    Overlap rule: a_start < b_end and b_start < a_end
    """
    return a_start < b_end and b_start < a_end


def to_float_safe(value) -> Optional[float]:
    """Safely convert to float; return None if invalid."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# -------- validators / normalizers --------
def valid_image_path(s: Optional[str]) -> bool:
    """Accept /static/... or absolute http(s) URL."""
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


def norm_type(value: Optional[str]) -> str:
    """Normalize vehicle type to lowercase string; return '' for None."""
    return (value or "").strip().lower()


def _lc(s):
    """Safe lowercase for case-insensitive compare."""
    return (s or "").lower()


# -------- dict -> rich model mappers --------
def user_from_dict(d: Optional[dict]) -> Optional[UserBase]:
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
    return IndividualUser(**base)


def vehicle_from_dict(d: Optional[dict]) -> Optional[VehicleBase]:
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
