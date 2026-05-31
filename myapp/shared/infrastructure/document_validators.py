"""Document/contact validators for Brazilian inputs.

Pure functions, no Django/DRF imports — services use these and translate the
result to BusinessRuleError when needed.
"""

import re
from abc import ABC, abstractmethod


class ICPFValidator(ABC):
    @abstractmethod
    def validate(self, cpf: str) -> str | None:
        """Return error message, or None if valid."""

    @abstractmethod
    def normalize(self, cpf: str) -> str:
        """Strip mask, return digits-only."""


class IPhoneValidator(ABC):
    @abstractmethod
    def validate(self, phone: str) -> str | None: ...

    @abstractmethod
    def normalize(self, phone: str) -> str: ...


class BrazilianCPFValidator(ICPFValidator):
    def normalize(self, cpf: str) -> str:
        return re.sub(r"\D", "", cpf or "")

    def validate(self, cpf: str) -> str | None:
        digits = self.normalize(cpf)
        if len(digits) != 11:
            return "CPF must contain 11 digits."
        if digits == digits[0] * 11:
            return "CPF is invalid."
        for i in (9, 10):
            total = sum(int(digits[j]) * ((i + 1) - j) for j in range(i))
            check = (total * 10) % 11
            if check == 10:
                check = 0
            if check != int(digits[i]):
                return "CPF is invalid."
        return None


class BrazilianPhoneValidator(IPhoneValidator):
    """BR phone: 10 digits (landline) or 11 (mobile, with leading 9)."""

    def normalize(self, phone: str) -> str:
        return re.sub(r"\D", "", phone or "")

    def validate(self, phone: str) -> str | None:
        digits = self.normalize(phone)
        if len(digits) not in (10, 11):
            return "Phone must contain 10 or 11 digits (DDD + number)."
        if len(digits) == 11 and digits[2] != "9":
            return "Mobile phone must start with 9 after the area code."
        return None
