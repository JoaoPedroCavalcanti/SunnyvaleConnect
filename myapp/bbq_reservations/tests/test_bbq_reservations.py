from datetime import date, timedelta

from django.urls import reverse, NoReverseMatch
from model_bakery import baker

from bbq_reservations.models import BBQReservationModel
from tests_base.base_tests_user import BaseTestsUsers


def _list_url() -> str:
    # SimpleRouter mounted at "/bbq/" with basename="bbq_reservations-router"
    try:
        return reverse("bbq_reservations-router-list")
    except NoReverseMatch:
        return "/bbq/"


def _detail_url(pk: int) -> str:
    try:
        return reverse("bbq_reservations-router-detail", kwargs={"pk": pk})
    except NoReverseMatch:
        return f"/bbq/{pk}/"


LIST_URL = _list_url()


class BBQReservationAuthTests(BaseTestsUsers):
    def test_anonymous_cannot_list(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 401)

    def test_authenticated_can_list(self):
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)


class BBQReservationCreateTests(BaseTestsUsers):
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
            BBQReservationModel,
            reservation_user=self.user_b,
            reservation_date=date.today() + timedelta(days=15),
        )
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "reservation_date": (
                    date.today() + timedelta(days=15)
                ).isoformat(),
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_book_within_30_days_of_last(self):
        last = date.today() + timedelta(days=5)
        baker.make(
            BBQReservationModel,
            reservation_user=self.user_a,
            reservation_date=last,
        )
        self.authenticate(self.user_a)
        too_soon = (last + timedelta(days=10)).isoformat()
        response = self.client.post(
            LIST_URL, data={"reservation_date": too_soon}
        )
        self.assertEqual(response.status_code, 400)


class BBQReservationListOrderTests(BaseTestsUsers):
    def test_ordering_descending_by_date(self):
        d1 = date.today() + timedelta(days=10)
        d2 = date.today() + timedelta(days=50)
        baker.make(
            BBQReservationModel, reservation_user=self.user_a, reservation_date=d1
        )
        baker.make(
            BBQReservationModel, reservation_user=self.user_b, reservation_date=d2
        )
        self.authenticate(self.admin)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        dates = [r["reservation_date"] for r in response.data["results"]]
        self.assertEqual(dates, sorted(dates, reverse=True))
