"""Tiny helpers for half-open day time intervals.

Used by ``bbq_reservations`` and ``hall_reservations`` to detect
multiple bookings overlapping on the same day. The conventions are:

- ``start_time`` missing  → 00:00:00 (beginning of the day).
- ``end_time``   missing  → 23:59:59 (end of the day).
- Adjacent intervals (one ends exactly when the next starts) are
  considered NON-overlapping.
"""

from datetime import time


DAY_START = time(0, 0, 0)
DAY_END = time(23, 59, 59)


def normalize_slot(
    start: time | None, end: time | None
) -> tuple[time, time]:
    return (start or DAY_START, end or DAY_END)


def slots_overlap(
    a_start: time | None,
    a_end: time | None,
    b_start: time | None,
    b_end: time | None,
) -> bool:
    a_s, a_e = normalize_slot(a_start, a_end)
    b_s, b_e = normalize_slot(b_start, b_end)
    return a_s < b_e and b_s < a_e
