from django.contrib.auth import get_user_model
from django.db import models


class Unit(models.Model):
    class Kind(models.TextChoices):
        NAMED = "NAMED", "Named"
        APARTMENT = "APARTMENT", "Apartment"
        APARTMENT_BLOCK = "APARTMENT_BLOCK", "Apartment block"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ARCHIVED = "ARCHIVED", "Archived"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    name = models.CharField(max_length=100, blank=True, default="")
    apartment = models.CharField(max_length=10, blank=True, default="")
    block = models.CharField(max_length=50, blank=True, default="")

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    condominium = models.ForeignKey(
        "condominiums.Condominium",
        on_delete=models.PROTECT,
        related_name="units",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "name"],
                condition=models.Q(kind="NAMED"),
                name="uniq_unit_condominium_name_named",
            ),
            models.UniqueConstraint(
                fields=["condominium", "apartment"],
                condition=models.Q(kind="APARTMENT"),
                name="uniq_unit_condominium_apartment",
            ),
            models.UniqueConstraint(
                fields=["condominium", "apartment", "block"],
                condition=models.Q(kind="APARTMENT_BLOCK"),
                name="uniq_unit_condominium_apartment_block",
            ),
        ]
        ordering = ["kind", "block", "apartment", "name"]

    def display_name(self) -> str:
        if self.kind == self.Kind.NAMED:
            return self.name
        if self.kind == self.Kind.APARTMENT:
            return f"Apt {self.apartment}"
        if self.block:
            return f"Apt {self.apartment} / Block {self.block}"
        return f"Apt {self.apartment}"

    def normalize_identifiers(self) -> None:
        """Canonical form for apt/block codes (case-insensitive uniqueness)."""
        self.apartment = (self.apartment or "").strip().upper()
        self.block = (self.block or "").strip().upper()
        self.name = (self.name or "").strip()

    def save(self, *args, **kwargs):
        self.normalize_identifiers()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.display_name()


class UnitMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        RESIDENT = "RESIDENT", "Resident"

    class Status(models.TextChoices):
        PENDING_ADMIN = "PENDING_ADMIN", "Pending admin approval"
        PENDING_OWNER = "PENDING_OWNER", "Pending owner approval"
        ACTIVE = "ACTIVE", "Active"
        LEFT = "LEFT", "Left"

    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="unit_memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    status = models.CharField(max_length=20, choices=Status.choices)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unit", "user"],
                name="uniq_unit_membership_unit_user",
            )
        ]
        ordering = ["unit_id", "id"]

    def __str__(self) -> str:
        return f"{self.user_id}@{self.unit_id} ({self.role}/{self.status})"


class UnitMembershipDecision(models.Model):
    """Immutable audit row for membership approvals and rejections."""

    class Action(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="membership_decisions",
    )
    unit_kind = models.CharField(max_length=20)
    unit_name = models.CharField(max_length=100, blank=True, default="")
    unit_apartment = models.CharField(max_length=10, blank=True, default="")
    unit_block = models.CharField(max_length=50, blank=True, default="")
    unit_display_name = models.CharField(max_length=160)

    actor = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    actor_username = models.CharField(max_length=150, blank=True, default="")
    actor_full_name = models.CharField(max_length=150, blank=True, default="")

    target = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    target_username = models.CharField(max_length=150, blank=True, default="")
    target_full_name = models.CharField(max_length=150, blank=True, default="")
    target_email = models.EmailField(blank=True, default="")

    action = models.CharField(max_length=20, choices=Action.choices)
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["unit", "-created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.action} {self.target_username or '?'} "
            f"@{self.unit_display_name}"
        )
