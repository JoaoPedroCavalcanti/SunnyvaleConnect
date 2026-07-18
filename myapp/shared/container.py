"""Application-wide DI container.

Manual, lazy, singleton-by-key. No external dependencies.

Usage from anywhere::

    from shared.container import container

    user = container.user_service.create(payload)

For tests you can replace any provider in-place::

    container.override("user_repository", FakeUserRepository())
    ...
    container.reset()
"""

from typing import Any, Callable

from shared.infrastructure.cache import DjangoCache, ICache
from shared.infrastructure.code_generator import ICodeGenerator, RandomCodeGenerator
from shared.infrastructure.document_validators import (
    BrazilianCPFValidator,
    BrazilianPhoneValidator,
    ICPFValidator,
    IPhoneValidator,
)
from shared.infrastructure.email_sender import DjangoEmailSender, IEmailSender
from shared.infrastructure.password_policy import (
    DefaultPasswordPolicy,
    IPasswordPolicy,
)
from shared.infrastructure.qr_encoder import IQRCodeEncoder, QRCodeEncoder
from shared.infrastructure.string_mixer import IStringMixer, SecretStringMixer
from shared.infrastructure.transactions import (
    DjangoTransactionRunner,
    ITransactionRunner,
)


_SECRET_MIXIN = "1783645917351"
_VISITOR_ACCESS_BASE_URL = "http://127.0.0.1:8000/visitor_access"


