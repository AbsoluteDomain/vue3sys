"""系统管理-审批配置路由。

"""
from django.urls import path

from . import views

urlpatterns = [
    path("configs", views.config_list, name="approval_config_list"),
    path("configs/create", views.config_create, name="approval_config_create"),
    path("configs/<int:config_id>", views.config_update, name="approval_config_update"),
    path("enabled-perms", views.enabled_perms, name="approval_enabled_perms"),
    path("submit", views.submit_request, name="approval_submit"),
    path("my-tasks/count", views.my_task_count, name="approval_my_task_count"),
    path("my-tasks", views.my_tasks, name="approval_my_tasks"),
    path("requests/<int:request_id>/history", views.request_history, name="approval_request_history"),
    path("requests/<int:request_id>/approve", views.approve_request, name="approval_approve"),
    path("requests/<int:request_id>/reject", views.reject_request, name="approval_reject"),
]
