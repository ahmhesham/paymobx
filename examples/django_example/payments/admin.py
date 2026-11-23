from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "transaction_id", "amount_cents", "is_paid", "created_at")
    list_filter = ("is_paid",)
    search_fields = ("reference", "transaction_id")
    readonly_fields = ("created_at", "updated_at")