class Container:
    """Single source of truth for service / repository wiring."""

    _instance: "Container | None" = None

    def __new__(cls) -> "Container":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._cache = {}
            instance._overrides = {}
            cls._instance = instance
        return cls._instance

    # ------------------------------------------------------------------ #
    # generic resolution helpers                                         #
    # ------------------------------------------------------------------ #
    def _resolve(self, key: str, factory: Callable[[], Any]) -> Any:
        if key in self._overrides:
            return self._overrides[key]
        if key not in self._cache:
            self._cache[key] = factory()
        return self._cache[key]

    def override(self, key: str, instance: Any) -> None:
        """Replace a provider (handy in tests)."""
        self._overrides[key] = instance

    def reset(self) -> None:
        """Clear cache + overrides. Use between tests."""
        self._cache.clear()
        self._overrides.clear()

    # ------------------------------------------------------------------ #
    # infrastructure (cross-cutting)                                     #
    # ------------------------------------------------------------------ #
    @property
    def email_sender(self) -> IEmailSender:
        return self._resolve("email_sender", DjangoEmailSender)

    @property
    def transaction_runner(self) -> ITransactionRunner:
        return self._resolve("transaction_runner", DjangoTransactionRunner)

    @property
    def code_generator(self) -> ICodeGenerator:
        return self._resolve("code_generator", RandomCodeGenerator)

    @property
    def string_mixer(self) -> IStringMixer:
        return self._resolve(
            "string_mixer", lambda: SecretStringMixer(_SECRET_MIXIN)
        )

    @property
    def password_policy(self) -> IPasswordPolicy:
        return self._resolve("password_policy", DefaultPasswordPolicy)

    @property
    def cpf_validator(self) -> ICPFValidator:
        return self._resolve("cpf_validator", BrazilianCPFValidator)

    @property
    def phone_validator(self) -> IPhoneValidator:
        return self._resolve("phone_validator", BrazilianPhoneValidator)

    @property
    def qr_encoder(self) -> IQRCodeEncoder:
        return self._resolve("qr_encoder", QRCodeEncoder)

    @property
    def cache(self) -> ICache:
        return self._resolve("cache", DjangoCache)

    # ------------------------------------------------------------------ #
    # repositories                                                       #
    # ------------------------------------------------------------------ #
    @property
    def user_repository(self):
        from users.repositories.user_repository import DjangoUserRepository

        return self._resolve("user_repository", DjangoUserRepository)

    @property
    def condominium_repository(self):
        from condominiums.repositories.condominium_repository import (
            DjangoCondominiumRepository,
        )

        return self._resolve("condominium_repository", DjangoCondominiumRepository)

    @property
    def reservable_location_repository(self):
        from reservations.repositories.reservable_location_repository import (
            DjangoReservableLocationRepository,
        )

        return self._resolve(
            "reservable_location_repository",
            DjangoReservableLocationRepository,
        )

    @property
    def reservation_repository(self):
        from reservations.repositories.reservation_repository import (
            DjangoReservationRepository,
        )

        return self._resolve(
            "reservation_repository", DjangoReservationRepository
        )

    @property
    def condo_payment_repository(self):
        from condo_payments.repositories.condo_payment_repository import (
            DjangoCondoPaymentRepository,
        )

        return self._resolve(
            "condo_payment_repository", DjangoCondoPaymentRepository
        )

    @property
    def delivery_notification_repository(self):
        from delivery_notification.repositories.delivery_notification_repository import (
            DjangoDeliveryNotificationRepository,
        )

        return self._resolve(
            "delivery_notification_repository",
            DjangoDeliveryNotificationRepository,
        )

    @property
    def service_request_repository(self):
        from service_requests.repositories.service_request_repository import (
            DjangoServiceRequestRepository,
        )

        return self._resolve(
            "service_request_repository", DjangoServiceRequestRepository
        )

    @property
    def sunny_vale_news_repository(self):
        from sunny_vale_news.repositories.sunny_vale_news_repository import (
            DjangoSunnyValeNewsRepository,
        )

        return self._resolve(
            "sunny_vale_news_repository", DjangoSunnyValeNewsRepository
        )

    @property
    def visitor_access_repository(self):
        from visitor_access.repositories.visitor_access_repository import (
            DjangoVisitorAccessRepository,
        )

        return self._resolve(
            "visitor_access_repository", DjangoVisitorAccessRepository
        )

    @property
    def visitor_group_repository(self):
        from visitor_access.repositories.visitor_group_repository import (
            DjangoVisitorGroupRepository,
        )

        return self._resolve(
            "visitor_group_repository", DjangoVisitorGroupRepository
        )

    @property
    def visitor_contact_repository(self):
        from visitor_access.repositories.visitor_contact_repository import (
            DjangoVisitorContactRepository,
        )

        return self._resolve(
            "visitor_contact_repository", DjangoVisitorContactRepository
        )

    @property
    def unit_repository(self):
        from units.repositories.unit_repository import DjangoUnitRepository

        return self._resolve("unit_repository", DjangoUnitRepository)

    @property
    def unit_membership_repository(self):
        from units.repositories.unit_membership_repository import (
            DjangoUnitMembershipRepository,
        )

        return self._resolve(
            "unit_membership_repository", DjangoUnitMembershipRepository
        )

    @property
    def unit_membership_decision_repository(self):
        from units.repositories.unit_membership_decision_repository import (
            DjangoUnitMembershipDecisionRepository,
        )

        return self._resolve(
            "unit_membership_decision_repository",
            DjangoUnitMembershipDecisionRepository,
        )

    # ------------------------------------------------------------------ #
    # services                                                           #
    # ------------------------------------------------------------------ #
    @property
    def user_service(self):
        from users.services.user_service import UserService

        return self._resolve(
            "user_service",
            lambda: UserService(
                user_repository=self.user_repository,
                password_policy=self.password_policy,
                cpf_validator=self.cpf_validator,
                phone_validator=self.phone_validator,
                membership_repository=self.unit_membership_repository,
                transaction_runner=self.transaction_runner,
            ),
        )

    @property
    def condominium_service(self):
        from condominiums.services.condominium_service import CondominiumService

        return self._resolve(
            "condominium_service",
            lambda: CondominiumService(
                repository=self.condominium_repository,
                code_generator=self.code_generator,
            ),
        )

    @property
    def reservable_location_service(self):
        from reservations.services.reservable_location_service import (
            ReservableLocationService,
        )

        return self._resolve(
            "reservable_location_service",
            lambda: ReservableLocationService(
                repository=self.reservable_location_repository,
                condominium_repository=self.condominium_repository,
            ),
        )

    @property
    def reservation_service(self):
        from reservations.services.reservation_service import ReservationService

        return self._resolve(
            "reservation_service",
            lambda: ReservationService(
                repository=self.reservation_repository,
                location_repository=self.reservable_location_repository,
                membership_repository=self.unit_membership_repository,
                user_repository=self.user_repository,
                email_sender=self.email_sender,
            ),
        )

    @property
    def condo_payment_service(self):
        from condo_payments.services.condo_payment_service import CondoPaymentService

        return self._resolve(
            "condo_payment_service",
            lambda: CondoPaymentService(repository=self.condo_payment_repository),
        )

    @property
    def delivery_notification_service(self):
        from delivery_notification.services.delivery_notification_service import (
            DeliveryNotificationService,
        )

        return self._resolve(
            "delivery_notification_service",
            lambda: DeliveryNotificationService(
                repository=self.delivery_notification_repository,
                unit_repository=self.unit_repository,
                membership_repository=self.unit_membership_repository,
                email_sender=self.email_sender,
            ),
        )

    @property
    def service_request_service(self):
        from service_requests.services.service_request_service import (
            ServiceRequestService,
        )

        return self._resolve(
            "service_request_service",
            lambda: ServiceRequestService(
                repository=self.service_request_repository,
                email_sender=self.email_sender,
            ),
        )

    @property
    def sunny_vale_news_service(self):
        from sunny_vale_news.services.sunny_vale_news_service import (
            SunnyValeNewsService,
        )

        return self._resolve(
            "sunny_vale_news_service",
            lambda: SunnyValeNewsService(repository=self.sunny_vale_news_repository),
        )

    @property
    def visitor_access_service(self):
        from visitor_access.services.visitor_access_service import VisitorAccessService

        return self._resolve(
            "visitor_access_service",
            lambda: VisitorAccessService(
                repository=self.visitor_access_repository,
                group_repository=self.visitor_group_repository,
                email_sender=self.email_sender,
                code_generator=self.code_generator,
                qr_encoder=self.qr_encoder,
            ),
        )

    @property
    def visitor_group_service(self):
        from visitor_access.services.visitor_group_service import VisitorGroupService

        return self._resolve(
            "visitor_group_service",
            lambda: VisitorGroupService(
                repository=self.visitor_group_repository,
                visitor_access_service=self.visitor_access_service,
            ),
        )

    @property
    def visitor_contact_service(self):
        from visitor_access.services.visitor_contact_service import VisitorContactService

        return self._resolve(
            "visitor_contact_service",
            lambda: VisitorContactService(
                repository=self.visitor_contact_repository,
                visitor_access_service=self.visitor_access_service,
            ),
        )

    @property
    def unit_service(self):
        from units.services.unit_service import UnitService

        return self._resolve(
            "unit_service",
            lambda: UnitService(
                unit_repository=self.unit_repository,
                membership_repository=self.unit_membership_repository,
                condominium_repository=self.condominium_repository,
            ),
        )

    @property
    def unit_membership_service(self):
        from units.services.unit_membership_service import UnitMembershipService

        return self._resolve(
            "unit_membership_service",
            lambda: UnitMembershipService(
                membership_repository=self.unit_membership_repository,
                unit_repository=self.unit_repository,
                user_repository=self.user_repository,
                email_sender=self.email_sender,
                decision_repository=self.unit_membership_decision_repository,
                transaction_runner=self.transaction_runner,
            ),
        )

    @property
    def unit_membership_decision_service(self):
        from units.services.unit_membership_decision_service import (
            UnitMembershipDecisionService,
        )

        return self._resolve(
            "unit_membership_decision_service",
            lambda: UnitMembershipDecisionService(
                decision_repository=self.unit_membership_decision_repository,
                membership_repository=self.unit_membership_repository,
                unit_repository=self.unit_repository,
            ),
        )

    @property
    def signup_service(self):
        from units.services.signup_service import SignupService

        return self._resolve(
            "signup_service",
            lambda: SignupService(
                user_service=self.user_service,
                membership_service=self.unit_membership_service,
                condominium_service=self.condominium_service,
                unit_repository=self.unit_repository,
                cache=self.cache,
                code_generator=self.code_generator,
                email_sender=self.email_sender,
            ),
        )

    @property
    def unit_signup_service(self):
        return self.signup_service

    @property
    def auth_service(self):
        from users.services.auth_service import AuthService

        return self._resolve(
            "auth_service",
            lambda: AuthService(
                user_repository=self.user_repository,
                membership_repository=self.unit_membership_repository,
            ),
        )

    @property
    def admin_dashboard_service(self):
        from admin_dashboard.services.admin_dashboard_service import (
            AdminDashboardService,
        )

        return self._resolve(
            "admin_dashboard_service",
            lambda: AdminDashboardService(
                user_repository=self.user_repository,
                reservation_repository=self.reservation_repository,
                news_repository=self.sunny_vale_news_repository,
                cache=self.cache,
            ),
        )

    @property
    def employee_dashboard_service(self):
        from employee_dashboard.services.employee_dashboard_service import (
            EmployeeDashboardService,
        )

        return self._resolve(
            "employee_dashboard_service",
            lambda: EmployeeDashboardService(
                delivery_repository=self.delivery_notification_repository,
                visitor_repository=self.visitor_access_repository,
                service_request_repository=self.service_request_repository,
            ),
        )


container = Container()
