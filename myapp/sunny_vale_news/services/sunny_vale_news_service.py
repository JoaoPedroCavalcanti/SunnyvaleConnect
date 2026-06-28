"""Business rules for SunnyVale news."""

from abc import ABC, abstractmethod

from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from shared.tenant import assert_same_condominium, require_condominium_id
from sunny_vale_news.models import SunnyValeNewsModel
from sunny_vale_news.repositories.sunny_vale_news_repository import (
    ISunnyValeNewsRepository,
)


_VALID_KINDS = {choice for choice, _ in SunnyValeNewsModel.Kind.choices}


class ISunnyValeNewsService(ABC):
    @abstractmethod
    def list(self, user, kind: str | None = None): ...

    @abstractmethod
    def get(self, user, news_id: int) -> SunnyValeNewsModel: ...

    @abstractmethod
    def create(self, user, payload: dict) -> SunnyValeNewsModel: ...

    @abstractmethod
    def update(self, user, news_id: int, payload: dict) -> SunnyValeNewsModel: ...

    @abstractmethod
    def delete(self, user, news_id: int) -> None: ...


class SunnyValeNewsService(ISunnyValeNewsService):
    def __init__(self, repository: ISunnyValeNewsRepository):
        self._repo = repository

    @staticmethod
    def _require_admin(user) -> None:
        if not getattr(user, "is_staff", False):
            raise PermissionDeniedError(
                "Only staff users can perform this action."
            )

    def list(self, user, kind=None):
        condominium_id = require_condominium_id(user)
        if kind is not None:
            if kind not in _VALID_KINDS:
                raise BusinessRuleError(
                    message=f"Invalid kind filter: {kind!r}.", field="kind"
                )
            return self._repo.list_by_kind(kind, condominium_id=condominium_id)
        return self._repo.list_all(condominium_id=condominium_id)

    def get(self, user, news_id):
        instance = self._repo.get_by_id(news_id)
        if not instance:
            raise NotFoundError("No news matches the given query.")
        assert_same_condominium(user, instance.condominium_id)
        return instance

    def create(self, user, payload):
        self._require_admin(user)
        data = dict(payload)
        # Authorship is stamped from the authenticated user, never from
        # the request payload — front cannot impersonate someone else.
        data["created_by"] = user
        data["author"] = getattr(user, "full_name", "") or user.username
        data["author_role"] = getattr(user, "role", "") or ""
        data["condominium_id"] = require_condominium_id(user)
        return self._repo.create(data)

    def update(self, user, news_id, payload):
        self._require_admin(user)
        instance = self.get(user, news_id)
        # Authorship snapshot is intentionally immutable on edits.
        data = {
            k: v
            for k, v in payload.items()
            if k not in {"created_by", "author", "author_role"}
        }
        return self._repo.update(instance, data)

    def delete(self, user, news_id):
        self._require_admin(user)
        instance = self.get(user, news_id)
        self._repo.delete(instance)
