"""Tiny helpers for day time intervals.

Used by ``bbq_reservations`` and ``hall_reservations`` to detect
overlapping or too-close bookings on the same day. The conventions are:

- ``start_time`` missing  → 00:00:00 (beginning of the day).
- ``end_time``   missing  → 23:59:59 (end of the day).
- Same-type bookings must not overlap and must leave a minimum gap
  (default 30 minutes) between one ending and the next starting.
"""

from datetime import datetime, time, timedelta


DAY_START = time(0, 0, 0)
DAY_END = time(23, 59, 59)
DEFAULT_MIN_GAP = timedelta(minutes=30)


def normalize_slot(
    start: time | None, end: time | None
) -> tuple[time, time]:
    return (start or DAY_START, end or DAY_END)


def _as_datetime(value: time) -> datetime:
    # Date is arbitrary — we only compare times within the same day.
    return datetime.combine(datetime.min.date(), value)


def slots_overlap(
    a_start: time | None,
    a_end: time | None,
    b_start: time | None,
    b_end: time | None,
) -> bool:
    a_s, a_e = normalize_slot(a_start, a_end)
    b_s, b_e = normalize_slot(b_start, b_end)
    return a_s < b_e and b_s < a_e


def slots_gap(
    a_start: time | None,
    a_end: time | None,
    b_start: time | None,
    b_end: time | None,
) -> timedelta | None:
    """Gap between two non-overlapping slots, or ``None`` if they overlap."""
    a_s, a_e = normalize_slot(a_start, a_end)
    b_s, b_e = normalize_slot(b_start, b_end)
    if a_s < b_e and b_s < a_e:
        return None
    if a_e <= b_s:
        return _as_datetime(b_s) - _as_datetime(a_e)
    return _as_datetime(a_s) - _as_datetime(b_e)


def slots_too_close(
    a_start: time | None,
    a_end: time | None,
    b_start: time | None,
    b_end: time | None,
    *,
    min_gap: timedelta = DEFAULT_MIN_GAP,
) -> bool:
    """True when slots do not overlap but the gap between them is < ``min_gap``."""
    gap = slots_gap(a_start, a_end, b_start, b_end)
    if gap is None:
        return False
    return gap < min_gap


def _to_time(value: datetime) -> time:
    return value.time().replace(microsecond=0)


def compute_free_slots(
    bookings: list[tuple[time | None, time | None]],
    *,
    min_gap: timedelta = DEFAULT_MIN_GAP,
) -> list[tuple[time, time]]:
    """Return free intervals for a day, respecting ``min_gap`` around bookings.

    A booking ``[start, end]`` blocks free time until ``end + min_gap`` and
    free time before it must end by ``start - min_gap``.
    """
    occupied: list[tuple[time, time]] = [
        normalize_slot(start, end) for start, end in bookings
    ]
    occupied.sort(key=lambda slot: slot[0])

    merged: list[tuple[time, time]] = []
    for start, end in occupied:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        prev_start, prev_end = merged[-1]
        merged[-1] = (prev_start, max(prev_end, end))

    free: list[tuple[time, time]] = []
    cursor_dt = _as_datetime(DAY_START)
    day_end_dt = _as_datetime(DAY_END)

    for start, end in merged:
        free_end_dt = _as_datetime(start) - min_gap
        if free_end_dt > cursor_dt:
            free.append((_to_time(cursor_dt), _to_time(free_end_dt)))
        next_cursor = _as_datetime(end) + min_gap
        if next_cursor > cursor_dt:
            cursor_dt = next_cursor

    if cursor_dt < day_end_dt:
        free.append((_to_time(cursor_dt), DAY_END))
    elif cursor_dt == day_end_dt and (not free or free[-1][1] != DAY_END):
        # Exactly at end-of-day with no remaining room — nothing to add.
        pass

    return [(s, e) for s, e in free if s < e]
