from django.db import models


class Order(models.Model):
    reference = models.CharField(max_length=100, unique=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    amount_cents = models.IntegerField(default=0)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.reference} (paid={self.is_paid})"