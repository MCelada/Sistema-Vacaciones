from django.urls import path
from . import views

urlpatterns = [
    path('me/', views.me, name='me'),
    path('user/me/', views.me, name='user-me'),
]

