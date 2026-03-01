from django.urls import path

from . import views

app_name = "osint_tools"

urlpatterns = [
    path("holehe/search/", views.holehe_search, name="holehe_search"),
    path("holehe/status/", views.holehe_status, name="holehe_status"),
    path("status/", views.tools_status, name="tools_status"),
]
