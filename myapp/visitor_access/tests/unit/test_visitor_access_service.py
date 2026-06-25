"""Unit tests for VisitorAccessService."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from shared.exceptions import BusinessRuleError, NotFoundError
from shared.test_doubles.fakes import (
    FakeCodeGenerator,
    FakeEmailSender,
    FakeStringMixer,
)
from visitor_access.models import VisitorAccessModel
from visitor_access.repositories.visitor_access_repository import (
    IVisitorAccessRepository,
)
from visitor_access.repositories.visitor_group_repository import (
    IVisitorGroupRepository,
)
from visitor_access.services.visitor_access_service import VisitorAccessService


pytestmark = pytest.mark.unit


Status = VisitorAccessModel.Status


def _display_status(item) -> str:
    """Replicates VisitorAccessModel.display_status for SimpleNamespace
    items (the fake repo doesn't materialize real models)."""
    now = timezone.now()
    if item.status == Status.SCHEDULED and item.scheduled_date < now:
        return Status.NO_SHOW
    if (
        item.status == Status.CHECKED_IN
        and getattr(item, "checkout_date_time", None) is not None
        and item.checkout_date_time < now
    ):
        return Status.EXPIRED
    return item.status


class FakeVisitorAccessRepo(IVisitorAccessRepository):
    def __init__(self):
        self._items: dict[int, SimpleNamespace] = {}
        self._next_id = 1

    def list_all(
        self,
        status_in=None,
        scheduled_after=None,
        scheduled_before=None,
        is_group=None,
    ):
        return self._filtered(
            self._items.values(),
            status_in,
            scheduled_after,
            scheduled_before,
            is_group,
        )

    def list_for_user(
        self,
        user_id,
        status_in=None,
        scheduled_after=None,
        scheduled_before=None,
        is_group=None,
    ):
        rows = [
            i for i in self._items.values()
            if getattr(i.host_user, "id", None) == user_id
        ]
        return self._filtered(
            rows, status_in, scheduled_after, scheduled_before, is_group
        )

    def get_by_id(self, pk):
        return self._items.get(int(pk))

    def create(self, data):
        defaults = {
            "checkout_date_time": None,
            "checkin_code": "",
            "checkout_code": "",
            "link_checkin": "",
            "link_checkout": "",
            "status": Status.SCHEDULED,
            "visitor_group": None,
        }
        defaults.update(data)
        item = SimpleNamespace(id=self._next_id, **defaults)
        item.host_user_id = getattr(data.get("host_user"), "id", None)
        item.visitor_group_id = getattr(data.get("visitor_group"), "id", None)
        self._items[self._next_id] = item
        self._next_id += 1
        return item

    def save(self, instance):
        self._items[instance.id] = instance
        return instance

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._items.pop(instance.id, None)

    @staticmethod
    def _filtered(rows, status_in, scheduled_after, scheduled_before, is_group):
        out = list(rows)
        if status_in:
            allowed = set(status_in)
            out = [r for r in out if r.status in allowed]
        if scheduled_after is not None:
            out = [r for r in out if r.scheduled_date >= scheduled_after]
        if scheduled_before is not None:
            out = [r for r in out if r.scheduled_date < scheduled_before]
        if is_group is True:
            out = [r for r in out if getattr(r, "visitor_group_id", None) is not None]
        elif is_group is False:
            out = [r for r in out if getattr(r, "visitor_group_id", None) is None]
        return out

    def count_scheduled_between(
        self, start, end, *, exclude_statuses=None
    ):
        rows = self._filtered(
            self._items.values(), None, start, end, None
        )
        if exclude_statuses:
            excluded = set(exclude_statuses)
            rows = [r for r in rows if r.status not in excluded]
        return len(rows)

    def count_with_scheduled_after(
        self, after, *, status_in=None, exclude_statuses=None
    ):
        rows = self._filtered(
            self._items.values(), status_in, after, None, None
        )
        if exclude_statuses:
            excluded = set(exclude_statuses)
            rows = [r for r in rows if r.status not in excluded]
        return len(rows)

    def list_upcoming(
        self, after, *, limit=10, status_in=None, exclude_statuses=None
    ):
        rows = self._filtered(
            self._items.values(), status_in, after, None, None
        )
        if exclude_statuses:
            excluded = set(exclude_statuses)
            rows = [r for r in rows if r.status not in excluded]
        rows.sort(key=lambda r: r.scheduled_date)
        return rows[:limit]


class FakeGroupRepo(IVisitorGroupRepository):
    """Only ``list_members`` is exercised by the access service."""

    def __init__(self):
        # group_id -> list[SimpleNamespace(name, email)]
        self.members_by_group: dict[int, list[SimpleNamespace]] = {}

    def list_members(self, group_id):
        return list(self.members_by_group.get(int(group_id), []))

    def list_for_user(self, user_id):  # pragma: no cover - not used
        return []

    def list_all(self):  # pragma: no cover
        return []

    def get_by_id(self, pk):  # pragma: no cover
        return None

    def exists_with_name_for_user(self, user_id, name, exclude_pk=None):  # pragma: no cover
        return False

    def create(self, data):  # pragma: no cover
        return None

    def update(self, instance, data):  # pragma: no cover
        return instance

    def delete(self, instance):  # pragma: no cover
        return None

    def replace_members(self, group, members):  # pragma: no cover
        return []

    def add_members(self, group, members):  # pragma: no cover
        return []


@pytest.fixture
def email_sender():
    return FakeEmailSender()


@pytest.fixture
def group_repo():
    return FakeGroupRepo()


@pytest.fixture
def service(email_sender, group_repo):
    return VisitorAccessService(
        repository=FakeVisitorAccessRepo(),
        group_repository=group_repo,
        email_sender=email_sender,
        code_generator=FakeCodeGenerator("99999"),
        string_mixer=FakeStringMixer(),
        visitor_access_base_url="http://test/visitor_access",
    )


def _user(pk=1, is_staff=False, role=None):
    return SimpleNamespace(
        id=pk,
        is_staff=is_staff,
        is_authenticated=True,
        role=role or ("ADMIN" if is_staff else "RESIDENT"),
        employee_types=[],
    )


def _payload(**overrides):
    data = {
        "visitor_name": "Guest",
        "email": "v@example.com",
        "scheduled_date": timezone.now() + timedelta(days=1),
    }
    data.update(overrides)
    return data


class TestCreate:
    def test_regular_user_creates_for_self(self, service, email_sender):
        u = _user()
        item = service.create(u, _payload())
        assert item.host_user is u
        assert item.status == Status.SCHEDULED
        assert "/checkin/" in item.link_checkin
        assert any(s["kind"] == "visitor_invite" for s in email_sender.sent)

    def test_regular_user_cannot_pass_host_user(self, service):
        with pytest.raises(BusinessRuleError):
            service.create(_user(1), _payload(host_user=_user(2)))

    def test_regular_user_can_pass_self_as_host_user(self, service):
        u = _user(1)
        item = service.create(u, _payload(host_user=u))
        assert item.host_user is u

    def test_admin_must_pass_host_user(self, service):
        with pytest.raises(BusinessRuleError):
            service.create(_user(is_staff=True), _payload())

    def test_past_date_rejected(self, service):
        with pytest.raises(BusinessRuleError):
            service.create(
                _user(),
                _payload(scheduled_date=timezone.now() - timedelta(days=1)),
            )

    def test_solo_invite_skipped_when_no_email(self, service, email_sender):
        service.create(_user(), _payload(email=""))
        assert all(s["kind"] != "visitor_invite" for s in email_sender.sent)


class TestCreateGroupVisit:
    """Group visits expand the invite into one email per member."""

    def test_invites_each_member_with_own_name(self, service, email_sender, group_repo):
        group = SimpleNamespace(id=42, name="Família Pai")
        group_repo.members_by_group[42] = [
            SimpleNamespace(name="João", email="joao@example.com"),
            SimpleNamespace(name="Maria", email="maria@example.com"),
        ]
        u = _user(1)

        item = service.create(
            u,
            _payload(
                visitor_name=group.name,
                email="",
                visitor_group=group,
            ),
        )
        assert item.visitor_group_id == 42

        invites = [s for s in email_sender.sent if s["kind"] == "visitor_invite"]
        assert sorted(s["to"] for s in invites) == [
            "joao@example.com",
            "maria@example.com",
        ]
        assert sorted(s["visitor_name"] for s in invites) == ["João", "Maria"]

    def test_members_without_email_are_skipped(
        self, service, email_sender, group_repo
    ):
        group = SimpleNamespace(id=7, name="G")
        group_repo.members_by_group[7] = [
            SimpleNamespace(name="A", email="a@x.com"),
            SimpleNamespace(name="B", email=""),
        ]
        service.create(
            _user(),
            _payload(visitor_name="G", email="", visitor_group=group),
        )
        invites = [s for s in email_sender.sent if s["kind"] == "visitor_invite"]
        assert [s["to"] for s in invites] == ["a@x.com"]


class TestCheckin:
    def test_checkin_inside_window(self, service, email_sender):
        u = _user(1)
        item = service.create(u, _payload())
        item.checkin_date_time = timezone.now() - timedelta(minutes=5)
        item.checkout_date_time = timezone.now() + timedelta(hours=2)

        result = service.checkin(str(item.id))
        assert result == {"checkin_code": "99999"}
        assert item.status == Status.CHECKED_IN
        assert any(s["kind"] == "checkin" for s in email_sender.sent)

    def test_checkin_outside_window(self, service):
        u = _user(1)
        item = service.create(u, _payload(scheduled_date=timezone.now() + timedelta(days=2)))
        result = service.checkin(str(item.id))
        assert isinstance(result, str)
        assert "scheduled time" in result

    def test_checkin_after_checkout_blocked(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        item.status = Status.CHECKED_OUT
        with pytest.raises(BusinessRuleError):
            service.checkin(str(item.id))

    def test_checkin_blocked_when_cancelled(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        item.status = Status.CANCELLED
        with pytest.raises(BusinessRuleError):
            service.checkin(str(item.id))

    def test_group_checkin_notifies_all_members(
        self, service, email_sender, group_repo
    ):
        group = SimpleNamespace(id=11, name="G")
        group_repo.members_by_group[11] = [
            SimpleNamespace(name="A", email="a@x.com"),
            SimpleNamespace(name="B", email="b@x.com"),
        ]
        item = service.create(
            _user(),
            _payload(visitor_name="G", email="", visitor_group=group),
        )
        item.checkin_date_time = timezone.now() - timedelta(minutes=1)
        item.checkout_date_time = timezone.now() + timedelta(hours=1)

        service.checkin(str(item.id))
        checkin_emails = [s for s in email_sender.sent if s["kind"] == "checkin"]
        assert sorted(s["to"] for s in checkin_emails) == ["a@x.com", "b@x.com"]


class TestCheckout:
    def test_checkout_blocked_if_still_scheduled(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        with pytest.raises(BusinessRuleError):
            service.checkout(str(item.id))

    def test_checkout_after_checkin(self, service, email_sender):
        u = _user(1)
        item = service.create(u, _payload(scheduled_date=timezone.now() + timedelta(hours=2)))
        item.status = Status.CHECKED_IN
        item.checkin_code = "11111"

        result = service.checkout(str(item.id))
        assert result == {"checkout_code": "99999"}
        assert item.status == Status.CHECKED_OUT
        assert any(s["kind"] == "checkout" for s in email_sender.sent)

    def test_checkout_blocked_when_cancelled(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        item.status = Status.CANCELLED
        with pytest.raises(BusinessRuleError):
            service.checkout(str(item.id))

    def test_group_checkout_notifies_all_members(
        self, service, email_sender, group_repo
    ):
        group = SimpleNamespace(id=22, name="G")
        group_repo.members_by_group[22] = [
            SimpleNamespace(name="A", email="a@x.com"),
            SimpleNamespace(name="B", email="b@x.com"),
        ]
        item = service.create(
            _user(),
            _payload(
                visitor_name="G",
                email="",
                visitor_group=group,
                scheduled_date=timezone.now() + timedelta(hours=2),
            ),
        )
        item.status = Status.CHECKED_IN
        item.checkin_code = "11111"

        service.checkout(str(item.id))
        checkout_emails = [s for s in email_sender.sent if s["kind"] == "checkout"]
        assert sorted(s["to"] for s in checkout_emails) == ["a@x.com", "b@x.com"]


class TestDelete:
    def test_cannot_cancel_past(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        item.scheduled_date = timezone.now() - timedelta(hours=1)
        with pytest.raises(BusinessRuleError):
            service.delete(u, item.id)

    def test_delete_future_marks_as_cancelled(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        result = service.delete(u, item.id)
        assert result.status == Status.CANCELLED
        same = service.get_for(u, item.id)
        assert same.status == Status.CANCELLED

    def test_cannot_cancel_already_cancelled(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        service.delete(u, item.id)
        with pytest.raises(BusinessRuleError):
            service.delete(u, item.id)

    def test_cannot_cancel_concluded(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        item.status = Status.CHECKED_OUT
        with pytest.raises(BusinessRuleError):
            service.delete(u, item.id)


class TestAllDay:
    def test_all_day_window_covers_full_day(self, service):
        u = _user(1)
        when = timezone.now() + timedelta(days=2)
        item = service.create(u, _payload(scheduled_date=when, all_day=True))
        assert item.all_day is True
        local_in = timezone.localtime(item.checkin_date_time)
        local_out = timezone.localtime(item.checkout_date_time)
        assert local_in.hour == 0
        assert local_in.minute == 0
        assert local_out.hour == 23
        assert local_out.minute == 59
        assert local_in.date() == timezone.localtime(when).date()

    def test_all_day_today_allowed(self, service):
        u = _user(1)
        # earlier hour today is fine for all-day
        earlier_today = timezone.localtime().replace(
            hour=1, minute=0, second=0, microsecond=0
        )
        item = service.create(u, _payload(scheduled_date=earlier_today, all_day=True))
        assert item.all_day is True

    def test_all_day_past_day_rejected(self, service):
        with pytest.raises(BusinessRuleError):
            service.create(
                _user(),
                _payload(
                    scheduled_date=timezone.now() - timedelta(days=2),
                    all_day=True,
                ),
            )

    def test_all_day_overrides_checkout_date_time(self, service):
        u = _user(1)
        when = timezone.now() + timedelta(days=2)
        custom_checkout = when + timedelta(hours=1)
        item = service.create(
            u,
            _payload(
                scheduled_date=when,
                all_day=True,
                checkout_date_time=custom_checkout,
            ),
        )
        local_out = timezone.localtime(item.checkout_date_time)
        assert local_out.hour == 23
        assert local_out.minute == 59


# ------------------------------------------------------------------------- #
# listing filters                                                           #
# ------------------------------------------------------------------------- #
def _seed_visits(service, owner):
    """Create a mixed bag of visits for filter tests."""
    now = timezone.now()
    # future + scheduled
    future = service.create(owner, _payload(scheduled_date=now + timedelta(days=2)))
    # past + still SCHEDULED → NO_SHOW
    no_show = service.create(owner, _payload(scheduled_date=now + timedelta(days=2)))
    no_show.scheduled_date = now - timedelta(days=2)
    # past + already CHECKED_OUT
    concluded = service.create(owner, _payload(scheduled_date=now + timedelta(days=2)))
    concluded.scheduled_date = now - timedelta(days=1)
    concluded.status = Status.CHECKED_OUT
    # cancelled (still future)
    cancelled = service.create(owner, _payload(scheduled_date=now + timedelta(days=3)))
    cancelled.status = Status.CANCELLED
    # checked-in but past checkout window → EXPIRED
    expired = service.create(owner, _payload(scheduled_date=now + timedelta(days=2)))
    expired.scheduled_date = now - timedelta(hours=4)
    expired.checkout_date_time = now - timedelta(hours=1)
    expired.status = Status.CHECKED_IN
    return {
        "future": future,
        "no_show": no_show,
        "concluded": concluded,
        "cancelled": cancelled,
        "expired": expired,
    }


class TestListFilters:
    def test_period_future_returns_only_future(self, service):
        u = _user(1)
        seeded = _seed_visits(service, u)
        ids = {v.id for v in service.list_for(u, period="future")}
        assert seeded["future"].id in ids
        assert seeded["cancelled"].id in ids  # still has a future date
        assert seeded["no_show"].id not in ids
        assert seeded["concluded"].id not in ids
        assert seeded["expired"].id not in ids

    def test_period_past_returns_only_past(self, service):
        u = _user(1)
        seeded = _seed_visits(service, u)
        ids = {v.id for v in service.list_for(u, period="past")}
        assert seeded["future"].id not in ids
        assert seeded["cancelled"].id not in ids
        assert seeded["no_show"].id in ids
        assert seeded["concluded"].id in ids
        assert seeded["expired"].id in ids

    def test_status_scheduled_only_future_rows(self, service):
        u = _user(1)
        seeded = _seed_visits(service, u)
        ids = {v.id for v in service.list_for(u, status="SCHEDULED")}
        assert ids == {seeded["future"].id}

    def test_status_no_show_only_past_scheduled(self, service):
        u = _user(1)
        seeded = _seed_visits(service, u)
        ids = {v.id for v in service.list_for(u, status="NO_SHOW")}
        assert ids == {seeded["no_show"].id}

    def test_status_expired_only_past_checked_in(self, service):
        u = _user(1)
        seeded = _seed_visits(service, u)
        ids = {v.id for v in service.list_for(u, status="EXPIRED")}
        assert ids == {seeded["expired"].id}

    def test_status_cancelled(self, service):
        u = _user(1)
        seeded = _seed_visits(service, u)
        ids = {v.id for v in service.list_for(u, status="CANCELLED")}
        assert ids == {seeded["cancelled"].id}

    def test_status_checked_out(self, service):
        u = _user(1)
        seeded = _seed_visits(service, u)
        ids = {v.id for v in service.list_for(u, status="CHECKED_OUT")}
        assert ids == {seeded["concluded"].id}

    def test_invalid_period_rejected(self, service):
        u = _user(1)
        with pytest.raises(BusinessRuleError):
            service.list_for(u, period="weird")

    def test_invalid_status_rejected(self, service):
        u = _user(1)
        with pytest.raises(BusinessRuleError):
            service.list_for(u, status="weird")

    def test_period_status_combined(self, service):
        """Past + CHECKED_OUT narrows to concluded only."""
        u = _user(1)
        seeded = _seed_visits(service, u)
        ids = {
            v.id for v in service.list_for(u, period="past", status="CHECKED_OUT")
        }
        assert ids == {seeded["concluded"].id}

    def test_is_group_false_excludes_group_visits(self, service, group_repo):
        u = _user(1)
        group_repo.members_by_group[1] = [
            SimpleNamespace(name="A", email="a@x.com")
        ]
        solo = service.create(u, _payload())
        group_visit = service.create(
            u,
            _payload(
                visitor_name="G",
                email="",
                visitor_group=SimpleNamespace(id=1, name="G"),
            ),
        )
        ids = {v.id for v in service.list_for(u, is_group=False)}
        assert solo.id in ids
        assert group_visit.id not in ids

    def test_is_group_true_returns_only_group_visits(self, service, group_repo):
        u = _user(1)
        group_repo.members_by_group[1] = [
            SimpleNamespace(name="A", email="a@x.com")
        ]
        solo = service.create(u, _payload())
        group_visit = service.create(
            u,
            _payload(
                visitor_name="G",
                email="",
                visitor_group=SimpleNamespace(id=1, name="G"),
            ),
        )
        ids = {v.id for v in service.list_for(u, is_group=True)}
        assert solo.id not in ids
        assert group_visit.id in ids


class TestDisplayStatus:
    """Sanity checks for the helper used by the OutputSerializer."""

    def test_scheduled_in_future_stays_scheduled(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        assert _display_status(item) == Status.SCHEDULED

    def test_scheduled_in_past_becomes_no_show(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        item.scheduled_date = timezone.now() - timedelta(hours=1)
        assert _display_status(item) == Status.NO_SHOW

    def test_checked_in_after_checkout_becomes_expired(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        item.status = Status.CHECKED_IN
        item.checkout_date_time = timezone.now() - timedelta(minutes=10)
        assert _display_status(item) == Status.EXPIRED

    def test_cancelled_stays_cancelled(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        item.status = Status.CANCELLED
        item.scheduled_date = timezone.now() - timedelta(days=1)
        assert _display_status(item) == Status.CANCELLED
