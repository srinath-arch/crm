from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/new/", views.customer_form, name="customer_create"),
    path("customers/import/", views.customer_import, name="customer_import"),
    path("customers/export/", views.customer_export, name="customer_export"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/edit/", views.customer_form, name="customer_edit"),
    path("customers/<int:pk>/delete/", views.customer_delete, name="customer_delete"),
    path("customers/<int:customer_pk>/contacts/new/", views.contact_form, name="contact_create"),
    path("customers/<int:customer_pk>/contacts/<int:pk>/edit/", views.contact_form, name="contact_edit"),
    path("customers/<int:customer_pk>/contacts/<int:pk>/delete/", views.contact_delete, name="contact_delete"),
    path("customers/<int:customer_pk>/activity/", views.activity_create, name="activity_create"),
    path("deals/", views.deal_list, name="deal_list"),
    path("deals/new/", views.deal_form, name="deal_create"),
    path("deals/<int:pk>/edit/", views.deal_form, name="deal_edit"),
    path("deals/<int:pk>/delete/", views.deal_delete, name="deal_delete"),
]