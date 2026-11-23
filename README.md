# paymobx

Python client for the Paymob payment gateway.

Two flows are supported:

- Modern: Intention API + Unified Checkout (cards, wallets, Fawry/Kiosk, BNPL)
- Legacy: Order -> Payment Key -> Iframe / Wallet

It also covers the payment lifecycle (refund, void, capture, inquiry, payment links, saved cards/MOTO, subscriptions), ships HMAC verification helpers, includes a Django integration, and works across all Paymob regions: Egypt, UAE, Oman, and Saudi Arabia.

## Installation

```bash
pip install git+https://github.com/ahmhesham/paymobx.git
```

Or from PyPI once published:

```bash
pip install paymobx
```

## Client

```python
from paymobx import PaymobxClient

client = PaymobxClient(
    secret_key="egy_sk_test_xxx",   # Intention API
    public_key="egy_pk_test_xxx",   # Unified Checkout URL
    api_key="your_api_key",         # legacy flow and lifecycle methods
    region="egypt",                 # egypt | uae | oman | ksa
)
```

| Parameter    | Used by                                                                    | Where to find it |
| ------------ | -------------------------------------------------------------------------- | ---------------- |
| `secret_key` | `create_intention`, `create_fawry_intention`                              | Dashboard -> Settings -> Developers |
| `public_key` | `get_unified_checkout_url`                                                | Dashboard -> Settings -> Developers |
| `api_key`    | `create_order`, `generate_payment_key`, wallet, all lifecycle methods     | Dashboard -> Settings -> Developers |
| `region`     | every API call                                                             | Pick your account's region: `egypt`, `uae`, `oman`, `ksa`. Default `egypt` |

The lifecycle methods (refund, void, capture, inquiry, payment links, saved cards, subscriptions) authenticate with `api_key` only. If you use the Intention flow and also need lifecycle control, pass both `secret_key` and `api_key`.

### Regions

Pass `region="uae"`, `"oman"`, or `"ksa"` and every method — modern and legacy, including refund / void / capture / inquiry / payment links / MOTO / subscriptions — goes to the correct Paymob host automatically.

```python
client_uae = PaymobxClient(
    secret_key="uae_sk_test_xxx",
    public_key="uae_pk_test_xxx",
    api_key="uae_api_key",
    region="uae",
)

client_uae.create_intention(...)          # uae.paymob.com/v1/intention/
client_uae.refund_transaction("987")      # uae.paymob.com/api/acceptance/void_refund/refund
```

## Modern flow

### create_intention(amount_cents, currency, payment_methods, billing_data, **kwargs)

Creates an intention and returns a dict with `client_secret`, which you pass to `get_unified_checkout_url`.

Required:

- `amount_cents`: amount in the smallest currency unit (10000 = 100.00)
- `currency`: ISO code (EGP, USD, SAR, AED, OMR)
- `payment_methods`: list of integration IDs
- `billing_data`: customer details; missing fields are filled with "NA"

Optional:

- `items`: line items (`name`, `amount_cents`, `description`)
- `special_reference`: your internal order ID
- `notification_url`: public HTTPS webhook for server-to-server confirmation
- `redirection_url`: public HTTPS URL to send the customer back to
- `expiration`: intention lifetime in seconds (default 3600)
- `extras`: any extra metadata dict

### get_unified_checkout_url(client_secret, region=None, public_key=None)

Builds the checkout URL. `region` defaults to the client's region; pass it explicitly to override for a single call. Supported regions: `egypt`, `uae`, `oman`, `ksa`.

### create_fawry_intention(amount_cents, currency, kiosk_integration_id, billing_data, **kwargs)

