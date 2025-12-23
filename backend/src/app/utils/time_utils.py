from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def to_ist(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def format_header_time(dt: datetime) -> str:
    """Format header time according to rules:
    - < 1 minute: "just now"
    - < 1 hour: "X min ago"
    - < 6 hours: "X hour(s) ago"
    - >= 6 hours and same day: "HH:MM AM/PM IST"
    - different day: "DD Mon YYYY"
    """
    now = datetime.now(timezone.utc).astimezone(IST)
    dt_ist = to_ist(dt)
    delta = now - dt_ist
    secs = delta.total_seconds()

    if secs < 60:
        return "just now"
    if secs < 3600:
        mins = int(secs // 60)
        return f"{mins} min ago"
    if secs < 3600 * 6:
        hours = int(secs // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"

    # After 6 hours: if same day, show time; else show date
    if dt_ist.date() == now.date():
        return dt_ist.strftime("%I:%M %p IST")
    return dt_ist.strftime("%d %b %Y")


def format_relative_time(dt: datetime) -> str:
    """More general relative formatter for read_by timestamps (e.g., '5 min ago' or time)"""
    return format_header_time(dt)