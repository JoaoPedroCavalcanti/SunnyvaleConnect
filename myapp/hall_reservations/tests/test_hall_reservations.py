from datetime import date, timedelta

from django.urls import reverse, NoReverseMatch
from model_bakery import baker

from hall_reservations.models import HallReservationModel
from tests_base.base_tests_user import BaseTestsUsers


def _list_url() -> str:
    try:
        return reverse("hall_reservation-router-list")
    except NoReverseMatch:
        return "/hall/"


LIST_URL = _list_url()


class HallReservationAuthTests(BaseTestsUsers):
    def test_anonymous_cannot_list(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 401)


class HallReservationCreateTests(BaseTestsUsers):
    def setUp(self):
        super().setUp()
        self.future_date = (date.today() + timedelta(days=10)).isoformat()

    def test_regular_user_creates_for_self(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL, data={"reservation_date": self.future_date}
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["reservation_user"], self.user_a.id)

    def test_regular_user_cannot_pass_reservation_user(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "reservation_date": self.future_date,
                "reservation_user": self.user_b.id,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_must_pass_reservation_user(self):
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL, data={"reservation_date": self.future_date}
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_creates_for_other_user(self):
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL,
            data={
                "reservation_date": self.future_date,
                "reservation_user": self.user_a.id,
            },
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_cannot_book_past_date(self):
        self.authenticate(self.user_a)
        past = (date.today() - timedelta(days=1)).isoformat()
        response = self.client.post(LIST_URL, data={"reservation_date": past})
        self.assertEqual(response.status_code, 400)

    def test_cannot_book_same_date_twice(self):
        baker.make(
            HallReservationModel,
            reservation_user=self.user_b,
            reservation_date=date.today() + timedelta(days=15),
        )
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "reservation_date": (
                    date.today() + timedelta(days=15)
                ).isoformat()
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_book_within_30_days_of_last(self):
        last = date.today() + timedelta(days=5)
        baker.make(
            HallReservationModel,
            reservation_user=self.user_a,
            reservation_date=last,
        )
        self.authenticate(self.user_a)
        too_soon = (last + timedelta(days=10)).isoformat()
        response = self.client.post(LIST_URL, data={"reservation_date": too_soon})
        self.assertEqual(response.status_code, 400)
