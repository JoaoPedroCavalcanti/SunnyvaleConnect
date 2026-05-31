from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    first_name = None
    last_name = None

    full_name = models.CharField(max_length=150)
    birth_date = models.DateField()
    cpf = models.CharField(max_length=11, unique=True)
    phone = models.CharField(max_length=11)
    apartment = models.CharField(max_length=10)
    block = models.CharField(max_length=10, blank=True, default="")
    photo = models.ImageField(upload_to="users/photos/", blank=True, null=True)

    REQUIRED_FIELDS = ["email", "full_name", "birth_date", "cpf", "phone", "apartment"]

    def __str__(self) -> str:
        return self.full_name or self.username
