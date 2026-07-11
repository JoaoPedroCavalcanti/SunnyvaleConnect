"""Unit tests for free-slot math."""

from datetime import time, timedelta

import pytest

from shared.time_slots import compute_free_slots


pytestmark = pytest.mark.unit


def test_empty_day_is_fully_free():
    free = compute_free_slots([])
    assert free == [(time(0, 0), time(23, 59, 59))]


def test_booking_carves_gap_on_both_sides():
    free = compute_free_slots([(time(12, 0), time(18, 0))])
    assert free == [
        (time(0, 0), time(11, 30)),
        (time(18, 30), time(23, 59, 59)),
    ]


def test_adjacent_bookings_collapse_gap_between():
    free = compute_free_slots(
        [
            (time(10, 0), time(12, 0)),
            (time(12, 30), time(14, 0)),
        ]
    )
    # 12:00 + 30min = 12:30, so no free slot between them.
    assert free == [
        (time(0, 0), time(9, 30)),
        (time(14, 30), time(23, 59, 59)),
    ]


def test_custom_min_gap():
    free = compute_free_slots(
        [(time(12, 0), time(13, 0))],
        min_gap=timedelta(minutes=15),
    )
    assert free == [
        (time(0, 0), time(11, 45)),
        (time(13, 15), time(23, 59, 59)),
    ]
