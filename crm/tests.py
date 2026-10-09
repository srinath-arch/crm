from io import StringIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from crm.models import Activity, Contact, Customer, Deal

User = get_user_model()


class CrmWorkflowTests(TestCase):
    def setUp(self):
        self.rep = User.objects.create_user(username="maya", password="pass-12345")
        self.other_rep = User.objects.create_user(username="eli", password="pass-12345")
        self.admin = User.objects.create_user(username="admin", password="pass-12345", is_staff=True)
        self.customer = Customer.objects.create(name="Maya Chen", company="Northstar Labs", email="maya@northstar.test", owner=self.rep)
        self.other_customer = Customer.objects.create(name="Eli Stone", company="Cedar Works", email="eli@cedar.test", owner=self.other_rep)

    def test_representative_sees_only_owned_customers_and_details(self):
        self.client.force_login(self.rep)
        response = self.client.get(reverse("customer_list"))
        self.assertContains(response, "Northstar Labs")
        self.assertNotContains(response, "Cedar Works")
        self.assertEqual(self.client.get(reverse("customer_detail", args=[self.other_customer.pk])).status_code, 404)

    def test_staff_can_see_all_customers(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("customer_list"))
        self.assertContains(response, "Northstar Labs")
        self.assertContains(response, "Cedar Works")

    def test_representative_can_create_customer_owned_by_self(self):
        self.client.force_login(self.rep)
        response = self.client.post(reverse("customer_create"), {
            "name": "New Lead", "company": "Greenhouse", "email": "lead@greenhouse.test", "phone": "555-1111",
        })
        self.assertEqual(response.status_code, 302)
        customer = Customer.objects.get(email="lead@greenhouse.test")
        self.assertEqual(customer.owner, self.rep)

    def test_contact_and_activity_are_customer_scoped(self):
        self.client.force_login(self.rep)
        response = self.client.post(reverse("contact_create", args=[self.customer.pk]), {
            "name": "Sam Lee", "email": "sam@northstar.test", "phone": "555-2222", "role": "Finance",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Contact.objects.get().customer, self.customer)
        response = self.client.post(reverse("activity_create", args=[self.customer.pk]), {
            "type": Activity.Type.CALL, "note": "Discussed the renewal timeline.",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Activity.objects.get().user, self.rep)

    def test_representative_can_create_deal_with_self_as_owner(self):
        self.client.force_login(self.rep)
        response = self.client.post(reverse("deal_create"), {
            "customer": self.customer.pk, "title": "Annual renewal", "value": "12500.00",
            "stage": Deal.Stage.PROPOSAL, "expected_close": "2026-12-01",
        })
        self.assertEqual(response.status_code, 302)
        deal = Deal.objects.get(title="Annual renewal")
        self.assertEqual(deal.owner, self.rep)

    def test_csv_import_bulk_creates_and_updates_owned_records(self):
        self.client.force_login(self.rep)
        csv_content = b"name,company,email,phone\nMaya Updated,Northstar Labs,maya@northstar.test,555-9999\nNew Person,Field Co,new@field.test,555-3333\n"
        upload = SimpleUploadedFile("customers.csv", csv_content, content_type="text/csv")
        response = self.client.post(reverse("customer_import"), {"file": upload}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, "Maya Updated")
        self.assertEqual(self.customer.phone, "555-9999")
        self.assertEqual(Customer.objects.filter(owner=self.rep).count(), 2)

    def test_csv_import_rejects_bad_rows_without_partial_writes(self):
        self.client.force_login(self.rep)
        csv_content = b"name,company,email,phone\nValid,Field Co,valid@field.test,555-3333\n,Field Co,bad@field.test,555-4444\n"
        upload = SimpleUploadedFile("customers.csv", csv_content, content_type="text/csv")
        response = self.client.post(reverse("customer_import"), {"file": upload}, follow=True)
        self.assertContains(response, "name is required")
        self.assertFalse(Customer.objects.filter(email="valid@field.test").exists())

    def test_export_is_scoped_and_returns_csv(self):
        self.client.force_login(self.rep)
        response = self.client.get(reverse("customer_export"))
        body = response.content.decode()
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("Northstar Labs", body)
        self.assertNotIn("Cedar Works", body)

    def test_requested_indexes_exist(self):
        customer_indexes = [index.fields for index in Customer._meta.indexes]
        deal_indexes = [index.fields for index in Deal._meta.indexes]
        self.assertIn(["email"], customer_indexes)
        self.assertIn(["owner"], customer_indexes)
        self.assertIn(["stage"], deal_indexes)

    def test_dashboard_counts_only_open_deals_as_active(self):
        Deal.objects.create(customer=self.customer, title="Closed", value=500, stage=Deal.Stage.WON, owner=self.rep)
        Deal.objects.create(customer=self.customer, title="Open", value=800, stage=Deal.Stage.PROPOSAL, owner=self.rep)
        self.client.force_login(self.rep)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["deal_count"], 1)

    def test_seed_and_benchmark_commands(self):
        call_command("seed_customers", owner=self.rep.username, count=3, stdout=StringIO())
        self.assertEqual(Customer.objects.filter(owner=self.rep, email__startswith="sample-").count(), 3)
        output = StringIO()
        call_command("benchmark_customer_import", owner=self.rep.username, count=3, stdout=output)
        self.assertIn("Benchmark records were rolled back.", output.getvalue())
        self.assertFalse(Customer.objects.filter(email__startswith="baseline-").exists())
        self.assertFalse(Customer.objects.filter(email__startswith="optimized-").exists())