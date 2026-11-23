from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),

    # modern
    path("pay/card/", views.pay_with_card, name="pay_card"),
    path("pay/wallet/", views.pay_with_wallet, name="pay_wallet"),
    path("pay/fawry/", views.pay_with_fawry, name="pay_fawry"),

    # legacy
    path("pay/card/legacy/", views.pay_with_card_legacy, name="pay_card_legacy"),
    path("pay/wallet/legacy/", views.pay_with_wallet_legacy, name="pay_wallet_legacy"),

    # callbacks
    path("callback/processed/", views.processed_callback, name="processed_callback"),
    path("callback/response/", views.payment_response, name="payment_response"),

    # order lookup
    path("orders/<str:reference>/", views.order_status, name="order_status"),

    # lifecycle
    path("txn/<str:transaction_id>/refund/", views.refund, name="refund"),
    path("txn/<str:transaction_id>/void/", views.void, name="void"),
    path("txn/<str:transaction_id>/capture/", views.capture, name="capture"),
    path("txn/<str:transaction_id>/", views.transaction_detail, name="transaction_detail"),
    path("txn/", views.transaction_by_reference, name="transaction_by_reference"),

    # links
    path("links/create/", views.create_link, name="create_link"),

    # saved cards / MOTO
    path("saved-card/charge/", views.charge_saved_card, name="charge_saved_card"),

    # subscriptions
    path("plans/create/", views.create_plan, name="create_plan"),
    path("subscriptions/webhook/", views.subscription_webhook, name="subscription_webhook"),
]