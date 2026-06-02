from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    RESIDENT = "RESIDENT", "Resident"
    ADMIN = "ADMIN", "Admin"
    EMPLOYEE = "EMPLOYEE", "Employee"


class User(AbstractUser):
    first_name = None
    last_name = None

    full_name = models.CharField(max_length=150)
    birth_date = models.DateField()
    cpf = models.CharField(max_length=11, unique=True)
    phone = models.CharField(max_length=11)
    apartment = models.CharField(max_length=10, blank=True, default="")
    block = models.CharField(max_length=10, blank=True, default="")
    photo = models.ImageField(upload_to="users/photos/", blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.RESIDENT,
    )

    REQUIRED_FIELDS = ["email", "full_name", "birth_date", "cpf", "phone"]

    def __str__(self) -> str:
        return self.full_name or self.username
