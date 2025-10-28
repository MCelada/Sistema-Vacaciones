from __future__ import annotations

from datetime import date, timedelta
import holidays
from typing import Dict, Tuple
from django.core.mail import send_mail

from .models import PublicHoliday, LeavePolicy, LeaveBalance, LeaveRequest


def parse_date(value: str) -> date:
	parts = [int(p) for p in value.split('-')]
	return date(parts[0], parts[1], parts[2])


def calculate_seniority_years(hire_date: date, for_year: int) -> int:
	end_of_year = date(for_year, 12, 31)
	return max(0, end_of_year.year - hire_date.year)


def resolve_total_vacation_days(seniority_years: int) -> int:
	policy = (
		LeavePolicy.objects
		.filter(min_seniority_years__lte=seniority_years, max_seniority_years__gt=seniority_years)
		.order_by('min_seniority_years')
		.first()
	)
	if policy is None:
		# Fallback: highest tier
		policy = LeavePolicy.objects.order_by('-max_seniority_years').first()
	return policy.allotted_vacation_days if policy else 14


def compute_cct_days(seniority_years: int, total_vacation_days: int) -> int:
	if seniority_years >= 10:
		return 3
	if seniority_years < 10 and total_vacation_days >= 16:
		return 2
	return 0


def round_nearest(n: float) -> int:
	return int(round(n))


def compute_allotments(total_vacation_days: int, cct_days: int) -> Tuple[int, int]:
	base = max(0, total_vacation_days - cct_days)
	workdays = round_nearest(base * (5.0 / 7.0))
	holiday = max(0, total_vacation_days - workdays - cct_days)
	return workdays, holiday


def calculate_annual_allotment(balance: LeaveBalance, hire_date: date) -> None:
	seniority = calculate_seniority_years(hire_date, balance.year)
	standard_days = resolve_total_vacation_days(seniority)

	# Proportional leave for employees who did not work the full year
	year_start = date(balance.year, 1, 1)
	year_end = date(balance.year, 12, 31)
	if hire_date.year == balance.year and hire_date > year_start:
		days_worked = (year_end - hire_date).days + 1
		total_days = proportional_days(days_worked, standard_days)
	else:
		total_days = standard_days

	cct = compute_cct_days(seniority, total_days)
	work, holiday = compute_allotments(total_days, cct)
	balance.allotted_workdays = work
	balance.allotted_holiday_leave = holiday
	balance.allotted_cct_days = cct


def proportional_days(days_worked_in_year: int, standard_days: int) -> int:
	return round_nearest((days_worked_in_year / 365.0) * standard_days)


def business_days_between(start: date, end: date) -> Tuple[int, int]:
	holiday_dates = set(PublicHoliday.objects.filter(date__range=(start, end)).values_list('date', flat=True))
	total = 0
	holiday_days = 0
	cur = start
	while cur <= end:
		if cur.weekday() < 5:  # Mon-Fri
			total += 1
			if cur in holiday_dates:
				holiday_days += 1
		cur += timedelta(days=1)
	workdays = total - holiday_days
	return workdays, holiday_days



