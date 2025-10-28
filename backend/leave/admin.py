from django.contrib import admin
from .models import Employee, LeavePolicy, LeaveBalance, PublicHoliday, LeaveRequest


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'employee_id_legacy', 'position', 'office', 'hire_date', 'is_active')
    search_fields = ('full_name', 'employee_id_legacy', 'position', 'office')
    list_filter = ('is_active', 'office')


@admin.register(LeavePolicy)
class LeavePolicyAdmin(admin.ModelAdmin):
    list_display = ('min_seniority_years', 'max_seniority_years', 'allotted_vacation_days')
    list_filter = ('min_seniority_years', 'max_seniority_years')


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'year', 'allotted_workdays', 'allotted_holiday_leave', 'allotted_cct_days',
                    'carried_over_workdays', 'carried_over_holiday_leave', 'carried_over_cct_days',
                    'taken_workdays', 'taken_holiday_leave', 'taken_cct_days')
    list_filter = ('year',)
    search_fields = ('employee__full_name', 'employee__employee_id_legacy')


@admin.register(PublicHoliday)
class PublicHolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'date')
    list_filter = ('date',)
    search_fields = ('name',)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'start_date', 'end_date', 'status', 'request_date',
                    'workdays_deducted', 'holiday_leave_deducted', 'cct_days_deducted')
    list_filter = ('status', 'request_date')
    search_fields = ('employee__full_name', 'employee__employee_id_legacy')
from django.contrib import admin

# Register your models here.
