import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ActivityForm, ContactForm, CustomerForm, DealForm
from .imports import bulk_import_customers
from .models import Activity, Contact, Customer, Deal


def visible_customers(user):
    customers = Customer.objects.select_related("owner")
    return customers if user.is_staff else customers.filter(owner=user)


def visible_deals(user):
    deals = Deal.objects.select_related("customer", "owner")
    return deals if user.is_staff else deals.filter(customer__owner=user)


@login_required
def dashboard(request):
    customers = visible_customers(request.user)
    deals = visible_deals(request.user)
    stage_rows = deals.values("stage").annotate(count=Count("id"), total=Sum("value"))
    stage_data = {row["stage"]: row for row in stage_rows}
    pipeline = [
        {"key": key, "label": label, "count": stage_data.get(key, {}).get("count", 0),
         "total": stage_data.get(key, {}).get("total") or 0}
        for key, label in Deal.Stage.choices
    ]
    activity = Activity.objects.filter(customer__in=customers).select_related("customer", "user")[:8]
    context = {
        "customer_count": customers.count(),
        "deal_count": deals.exclude(stage__in=[Deal.Stage.WON, Deal.Stage.LOST]).count(),
        "pipeline_value": deals.exclude(stage__in=[Deal.Stage.WON, Deal.Stage.LOST]).aggregate(total=Sum("value"))["total"] or 0,
        "pipeline": pipeline,
        "recent_activity": activity,
        "max_stage_count": max((item["count"] for item in pipeline), default=0) or 1,
    }
    return render(request, "crm/dashboard.html", context)


@login_required
def customer_list(request):
    customers = visible_customers(request.user).annotate(deal_count=Count("deals", distinct=True))
    query = request.GET.get("q", "").strip()
    stage = request.GET.get("stage", "")
    owner = request.GET.get("owner", "")
    if query:
        customers = customers.filter(Q(name__icontains=query) | Q(company__icontains=query) | Q(email__icontains=query))
    if stage:
        customers = customers.filter(deals__stage=stage)
    if request.user.is_staff and owner:
        customers = customers.filter(owner_id=owner)
    context = {"customers": customers.distinct(), "query": query, "stage": stage,
               "stages": Deal.Stage.choices, "owners": Customer.objects.values_list("owner_id", "owner__username").distinct()}
    return render(request, "crm/customer_list.html", context)


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(visible_customers(request.user), pk=pk)
    return render(request, "crm/customer_detail.html", {
        "customer": customer,
        "contacts": customer.contacts.all(),
        "deals": customer.deals.select_related("owner"),
        "open_deal_count": customer.deals.exclude(stage__in=[Deal.Stage.WON, Deal.Stage.LOST]).count(),
        "activities": customer.activities.select_related("user"),
        "activity_form": ActivityForm(),
    })


@login_required
def customer_form(request, pk=None):
    customer = get_object_or_404(visible_customers(request.user), pk=pk) if pk else None
    form = CustomerForm(request.POST or None, instance=customer, user=request.user)
    if form.is_valid():
        saved = form.save(commit=False)
        if not request.user.is_staff:
            saved.owner = request.user
        saved.save()
        messages.success(request, "Customer saved.")
        return redirect("customer_detail", pk=saved.pk)
    return render(request, "crm/form_page.html", {"form": form, "title": "Edit customer" if customer else "New customer"})


@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(visible_customers(request.user), pk=pk)
    if request.method == "POST":
        customer.delete()
        messages.success(request, "Customer deleted.")
        return redirect("customer_list")
    return render(request, "crm/confirm_delete.html", {"object": customer, "cancel_url": "customer_detail", "cancel_pk": pk})


@login_required
def contact_form(request, customer_pk, pk=None):
    customer = get_object_or_404(visible_customers(request.user), pk=customer_pk)
    contact = get_object_or_404(customer.contacts, pk=pk) if pk else None
    form = ContactForm(request.POST or None, instance=contact)
    if form.is_valid():
        saved = form.save(commit=False)
        saved.customer = customer
        saved.save()
        messages.success(request, "Contact saved.")
        return redirect("customer_detail", pk=customer.pk)
    return render(request, "crm/form_page.html", {"form": form, "title": "Edit contact" if contact else "New contact", "back_url": "customer_detail", "back_pk": customer.pk})


@login_required
def contact_delete(request, customer_pk, pk):
    customer = get_object_or_404(visible_customers(request.user), pk=customer_pk)
    contact = get_object_or_404(customer.contacts, pk=pk)
    if request.method == "POST":
        contact.delete()
        messages.success(request, "Contact deleted.")
        return redirect("customer_detail", pk=customer.pk)
    return render(request, "crm/confirm_delete.html", {"object": contact, "cancel_url": "customer_detail", "cancel_pk": customer.pk})


