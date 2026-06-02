"""Unit tests for UserService with an in-memory fake repository."""

from datetime import date

import pytest

from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.infrastructure.document_validators import (
    BrazilianCPFValidator,
    BrazilianPhoneValidator,
)
from shared.infrastructure.password_policy import DefaultPasswordPolicy
from users.models import UserRole
from users.repositories.user_repository import IUserRepository
from users.services.user_service import UserService


pytestmark = pytest.mark.unit


# Two valid CPFs (correct check digits) for the tests.
VALID_CPF_A = "39053344705"
VALID_CPF_B = "12345678909"


class _FakeUser:
    def __init__(
        self,
        pk,
        username="u",
        email="u@e.com",
        is_staff=False,
        is_authenticated=True,
        role=UserRole.RESIDENT,
    ):
        self.id = pk
        self.pk = pk
        self.username = username
        self.email = email
        self.full_name = ""
        self.cpf = ""
        self.phone = ""
        self.birth_date = None
        self.apartment = ""
        self.block = ""
        self.photo = None
        self.is_staff = is_staff
        self.is_authenticated = is_authenticated
        self.role = role


def _anon():
    return _FakeUser(0, is_authenticated=False)


class FakeUserRepository(IUserRepository):
    def __init__(self):
        self._users: dict[int, _FakeUser] = {}
        self._next_id = 1

    def list_all(self):
        return list(self._users.values())

    def list_by_role(self, role):
        return [u for u in self._users.values() if u.role == role]

    def get_by_id(self, pk):
        return self._users.get(int(pk))

    def exists_with_email(self, email):
        return any(u.email == email for u in self._users.values())

    def exists_with_username(self, username):
        return any(u.username == username for u in self._users.values())

    def exists_with_cpf(self, cpf):
        return any(u.cpf == cpf for u in self._users.values())

    def create_user(self, **fields):
        password = fields.pop("password", "")
        user = _FakeUser(
            self._next_id,
            username=fields.get("username", ""),
            email=fields.get("email", ""),
        )
        for k, v in fields.items():
            setattr(user, k, v)
        user._password = password
        self._users[self._next_id] = user
        self._next_id += 1
        return user

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._users.pop(instance.id, None)

    def set_active(self, instance, value):
        instance.is_active = value
        return instance

    def list_admin_emails(self):
        return [u.email for u in self._users.values() if u.is_staff]

    def get_by_username(self, username):
        for u in self._users.values():
            if u.username == username:
                return u
        return None

    def check_password(self, instance, raw_password):
        return getattr(instance, "_password", None) == raw_password

    def count_active(self):
        return sum(
            1 for u in self._users.values() if getattr(u, "is_active", True)
        )


@pytest.fixture
def service():
    return UserService(
        user_repository=FakeUserRepository(),
        password_policy=DefaultPasswordPolicy(),
        cpf_validator=BrazilianCPFValidator(),
        phone_validator=BrazilianPhoneValidator(),
    )


def _valid_payload(**overrides):
    data = {
        "username": "joao",
        "password": "StrongPass1!",
        "full_name": "Joao Pedro",
        "birth_date": date(1995, 5, 20),
        "cpf": VALID_CPF_A,
        "phone": "11987654321",
        "email": "joao@example.com",
        "apartment": "101",
        "block": "A",
    }
    data.update(overrides)
    return data


class TestCreate:
    def test_anonymous_can_create(self, service):
        user = service.create(_anon(), _valid_payload())
        assert user.username == "joao"
        assert user.cpf == VALID_CPF_A

    def test_admin_can_create(self, service):
        admin = _FakeUser(99, is_staff=True)
        user = service.create(admin, _valid_payload())
        assert user.username == "joao"

    def test_regular_user_cannot_create(self, service):
        with pytest.raises(PermissionDeniedError):
            service.create(_FakeUser(99), _valid_payload())

    def test_rejects_duplicate_email(self, service):
        service.create(_anon(), _valid_payload())
        with pytest.raises(BusinessRuleError) as exc:
            service.create(
                _anon(),
                _valid_payload(username="other", cpf=VALID_CPF_B),
            )
        assert exc.value.field == "email"

    def test_rejects_duplicate_username(self, service):
        service.create(_anon(), _valid_payload())
        with pytest.raises(BusinessRuleError) as exc:
            service.create(
                _anon(),
                _valid_payload(email="other@e.com", cpf=VALID_CPF_B),
            )
        assert exc.value.field == "username"

    def test_rejects_duplicate_cpf(self, service):
        service.create(_anon(), _valid_payload())
        with pytest.raises(BusinessRuleError) as exc:
            service.create(
                _anon(),
                _valid_payload(username="other", email="other@e.com"),
            )
        assert exc.value.field == "cpf"

    def test_rejects_invalid_cpf_check_digits(self, service):
        with pytest.raises(BusinessRuleError) as exc:
            service.create(_anon(), _valid_payload(cpf="11111111111"))
        assert exc.value.field == "cpf"

    def test_rejects_short_phone(self, service):
        with pytest.raises(BusinessRuleError) as exc:
            service.create(_anon(), _valid_payload(phone="123"))
        assert exc.value.field == "phone"

    def test_normalizes_cpf_with_mask(self, service):
        user = service.create(_anon(), _valid_payload(cpf="390.533.447-05"))
        assert user.cpf == VALID_CPF_A

    def test_normalizes_email_lowercase(self, service):
        user = service.create(_anon(), _valid_payload(email="UPPER@MAIL.COM"))
        assert user.email == "upper@mail.com"

    def test_rejects_weak_password(self, service):
        with pytest.raises(BusinessRuleError) as exc:
            service.create(_anon(), _valid_payload(password="a"))
        assert exc.value.field == "password"
        assert isinstance(exc.value.message, list)


