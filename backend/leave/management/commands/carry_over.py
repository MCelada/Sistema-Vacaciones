from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date

from leave.models import LeaveBalance


class Command(BaseCommand):
    help = 'Carry over unused balances to next year for all employees.'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, default=date.today().year)

    def handle(self, *args, **options):
        year = options['year']
        next_year = year + 1
        self.stdout.write(f"Carrying over balances from {year} to {next_year}...")
        with transaction.atomic():
            for bal in LeaveBalance.objects.select_related('employee').filter(year=year):
                remain_work = max(0, (bal.allotted_workdays + bal.carried_over_workdays) - bal.taken_workdays)
                remain_holiday = max(0, (bal.allotted_holiday_leave + bal.carried_over_holiday_leave) - bal.taken_holiday_leave)
                remain_cct = max(0, (bal.allotted_cct_days + bal.carried_over_cct_days) - bal.taken_cct_days)

                next_bal, _ = LeaveBalance.objects.get_or_create(employee=bal.employee, year=next_year)
                next_bal.carried_over_workdays = remain_work
                next_bal.carried_over_holiday_leave = remain_holiday
                next_bal.carried_over_cct_days = remain_cct
                next_bal.save()
        self.stdout.write(self.style.SUCCESS('Done.'))

