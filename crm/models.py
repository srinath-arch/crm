from django.conf import settings
from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=160)
    company = models.CharField(max_length=180, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="customers", db_index=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["email"]), models.Index(fields=["owner"])]

    def __str__(self):
        return self.company or self.name


class Contact(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=160)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    role = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Deal(models.Model):
    class Stage(models.TextChoices):
        LEAD = "lead", "Lead"
        CONTACTED = "contacted", "Contacted"
        PROPOSAL = "proposal", "Proposal"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="deals")
    title = models.CharField(max_length=180)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.LEAD)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="deals")
    expected_close = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["expected_close", "title"]
        indexes = [models.Index(fields=["stage"])]

    def __str__(self):
        return self.title


class Activity(models.Model):
    class Type(models.TextChoices):
        NOTE = "note", "Note"
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="activities")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="activities")
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.NOTE)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_type_display()} · {self.customer}"