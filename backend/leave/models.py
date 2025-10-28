from django.db import models


class Employee(models.Model):
    employee_id_legacy = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=200)
    position = models.CharField(max_length=200, blank=True)
    office = models.CharField(max_length=200, blank=True)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.employee_id_legacy})"


class LeavePolicy(models.Model):
    min_seniority_years = models.IntegerField()
    max_seniority_years = models.IntegerField()
    allotted_vacation_days = models.IntegerField()

    class Meta:
        ordering = ['min_seniority_years']

    def __str__(self) -> str:
        return f"{self.min_seniority_years}-{self.max_seniority_years}: {self.allotted_vacation_days}"


class LeaveBalance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    year = models.IntegerField()

    allotted_workdays = models.IntegerField(default=0)
    allotted_holiday_leave = models.IntegerField(default=0)
    allotted_cct_days = models.IntegerField(default=0)

    carried_over_workdays = models.IntegerField(default=0)
    carried_over_holiday_leave = models.IntegerField(default=0)
    carried_over_cct_days = models.IntegerField(default=0)

    taken_workdays = models.IntegerField(default=0)
    taken_holiday_leave = models.IntegerField(default=0)
    taken_cct_days = models.IntegerField(default=0)

    # New detailed yearly breakdown fields
    cct_days_previous_year = models.IntegerField(default=0)
    cct_days_current_year = models.IntegerField(default=0)
    business_days_previous_year = models.IntegerField(default=0)
    business_days_current_year = models.IntegerField(default=0)
    holidays_previous_year = models.IntegerField(default=0)
    holidays_current_year = models.IntegerField(default=0)

    class Meta:
        unique_together = ('employee', 'year')

    def __str__(self) -> str:
        return f"Balance {self.employee} - {self.year}"


class PublicHoliday(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField(unique=True)

    class Meta:
        ordering = ['date']

    def __str__(self) -> str:
        return f"{self.name} ({self.date})"


class LeaveRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    is_cct_leave = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    request_date = models.DateTimeField(auto_now_add=True)

    workdays_deducted = models.IntegerField(default=0)
    holiday_leave_deducted = models.IntegerField(default=0)
    cct_days_deducted = models.IntegerField(default=0)
    proof_document = models.FileField(upload_to='proof_documents/', null=True, blank=True)

    class Meta:
        ordering = ['-request_date']

    def __str__(self) -> str:
        return f"Request {self.employee} {self.start_date} - {self.end_date} ({self.status})"
from django.db import models

# Create your models here.
