"""Business rules for condominiums (platform + public lookup)."""

from abc import ABC, abstractmethod

from condominiums.repositories.condominium_repository import ICondominiumRepository
from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from shared.infrastructure.code_generator import ICodeGenerator


_CODE_LENGTH = 8
_MAX_CODE_ATTEMPTS = 20


class ICondominiumService(ABC):
    @abstractmethod
    def lookup_by_code(self, code: str): ...

    @abstractmethod
    def resolve_for_signup(self, code: str): ...

    @abstractmethod
    def list_for_platform(self, user): ...

    @abstractmethod
    def create(self, user, payload: dict): ...


class CondominiumService(ICondominiumService):
    def __init__(
        self,
        repository: ICondominiumRepository,
        code_generator: ICodeGenerator,
    ):
        self._repo = repository
        self._codes = code_generator

    @staticmethod
    def _require_platform_superuser(user) -> None:
        if not getattr(user, "is_superuser", False):
            raise PermissionDeniedError(
                "Only platform superusers can manage condominiums."
            )

    def lookup_by_code(self, code: str):
        condominium = self._repo.get_by_code(code)
        if not condominium or not condominium.is_active:
            raise NotFoundError("Invalid or inactive condominium code.")
        return condominium

    def resolve_for_signup(self, code: str):
        return self.lookup_by_code(code)

    def list_for_platform(self, user):
        self._require_platform_superuser(user)
        return self._repo.list_all()

    def create(self, user, payload: dict):
        self._require_platform_superuser(user)
        data = dict(payload)
        data.pop("code", None)
        data["code"] = self._generate_unique_code()
        return self._repo.create(data)

    def _generate_unique_code(self) -> str:
        for _ in range(_MAX_CODE_ATTEMPTS):
            candidate = self._codes.alphanumeric(_CODE_LENGTH)
            if not self._repo.exists_with_code(candidate):
                return candidate
        raise BusinessRuleError(
            "Could not generate a unique condominium code. Try again."
        )
