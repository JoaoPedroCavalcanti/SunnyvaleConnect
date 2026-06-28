from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    RESIDENT = "RESIDENT", "Resident"
    ADMIN = "ADMIN", "Admin"
    EMPLOYEE = "EMPLOYEE", "Employee"


class EmployeeType(models.TextChoices):
    DOORMAN = "DOORMAN", "Doorman"
    CLEANING = "CLEANING", "Cleaning"


class User(AbstractUser):
    first_name = None
    last_name = None

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=254, unique=True)
    full_name = models.CharField(max_length=150)
    birth_date = models.DateField()
    cpf = models.CharField(max_length=11)
    phone = models.CharField(max_length=11)
    apartment = models.CharField(max_length=10, blank=True, default="")
    block = models.CharField(max_length=10, blank=True, default="")
    photo = models.ImageField(upload_to="users/photos/", blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.RESIDENT,
    )
    employee_types = models.JSONField(default=list, blank=True)
    condominium = models.ForeignKey(
        "condominiums.Condominium",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )

    REQUIRED_FIELDS = ["email", "full_name", "birth_date", "cpf", "phone"]

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["condominium", "cpf"],
                name="uniq_user_condominium_cpf",
            ),
        ]

    def __str__(self) -> str:
        return self.full_name or self.username
