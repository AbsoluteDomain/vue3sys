from django.urls import path

from . import views

urlpatterns = [
    # 管理端
    path("admin/list/", views.release_admin_list, name="release_admin_list"),
    path("admin/<int:release_id>/", views.release_admin_detail, name="release_admin_detail"),
    path("admin/create/", views.release_admin_create, name="release_admin_create"),
    path("admin/<str:release_ids>/delete/", views.release_admin_delete, name="release_admin_delete"),
    path("admin/<int:release_id>/update/", views.release_admin_update, name="release_admin_update"),
    path("admin/<int:release_id>/publish/", views.release_admin_publish, name="release_admin_publish"),
    path("admin/<int:release_id>/revoke/", views.release_admin_revoke, name="release_admin_revoke"),
    # 用户端
    path("published/", views.release_published_list, name="release_published_list"),
    path("<int:release_id>/detail/", views.release_user_detail, name="release_user_detail"),
    path("latest-unread/", views.release_latest_unread, name="release_latest_unread"),
    path("<int:release_id>/read/", views.release_mark_read, name="release_mark_read"),
]
