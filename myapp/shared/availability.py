"""Build calendar-day availability payloads for shared resources."""

from dataclasses import dataclass
from datetime import date, time, timedelta

from shared.time_slots import DEFAULT_MIN_GAP, compute_free_slots


DAY_STATUS_FREE = "free"
DAY_STATUS_PARTIAL = "partial"
DAY_STATUS_FULL = "full"
DAY_STATUS_PAST = "past"


@dataclass(frozen=True)
class FreeSlot:
    start_time: time
    end_time: time


@dataclass(frozen=True)
class AvailabilityBooking:
    id: int
    start_time: time | None
    end_time: time | None
    status: str
    unit: dict | None
    reservation_user: dict | None


@dataclass(frozen=True)
class DayAvailability:
    date: date
    status: str
    bookings: list[AvailabilityBooking]
    free_slots: list[FreeSlot]


@dataclass(frozen=True)
class AvailabilityRange:
    from_date: date
    to_date: date
    min_gap_minutes: int
    days: list[DayAvailability]


def unit_label(unit) -> dict | None:
    if unit is None:
        return None
    return {
        "id": unit.id,
        "display_name": unit.display_name(),
    }


def user_label(user) -> dict | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "username": getattr(user, "username", "") or "",
        "full_name": getattr(user, "full_name", "") or "",
    }


def booking_payload(instance, *, status: str) -> AvailabilityBooking:
    return AvailabilityBooking(
        id=instance.id,
        start_time=instance.start_time,
        end_time=instance.end_time,
        status=status,
        unit=unit_label(getattr(instance, "unit", None)),
        reservation_user=user_label(
            getattr(instance, "reservation_user", None)
        ),
    )


def day_status(
    day: date,
    *,
    blocking_count: int,
    free_slots: list[FreeSlot],
    today: date,
) -> str:
    if day < today:
        return DAY_STATUS_PAST
    if blocking_count == 0:
        return DAY_STATUS_FREE
    if free_slots:
        return DAY_STATUS_PARTIAL
    return DAY_STATUS_FULL


def build_availability_range(
    *,
    from_date: date,
    to_date: date,
    blocking_by_date: dict[date, list],
    today: date | None = None,
    min_gap: timedelta = DEFAULT_MIN_GAP,
) -> AvailabilityRange:
    """Assemble one entry per day in ``[from_date, to_date]``.

    Pending and approved reservations both occupy slots. Rejected
    reservations are not included.
    """
    today = today or date.today()
    days: list[DayAvailability] = []
    current = from_date
    while current <= to_date:
        blocking = blocking_by_date.get(current, [])
        free = [
            FreeSlot(start_time=start, end_time=end)
            for start, end in compute_free_slots(
                [(b.start_time, b.end_time) for b in blocking],
                min_gap=min_gap,
            )
        ]
        bookings = [
            booking_payload(b, status=b.status) for b in blocking
        ]
        bookings.sort(
            key=lambda b: (b.start_time or time(0, 0), b.id)
        )
        days.append(
            DayAvailability(
                date=current,
                status=day_status(
                    current,
                    blocking_count=len(blocking),
                    free_slots=free,
                    today=today,
                ),
                bookings=bookings,
                free_slots=free,
            )
        )
        current += timedelta(days=1)

    return AvailabilityRange(
        from_date=from_date,
        to_date=to_date,
        min_gap_minutes=int(min_gap.total_seconds() // 60),
        days=days,
    )
