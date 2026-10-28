from django.urls import path

from .views import get_test_record_history, list_test_records

urlpatterns = [
    path("list/", list_test_records, name="test_record_list"),
    path("history/", get_test_record_history, name="test_record_history"),
]
