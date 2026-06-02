from django.contrib.auth import get_user_model
from django.db import models


class Household(models.Model):
    class Status(models.TextChoices):
        PENDING_ADMIN = "PENDING_ADMIN", "Pending admin approval"
        ACTIVE = "ACTIVE", "Active"
        ARCHIVED = "ARCHIVED", "Archived"

    apartment = models.CharField(max_length=10)
    block = models.CharField(max_length=10, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING_ADMIN
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["apartment", "block"], name="uniq_household_apartment_block"
            )
        ]
        ordering = ["block", "apartment"]

    def __str__(self) -> str:
        if self.block:
            return f"Apt {self.apartment} / Block {self.block}"
        return f"Apt {self.apartment}"


class HouseholdMembership(models.Model):
    class Role(models.TextChoices):
        HOLDER = "HOLDER", "Holder"
        RESIDENT = "RESIDENT", "Resident"

    class Status(models.TextChoices):
        PENDING_HOLDER = "PENDING_HOLDER", "Pending holder approval"
        PENDING_ADMIN = "PENDING_ADMIN", "Pending admin approval"
        ACTIVE = "ACTIVE", "Active"
        LEFT = "LEFT", "Left"

    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    status = models.CharField(max_length=20, choices=Status.choices)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["household", "user"],
                name="uniq_membership_household_user",
            )
        ]
        ordering = ["household_id", "id"]

    def __str__(self) -> str:
        return f"{self.user_id}@{self.household_id} ({self.role}/{self.status})"


class Dependent(models.Model):
    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="dependents"
    )
    full_name = models.CharField(max_length=150)
    birth_date = models.DateField()
    cpf = models.CharField(max_length=11, blank=True, default="")
    relationship = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["household_id", "full_name"]

    def __str__(self) -> str:
        return self.full_name
