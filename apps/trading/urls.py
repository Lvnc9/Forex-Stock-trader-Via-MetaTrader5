from django.urls import path

from apps.trading.views import (
    DeploymentCreateView,
    DeploymentListView,
    DeploymentPauseView,
    DeploymentReviewView,
    DeploymentStopView,
)

app_name = "trading"

urlpatterns = [
    path("", DeploymentListView.as_view(), name="list"),
    path("deploy/", DeploymentCreateView.as_view(), name="deploy"),
    path("<int:pk>/review/", DeploymentReviewView.as_view(), name="review"),
    path("<int:pk>/pause/", DeploymentPauseView.as_view(), name="pause"),
    path("<int:pk>/stop/", DeploymentStopView.as_view(), name="stop"),
]
