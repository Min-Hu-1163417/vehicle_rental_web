"""Jinja filters and date formatting helpers."""
from datetime import datetime, date, timezone
import pytz


def fmt_iso_local(value: str, use_12h: bool = False) -> str:
    """
    Format a date/datetime string into New Zealand local time.
    Supports:
      - 'YYYY-MM-DD'
      - 'YYYY-MM-DD HH:MM:SS'
      - 'YYYY-MM-DDTHH:MM:SS'
      - Above with 'Z' or timezone offsets like '+00:00'
    On parse error, returns the original value (so the UI never goes blank).
    """
    if value is None:
        return ""

    s = str(value).strip()
    if not s:
        return ""

    try:
        # Normalize: handle 'T' and trailing 'Z'
        s_norm = s.replace("T", " ")
        if s_norm.endswith("Z"):
            s_norm = s_norm[:-1] + "+00:00"

        dt = None
        # 1) Try Python's flexible ISO parser (handles offsets like +00:00)
        try:
            dt = datetime.fromisoformat(s_norm)
        except Exception:
            dt = None

        # 2) If still None, try explicit formats (with and without seconds)
        if dt is None:
            if ":" in s_norm:
                # With time part
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                    try:
                        dt = datetime.strptime(s_norm, fmt)
                        break
                    except Exception:
                        pass
            else:
                # Date-only
                try:
                    d = datetime.strptime(s_norm, "%Y-%m-%d").date()
                    # Return date-only format right away (no time to convert)
                    return d.strftime("%d/%m/%Y")
                except Exception:
                    pass

        if dt is None:
            # Could not parse, show original
            return s

        # If naive datetime, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Convert to Pacific/Auckland
        nz = pytz.timezone("Pacific/Auckland")
        dt_nz = dt.astimezone(nz)

        if use_12h:
            # Avoid %-I (not portable on Windows). Strip any leading zero manually.
            hh = dt_nz.strftime("%I").lstrip("0") or "0"
            return f"{dt_nz.strftime('%d %b %Y')}, {hh}:{dt_nz.strftime('%M %p')}"
        else:
            return dt_nz.strftime("%d/%m/%Y %H:%M")
    except Exception:
        # On any unexpected error, don't hide the value
        return s
