"""Cache abstraction so services can be unit-tested without Django's cache."""

from abc import ABC, abstractmethod
from typing import Any

from django.core.cache import cache as django_cache


class ICache(ABC):
    @abstractmethod
    def get(self, key: str) -> Any | None: ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int) -> None: ...


class DjangoCache(ICache):
    def get(self, key):
        return django_cache.get(key)

    def set(self, key, value, ttl_seconds):
        django_cache.set(key, value, ttl_seconds)
