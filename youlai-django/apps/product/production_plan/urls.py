from django.urls import path

from .views import (
    calculate_production_requirements,
    get_production_plan,
    save_production_plan,
    list_production_plan,
)

urlpatterns = [
    path("calculate", calculate_production_requirements, name="calculate_production_requirements"),
    path("get", get_production_plan, name="get_production_plan"),
    path("save", save_production_plan, name="save_production_plan"),
    path("list", list_production_plan, name="list_production_plan"),
]