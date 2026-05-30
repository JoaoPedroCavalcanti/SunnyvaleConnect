"""Random check-in / check-out code generator abstraction."""

import random
from abc import ABC, abstractmethod


class ICodeGenerator(ABC):
    @abstractmethod
    def five_digits(self) -> str: ...


class RandomCodeGenerator(ICodeGenerator):
    def five_digits(self) -> str:
        return "".join(str(random.randint(0, 9)) for _ in range(5))
