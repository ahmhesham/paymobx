import json

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from paymobx import PaymobxClient, PaymobxError
from paymobx.integrations.django import (
    is_valid_callback,
    is_valid_response,
    is_paid_callback,
    is_paid_response,
)

from .models import Order


client = PaymobxClient(
    api_key=settings.PAYMOBX_API_KEY,
    secret_key=settings.PAYMOBX_SECRET_KEY,
    public_key=settings.PAYMOBX_PUBLIC_KEY,
    region=getattr(settings, "PAYMOBX_REGION", "egypt"),
)


def index(request):
    return render(request, "payments/index.html")


# =====================================================================
# MODERN FLOW (Intention API + Unified Checkout)
# =====================================================================

def _checkout_url(request, integration_id, billing_data, reference, amount_cents=10000):
    """Create an intention, record the order, and return the checkout URL."""
    intention = client.create_intention(
        amount_cents=amount_cents,
        currency="EGP",
        payment_methods=[integration_id],
        billing_data=billing_data,
        special_reference=reference,
        notification_url=request.build_absolute_uri(reverse("processed_callback")),
        redirection_url=request.build_absolute_uri(reverse("payment_response")),
    )

    Order.objects.update_or_create(
        reference=reference,
        defaults={"amount_cents": amount_cents, "is_paid": False},
    )

    return client.get_unified_checkout_url(
        client_secret=intention["client_secret"],
    )


def pay_with_card(request):
    try:
        url = _checkout_url(
            request,
            integration_id=settings.PAYMOBX_CARD_INTEGRATION_ID,
            billing_data={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone_number": "+201012345678",
            },
            reference="modern-card-demo",
        )
    except PaymobxError as e:
        return render(request, "payments/status.html", {"error": str(e)}, status=502)
    return redirect(url)


def pay_with_wallet(request):
    wallet_number = request.GET.get("wallet_number", "01010101010")
    try:
        url = _checkout_url(
            request,
            integration_id=settings.PAYMOBX_WALLET_INTEGRATION_ID,
            billing_data={
                "first_name": "Wallet",
                "phone_number": wallet_number,
                "email": "wallet@example.com",
            },
            reference="modern-wallet-demo",
        )
    except PaymobxError as e:
        return render(request, "payments/status.html", {"error": str(e)}, status=502)
    return redirect(url)


def pay_with_fawry(request):
    try:
        url = _checkout_url(
            request,
            integration_id=settings.PAYMOBX_KIOSK_INTEGRATION_ID,
            billing_data={
                "first_name": "Fawry",
                "phone_number": "+201000000000",
                "email": "fawry@example.com",
            },
            reference="modern-fawry-demo",
            amount_cents=15000,
        )
    except PaymobxError as e:
        return render(request, "payments/status.html", {"error": str(e)}, status=502)
    return redirect(url)


# =====================================================================
# LEGACY FLOW (Order -> Payment Key -> Iframe / Wallet Redirect)
# =====================================================================

def pay_with_card_legacy(request):
    try:
        paymob_order = client.create_order(amount_cents=10000, currency="EGP")

        Order.objects.update_or_create(
            reference=str(paymob_order["id"]),
            defaults={"amount_cents": 10000, "is_paid": False},
        )

        token = client.generate_payment_key(
            amount_cents=10000,
            order_id=paymob_order["id"],
            integration_id=settings.PAYMOBX_CARD_INTEGRATION_ID,
            billing_data={"first_name": "Legacy", "email": "legacy@example.com"},
            currency="EGP",
        )

        iframe_url = client.get_iframe_url(
            iframe_id=settings.PAYMOBX_IFRAME_ID,
            payment_token=token,
        )
    except PaymobxError as e:
        return render(request, "payments/status.html", {"error": str(e)}, status=502)
    return redirect(iframe_url)


def pay_with_wallet_legacy(request):
    wallet_number = request.GET.get("wallet_number", "01010101010")

    try:
        paymob_order = client.create_order(amount_cents=10000, currency="EGP")

        Order.objects.update_or_create(
            reference=str(paymob_order["id"]),
            defaults={"amount_cents": 10000, "is_paid": False},
        )

        token = client.generate_payment_key(
            amount_cents=10000,
            order_id=paymob_order["id"],
            integration_id=settings.PAYMOBX_WALLET_INTEGRATION_ID,
            billing_data={"first_name": "Legacy", "phone_number": wallet_number},
            currency="EGP",
        )

        redirection_url = client.initiate_wallet_payment(
            payment_token=token,
            wallet_number=wallet_number,
        )
    except PaymobxError as e:
        return render(request, "payments/status.html", {"error": str(e)}, status=502)
    return redirect(redirection_url)


# =====================================================================
# CALLBACKS
# =====================================================================

@csrf_exempt
def processed_callback(request):
    if not is_valid_callback(request, settings.PAYMOBX_HMAC):
        return HttpResponse(status=400)

    if is_paid_callback(request, settings.PAYMOBX_HMAC):
        data = json.loads(request.body)
        obj = data.get("obj", {})
        order_info = obj.get("order", {})

        reference = (
            order_info.get("merchant_order_id")
            or str(order_info.get("id", ""))
        )

        if reference:
            Order.objects.filter(reference=reference).update(
                is_paid=True,
                transaction_id=str(obj.get("id", "")),
            )

    return HttpResponse(status=200)


