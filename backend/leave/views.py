from datetime import date
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Employee, LeavePolicy, PublicHoliday, LeaveBalance, LeaveRequest
from .serializers import (
    EmployeeSerializer, LeavePolicySerializer, PublicHolidaySerializer,
    LeaveBalanceSerializer, LeaveRequestSerializer,
)
from . import utils


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        role = getattr(request.user, 'role', None)
        return role in ('admin', 'hr_admin')


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'list', 'create_employee']:
            return [IsAdmin()]
        return super().get_permissions()

    @action(detail=False, methods=['post'], url_path='create-employee')
    def create_employee(self, request):
        # Only admins can create employees
        if not request.user or getattr(request.user, 'role', None) != 'admin':
            return Response({'detail': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
        data = request.data
        required_fields = ['last_name', 'first_name', 'employee_id', 'position', 'office', 'hire_date']
        for field in required_fields:
            if field not in data:
                return Response({'detail': f'Campo requerido: {field}'}, status=status.HTTP_400_BAD_REQUEST)
        full_name = f"{data['first_name']} {data['last_name']}"
        employee = Employee.objects.create(
            employee_id_legacy=data['employee_id'],
            full_name=full_name,
            position=data['position'],
            office=data['office'],
            hire_date=data['hire_date'],
            is_active=True
        )
        # Automate leave balance allocation
        from datetime import date
        today = date.today()
        hire_date = date.fromisoformat(data['hire_date'])
        years = today.year - hire_date.year - ((today.month, today.day) < (hire_date.month, hire_date.day))
        if years < 5:
            business_days = 10
            holidays = 4
            cct_days = 2
        elif years < 10:
            business_days = 15
            holidays = 6
            cct_days = 2
        elif years < 20:
            business_days = 20
            holidays = 8
            cct_days = 3
        else:
            business_days = 25
            holidays = 10
            cct_days = 3
        LeaveBalance.objects.create(
            employee=employee,
            year=today.year,
            business_days_current_year=business_days,
            holidays_current_year=holidays,
            cct_days_current_year=cct_days
        )
        serializer = EmployeeSerializer(employee)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LeavePolicyViewSet(viewsets.ModelViewSet):
    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]


class PublicHolidayViewSet(viewsets.ModelViewSet):
    queryset = PublicHoliday.objects.all()
    serializer_class = PublicHolidaySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveBalance.objects.select_related('employee').all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', None) == 'admin':
            return super().get_queryset()
        if hasattr(user, 'employee'):
            return self.queryset.filter(employee=user.employee)
        return self.queryset.none()

    @action(detail=True, methods=['patch'], url_path='edit-balance')
    def edit_balance(self, request, pk=None):
        # Require password for editing
        password = request.data.get('password')
        if password != 'Admin123!':
            return Response({'detail': 'Contraseña incorrecta'}, status=status.HTTP_403_FORBIDDEN)
        balance = self.get_object()
        editable_fields = ['business_days_current_year', 'holidays_current_year', 'cct_days_current_year']
        for field in editable_fields:
            if field in request.data:
                setattr(balance, field, request.data[field])
        balance.save()
        serializer = LeaveBalanceSerializer(balance)
        return Response(serializer.data)
        qs = self.get_queryset().filter(year=year)
        return Response(self.get_serializer(qs, many=True).data)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related('employee').all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', None) == 'admin':
            return super().get_queryset()
        if user.employee_id:
            return self.queryset.filter(employee_id=user.employee_id)
        return self.queryset.none()

    def create(self, request, *args, **kwargs):
        user = request.user
        if not user.employee_id:
            return Response({'detail': 'User not linked to employee'}, status=status.HTTP_400_BAD_REQUEST)
        start = request.data.get('start_date')
        end = request.data.get('end_date')
        if not start or not end:
            return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = utils.parse_date(start)
        end_date = utils.parse_date(end)
        if end_date < start_date:
            return Response({'detail': 'end_date before start_date'}, status=status.HTTP_400_BAD_REQUEST)
        if start_date < date.today():
            return Response({'detail': 'start_date cannot be in the past'}, status=status.HTTP_400_BAD_REQUEST)

        is_cct_leave = bool(request.data.get('is_cct_leave', True))
        total_days = (end_date - start_date).days + 1
        # Prevent duplicate leave requests
        if LeaveRequest.objects.filter(employee=user.employee, start_date=start_date, end_date=end_date).exists():
            from rest_framework import serializers as drf_serializers
            raise drf_serializers.ValidationError({ 'detail': 'Ya existe una solicitud para ese periodo.' })
        if not is_cct_leave:
            # Non-CCT leave must be requested in weekly blocks
            if total_days % 7 != 0:
                from rest_framework import serializers as drf_serializers
                raise drf_serializers.ValidationError({ 'detail': 'debera seleccionar de a 7 dias' })
            # Monday-to-Sunday rule
            if start_date.weekday() != 0 or end_date.weekday() != 6:
                from rest_framework import serializers as drf_serializers
                raise drf_serializers.ValidationError({ 'detail': 'las solicitudes deben ser de lunes a domingo' })
        # Sufficient balance validation
        year = start_date.year
        balance, _ = LeaveBalance.objects.get_or_create(employee=user.employee, year=year)
        if is_cct_leave:
            available = balance.cct_days_previous_year + balance.cct_days_current_year
            if total_days > available:
                from rest_framework import serializers as drf_serializers
                raise drf_serializers.ValidationError({ 'detail': 'no se dispone la cantidad de dias solicitados' })
        else:
            weeks = total_days // 7
            business_days_needed = weeks * 5
            holidays_needed = weeks * 2
            available_business = balance.business_days_previous_year + balance.business_days_current_year
            available_holidays = balance.holidays_previous_year + balance.holidays_current_year
            if business_days_needed > available_business or holidays_needed > available_holidays:
                from rest_framework import serializers as drf_serializers
                raise drf_serializers.ValidationError({ 'detail': 'no se dispone la cantidad de dias solicitados' })
        if is_cct_leave:
            breakdown = utils.calculate_request_breakdown(start_date, end_date)
            requested_days = breakdown['workdays'] + breakdown['holiday']
            year = start_date.year
            balance, _ = LeaveBalance.objects.get_or_create(employee=user.employee, year=year)
            available = balance.cct_days_previous_year + balance.cct_days_current_year
            if requested_days > available:
                from rest_framework import serializers as drf_serializers
                raise drf_serializers.ValidationError({ 'detail': 'Insufficient leave balance. You do not have enough days available for this request.' })

        req = LeaveRequest.objects.create(
            employee=user.employee,
            start_date=start_date,
            end_date=end_date,
            is_cct_leave=is_cct_leave,
        )
        utils.send_request_notifications(req, created=True)
        serializer = self.get_serializer(req)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsAdmin])
    def approve(self, request, pk=None):
        req = self.get_object()
        if req.status != LeaveRequest.STATUS_PENDING:
            return Response({'detail': 'Already processed'}, status=status.HTTP_400_BAD_REQUEST)
        # Handle file upload for proof_document
        proof_file = request.FILES.get('proof_document')
        if proof_file:
            req.proof_document = proof_file
        try:
            with transaction.atomic():
                employee = req.employee
                balance = LeaveBalance.objects.select_for_update().get(employee=employee, year=req.start_date.year)
                applied = utils.calculate_advanced_leave_deduction(req, balance)
                req.cct_days_deducted = applied.get('cct_days_deducted', 0)
                req.workdays_deducted = applied.get('business_days_deducted', 0)
                req.holiday_leave_deducted = applied.get('holidays_deducted', 0)
                req.status = LeaveRequest.STATUS_APPROVED
                req.save()
        except Exception as e:
            return Response({'detail': f'Approval failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        utils.send_request_notifications(req, approved=True)
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsAdmin])
    def reject(self, request, pk=None):
        req = self.get_object()
        if req.status != LeaveRequest.STATUS_PENDING:
            return Response({'detail': 'Already processed'}, status=status.HTTP_400_BAD_REQUEST)
        # On reject, we could optionally rollback balance. For simplicity, do nothing (request never deducted until approve),
        # since we deduct at request time above, we would need to refund here. Let's refund.
        with transaction.atomic():
            # If deductions were made earlier (legacy), refund; otherwise just mark rejected
            if any([req.cct_days_deducted, req.workdays_deducted, req.holiday_leave_deducted]):
                utils.refund_request(req)
            req.status = LeaveRequest.STATUS_REJECTED
            req.save()
        utils.send_request_notifications(req, rejected=True)
        return Response(self.get_serializer(req).data)


class MeBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if IsAdmin().has_permission(request, self):
            return Response({'detail': 'Admins cannot access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
        if not request.user.employee_id:
            return Response({'detail': 'User not linked to employee'}, status=status.HTTP_400_BAD_REQUEST)
        employee = request.user.employee
        year = date.today().year
        balance, _ = LeaveBalance.objects.get_or_create(employee=employee, year=year)
        data = {
            'cct_days_previous_year': balance.cct_days_previous_year,
            'cct_days_current_year': balance.cct_days_current_year,
            'business_days_previous_year': balance.business_days_previous_year,
            'business_days_current_year': balance.business_days_current_year,
            'holidays_previous_year': balance.holidays_previous_year,
            'holidays_current_year': balance.holidays_current_year,
        }
        return Response(data)


class MyRequestsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user.employee_id:
            return Response([], status=status.HTTP_200_OK)
        qs = LeaveRequest.objects.filter(employee=request.user.employee).order_by('-request_date')
        data = LeaveRequestSerializer(qs, many=True).data
        return Response(data)

    def post(self, request):
        # Reuse the create logic from the viewset without routing collisions
        viewset = LeaveRequestViewSet.as_view({'post': 'create'})
        # Forward the native Django HttpRequest to avoid DRF/Django mismatch
        return viewset(request._request)


class AdminLeaveBalancesList(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        year = date.today().year
        items = []
        for emp in Employee.objects.all():
            bal, _ = LeaveBalance.objects.get_or_create(employee=emp, year=year)
            buckets = utils.available_buckets(bal)
            user = emp.users.first()
            items.append({
                'user_id': user.id if user else None,
                'employee_id': emp.id,
                'employee_name': emp.full_name,
                'cct_days_previous_year': bal.cct_days_previous_year,
                'cct_days_current_year': bal.cct_days_current_year,
                'business_days_previous_year': bal.business_days_previous_year,
                'business_days_current_year': bal.business_days_current_year,
                'holidays_previous_year': bal.holidays_previous_year,
                'holidays_current_year': bal.holidays_current_year,
            })
        return Response(items)


class AdminLeaveBalanceDetail(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def put(self, request, user_id: int):
        return self._update(request, user_id)

    def patch(self, request, user_id: int):
        return self._update(request, user_id)

    def _update(self, request, user_id: int):
        # user_id corresponds to accounts.User primary key, map to employee via FK
        from accounts.models import User
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        if not user.employee_id:
            return Response({'detail': 'User not linked to employee'}, status=status.HTTP_400_BAD_REQUEST)
        # Update the six fields; treat missing as keep existing
        fields = [
            'cct_days_previous_year', 'cct_days_current_year',
            'business_days_previous_year', 'business_days_current_year',
            'holidays_previous_year', 'holidays_current_year',
        ]
        year = date.today().year
        with transaction.atomic():
            bal, _ = LeaveBalance.objects.select_for_update().get_or_create(employee=user.employee, year=year)
            for f in fields:
                if f in request.data:
                    setattr(bal, f, int(request.data[f]))
            bal.save()
        data = {f: getattr(bal, f) for f in fields}
        data.update({'employee_id': user.employee.id})
        return Response(data)


class AdminRequests(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        qs = LeaveRequest.objects.select_related('employee')
        status_filter = request.query_params.get('status')
        if status_filter in {LeaveRequest.STATUS_PENDING, LeaveRequest.STATUS_APPROVED, LeaveRequest.STATUS_REJECTED}:
            qs = qs.filter(status=status_filter)
        data = LeaveRequestSerializer(qs.order_by('-request_date'), many=True).data
        return Response(data)

    def put(self, request, request_id: int):
        return self._update_status(request, request_id)

    def patch(self, request, request_id: int):
        return self._update_status(request, request_id)

    def _update_status(self, request, request_id: int):
        try:
            req = LeaveRequest.objects.get(pk=request_id)
        except LeaveRequest.DoesNotExist:
            return Response({'detail': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get('status')
        if new_status not in {LeaveRequest.STATUS_APPROVED, LeaveRequest.STATUS_REJECTED}:
            return Response({'detail': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        if req.status != LeaveRequest.STATUS_PENDING:
            return Response({'detail': 'Already processed'}, status=status.HTTP_400_BAD_REQUEST)

        # Handle file upload for proof_document
        proof_file = request.FILES.get('proof_document')
        if proof_file:
            req.proof_document = proof_file

        if new_status == LeaveRequest.STATUS_REJECTED:
            req.status = LeaveRequest.STATUS_REJECTED
            req.save()
            return Response(LeaveRequestSerializer(req).data)
        # Approve -> deduct
        with transaction.atomic():
            bal = LeaveBalance.objects.select_for_update().get(employee=req.employee, year=req.start_date.year)
            try:
                applied = utils.calculate_advanced_leave_deduction(req, bal)
            except Exception as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            req.cct_days_deducted = applied.get('cct_days_deducted', 0)
            req.workdays_deducted = applied.get('business_days_deducted', 0)
            req.holiday_leave_deducted = applied.get('holidays_deducted', 0)
            req.status = LeaveRequest.STATUS_APPROVED
            req.save()
        return Response(LeaveRequestSerializer(req).data)

from django.shortcuts import render

# Create your views here.
