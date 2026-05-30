"""Password validation policy abstraction."""

from abc import ABC, abstractmethod


class IPasswordPolicy(ABC):
    @abstractmethod
    def validate(self, password: str) -> list[str]:
        """Return a list of error messages. Empty list = valid password."""


class DefaultPasswordPolicy(IPasswordPolicy):
    def validate(self, password: str) -> list[str]:
        errors: list[str] = []
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        if password.isalnum():
            errors.append(
                "Password must be have at least 1 special character(ex: !$%*<)."
            )
        return errors
