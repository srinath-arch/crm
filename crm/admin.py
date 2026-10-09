from django.contrib import admin

from .models import Activity, Contact, Customer, Deal


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0


class DealInline(admin.TabularInline):
    model = Deal
    extra = 0


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "email", "owner", "created_at")
    list_filter = ("owner", "created_at")
    search_fields = ("name", "company", "email")
    inlines = (ContactInline, DealInline)


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ("title", "customer", "stage", "value", "owner", "expected_close")
    list_filter = ("stage", "owner")
    search_fields = ("title", "customer__name", "customer__company")


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("customer", "type", "user", "created_at")
    list_filter = ("type", "created_at")
    search_fields = ("customer__name", "note")