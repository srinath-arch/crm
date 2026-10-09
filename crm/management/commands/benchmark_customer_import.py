import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from crm.imports import bulk_import_customers
from crm.models import Customer


class _RollbackBenchmark(Exception):
    pass


class Command(BaseCommand):
    help = "Compare row-by-row customer upserts with the optimized bulk import."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=1000)
        parser.add_argument("--owner", required=True)

    def handle(self, *args, **options):
        count = options["count"]
        if count < 1 or count > 10000:
            raise CommandError("Count must be between 1 and 10,000.")
        try:
            owner = get_user_model().objects.get(username=options["owner"])
        except get_user_model().DoesNotExist as error:
            raise CommandError(f"User '{options['owner']}' does not exist.") from error

        baseline_rows = self._rows(count, "baseline")
        optimized_rows = self._rows(count, "optimized")
        baseline_seconds = optimized_seconds = 0
        try:
            with transaction.atomic():
                started = time.perf_counter()
                for row in baseline_rows:
                    Customer.objects.update_or_create(
                        owner=owner,
                        email=row["email"],
                        defaults={"name": row["name"], "company": row["company"], "phone": row["phone"]},
                    )
                baseline_seconds = time.perf_counter() - started

                started = time.perf_counter()
                bulk_import_customers(owner, optimized_rows)
                optimized_seconds = time.perf_counter() - started
                raise _RollbackBenchmark
        except _RollbackBenchmark:
            pass

        improvement = baseline_seconds / optimized_seconds if optimized_seconds else 0
        self.stdout.write(f"Rows: {count}")
        self.stdout.write(f"Row-by-row: {baseline_seconds:.3f}s")
        self.stdout.write(f"Bulk import: {optimized_seconds:.3f}s")
        self.stdout.write(f"Speedup: {improvement:.2f}x")
        self.stdout.write("Benchmark records were rolled back.")

    @staticmethod
    def _rows(count, tag):
        return [
            {"name": f"Benchmark {tag} {index}", "company": f"Benchmark Co {index}",
             "email": f"{tag}-{index}@example.test", "phone": "555-0100"}
            for index in range(count)
        ]