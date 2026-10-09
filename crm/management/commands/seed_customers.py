from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from crm.models import Activity, Contact, Customer, Deal


class Command(BaseCommand):
    help = "Seed a sales user with sample customers, contacts, deals, and activities."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=1000)
        parser.add_argument("--owner", required=True, help="Username that will own the sample records")

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        if count < 1 or count > 100000:
            raise CommandError("Count must be between 1 and 100,000.")
        try:
            owner = get_user_model().objects.get(username=options["owner"])
        except get_user_model().DoesNotExist as error:
            raise CommandError(f"User '{options['owner']}' does not exist.") from error

        customers = [
            Customer(
                name=f"Sample Customer {index:04d}",
                company=f"Northstar {index:04d}",
                email=f"sample-{index:04d}@example.test",
                phone=f"+1 555 {index % 1000:03d} {index % 10000:04d}",
                owner=owner,
            )
            for index in range(1, count + 1)
        ]
        Customer.objects.bulk_create(customers, batch_size=500)
        Contact.objects.bulk_create([
            Contact(customer=customer, name=f"Contact {index:04d}", email=f"contact-{index:04d}@example.test", role="Operations")
            for index, customer in enumerate(customers, start=1)
        ], batch_size=500)
        Deal.objects.bulk_create([
            Deal(customer=customer, title=f"Northstar renewal {index:04d}", value=Decimal(5000 + index * 25),
                 stage=Deal.Stage.choices[index % len(Deal.Stage.choices)][0], owner=owner,
                 expected_close=date.today() + timedelta(days=(index % 120)))
            for index, customer in enumerate(customers, start=1)
        ], batch_size=500)
        Activity.objects.bulk_create([
            Activity(customer=customers[index], user=owner, type=Activity.Type.NOTE, note="Sample account added to the CRM.")
            for index in range(min(count, 100))
        ], batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Seeded {count} customers for {owner.username}."))