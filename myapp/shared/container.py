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
    def bbq_repository(self):
        from bbq_reservations.repositories.bbq_repository import DjangoBBQRepository

        return self._resolve("bbq_repository", DjangoBBQRepository)

    @property
    def hall_repository(self):
        from hall_reservations.repositories.hall_repository import DjangoHallRepository

        return self._resolve("hall_repository", DjangoHallRepository)

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
    def household_repository(self):
        from households.repositories.household_repository import (
            DjangoHouseholdRepository,
        )

        return self._resolve("household_repository", DjangoHouseholdRepository)

    @property
    def membership_repository(self):
        from households.repositories.membership_repository import (
            DjangoMembershipRepository,
        )

        return self._resolve("membership_repository", DjangoMembershipRepository)

    @property
    def dependent_repository(self):
        from households.repositories.dependent_repository import (
            DjangoDependentRepository,
        )

        return self._resolve("dependent_repository", DjangoDependentRepository)

    @property
    def membership_decision_repository(self):
        from households.repositories.membership_decision_repository import (
            DjangoMembershipDecisionRepository,
        )

        return self._resolve(
            "membership_decision_repository",
            DjangoMembershipDecisionRepository,
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
    def bbq_service(self):
        from bbq_reservations.services.bbq_service import BBQReservationService

        return self._resolve(
            "bbq_service",
            lambda: BBQReservationService(
                repository=self.bbq_repository,
                membership_repository=self.membership_repository,
                email_sender=self.email_sender,
            ),
        )

    @property
    def hall_service(self):
        from hall_reservations.services.hall_service import HallReservationService

        return self._resolve(
            "hall_service",
            lambda: HallReservationService(
                repository=self.hall_repository,
                membership_repository=self.membership_repository,
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
                household_repository=self.household_repository,
                membership_repository=self.membership_repository,
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
    def household_service(self):
        from households.services.household_service import HouseholdService

        return self._resolve(
            "household_service",
            lambda: HouseholdService(
                household_repository=self.household_repository,
                membership_repository=self.membership_repository,
                user_repository=self.user_repository,
                email_sender=self.email_sender,
                transaction_runner=self.transaction_runner,
                condominium_repository=self.condominium_repository,
            ),
        )

    @property
    def membership_service(self):
        from households.services.membership_service import MembershipService

        return self._resolve(
            "membership_service",
            lambda: MembershipService(
                membership_repository=self.membership_repository,
                household_repository=self.household_repository,
                user_repository=self.user_repository,
                email_sender=self.email_sender,
                decision_repository=self.membership_decision_repository,
                transaction_runner=self.transaction_runner,
            ),
        )

    @property
    def membership_decision_service(self):
        from households.services.membership_decision_service import (
            MembershipDecisionService,
        )

        return self._resolve(
            "membership_decision_service",
            lambda: MembershipDecisionService(
                decision_repository=self.membership_decision_repository,
                membership_repository=self.membership_repository,
                household_repository=self.household_repository,
            ),
        )

    @property
    def dependent_service(self):
        from households.services.dependent_service import DependentService

        return self._resolve(
            "dependent_service",
            lambda: DependentService(
                dependent_repository=self.dependent_repository,
                membership_repository=self.membership_repository,
                household_repository=self.household_repository,
                user_repository=self.user_repository,
                cpf_validator=self.cpf_validator,
            ),
        )

    @property
    def signup_service(self):
        from households.services.signup_service import SignupService

        return self._resolve(
            "signup_service",
            lambda: SignupService(
                user_service=self.user_service,
                household_service=self.household_service,
                membership_service=self.membership_service,
                condominium_service=self.condominium_service,
            ),
        )

    @property
    def auth_service(self):
        from users.services.auth_service import AuthService

        return self._resolve(
            "auth_service",
            lambda: AuthService(
                user_repository=self.user_repository,
                membership_repository=self.membership_repository,
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
                bbq_repository=self.bbq_repository,
                hall_repository=self.hall_repository,
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
