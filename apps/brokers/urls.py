from django.urls import path

from apps.brokers.views import BrokerAgentDeleteView, BrokerAgentsView, BrokerCreateAgentView

app_name = "brokers"

urlpatterns = [
    path("", BrokerAgentsView.as_view(), name="agents"),
    path("create/", BrokerCreateAgentView.as_view(), name="create"),
    path("<int:pk>/delete/", BrokerAgentDeleteView.as_view(), name="delete"),
]
