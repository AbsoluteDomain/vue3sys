"""系统管理-AI 助手路由。

"""
from django.urls import path

from . import views

urlpatterns = [
    path("chat", views.chat, name="ai_chat"),
]
