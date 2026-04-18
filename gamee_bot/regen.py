from __future__ import annotations

from datetime import datetime, timezone


def format_next_live_countdown(next_live_at_utc: datetime | None) -> str:
    """Текст как в игре: время до следующей жизни по nextLiveAddedTimestamp."""
    if next_live_at_utc is None:
        return ""
    at = next_live_at_utc
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = at - now
    if delta.total_seconds() <= 0:
        return "+1 скоро"
    sec = int(delta.total_seconds())
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"+1 через {h}:{m:02d}:{s:02d}"
    return f"+1 через {m:02d}:{s:02d}"


def format_daily_checkin_countdown(deadline_utc: datetime | None) -> str:
    """До следующей ежедневной награды: «через 3ч 57м» (без секунд, если есть минуты)."""
    if deadline_utc is None:
        return ""
    at = deadline_utc
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = at - now
    if delta.total_seconds() <= 0:
        return ""
    sec = int(delta.total_seconds())
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"через {h}ч {m}м"
    if m > 0:
        return f"через {m}м"
    return f"через {s}с"
