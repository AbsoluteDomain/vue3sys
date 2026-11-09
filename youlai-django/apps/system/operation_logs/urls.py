from django.urls import path

from . import views

urlpatterns = [
    path('list/', views.operation_log_list, name='operation_log_list'),
    path('approval-records/', views.approval_record_list, name='approval_record_list'),
]
