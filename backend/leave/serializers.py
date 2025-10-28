from rest_framework import serializers
from .models import Employee, LeavePolicy, PublicHoliday, LeaveBalance, LeaveRequest


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['id', 'employee_id_legacy', 'full_name', 'position', 'office', 'hire_date', 'is_active']


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ['id', 'min_seniority_years', 'max_seniority_years', 'allotted_vacation_days']


class PublicHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicHoliday
        fields = ['id', 'name', 'date']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            'id', 'employee', 'year',
            'allotted_workdays', 'allotted_holiday_leave', 'allotted_cct_days',
            'carried_over_workdays', 'carried_over_holiday_leave', 'carried_over_cct_days',
            'taken_workdays', 'taken_holiday_leave', 'taken_cct_days',
            'cct_days_previous_year', 'cct_days_current_year',
            'business_days_previous_year', 'business_days_current_year',
            'holidays_previous_year', 'holidays_current_year',
        ]


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    proof_document = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'start_date', 'end_date', 'is_cct_leave', 'status', 'request_date',
            'workdays_deducted', 'holiday_leave_deducted', 'cct_days_deducted', 'proof_document'
        ]
        read_only_fields = ['status', 'request_date', 'workdays_deducted', 'holiday_leave_deducted', 'cct_days_deducted']

