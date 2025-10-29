"""Jinja filters and date formatting helpers."""
from datetime import datetime

import pytz


def fmt_iso_local(value: str, use_12h=False):
    """
    Convert ISO or 'YYYY-MM-DD HH:MM:SS' string to NZ local time display.
    - If value is empty or invalid, return empty string.
    - use_12h=True → e.g. '29 Oct 2025, 4:24 PM'
      use_12h=False → e.g. '29/10/2025 16:24'
    """
    if not value:
        return ""

    try:
        value = value.replace("T", " ")
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

        # Convert to New Zealand time (Pacific/Auckland)
        nz = pytz.timezone("Pacific/Auckland")
        dt = pytz.utc.localize(dt).astimezone(nz) if dt.tzinfo is None else dt.astimezone(nz)

        if use_12h:
            return dt.strftime("%d %b %Y, %-I:%M %p")  # 29 Oct 2025, 4:24 PM
        else:
            return dt.strftime("%d/%m/%Y %H:%M")  # 29/10/2025 16:24
    except Exception:
        return value
