"""Unit tests for UserService with an in-memory fake repository."""

from datetime import date

from types import SimpleNamespace

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
from shared.infrastructure.transactions import NullTransactionRunner
from shared.tenant import build_tenant_username
from units.models import UnitMembership
from units.tests.unit._fakes import FakeUnitMembershipRepository
from users.models import EmployeeType, UserRole
from users.repositories.user_repository import IUserRepository
from users.services.user_service import UserService


pytestmark = pytest.mark.unit


VALID_CPF_A = "39053344705"
VALID_CPF_B = "12345678909"
TEST_CONDOMINIUM_ID = 1
TEST_CONDOMINIUM_CODE = "TEST01"


def _test_condominium():
    return SimpleNamespace(
        id=TEST_CONDOMINIUM_ID,
        pk=TEST_CONDOMINIUM_ID,
        code=TEST_CONDOMINIUM_CODE,
        is_active=True,
    )


class _FakeUser:
    def __init__(
        self,
        pk,
        username="u",
        email="u@e.com",
        is_staff=False,
        is_authenticated=True,
        role=UserRole.RESIDENT,
        employee_types=None,
        condominium_id=TEST_CONDOMINIUM_ID,
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
        self.is_active = True
        self.is_authenticated = is_authenticated
        self.role = role
        self.employee_types = list(employee_types or [])
        self.condominium_id = condominium_id
        self.condominium = _test_condominium()


def _anon():
    return _FakeUser(0, is_authenticated=False, condominium_id=None)


class FakeUserRepository(IUserRepository):
    def __init__(self):
        self._users: dict[int, _FakeUser] = {}
        self._next_id = 1

    def list_all(self, *, condominium_id=None):
        users = list(self._users.values())
        if condominium_id is not None:
            users = [u for u in users if u.condominium_id == condominium_id]
        return users

    def list_by_role(self, role, *, condominium_id=None):
        return [
            u
            for u in self.list_all(condominium_id=condominium_id)
            if u.role == role
        ]

    def list_filtered(self, *, role=None, is_active=None, employee_type=None, condominium_id=None):
        users = self.list_all(condominium_id=condominium_id)
        if role is not None:
            users = [u for u in users if u.role == role]
        if is_active is not None:
            users = [u for u in users if u.is_active == is_active]
        if employee_type is not None:
            users = [
                u
                for u in users
                if employee_type in (u.employee_types or [])
            ]
        return users

    def get_by_id(self, pk):
        return self._users.get(int(pk))

    def exists_with_email(self, email):
        normalized = (email or "").lower().strip()
        return any(u.email.lower().strip() == normalized for u in self._users.values())

    def exists_with_username(
        self, username, *, condominium_code, exclude_id=None
    ):
        storage_username = build_tenant_username(condominium_code, username)
        return any(
            u.username == storage_username and u.id != exclude_id
            for u in self._users.values()
        )

    def exists_with_cpf(
        self, cpf, *, condominium_id, exclude_id=None
    ):
        return any(
            u.cpf == cpf
            and u.condominium_id == condominium_id
            and u.id != exclude_id
            for u in self._users.values()
        )

    def create_user(self, **fields):
        password = fields.pop("password", "")
        user = _FakeUser(
            self._next_id,
            username=fields.get("username", ""),
            email=fields.get("email", ""),
            condominium_id=fields.get("condominium_id", TEST_CONDOMINIUM_ID),
        )
        for k, v in fields.items():
            setattr(user, k, v)
        user._password = password
        self._users[self._next_id] = user
        self._next_id += 1
        return user

    def update(self, instance, data):
        for k, v in data.items():
            if k == "password":
                instance._password = v
            else:
                setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._users.pop(instance.id, None)

    def set_active(self, instance, value):
        instance.is_active = value
        return instance

    def list_admin_emails(self, *, condominium_id):
        return [
            u.email
            for u in self._users.values()
            if u.is_staff and u.condominium_id == condominium_id
        ]

    def get_by_email(self, email):
        normalized = (email or "").lower().strip()
        for user in self._users.values():
            if user.email.lower().strip() == normalized:
                return user
        return None

    def get_by_username(self, username, *, condominium_code=None):
        if condominium_code:
            username = build_tenant_username(condominium_code, username)
        for u in self._users.values():
            if u.username == username:
                return u
        return None

    def check_password(self, instance, raw_password):
        return getattr(instance, "_password", None) == raw_password

    def count_active(self, *, condominium_id=None):
        users = self._users.values()
        if condominium_id is not None:
            users = [u for u in users if u.condominium_id == condominium_id]
        return sum(1 for u in users if getattr(u, "is_active", True))


@pytest.fixture
def service():
    return UserService(
        user_repository=FakeUserRepository(),
        password_policy=DefaultPasswordPolicy(),
        cpf_validator=BrazilianCPFValidator(),
        phone_validator=BrazilianPhoneValidator(),
        membership_repository=FakeUnitMembershipRepository(),
        transaction_runner=NullTransactionRunner(),
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
        "condominium_id": TEST_CONDOMINIUM_ID,
        "condominium_code": TEST_CONDOMINIUM_CODE,
    }
    data.update(overrides)
    return data


class TestCreate:
    def test_anonymous_can_create(self, service):
        user = service.create(_anon(), _valid_payload())
        assert user.username == build_tenant_username(TEST_CONDOMINIUM_CODE, "joao")
        assert user.cpf == VALID_CPF_A

    def test_admin_can_create(self, service):
        admin = _FakeUser(99, is_staff=True)
        user = service.create(admin, _valid_payload())
        assert user.username == build_tenant_username(TEST_CONDOMINIUM_CODE, "joao")

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
        assert user.username == build_tenant_username(TEST_CONDOMINIUM_CODE, "joao")

    def test_admin_can_edit_username_cpf_and_email(self, service):
        user = service.create(_anon(), _valid_payload())
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)

        updated = service.update(
            admin,
            user.id,
            {
                "username": "novo",
                "cpf": VALID_CPF_B,
                "email": "NEW@EXAMPLE.COM",
            },
        )

        assert updated.username == build_tenant_username(
            TEST_CONDOMINIUM_CODE, "novo"
        )
        assert updated.cpf == VALID_CPF_B
        assert updated.email == "new@example.com"

    def test_admin_cannot_deactivate_self_via_patch(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        with pytest.raises(PermissionDeniedError):
            service.update_self(admin, {"is_active": False})


class TestEmployeeRestrictions:
    def test_employee_cannot_update_self(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        emp = service.create(
            admin,
            _valid_payload(
                role=UserRole.EMPLOYEE,
                employee_types=[EmployeeType.DOORMAN],
                apartment="",
                block="",
            ),
        )
        with pytest.raises(PermissionDeniedError):
            service.update_self(emp, {"full_name": "Hacked"})

    def test_admin_can_update_employee(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        emp = service.create(
            admin,
            _valid_payload(
                role=UserRole.EMPLOYEE,
                employee_types=[EmployeeType.DOORMAN],
                apartment="",
                block="",
            ),
        )
        updated = service.update(admin, emp.id, {"full_name": "New Name"})
        assert updated.full_name == "New Name"

    def test_employee_apartment_stripped_on_admin_update(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        emp = service.create(
            admin,
            _valid_payload(
                role=UserRole.EMPLOYEE,
                employee_types=[EmployeeType.DOORMAN],
                apartment="",
                block="",
            ),
        )
        updated = service.update(admin, emp.id, {"apartment": "101", "block": "A"})
        assert updated.apartment == ""
        assert updated.block == ""


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
        emp = service.create(
            admin,
            _valid_payload(
                role=UserRole.EMPLOYEE,
                employee_types=[EmployeeType.CLEANING],
                apartment="",
                block="",
            ),
        )
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
        result = service.update(
            admin,
            target.id,
            {
                "role": UserRole.EMPLOYEE,
                "employee_types": [EmployeeType.DOORMAN],
            },
        )
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
        assert "rebaixar" in str(exc.value.message).lower()


class TestRoleOnDelete:
    def test_resident_cannot_deactivate_self(self, service):
        resident = service.create(_anon(), _valid_payload())
        with pytest.raises(PermissionDeniedError):
            service.delete(resident, resident.id)

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
        assert other.is_active is False
        assert service._repo.get_by_id(other.id) is other

    def test_admin_can_deactivate_employee(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        employee = service.create(
            admin,
            _valid_payload(
                role=UserRole.EMPLOYEE,
                employee_types=[EmployeeType.DOORMAN],
                apartment="",
                block="",
            ),
        )

        service.delete(admin, employee.id)

        assert employee.is_active is False

    def test_deactivating_owner_transfers_to_oldest_active_member(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        owner = service.create(_anon(), _valid_payload())
        replacement = service.create(
            _anon(),
            _valid_payload(
                username="replacement",
                email="replacement@example.com",
                cpf=VALID_CPF_B,
            ),
        )
        unit = SimpleNamespace(id=10)
        owner_membership = service._memberships.create(
            {
                "unit": unit,
                "user": owner,
                "role": UnitMembership.Role.OWNER,
                "status": UnitMembership.Status.ACTIVE,
            }
        )
        replacement_membership = service._memberships.create(
            {
                "unit": unit,
                "user": replacement,
                "role": UnitMembership.Role.RESIDENT,
                "status": UnitMembership.Status.ACTIVE,
            }
        )

        service.delete(admin, owner.id)

        assert owner.is_active is False
        assert owner_membership.status == UnitMembership.Status.LEFT
        assert replacement_membership.status == UnitMembership.Status.ACTIVE
        assert replacement_membership.role == UnitMembership.Role.OWNER

    def test_deactivating_only_owner_leaves_unit_without_owner(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        owner = service.create(_anon(), _valid_payload())
        unit = SimpleNamespace(id=10)
        membership = service._memberships.create(
            {
                "unit": unit,
                "user": owner,
                "role": UnitMembership.Role.OWNER,
                "status": UnitMembership.Status.ACTIVE,
            }
        )

        service.delete(admin, owner.id)

        assert owner.is_active is False
        assert membership.status == UnitMembership.Status.LEFT


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
                employee_types=[EmployeeType.CLEANING],
                apartment="",
                block="",
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

    def test_admin_list_without_role_includes_all_roles(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        service.create(_anon(), _valid_payload())
        service.create(
            admin,
            _valid_payload(
                username="emp",
                email="emp@x.com",
                cpf=VALID_CPF_B,
                role=UserRole.EMPLOYEE,
                employee_types=[EmployeeType.CLEANING],
                apartment="",
                block="",
            ),
        )
        roles = {u.role for u in service.list_for(admin)}
        assert UserRole.RESIDENT in roles
        assert UserRole.EMPLOYEE in roles

    def test_is_active_filter(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        active = service.create(_anon(), _valid_payload())
        inactive = service.create(
            admin,
            _valid_payload(
                username="inactive",
                email="inactive@x.com",
                cpf=VALID_CPF_B,
            ),
        )
        service._repo.set_active(inactive, False)
        # Default list excludes inactive / pending accounts.
        assert list(service.list_for(admin)) == [active]
        active_only = list(service.list_for(admin, is_active=True))
        assert active_only == [active]
        inactive_only = list(service.list_for(admin, is_active=False))
        assert inactive_only == [inactive]

    def test_employee_type_filter(self, service):
        admin = _FakeUser(99, is_staff=True, role=UserRole.ADMIN)
        service.create(
            admin,
            _valid_payload(
                username="porteiro",
                email="porteiro@x.com",
                cpf=VALID_CPF_B,
                role=UserRole.EMPLOYEE,
                employee_types=[EmployeeType.DOORMAN],
                apartment="",
                block="",
            ),
        )
        service.create(
            admin,
            _valid_payload(
                username="zelador",
                email="zelador@x.com",
                cpf="52998224725",
                role=UserRole.EMPLOYEE,
                employee_types=[EmployeeType.CLEANING],
                apartment="",
                block="",
            ),
        )
        doormen = list(
            service.list_for(admin, employee_type=EmployeeType.DOORMAN)
        )
        assert len(doormen) == 1
        assert doormen[0].username == build_tenant_username(
            TEST_CONDOMINIUM_CODE, "porteiro"
        )
