# app/utils/constants.py

"""
Global constants for roles, statuses, and allowed types.
These constants are imported by both models and services.
"""

# Date format (used for rental start/end)
DATE_FMT = "%Y-%m-%d"


class Role:
    INDIVIDUAL = "individual"
    CORPORATE = "corporate"
    STAFF = "staff"


class RentalStatus:
    RENTED = "rented"
    OVERDUE = "overdue"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class VehicleStatus:
    AVAILABLE = "available"
    RENTED = "rented"
    OVERDUE = "overdue"


# --- Misc ---
ALLOWED_TYPES = {"car", "motorbike", "truck"}
PLACEHOLDER = "/static/images/placeholder.png"
