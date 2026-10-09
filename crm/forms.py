from django import forms
from django.contrib.auth import get_user_model

from .models import Activity, Contact, Customer, Deal

User = get_user_model()


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "company", "email", "phone", "owner"]
        widgets = {"owner": forms.Select(attrs={"class": "select"})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if user.is_staff:
            self.fields["owner"].queryset = User.objects.order_by("username")
        else:
            self.fields.pop("owner")


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ["name", "email", "phone", "role"]


class DealForm(forms.ModelForm):
    class Meta:
        model = Deal
        fields = ["customer", "title", "value", "stage", "owner", "expected_close"]
        widgets = {"expected_close": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        customers = Customer.objects.all() if user.is_staff else Customer.objects.filter(owner=user)
        self.fields["customer"].queryset = customers.order_by("name")
        if user.is_staff:
            self.fields["owner"].queryset = User.objects.order_by("username")
        else:
            self.fields.pop("owner")


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["type", "note"]