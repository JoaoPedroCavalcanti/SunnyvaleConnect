"""Business rules for SunnyVale news."""

from abc import ABC, abstractmethod

from shared.exceptions import NotFoundError, PermissionDeniedError
from sunny_vale_news.models import SunnyValeNewsModel
from sunny_vale_news.repositories.sunny_vale_news_repository import (
    ISunnyValeNewsRepository,
)


class ISunnyValeNewsService(ABC):
    @abstractmethod
    def list(self): ...

    @abstractmethod
    def get(self, news_id: int) -> SunnyValeNewsModel: ...

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

    def list(self):
        return self._repo.list_all()

    def get(self, news_id):
        instance = self._repo.get_by_id(news_id)
        if not instance:
            raise NotFoundError("No news matches the given query.")
        return instance

    def create(self, user, payload):
        self._require_admin(user)
        return self._repo.create(payload)

    def update(self, user, news_id, payload):
        self._require_admin(user)
        instance = self.get(news_id)
        return self._repo.update(instance, payload)

    def delete(self, user, news_id):
        self._require_admin(user)
        instance = self.get(news_id)
        self._repo.delete(instance)
