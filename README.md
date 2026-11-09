# paymobx Python Integration

A simple Python library for integrating [Paymob](https://paymob.com/) payments.

Supports two flows:

- **Modern (recommended)** — Intention API + Unified Checkout (cards, wallets, **Fawry/Kiosk**, BNPL)
- **Legacy** — Order → Payment Key → Iframe / Wallet

Plus framework-agnostic **HMAC verification** helpers and a built-in **Django integration**.

## Installation

Install directly from GitHub (latest dev version):

```bash
pip install git+https://github.com/ahmhesham/paymobx.git
```

Or from PyPI (once published):

```bash
pip install paymobx
```

---

## Core Components

The library revolves around the `PaymobxClient` and a set of utility functions for HMAC verification.

### `PaymobxClient`

The main entry point for all Paymob API interactions.

#### Initialization

```python
from paymobx import PaymobxClient

client = PaymobxClient(
    secret_key="egy_sk_test_xxx",   # Intention API (modern flow)
    public_key="egy_pk_test_xxx",   # Unified Checkout URL
    api_key="your_api_key",         # Optional — legacy flow only
)
```

| Parameter    | Used by                                              | Where to find it |
| ------------ | ---------------------------------------------------- | ---------------- |
| `secret_key` | `create_intention`, `create_fawry_intention`         | Dashboard → Settings → Developers |
| `public_key` | `get_unified_checkout_url`                           | Dashboard → Settings → Developers |
| `api_key`    | `create_order`, `generate_payment_key`, wallet       | Dashboard → Settings → Developers |

---

## Modern Flow — Intention API + Unified Checkout (Recommended)

### `create_intention(amount_cents, currency, payment_methods, billing_data, **kwargs) -> dict`

Creates a payment intention and returns a dict containing `client_secret`, which you pass to `get_unified_checkout_url`.

**Required:**

- **`amount_cents`**: Amount in smallest currency unit (e.g. `10000` = `100.00`).
- **`currency`**: ISO currency code (`"EGP"`, `"USD"`, `"SAR"`, `"AED"`, `"OMR"`).
- **`payment_methods`**: List of integration IDs (card, wallet, kiosk, BNPL…).
- **`billing_data`**: Customer details. Missing fields are auto-filled with `"NA"` — but always provide at least `first_name` and `phone_number`.

**Optional:**

- **`items`**: Line items (`name`, `amount_cents`, `description`).
- **`special_reference`**: Your internal order ID.
- **`notification_url`**: Public HTTPS webhook (POST) for server-to-server confirmation.
- **`redirection_url`**: Public HTTPS URL to redirect the customer after payment.
- **`expiration`**: Intention lifetime in seconds (default `3600`).
- **`extras`**: Arbitrary metadata dict.

### `get_unified_checkout_url(client_secret, region="egypt") -> str`

Builds the Paymob Unified Checkout URL. Supported regions: `"egypt"`, `"uae"`, `"oman"`, `"ksa"`.

### `create_fawry_intention(amount_cents, currency, kiosk_integration_id, billing_data, **kwargs) -> dict`

Convenience wrapper around `create_intention` that restricts payment methods to a single **Kiosk** integration ID (this is how **Fawry** is exposed on Paymob).

### Full Card Flow Example

```python
from paymobx import PaymobxClient

client = PaymobxClient(
    secret_key="egy_sk_test_xxx",
    public_key="egy_pk_test_xxx",
)

intention = client.create_intention(
    amount_cents=15000,
    currency="EGP",
    payment_methods=[1234],  # Your Card Integration ID
    billing_data={
        "first_name": "Magka",
        "email": "user@example.com",
        "phone_number": "+201012345678",
    },
    special_reference="order-001",
    notification_url="https://your-app.com/callback/processed/",
    redirection_url="https://your-app.com/callback/response/",
)

url = client.get_unified_checkout_url(
    client_secret=intention["client_secret"],
    region="egypt",
)
print(f"Redirect user to: {url}")
```

### Fawry / Kiosk Flow Example

Create a **Kiosk** integration in the Paymob dashboard (Developers → Payment Integrations → Add → "Accept Kiosk") and use its integration ID:

```python
intention = client.create_fawry_intention(
    amount_cents=15000,
    currency="EGP",
    kiosk_integration_id=654321,
    billing_data={
        "first_name": "Ahmed",
        "phone_number": "+201000000000",
        "email": "ahmed@example.com",
    },
    special_reference="fawry-001",
)

url = client.get_unified_checkout_url(intention["client_secret"])
# Customer sees Fawry as the payment option on Unified Checkout
print(f"Fawry checkout: {url}")
```

---

## Legacy Flow — Order / Payment Key / Iframe / Wallet

The legacy methods still work unchanged. Use them if you already have an `iframe_id`-based integration or need a direct wallet redirect.

### `create_order(amount_cents, currency, items=None, delivery_needed=False) -> dict`

Creates an order in the Paymob ecommerce system.

### `generate_payment_key(amount_cents, order_id, integration_id, billing_data, currency, expiration=3600) -> str`

Generates a session token (payment key). Missing `billing_data` fields are auto-filled with `"NA"`.

### `get_iframe_url(iframe_id, payment_token) -> str`

Builds the full URL for a card payment iframe.

### `initiate_wallet_payment(payment_token, wallet_number) -> str`

Initiates a mobile wallet transaction and returns the redirection URL.

### Full Card Flow (Legacy)

```python
client = PaymobxClient(api_key="your_api_key")

order = client.create_order(amount_cents=15000, currency="USD")

token = client.generate_payment_key(
    amount_cents=15000,
    order_id=order["id"],
    integration_id=1234,
    billing_data={"first_name": "Magka", "email": "user@example.com"},
    currency="USD",
)

url = client.get_iframe_url(iframe_id=5678, payment_token=token)
print(f"Direct user to: {url}")
```

### Full Mobile Wallet Flow (Legacy)

```python
client = PaymobxClient(api_key="your_api_key")

order = client.create_order(amount_cents=10000, currency="EGP")

token = client.generate_payment_key(
    amount_cents=10000,
    order_id=order["id"],
    integration_id=4321,  # Wallet Integration ID
    billing_data={"first_name": "Magka"},
    currency="EGP",
)

redirection_url = client.initiate_wallet_payment(
    payment_token=token,
    wallet_number="01010101010",
)
print(f"Redirect user to: {redirection_url}")
```

---

## HMAC Verification Utilities

Use these to securely verify that requests to your server are actually from Paymob. They work for **both** legacy and modern Intention callbacks (the signed field list is identical).

### `verify_hmac(request_data: dict, hmac_secret: str, hmac_received: str) -> bool`

Verifies the HMAC for **Transaction Callbacks** (POST webhooks).

### `verify_response_hmac(query_params: dict, hmac_secret: str, hmac_received: str) -> bool`

Verifies the HMAC for **Transaction Response Callbacks** (GET redirects).

```python
from paymobx import verify_hmac, verify_response_hmac

# POST webhook
ok = verify_hmac(request_data, hmac_secret, received_hmac)

# GET redirect
ok = verify_response_hmac(request.GET.dict(), hmac_secret, received_hmac)
```

---

## Django Integration

Dedicated helpers for Django live in `paymobx.integrations.django`.

### 1. Transaction Processed Callback (Webhook)

```python
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from paymobx.integrations.django import is_valid_callback
import json

@csrf_exempt
def processed_callback(request):
    if is_valid_callback(request, settings.PAYMOBX_HMAC):
        data = json.loads(request.body)
        if data["obj"]["success"]:
            # Success! Update your database here
            pass
        return HttpResponse(status=200)
    return HttpResponse(status=400)
```

### 2. Transaction Response (Redirect)

```python
from paymobx.integrations.django import is_valid_response

def payment_success(request):
    if is_valid_response(request, settings.PAYMOBX_HMAC):
        return render(request, "success.html")
    return render(request, "failed.html")
```

---

## Error Handling

The library raises specific exceptions for easier debugging:

| Exception                    | When it's raised |
| ---------------------------- | ---------------- |
| `PaymobxAuthenticationError` | Bad `api_key` / `secret_key`, or 401 from Paymob |
| `PaymobxRequestError`        | Any non-2xx API response (`.status_code`, `.response` available) |
| `PaymobxValidationError`     | Client-side validation failed (missing required arg, bad region, etc.) |
| `PaymobxError`               | Base class for catching all paymobx exceptions |

```python
from paymobx import PaymobxError, PaymobxRequestError

try:
    intention = client.create_intention(...)
except PaymobxRequestError as e:
    print(f"Paymob returned {e.status_code}: {e}")
except PaymobxError as e:
    print(f"paymobx error: {e}")
```

---

## Full Usage Examples

- [`examples/full_usage_example.py`](examples/full_usage_example.py) — demonstrates every method (modern + legacy).
- [`examples/django_example/`](examples/django_example/) — a complete Django project with Card, Wallet, and Fawry buttons, and HMAC-verified callbacks.

---

## Changelog

### 1.1.0

- **New**: Intention API support (`create_intention`, `create_fawry_intention`).
- **New**: Unified Checkout URL builder (`get_unified_checkout_url`) for EG / UAE / OM / KSA.
- **New**: Fawry / Kiosk helper.
- **New**: `PaymobxValidationError` for clearer client-side errors.
- **Fix**: Legacy iframe URL now uses `accept.paymob.com` (was `accept.paymobsolutions.com`).
- **Fix**: HMAC helpers no longer crash when the `hmac` query param is missing.

### 1.0.0

- Initial release: legacy Order / Payment Key / Iframe / Wallet flow + HMAC utilities.