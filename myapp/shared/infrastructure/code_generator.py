"""Random access-code generator abstraction."""

import random
import secrets
import string
from abc import ABC, abstractmethod

_ALPHANUM = string.ascii_uppercase + string.digits


class ICodeGenerator(ABC):
    @abstractmethod
    def five_digits(self) -> str: ...

    @abstractmethod
    def six_digits(self) -> str: ...

    @abstractmethod
    def alphanumeric(self, length: int = 5) -> str: ...


class RandomCodeGenerator(ICodeGenerator):
    def five_digits(self) -> str:
        return "".join(str(random.randint(0, 9)) for _ in range(5))

    def six_digits(self) -> str:
        return "".join(str(random.randint(0, 9)) for _ in range(6))

    def alphanumeric(self, length: int = 5) -> str:
        return "".join(secrets.choice(_ALPHANUM) for _ in range(length))
