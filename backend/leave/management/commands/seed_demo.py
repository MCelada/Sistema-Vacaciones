from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import date

from leave.models import Employee, LeavePolicy, PublicHoliday, LeaveBalance
from leave.utils import calculate_annual_allotment


class Command(BaseCommand):
    help = 'Seed demo data: 3 employees with users, base policies and some public holidays.'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, default=date.today().year)
        parser.add_argument('--password', type=str, default='Password123!')

    def handle(self, *args, **options):
        year = options['year']
        default_password = options['password']
        User = get_user_model()

        with transaction.atomic():
            # Policies (example tiers)
            if not LeavePolicy.objects.exists():
                LeavePolicy.objects.bulk_create([
                    LeavePolicy(min_seniority_years=0, max_seniority_years=5, allotted_vacation_days=14),
                    LeavePolicy(min_seniority_years=5, max_seniority_years=10, allotted_vacation_days=21),
                    LeavePolicy(min_seniority_years=10, max_seniority_years=20, allotted_vacation_days=28),
                    LeavePolicy(min_seniority_years=20, max_seniority_years=100, allotted_vacation_days=35),
                ])

            # Some holidays for the year
            base_holidays = [
                ('Año Nuevo', date(year, 1, 1)),
                ('Día de la Independencia', date(year, 7, 9)),
                ('Navidad', date(year, 12, 25)),
            ]
            for name, d in base_holidays:
                PublicHoliday.objects.get_or_create(name=name, date=d)

            # Create employees and users
            demo = [
                ('E001', 'Ana Gómez', 'Analista', 'Buenos Aires', date(year - 1, 3, 15), 'ana@example.com'),
                ('E002', 'Luis Pérez', 'Desarrollador', 'Córdoba', date(year - 6, 6, 1), 'luis@example.com'),
                ('E003', 'María López', 'RRHH', 'Mendoza', date(year - 12, 9, 20), 'maria@example.com'),
            ]
            for legajo, name, position, office, hire, email in demo:
                emp, _ = Employee.objects.get_or_create(
                    employee_id_legacy=legajo,
                    defaults={'full_name': name, 'position': position, 'office': office, 'hire_date': hire, 'is_active': True}
                )
                user, created = User.objects.get_or_create(email=email, defaults={'username': email.split('@')[0], 'role': 'employee'})
                if created:
                    user.set_password(default_password)
                user.employee = emp
                user.save()

                # Create balance and allot for current year
                bal, _ = LeaveBalance.objects.get_or_create(employee=emp, year=year)
                calculate_annual_allotment(bal, emp.hire_date)
                bal.save()

            # Create an admin user if not exists
            admin_email = 'admin@example.com'
            admin, created = User.objects.get_or_create(email=admin_email, defaults={'username': 'admin', 'role': 'admin', 'is_staff': True, 'is_superuser': True})
            if created:
                admin.set_password(default_password)
            admin.save()

        self.stdout.write(self.style.SUCCESS('Seeded demo data. Default password: %s' % default_password))