@login_required
def deal_list(request):
    deals = visible_deals(request.user)
    query = request.GET.get("q", "").strip()
    stage = request.GET.get("stage", "")
    owner = request.GET.get("owner", "")
    if query:
        deals = deals.filter(Q(title__icontains=query) | Q(customer__name__icontains=query) | Q(customer__company__icontains=query))
    if stage:
        deals = deals.filter(stage=stage)
    if request.user.is_staff and owner:
        deals = deals.filter(owner_id=owner)
    owners = deals.model.objects.values_list("owner_id", "owner__username").distinct()
    return render(request, "crm/deal_list.html", {"deals": deals, "query": query, "stage": stage,
        "stages": Deal.Stage.choices, "owners": owners})


@login_required
def deal_form(request, pk=None):
    deal = get_object_or_404(visible_deals(request.user), pk=pk) if pk else None
    form = DealForm(request.POST or None, instance=deal, user=request.user)
    if form.is_valid():
        saved = form.save(commit=False)
        if not request.user.is_staff:
            saved.owner = request.user
        saved.save()
        messages.success(request, "Deal saved.")
        return redirect("deal_list")
    return render(request, "crm/form_page.html", {"form": form, "title": "Edit deal" if deal else "New deal"})


@login_required
def deal_delete(request, pk):
    deal = get_object_or_404(visible_deals(request.user), pk=pk)
    if request.method == "POST":
        deal.delete()
        messages.success(request, "Deal deleted.")
        return redirect("deal_list")
    return render(request, "crm/confirm_delete.html", {"object": deal, "cancel_url": "deal_list"})


@login_required
@require_POST
def activity_create(request, customer_pk):
    customer = get_object_or_404(visible_customers(request.user), pk=customer_pk)
    form = ActivityForm(request.POST)
    if form.is_valid():
        activity = form.save(commit=False)
        activity.customer = customer
        activity.user = request.user
        activity.save()
        messages.success(request, "Activity logged.")
    else:
        messages.error(request, "Add a note before logging activity.")
    return redirect("customer_detail", pk=customer.pk)


@login_required
def customer_export(request):
    customers = visible_customers(request.user).prefetch_related("contacts", "deals")
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="crm-customers.csv"'
    writer = csv.writer(response)
    writer.writerow(["name", "company", "email", "phone", "owner", "contact_count", "deal_count"])
    for customer in customers.iterator(chunk_size=500):
        writer.writerow([customer.name, customer.company, customer.email, customer.phone, customer.owner.username,
                         customer.contacts.count(), customer.deals.count()])
    return response


@login_required
def customer_import(request):
    if request.method == "POST":
        upload = request.FILES.get("file")
        if not upload or upload.size > 5 * 1024 * 1024:
            messages.error(request, "Choose a CSV file smaller than 5 MB.")
            return redirect("customer_import")
        try:
            decoded = upload.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(decoded))
            required = {"name", "company", "email", "phone"}
            if not reader.fieldnames or not required.issubset({field.strip().lower() for field in reader.fieldnames}):
                raise ValueError("CSV must include name, company, email, and phone columns.")
            rows = []
            seen_emails = set()
            for index, row in enumerate(reader, start=2):
                if index > 10001:
                    raise ValueError("A single import is limited to 10,000 customers.")
                if None in row:
                    raise ValueError(f"Row {index}: too many columns.")
                normalized = {key.strip().lower(): (value or "").strip() for key, value in row.items() if key}
                name = normalized.get("name", "")
                email = normalized.get("email", "")
                if not name:
                    raise ValueError(f"Row {index}: name is required.")
                if email:
                    try:
                        validate_email(email)
                    except ValidationError as error:
                        raise ValueError(f"Row {index}: {error.messages[0]}") from error
                    if email in seen_emails:
                        raise ValueError(f"Row {index}: duplicate email in this file.")
                    seen_emails.add(email)
                rows.append({"name": name, "company": normalized.get("company", ""),
                             "email": email, "phone": normalized.get("phone", "")})

            imported = 0
            with transaction.atomic():
                imported = bulk_import_customers(request.user, rows)
            messages.success(request, f"Imported {imported} customer rows.")
            return redirect("customer_list")
        except (UnicodeDecodeError, csv.Error, ValueError) as error:
            messages.error(request, str(error))
    return render(request, "crm/import.html")