"""
Standalone usage examples for paymobx 1.2.0.

Run against your own sandbox keys. Do NOT commit real keys to git.
"""
from paymobx import PaymobxClient


# --------------------------------------------------------------------------
# 1. MODERN FLOW — Intention API + Unified Checkout (recommended)
# --------------------------------------------------------------------------
client = PaymobxClient(
    secret_key="egy_sk_test_xxx",   # Dashboard -> Settings -> Developers
    public_key="egy_pk_test_xxx",   # Same location
    region="egypt",                 # Optional, defaults to "egypt". See section 8.
)

intention = client.create_intention(
    amount_cents=10000,
    currency="EGP",
    payment_methods=[123456],                     # e.g. Card integration ID
    billing_data={
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone_number": "+201012345678",
    },
    items=[{"name": "Item 1", "amount_cents": 10000, "description": "Test"}],
    special_reference="order-001",
    notification_url="https://your-app.com/callback/processed/",
    redirection_url="https://your-app.com/callback/response/",
)

checkout_url = client.get_unified_checkout_url(
    client_secret=intention["client_secret"],
)
print(f"Redirect customer to: {checkout_url}")


# --------------------------------------------------------------------------
# 2. FAWRY / KIOSK — same Intention API, Kiosk integration ID
# --------------------------------------------------------------------------
fawry_intention = client.create_fawry_intention(
    amount_cents=15000,
    currency="EGP",
    kiosk_integration_id=654321,                   # Kiosk integration ID
    billing_data={
        "first_name": "Ahmed",
        "phone_number": "+201000000000",
        "email": "ahmed@example.com",
    },
    special_reference="fawry-001",
)
fawry_url = client.get_unified_checkout_url(fawry_intention["client_secret"])
print(f"Fawry checkout: {fawry_url}")


# --------------------------------------------------------------------------
# 3. LEGACY FLOW — Order / Payment Key / Iframe / Wallet
# --------------------------------------------------------------------------
legacy_client = PaymobxClient(api_key="your_API_key")

order = legacy_client.create_order(
    amount_cents=10000,
    currency="EGP",
    items=[{"name": "Item 1", "amount_cents": 10000}],
)

payment_token = legacy_client.generate_payment_key(
    amount_cents=10000,
    order_id=order["id"],
    integration_id=123456,
    billing_data={"first_name": "John", "email": "john@example.com"},
    currency="EGP",
)

iframe_url = legacy_client.get_iframe_url(iframe_id=5678, payment_token=payment_token)
print(f"Card iframe: {iframe_url}")

wallet_url = legacy_client.initiate_wallet_payment(
    payment_token=payment_token,
    wallet_number="01010101010",
)
print(f"Wallet redirect: {wallet_url}")


# --------------------------------------------------------------------------
# 4. PAYMENT LIFECYCLE — refund, void, capture, inquiry
#
# These use the legacy auth flow, so api_key is required.
# Reusing legacy_client above.
# --------------------------------------------------------------------------

# Full refund
legacy_client.refund_transaction("987654321")

# Partial refund (50.00 EGP)
legacy_client.refund_transaction("987654321", amount_cents=5000)

# Void before settlement (same day usually)
legacy_client.void_transaction("987654321")

# Capture from an Auth/Cap integration
legacy_client.capture_transaction("987654321", amount_cents=10000)

# Inquiry by Paymob transaction ID
txn = legacy_client.get_transaction_by_id("987654321")
print(txn)

# Inquiry by your own reference (the special_reference from create_intention)
txn = legacy_client.get_transaction_by_order_id(merchant_order_id="order-001")
print(txn)

# Or by the Paymob order ID
txn = legacy_client.get_transaction_by_order_id(order_id=order["id"])
print(txn)


# --------------------------------------------------------------------------
# 5. PAYMENT LINKS — Paymob-hosted checkout page
# --------------------------------------------------------------------------
link = legacy_client.create_payment_link(
    amount_cents=15000,
    currency="EGP",
    integration_id=123456,
    full_name="John Doe",
    phone_number="+201012345678",
    email="john.doe@example.com",
    description="Invoice #001",
    reference_id="order-001",
    notification_url="https://your-app.com/callback/processed/",
    redirection_url="https://your-app.com/callback/response/",
)
print(f"Payment link: {link}")


# --------------------------------------------------------------------------
# 6. SAVED CARDS / MOTO
#
# Needs a MOTO integration ID. The payment_token comes from a MOTO
# payment key, the card_token is from a previous successful payment.
# --------------------------------------------------------------------------
response = legacy_client.pay_with_saved_card(
    payment_token="moto_payment_key_xxx",
    card_token="saved_card_token_xxx",
    # subtype="CARD",   # override if your integration expects "CARD"
)
print(response)


# --------------------------------------------------------------------------
# 7. SUBSCRIPTION PLANS — recurring billing on top of MOTO
# --------------------------------------------------------------------------
plan = legacy_client.create_subscription_plan(
    plan_name="Pro Monthly",
    amount_cents=9900,
    frequency="MONTHLY",                           # "MONTHLY" | "WEEKLY"
    moto_integration_id=5555,
    webhook_url="https://your-app.com/subscriptions/webhook/",
)
print(plan)


# --------------------------------------------------------------------------
# 8. REGIONS — same API, different host
#
# Passing region="uae" / "oman" / "ksa" routes EVERY method (modern, legacy,
# and lifecycle) to the correct Paymob host. Default is "egypt".
#
#   egypt -> accept.paymob.com
#   uae   -> uae.paymob.com
#   oman  -> oman.paymob.com
#   ksa   -> ksa.paymob.com
# --------------------------------------------------------------------------
client_uae = PaymobxClient(
    secret_key="uae_sk_test_xxx",
    public_key="uae_pk_test_xxx",
    api_key="uae_api_key",
    region="uae",
)

# uae.paymob.com/v1/intention/
uae_intention = client_uae.create_intention(
    amount_cents=20000,
    currency="AED",
    payment_methods=[789012],
    billing_data={
        "first_name": "Sara",
        "phone_number": "+971501234567",
        "email": "sara@example.com",
    },
    special_reference="uae-order-001",
)
print(client_uae.get_unified_checkout_url(uae_intention["client_secret"]))

# uae.paymob.com/api/acceptance/void_refund/refund
client_uae.refund_transaction("111222333")

# uae.paymob.com/api/acceptance/transactions/{id}
client_uae.get_transaction_by_id("111222333")