def payment_response(request):
    if not is_valid_response(request, settings.PAYMOBX_HMAC):
        return render(request, "payments/status.html", {"error": "Invalid verification"})

    paid = is_paid_response(request, settings.PAYMOBX_HMAC)
    return render(request, "payments/status.html", {"success": paid})


# =====================================================================
# ORDER LOOKUP
# =====================================================================

def order_status(request, reference):
    try:
        order = Order.objects.get(reference=reference)
    except Order.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)

    return JsonResponse({
        "reference": order.reference,
        "transaction_id": order.transaction_id,
        "amount_cents": order.amount_cents,
        "is_paid": order.is_paid,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
    })


# =====================================================================
# PAYMENT LIFECYCLE
# =====================================================================

@require_POST
def refund(request, transaction_id):
    amount_cents = request.POST.get("amount_cents")
    amount_cents = int(amount_cents) if amount_cents else None

    try:
        result = client.refund_transaction(transaction_id, amount_cents=amount_cents)
    except PaymobxError as e:
        return JsonResponse({"error": str(e)}, status=502)

    return JsonResponse(result)


@require_POST
def void(request, transaction_id):
    try:
        result = client.void_transaction(transaction_id)
    except PaymobxError as e:
        return JsonResponse({"error": str(e)}, status=502)

    return JsonResponse(result)


@require_POST
def capture(request, transaction_id):
    amount_cents = int(request.POST.get("amount_cents", 0))

    try:
        result = client.capture_transaction(transaction_id, amount_cents=amount_cents)
    except PaymobxError as e:
        return JsonResponse({"error": str(e)}, status=502)

    return JsonResponse(result)


def transaction_detail(request, transaction_id):
    try:
        result = client.get_transaction_by_id(transaction_id)
    except PaymobxError as e:
        return JsonResponse({"error": str(e)}, status=502)

    return JsonResponse(result)


def transaction_by_reference(request):
    merchant_order_id = request.GET.get("merchant_order_id")
    order_id = request.GET.get("order_id")

    if not merchant_order_id and not order_id:
        return JsonResponse(
            {"error": "Provide ?order_id= or ?merchant_order_id="},
            status=400,
        )

    try:
        result = client.get_transaction_by_order_id(
            merchant_order_id=merchant_order_id,
            order_id=order_id,
        )
    except PaymobxError as e:
        return JsonResponse({"error": str(e)}, status=502)

    return JsonResponse(result)


# =====================================================================
# PAYMENT LINKS
# =====================================================================

@require_POST
def create_link(request):
    try:
        link = client.create_payment_link(
            amount_cents=15000,
            currency="EGP",
            integration_id=settings.PAYMOBX_CARD_INTEGRATION_ID,
            full_name="John Doe",
            phone_number="+201012345678",
            email="john.doe@example.com",
            description="Invoice #001",
            reference_id="link-demo-001",
            notification_url=request.build_absolute_uri(reverse("processed_callback")),
            redirection_url=request.build_absolute_uri(reverse("payment_response")),
        )
    except PaymobxError as e:
        return JsonResponse({"error": str(e)}, status=502)

    return JsonResponse(link)


# =====================================================================
# SAVED CARDS / MOTO
# =====================================================================

@require_POST
def charge_saved_card(request):
    payment_token = request.POST.get("payment_token")
    card_token = request.POST.get("card_token")

    if not payment_token or not card_token:
        return JsonResponse(
            {"error": "Provide payment_token and card_token"},
            status=400,
        )

    try:
        result = client.pay_with_saved_card(
            payment_token=payment_token,
            card_token=card_token,
        )
    except PaymobxError as e:
        return JsonResponse({"error": str(e)}, status=502)

    return JsonResponse(result)


# =====================================================================
# SUBSCRIPTION PLANS
# =====================================================================

@require_POST
def create_plan(request):
    try:
        plan = client.create_subscription_plan(
            plan_name=request.POST.get("plan_name", "Pro Monthly"),
            amount_cents=int(request.POST.get("amount_cents", 9900)),
            frequency=request.POST.get("frequency", "MONTHLY"),
            moto_integration_id=settings.PAYMOBX_MOTO_INTEGRATION_ID,
            webhook_url=request.build_absolute_uri(reverse("subscription_webhook")),
        )
    except PaymobxError as e:
        return JsonResponse({"error": str(e)}, status=502)

    return JsonResponse(plan)


@csrf_exempt
def subscription_webhook(request):
    if not is_valid_callback(request, settings.PAYMOBX_HMAC):
        return HttpResponse(status=400)

    if is_paid_callback(request, settings.PAYMOBX_HMAC):
        data = json.loads(request.body)
        obj = data.get("obj", {})
        order_info = obj.get("order", {})
        print(f"SUBSCRIPTION: renewal paid for order {order_info.get('id')}")

    return HttpResponse(status=200)