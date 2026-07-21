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
            errors.append("A senha deve conter ao menos uma letra maiúscula.")
        if len(password) < 8:
            errors.append("A senha deve ter no mínimo 8 caracteres.")
        if password.isalnum():
            errors.append(
                "A senha deve ter ao menos 1 caractere especial (ex: !$%*<)."
            )
        return errors
