from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Tuple

# WC2026 is hosted across USA/Canada/Mexico with a US-based client — US Eastern
# is the most sensible single reference for "what day is it" rather than raw
# UTC, which flips the day boundary hours before US local midnight (e.g. 8 PM
# Eastern, not midnight), causing evening matches to appear under the wrong day.
_EASTERN = ZoneInfo("America/New_York")


def get_today_bounds_et() -> Tuple[float, float]:
    """Unix timestamps for the start/end of 'today' in US Eastern Time, DST-aware."""
    now_et = datetime.now(_EASTERN)
    start = now_et.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start.timestamp(), end.timestamp()


def get_day_bounds_et(offset_days: int = 0) -> Tuple[float, float, str]:
    """Same as get_today_bounds_et but for 'today + offset_days' (ET, DST-aware),
    plus that day's date string (YYYY-MM-DD) — used to scan forward across
    several days (e.g. MLS's Top Plays carousel, which needs the next day
    that actually has games, not just today)."""
    now_et = datetime.now(_EASTERN)
    start = (now_et + timedelta(days=offset_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start.timestamp(), end.timestamp(), start.strftime("%Y-%m-%d")
