from django import forms

from apps.brokers.models import TradingAgent


class CreateAgentForm(forms.ModelForm):
    class Meta:
        model = TradingAgent
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"class": "tb-input"})}
