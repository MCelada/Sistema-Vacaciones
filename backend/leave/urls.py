from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmployeeViewSet, LeavePolicyViewSet, PublicHolidayViewSet,
    LeaveBalanceViewSet, LeaveRequestViewSet,
    MeBalanceView, MyRequestsView, AdminLeaveBalancesList, AdminLeaveBalanceDetail, AdminRequests,
)
from .views_pdf import LeaveRequestPDFView

router = DefaultRouter()
router.register('employees', EmployeeViewSet, basename='employee')
router.register('policies', LeavePolicyViewSet, basename='policy')
router.register('holidays', PublicHolidayViewSet, basename='holiday')
router.register('balances', LeaveBalanceViewSet, basename='balance')
router.register('requests', LeaveRequestViewSet, basename='request')

urlpatterns = [
    path('', include(router.urls)),
    path('leave/balance/', MeBalanceView.as_view(), name='leave-balance'),
    path('leave/requests/', MyRequestsView.as_view(), name='my-requests'),
    path('admin/leave-balances/', AdminLeaveBalancesList.as_view(), name='admin-leave-balances'),
    path('admin/leave-balances/<int:user_id>/', AdminLeaveBalanceDetail.as_view(), name='admin-leave-balance-detail'),
    path('admin/requests/', AdminRequests.as_view(), name='admin-requests'),
    path('admin/requests/<int:request_id>/', AdminRequests.as_view(), name='admin-requests-detail'),
    path('requests/<int:pk>/pdf/', LeaveRequestPDFView.as_view(), name='leave-request-pdf'),
]

