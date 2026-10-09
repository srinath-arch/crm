from .models import Customer


def bulk_import_customers(owner, rows):
    emails = [row["email"] for row in rows if row["email"]]
    existing = {}
    for start in range(0, len(emails), 500):
        batch = emails[start:start + 500]
        existing.update({
            customer.email: customer
            for customer in Customer.objects.filter(owner=owner, email__in=batch)
        })

    updates = []
    creates = []
    for row in rows:
        customer = existing.get(row["email"]) if row["email"] else None
        if customer:
            customer.name = row["name"]
            customer.company = row["company"]
            customer.phone = row["phone"]
            updates.append(customer)
        else:
            creates.append(Customer(owner=owner, **row))
    if creates:
        Customer.objects.bulk_create(creates, batch_size=500)
    if updates:
        Customer.objects.bulk_update(updates, ["name", "company", "phone"], batch_size=500)
    return len(rows)