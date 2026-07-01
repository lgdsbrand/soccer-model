from datetime import datetime
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
