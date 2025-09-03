from django import forms
from .models import Agency, Client, ClientHashtag


class AgencyForm(forms.ModelForm):
    class Meta:
        model = Agency
        fields = ["name"]


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["agency", "name", "user"]
        widgets = {
            "agency": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "user": forms.Select(attrs={"class": "form-select"}),
        }


class ClientHashtagForm(forms.ModelForm):
    class Meta:
        model = ClientHashtag
        fields = ["client", "hashtag"]


