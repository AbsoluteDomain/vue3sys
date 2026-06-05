from django.urls import path

from . import views

urlpatterns = [
    path('list/', views.operation_log_list, name='operation_log_list'),
]
