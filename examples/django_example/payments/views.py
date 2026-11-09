import json

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from paymobx import PaymobxClient
from paymobx.integrations.django import is_valid_callback, is_valid_response


client = PaymobxClient(
    api_key=getattr(settings, "PAYMOBX_API_KEY", None) or None,
    secret_key=getattr(settings, "PAYMOBX_SECRET_KEY", None) or None,
    public_key=getattr(settings, "PAYMOBX_PUBLIC_KEY", None) or None,
)


def index(request):
    return render(request, "payments/index.html")


def _checkout_url(request, integration_id, billing_data, reference, amount_cents=10000):
    """Create an Intention and return the Unified Checkout URL."""
    intention = client.create_intention(
        amount_cents=amount_cents,
        currency="EGP",
        payment_methods=[integration_id],
        billing_data=billing_data,
        special_reference=reference,
        notification_url=request.build_absolute_uri(reverse("processed_callback")),
        redirection_url=request.build_absolute_uri(reverse("payment_response")),
    )
    return client.get_unified_checkout_url(
        client_secret=intention["client_secret"],
        region="egypt",
    )


def pay_with_card(request):
    return redirect(_checkout_url(
        request,
        integration_id=settings.PAYMOBX_CARD_INTEGRATION_ID,
        billing_data={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone_number": "+201012345678",
        },
        reference="card-demo",
    ))


def pay_with_wallet(request):
    wallet_number = request.GET.get("wallet_number", "01010101010")
    return redirect(_checkout_url(
        request,
        integration_id=settings.PAYMOBX_WALLET_INTEGRATION_ID,
        billing_data={
            "first_name": "Wallet",
            "phone_number": wallet_number,
            "email": "wallet@example.com",
        },
        reference="wallet-demo",
    ))


def pay_with_fawry(request):
    return redirect(_checkout_url(
        request,
        integration_id=settings.PAYMOBX_KIOSK_INTEGRATION_ID,
        billing_data={
            "first_name": "Fawry",
            "phone_number": "+201000000000",
            "email": "fawry@example.com",
        },
        reference="fawry-demo",
        amount_cents=15000,
    ))


@csrf_exempt
def processed_callback(request):
    if is_valid_callback(request, settings.PAYMOBX_HMAC):
        data = json.loads(request.body)
        is_success = data["obj"]["success"]
        order_id = data["obj"]["order"]["id"]
        print(f"WEBHOOK: Payment status for order {order_id} is {is_success}")
        return HttpResponse(status=200)
    return HttpResponse(status=400)


def payment_response(request):
    if is_valid_response(request, settings.PAYMOBX_HMAC):
        success = request.GET.get("success") == "true"
        return render(request, "payments/status.html", {"success": success})
    return render(request, "payments/status.html", {"error": "Invalid verification"})