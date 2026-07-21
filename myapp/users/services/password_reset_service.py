"""Password reset via email OTP (forgot-password flow)."""

from abc import ABC, abstractmethod

from shared.exceptions import BusinessRuleError
from shared.infrastructure.cache import ICache
from shared.infrastructure.code_generator import ICodeGenerator
from shared.infrastructure.email_sender import IEmailSender
from shared.infrastructure.password_policy import IPasswordPolicy
from users.repositories.user_repository import IUserRepository

_OTP_TTL_SECONDS = 15 * 60
_RESEND_TTL_SECONDS = 60


class IPasswordResetService(ABC):
    @abstractmethod
    def request_reset(self, email: str) -> None: ...

    @abstractmethod
    def confirm_reset(self, email: str, code: str, new_password: str) -> None: ...

    @abstractmethod
    def resend_code(self, email: str) -> None: ...


class PasswordResetService(IPasswordResetService):
    def __init__(
        self,
        user_repository: IUserRepository,
        cache: ICache,
        code_generator: ICodeGenerator,
        email_sender: IEmailSender,
        password_policy: IPasswordPolicy,
    ):
        self._users = user_repository
        self._cache = cache
        self._codes = code_generator
        self._email = email_sender
        self._policy = password_policy

    def request_reset(self, email: str) -> None:
        """Always succeeds outwardly; only sends OTP when the account exists."""
        user = self._users.get_by_email((email or "").lower().strip())
        if not user or not user.email:
            return
        self._issue_code(user)

    def confirm_reset(self, email: str, code: str, new_password: str) -> None:
        normalized = (email or "").lower().strip()
        pending = self._cache.get(self._otp_key(normalized))
        if pending is None or str(pending) != str(code).strip():
            raise BusinessRuleError("Código de verificação inválido ou expirado.")

        errors = self._policy.validate(new_password or "")
        if errors:
            raise BusinessRuleError(message=errors, field="new_password")

        user = self._users.get_by_email(normalized)
        if not user:
            raise BusinessRuleError("Código de verificação inválido ou expirado.")

        self._users.update(user, {"password": new_password})
        self._cache.delete(self._otp_key(normalized))
        self._cache.delete(self._resend_key(normalized))

    def resend_code(self, email: str) -> None:
        normalized = (email or "").lower().strip()
        user = self._users.get_by_email(normalized)
        # Same opaque response surface as request_reset for unknown emails,
        # but rate-limit when a pending OTP already exists.
        if self._cache.get(self._resend_key(normalized)) is not None:
            raise BusinessRuleError(
                "Aguarde antes de solicitar outro código de verificação."
            )
        if not user or not user.email:
            self._cache.set(self._resend_key(normalized), "1", _RESEND_TTL_SECONDS)
            return
        if self._cache.get(self._otp_key(normalized)) is None:
            # No active reset session — start one instead of failing loudly.
            self._issue_code(user)
            self._cache.set(self._resend_key(normalized), "1", _RESEND_TTL_SECONDS)
            return
        self._issue_code(user)
        self._cache.set(self._resend_key(normalized), "1", _RESEND_TTL_SECONDS)

    def _issue_code(self, user) -> None:
        code = self._codes.six_digits()
        email = (user.email or "").lower().strip()
        self._cache.set(self._otp_key(email), code, _OTP_TTL_SECONDS)
        self._email.send_password_reset_code(
            to_email=email,
            user_name=user.full_name or user.username,
            code=code,
        )

    def _otp_key(self, email: str) -> str:
        return f"password_reset:{(email or '').lower().strip()}"

    def _resend_key(self, email: str) -> str:
        return f"password_reset_resend:{(email or '').lower().strip()}"
