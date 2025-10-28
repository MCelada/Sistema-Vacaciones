from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date

from leave.models import Employee, LeaveBalance
from leave.utils import calculate_annual_allotment


class Command(BaseCommand):
    help = 'Compute annual leave allotments for all active employees for a given year.'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, default=date.today().year)

    def handle(self, *args, **options):
        year = options['year']
        self.stdout.write(f"Calculating annual allotments for {year}...")
        with transaction.atomic():
            for emp in Employee.objects.filter(is_active=True):
                balance, _ = LeaveBalance.objects.get_or_create(employee=emp, year=year)
                calculate_annual_allotment(balance, emp.hire_date)
                balance.save()
        self.stdout.write(self.style.SUCCESS('Done.'))

