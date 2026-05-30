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

from shared.infrastructure.code_generator import ICodeGenerator, RandomCodeGenerator
from shared.infrastructure.email_sender import DjangoEmailSender, IEmailSender
from shared.infrastructure.password_policy import (
    DefaultPasswordPolicy,
    IPasswordPolicy,
)
from shared.infrastructure.string_mixer import IStringMixer, SecretStringMixer


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
    def visitor_access_base_url(self) -> str:
        return self._overrides.get("visitor_access_base_url", _VISITOR_ACCESS_BASE_URL)

    # ------------------------------------------------------------------ #
    # repositories                                                       #
    # ------------------------------------------------------------------ #
    @property
    def user_repository(self):
        from users.repositories.user_repository import DjangoUserRepository

        return self._resolve("user_repository", DjangoUserRepository)

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
            ),
        )

    @property
    def bbq_service(self):
        from bbq_reservations.services.bbq_service import BBQReservationService

        return self._resolve(
            "bbq_service",
            lambda: BBQReservationService(repository=self.bbq_repository),
        )

    @property
    def hall_service(self):
        from hall_reservations.services.hall_service import HallReservationService

        return self._resolve(
            "hall_service",
            lambda: HallReservationService(repository=self.hall_repository),
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
                user_repository=self.user_repository,
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
            lambda: ServiceRequestService(repository=self.service_request_repository),
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
                email_sender=self.email_sender,
                code_generator=self.code_generator,
                string_mixer=self.string_mixer,
                visitor_access_base_url=self.visitor_access_base_url,
            ),
        )


container = Container()
