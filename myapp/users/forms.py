"""Django admin forms for User."""

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from shared.tenant import build_tenant_username, display_username, normalize_condominium_code
from users.models import User, UserRole


class _TenantUsernameMixin:
    def _condominium_from_form(self):
        if hasattr(self, "cleaned_data") and "condominium" in self.cleaned_data:
            return self.cleaned_data.get("condominium")
        if getattr(self, "instance", None) and self.instance.pk:
            return getattr(self.instance, "condominium", None)
        raw_id = (self.data.get("condominium") or "").strip()
        if raw_id.isdigit():
            from condominiums.models import Condominium

            return Condominium.objects.filter(pk=int(raw_id)).first()
        return None

    def _normalize_username(self, username: str) -> str:
        condominium = self._condominium_from_form()
        if not username:
            return username
        if condominium and condominium.code:
            code = normalize_condominium_code(condominium.code)
            prefix = f"{code}:"
            local = username
            if local.upper().startswith(prefix):
                local = local[len(prefix) :]
            return build_tenant_username(condominium.code, local)
        return username

    def clean_username(self):
        return self._normalize_username(self.cleaned_data.get("username", ""))

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        condominium = cleaned.get("condominium")
        is_superuser = cleaned.get("is_superuser", False)

        if is_superuser and condominium:
            self.add_error(
                "condominium",
                "Platform superusers cannot be linked to a condominium.",
            )
        if not is_superuser and not condominium:
            self.add_error(
                "condominium",
                "Select the condominium this account belongs to.",
            )

        if role == UserRole.ADMIN:
            cleaned["is_staff"] = True
        elif not is_superuser:
            cleaned["is_staff"] = False

        return cleaned


class SunnyvaleUserAddForm(_TenantUsernameMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "condominium",
            "username",
            "email",
            "full_name",
            "birth_date",
            "cpf",
            "phone",
            "apartment",
            "block",
            "role",
            "employee_types",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = (
            "Local username for condominium accounts (e.g. admin). "
            "Stored internally as CODE:username."
        )
        self.fields["condominium"].help_text = (
            "Required for condominium admins, residents and employees."
        )


class SunnyvaleUserChangeForm(_TenantUsernameMixin, UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.condominium_id:
            self.fields["username"].initial = display_username(self.instance)
            code = self.instance.condominium.code
            self.fields["username"].help_text = (
                f"Local username. Saved as {code}:<username>."
            )