class TestGetFor:
    def test_admin_sees_anyone(self, service):
        target = service.create(_anon(), _valid_payload())
        admin = _FakeUser(99, is_staff=True)
        assert service.get_for(admin, target.id) is target

    def test_regular_user_sees_only_self(self, service):
        target = service.create(_anon(), _valid_payload())
        other = _FakeUser(99)
        with pytest.raises(NotFoundError):
            service.get_for(other, target.id)


class TestListFor:
    def test_admin_lists_all(self, service):
        service.create(_anon(), _valid_payload())
        admin = _FakeUser(99, is_staff=True)
        assert len(list(service.list_for(admin))) == 1

    def test_regular_user_lists_only_self(self, service):
        u = _FakeUser(99)
        assert list(service.list_for(u)) == [u]


class TestUpdateSelf:
    def test_drops_immutable_cpf(self, service):
        user = service.create(_anon(), _valid_payload())
        original_cpf = user.cpf
        service.update_self(user, {"cpf": VALID_CPF_B, "full_name": "New Name"})
        assert user.cpf == original_cpf
        assert user.full_name == "New Name"

    def test_drops_immutable_username(self, service):
        user = service.create(_anon(), _valid_payload())
        service.update_self(user, {"username": "hacked"})
        assert user.username == "joao"


class TestRoleOnCreate:
    def test_anonymous_signup_defaults_to_resident(self, service):
        user = service.create(_anon(), _valid_payload())
        assert user.role == UserRole.RESIDENT
        assert user.is_staff is False

    def test_anonymous_cannot_self_assign_admin(self, service):
        with pytest.raises(PermissionDeniedError):
            service.create(_anon(), _valid_payload(role=UserRole.ADMIN))

    def test_anonymous_cannot_self_assign_employee(self, service):
        with pytest.raises(PermissionDeniedError):
            service.create(_anon(), _valid_payload(role=UserRole.EMPLOYEE))

    def test_admin_can_create_admin_and_syncs_is_staff(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        new_admin = service.create(
            admin, _valid_payload(role=UserRole.ADMIN)
        )
        assert new_admin.role == UserRole.ADMIN
        assert new_admin.is_staff is True

    def test_admin_can_create_employee_without_is_staff(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        emp = service.create(admin, _valid_payload(role=UserRole.EMPLOYEE))
        assert emp.role == UserRole.EMPLOYEE
        assert emp.is_staff is False

    def test_invalid_role_rejected(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        with pytest.raises(BusinessRuleError) as exc:
            service.create(admin, _valid_payload(role="GHOST"))
        assert exc.value.field == "role"


class TestRoleOnUpdate:
    def test_admin_can_promote_resident_to_employee(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        target = service.create(_anon(), _valid_payload())
        result = service.update(admin, target.id, {"role": UserRole.EMPLOYEE})
        assert result.role == UserRole.EMPLOYEE
        assert result.is_staff is False

    def test_admin_can_promote_resident_to_admin(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        target = service.create(_anon(), _valid_payload())
        result = service.update(admin, target.id, {"role": UserRole.ADMIN})
        assert result.role == UserRole.ADMIN
        assert result.is_staff is True

    def test_admin_can_demote_other_admin(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        target = service.create(admin, _valid_payload(role=UserRole.ADMIN))
        result = service.update(admin, target.id, {"role": UserRole.RESIDENT})
        assert result.role == UserRole.RESIDENT
        assert result.is_staff is False

    def test_non_admin_cannot_change_role(self, service):
        target = service.create(_anon(), _valid_payload())
        with pytest.raises(PermissionDeniedError):
            service.update_self(target, {"role": UserRole.ADMIN})

    def test_admin_cannot_demote_self(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        with pytest.raises(PermissionDeniedError) as exc:
            service.update_self(admin, {"role": UserRole.RESIDENT})
        assert "demote" in str(exc.value.message).lower()


class TestRoleOnDelete:
    def test_admin_cannot_delete_self(self, service):
        admin = service.create(
            _FakeUser(99, is_staff=True, role=UserRole.ADMIN),
            _valid_payload(role=UserRole.ADMIN),
        )
        with pytest.raises(PermissionDeniedError):
            service.delete(admin, admin.id)

    def test_admin_can_delete_other_admin(self, service):
        boss = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        other = service.create(boss, _valid_payload(role=UserRole.ADMIN))
        service.delete(boss, other.id)


class TestListByRole:
    def test_admin_filters_by_role(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        service.create(_anon(), _valid_payload())
        service.create(
            admin,
            _valid_payload(
                username="emp",
                email="emp@x.com",
                cpf=VALID_CPF_B,
                role=UserRole.EMPLOYEE,
            ),
        )
        residents = list(service.list_for(admin, role=UserRole.RESIDENT))
        employees = list(service.list_for(admin, role=UserRole.EMPLOYEE))
        assert len(residents) == 1
        assert len(employees) == 1

    def test_role_filter_ignored_for_regular_user(self, service):
        u = _FakeUser(99)
        result = list(service.list_for(u, role=UserRole.ADMIN))
        assert result == [u]

    def test_invalid_role_filter_rejected(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        with pytest.raises(BusinessRuleError):
            list(service.list_for(admin, role="GHOST"))
