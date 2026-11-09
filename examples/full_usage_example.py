"""
Standalone usage examples for paymobx 1.1.0.

Run against your own sandbox keys. Do NOT commit real keys to git.
"""
from paymobx import PaymobxClient


# --------------------------------------------------------------------------
# 1. MODERN FLOW — Intention API + Unified Checkout (recommended)
# --------------------------------------------------------------------------
client = PaymobxClient(
    secret_key="egy_sk_test_xxx",   # Dashboard -> Settings -> Developers
    public_key="egy_pk_test_xxx",   # Same location
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
    region="egypt",                                # "egypt" | "uae" | "oman" | "ksa"
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