from django.urls import path

from . import views


app_name = "underwriting"


urlpatterns = [
    path(
        "applications/new/",
        views.application_new,
        name="application_new",
    ),
    path(
        "applications/<int:application_id>/",
        views.application_detail,
        name="application_detail",
    ),
    path(
        "underwriting/",
        views.underwriting_queue,
        name="underwriting_queue",
    ),
    path(
        "underwriting/<int:application_id>/",
        views.underwriting_review,
        name="underwriting_review",
    ),
]