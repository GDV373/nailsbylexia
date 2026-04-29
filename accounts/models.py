from django.db import models

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "phone"]

    email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.email