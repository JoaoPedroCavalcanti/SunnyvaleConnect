"""Transaction abstraction so services can group writes atomically without
importing Django's ORM directly (and without forcing unit tests to spin up a
real database)."""

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager, contextmanager

from django.db import transaction


class ITransactionRunner(ABC):
    @abstractmethod
    def atomic(self) -> AbstractContextManager[None]: ...


class DjangoTransactionRunner(ITransactionRunner):
    def atomic(self) -> AbstractContextManager[None]:
        return transaction.atomic()


class NullTransactionRunner(ITransactionRunner):
    """No-op runner. Useful for unit tests with in-memory fakes where there
    is no real DB connection to wrap."""

    @contextmanager
    def atomic(self):
        yield
