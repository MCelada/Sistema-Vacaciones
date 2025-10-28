from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_EMPLOYEE = 'employee'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = (
        (ROLE_EMPLOYEE, 'Employee'),
        (ROLE_ADMIN, 'Admin'),
    )

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_EMPLOYEE)

    # Link to employee profile (nullable until created)
    employee = models.ForeignKey('leave.Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='users')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"
from django.db import models

# Create your models here.