def calculate_advanced_leave_deduction(req: 'LeaveRequest', balance: 'LeaveBalance') -> Dict[str, int]:
	"""
	Implements advanced deduction logic for CCT and non-CCT leave requests.
	Returns a dict with the deducted amounts for each bucket.
	"""
	start_date = req.start_date
	end_date = req.end_date
	year = start_date.year
	today = date.today()
	applied = {
		'cct_days_deducted': 0,
		'business_days_deducted': 0,
		'holidays_deducted': 0,
	}
	if req.is_cct_leave:
		# ...existing code...
		total_days = (end_date - start_date).days + 1
		prev = balance.cct_days_previous_year
		curr = balance.cct_days_current_year
		if prev >= total_days:
			balance.cct_days_previous_year -= total_days
			applied['cct_days_deducted'] = total_days
		else:
			balance.cct_days_previous_year = 0
			remainder = total_days - prev
			if curr >= remainder:
				balance.cct_days_current_year -= remainder
				applied['cct_days_deducted'] = total_days
			else:
				# Not enough balance
				raise Exception('Insufficient CCT leave balance')
	else:
		# For every 7 days, deduct 5 business days and 2 holidays
		total_days = (end_date - start_date).days + 1
		weeks = total_days // 7
		business_days = weeks * 5
		holiday_days = weeks * 2
		# Deduct business days
		prev = balance.business_days_previous_year
		curr = balance.business_days_current_year
		if prev >= business_days:
			balance.business_days_previous_year -= business_days
			applied['business_days_deducted'] = business_days
		else:
			balance.business_days_previous_year = 0
			remainder = business_days - prev
			if curr >= remainder:
				balance.business_days_current_year -= remainder
				applied['business_days_deducted'] = business_days
			else:
				raise Exception('Insufficient business days balance')
		# Deduct holidays
		prev_h = balance.holidays_previous_year
		curr_h = balance.holidays_current_year
		if prev_h >= holiday_days:
			balance.holidays_previous_year -= holiday_days
			applied['holidays_deducted'] = holiday_days
		else:
			balance.holidays_previous_year = 0
			remainder_h = holiday_days - prev_h
			if curr_h >= remainder_h:
				balance.holidays_current_year -= remainder_h
				applied['holidays_deducted'] = holiday_days
			else:
				raise Exception('Insufficient holidays balance')
	balance.save()
	return applied


def available_buckets(balance: LeaveBalance) -> Dict[str, int]:
	work = balance.allotted_workdays + balance.carried_over_workdays - balance.taken_workdays
	holiday = balance.allotted_holiday_leave + balance.carried_over_holiday_leave - balance.taken_holiday_leave
	cct = balance.allotted_cct_days + balance.carried_over_cct_days - balance.taken_cct_days
	return {'workdays': max(0, work), 'holiday': max(0, holiday), 'cct': max(0, cct)}


def apply_debit_order(balance: LeaveBalance, breakdown: Dict[str, int]) -> Tuple[bool, Dict[str, int]]:
	buckets = available_buckets(balance)
	needed_work = breakdown['workdays']
	needed_holiday = breakdown['holiday']

	applied = {'cct': 0, 'workdays': 0, 'holiday': 0}

	# Use CCT first
	use_cct = min(buckets['cct'], needed_work + needed_holiday)
	applied['cct'] = use_cct
	remaining = needed_work + needed_holiday - use_cct

	# Then workdays
	use_work = min(buckets['workdays'], remaining)
	applied['workdays'] = use_work
	remaining -= use_work

	# Then holiday leave
	use_holiday = min(buckets['holiday'], remaining)
	applied['holiday'] = use_holiday
	remaining -= use_holiday

	if remaining > 0:
		return False, applied

	# Apply deductions to taken counters
	balance.taken_cct_days += applied['cct']
	balance.taken_workdays += applied['workdays']
	balance.taken_holiday_leave += applied['holiday']
	return True, applied


def refund_request(req: LeaveRequest) -> None:
	balance = LeaveBalance.objects.filter(employee=req.employee, year=req.start_date.year).first()
	if not balance:
		return
	balance.taken_cct_days = max(0, balance.taken_cct_days - req.cct_days_deducted)
	balance.taken_workdays = max(0, balance.taken_workdays - req.workdays_deducted)
	balance.taken_holiday_leave = max(0, balance.taken_holiday_leave - req.holiday_leave_deducted)
	balance.save()


def send_request_notifications(req: LeaveRequest, created: bool = False, approved: bool = False, rejected: bool = False) -> None:
	subject = 'Solicitud de Vacaciones'
	if created:
		subject += ' - Recibida'
	if approved:
		subject += ' - Aprobada'
	if rejected:
		subject += ' - Rechazada'
	body = (
		f"Empleado: {req.employee.full_name}\n"
		f"Periodo: {req.start_date} a {req.end_date}\n"
		f"Estado: {req.status}\n"
		f"Descuentos - CCT: {req.cct_days_deducted}, Hábiles: {req.workdays_deducted}, Feriados: {req.holiday_leave_deducted}\n"
	)
	# Simple console email by default; can be configured with SMTP in settings
	recipients = []
	if req.employee and req.employee.users.exists():
		recipients = [u.email for u in req.employee.users.all() if u.email]
	send_mail(subject, body, 'no-reply@example.com', recipients, fail_silently=True)