Wrapper around `create_intention` that uses a single Kiosk integration ID (that's how Fawry is exposed on Paymob).

### Card example

```python
from paymobx import PaymobxClient

client = PaymobxClient(
    secret_key="egy_sk_test_xxx",
    public_key="egy_pk_test_xxx",
)

intention = client.create_intention(
    amount_cents=15000,
    currency="EGP",
    payment_methods=[1234],
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
)
print(url)
```

### Fawry example

Create a Kiosk integration in the dashboard (Developers -> Payment Integrations -> Add -> Accept Kiosk) and use its ID:

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
print(url)
```

## Legacy flow

Use this if you already have an iframe integration or need a direct wallet redirect.

- `create_order(amount_cents, currency, items=None, delivery_needed=False)` creates an order
- `generate_payment_key(amount_cents, order_id, integration_id, billing_data, currency, expiration=3600)` returns a session token
- `get_iframe_url(iframe_id, payment_token)` builds the iframe URL
- `initiate_wallet_payment(payment_token, wallet_number)` returns the redirect URL

### Card example

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
print(url)
```

### Wallet example

```python
client = PaymobxClient(api_key="your_api_key")

order = client.create_order(amount_cents=10000, currency="EGP")

token = client.generate_payment_key(
    amount_cents=10000,
    order_id=order["id"],
    integration_id=4321,
    billing_data={"first_name": "Magka"},
    currency="EGP",
)

url = client.initiate_wallet_payment(
    payment_token=token,
    wallet_number="01010101010",
)
print(url)
```

## Payment lifecycle

These methods live on `PaymobxClient` through `PaymentOperationsMixin`. They authenticate with `api_key` and automatically use the client's `region`.

```python
from paymobx import PaymobxClient

client = PaymobxClient(api_key="your_api_key", region="egypt")
```

### Refund / void / capture

| Method | Endpoint |
| ------ | -------- |
| `refund_transaction(transaction_id, amount_cents=None)` | `POST /api/acceptance/void_refund/refund` |
| `void_transaction(transaction_id)` | `POST /api/acceptance/void_refund/void` |
| `capture_transaction(transaction_id, amount_cents)` | `POST /api/acceptance/capture` |

```python
client.refund_transaction("987654321")                    # full refund
client.refund_transaction("987654321", amount_cents=5000) # partial refund
client.void_transaction("987654321")
client.capture_transaction("987654321", amount_cents=15000)
```

Void only works before settlement (usually same day). Capture is for Auth/Cap integrations.

### Inquiry

| Method | Endpoint |
| ------ | -------- |
| `get_transaction_by_id(transaction_id)` | `GET /api/acceptance/transactions/{id}` |
| `get_transaction_by_order_id(order_id=None, merchant_order_id=None)` | `POST /api/ecommerce/orders/transaction_inquiry` |

```python
client.get_transaction_by_id("987654321")
client.get_transaction_by_order_id(merchant_order_id="order-001")
```

`merchant_order_id` is the `special_reference` you set when creating the intention. Useful when a webhook is missed.

### Payment links

| Method | Endpoint |
| ------ | -------- |
| `create_payment_link(...)` | `POST /api/ecommerce/payment-links` |

```python
link = client.create_payment_link(
    amount_cents=15000,
    currency="EGP",
    integration_id=1234,
    full_name="Magka",
    phone_number="+201012345678",
    email="user@example.com",
    description="Invoice #001",
    reference_id="order-001",
    notification_url="https://your-app.com/callback/processed/",
    redirection_url="https://your-app.com/callback/response/",
)
print(link)
```

### Saved cards / MOTO

Needs a MOTO integration ID, a `payment_token` for that integration, and a saved `card_token`.

| Method | Endpoint |
| ------ | -------- |
| `pay_with_saved_card(payment_token, card_token, subtype="TOKEN")` | `POST /api/acceptance/payments/pay` |

```python
response = client.pay_with_saved_card(
    payment_token="moto_payment_key_xxx",
    card_token="saved_card_token_xxx",
)
print(response)
```

Set `subtype="CARD"` if your integration expects that instead of `TOKEN`.

### Subscription plans

| Method | Endpoint |
| ------ | -------- |
| `create_subscription_plan(...)` | `POST /api/acceptance/subscription-plans` |

```python
plan = client.create_subscription_plan(
    plan_name="Pro Monthly",
    amount_cents=9900,
    frequency="MONTHLY",
    moto_integration_id=5555,
    webhook_url="https://your-app.com/subscriptions/webhook/",
)
print(plan)
```

Paymob calls `webhook_url` on every billing cycle.

## HMAC verification

Both helpers work with legacy and Intention callbacks.

- `verify_hmac(request_data, hmac_secret, hmac_received)` for POST webhooks
- `verify_response_hmac(query_params, hmac_secret, hmac_received)` for GET redirects

```python
from paymobx import verify_hmac, verify_response_hmac

ok = verify_hmac(request_data, hmac_secret, received_hmac)
ok = verify_response_hmac(request.GET.dict(), hmac_secret, received_hmac)
```

## Django

Helpers live in `paymobx.integrations.django`.

### Webhook

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
            pass  # update your database here
        return HttpResponse(status=200)
    return HttpResponse(status=400)
```

### Redirect

```python
from paymobx.integrations.django import is_valid_response

def payment_success(request):
    if is_valid_response(request, settings.PAYMOBX_HMAC):
        return render(request, "success.html")
    return render(request, "failed.html")
```

### Paid-status shortcuts

Two more helpers combine HMAC verification with the success check, so a webhook view stays one line:

```python
from paymobx.integrations.django import is_paid_callback, is_paid_response

@csrf_exempt
def processed_callback(request):
    if is_paid_callback(request, settings.PAYMOBX_HMAC):
        # HMAC is valid and obj.success is true
        pass
    return HttpResponse(status=200)

def payment_response(request):
    paid = is_paid_response(request, settings.PAYMOBX_HMAC)
    return render(request, "status.html", {"success": paid})
```

## Errors

| Exception                    | When it's raised |
| ---------------------------- | ---------------- |
| `PaymobxAuthenticationError` | Bad `api_key` / `secret_key`, or 401 from Paymob |
| `PaymobxRequestError`        | Any non-2xx response; `status_code` and `response` are attached |
| `PaymobxValidationError`     | Client-side validation failed (missing argument, bad region, etc) |
| `PaymobxError`               | Base class |

```python
from paymobx import PaymobxError, PaymobxRequestError

try:
    client.create_intention(...)
except PaymobxRequestError as e:
    print(e.status_code, e)
except PaymobxError as e:
    print(e)
```

## Examples

- `examples/full_usage_example.py` covers every method (modern, legacy, lifecycle)
- `examples/django_example/` is a full Django project with card, wallet and Fawry buttons, plus HMAC-verified callbacks

## Changelog

### 1.2.0

- Added lifecycle methods on `PaymobxClient` through `PaymentOperationsMixin`:
  - `refund_transaction`
  - `void_transaction`
  - `capture_transaction`
  - `get_transaction_by_id`
  - `get_transaction_by_order_id`
  - `create_payment_link`
  - `pay_with_saved_card`
  - `create_subscription_plan`
- Added regional routing: pass `region="egypt"`, `"uae"`, `"oman"`, or `"ksa"` to route every method to the correct Paymob host
- Exported `PaymentOperationsMixin`
- Added `is_paid_callback` and `is_paid_response` Django helpers
- Lifecycle methods authenticate with `api_key`

### 1.1.0

- Intention API support (`create_intention`, `create_fawry_intention`)
- Unified Checkout URL builder for EG, UAE, OM, KSA
- Fawry/Kiosk helper
- `PaymobxValidationError`
- Fixed legacy iframe URL host (`accept.paymob.com`)
- HMAC helpers no longer crash when the `hmac` query param is missing

### 1.0.0

- Initial release: legacy order, payment key, iframe, wallet, HMAC helpers