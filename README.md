# paymobx Python Integration

A simple Python library for integrating [paymob](https://paymob.com/) payments.

## Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/ahmhesham/paymobx.git
```

## Core Components

The library revolves around the `PaymobxClient` and a set of utility functions for HMAC verification.

### 1. `PaymobxClient`

The main entry point for all paymob API interactions.

#### Initialization

```python
from paymobx import PaymobxClient

client = PaymobxClient(api_key="your_PAYMOB_api_key")
```

#### `create_order(amount_cents: int, currency: str, items: list = None, delivery_needed: bool = False) -> dict`

Creates an order in the paymob ecommerce system.

- **`amount_cents`**: Total amount in the smallest currency unit (e.g., `1000` for `10.00`).
- **`currency`**: Three-letter currency code (e.g., `"EGP"`, `"USD"`, `"SAR"`).
- **`items`**: (Optional) List of line items for the order.
- **`delivery_needed`**: (Optional) Boolean indicating if shipping is required.

#### `generate_payment_key(amount_cents: int, order_id: str, integration_id: int, billing_data: dict, currency: str, expiration: int = 3600) -> str`

Generates a session token (payment key) required to initiate a payment.

- **`billing_data`**: A dictionary of user details. You can provide as many fields as you have; the library automatically fills missing mandatory fields with `"NA"`.
  - *Key fields*: `first_name`, `last_name`, `email`, `phone_number`.
- **`integration_id`**: Your Payment Integration ID from the paymob dashboard.

#### `get_iframe_url(iframe_id: int, payment_token: str) -> str`

Generates the full URL for a card payment iframe.

- **`iframe_id`**: Your Iframe ID from the paymob dashboard.
- **`payment_token`**: The string returned by `generate_payment_key`.

#### `initiate_wallet_payment(payment_token: str, wallet_number: str) -> str`

Initiates a mobile wallet transaction and returns the redirection URL.

- **`wallet_number`**: The customer's mobile wallet identifier (e.g., `"01010101010"`).

---

### 2. HMAC Verification Utilities

Use these to securely verify that requests incoming to your server are actually from paymob.

#### `verify_hmac(request_data: dict, hmac_secret: str, hmac_received: str) -> bool`

Verifies the HMAC for **Transaction Callbacks** (webhooks sent as POST).

#### `verify_response_hmac(query_params: dict, hmac_secret: str, hmac_received: str) -> bool`

Verifies the HMAC for **Transaction Response Callbacks** (sent as GET parameters after a redirect).

---

### Full Usage Examples

For a complete demonstration of every function in the package, see [examples/full_usage_example.py](file:///c:/Users/magka/Desktop/paymobx-integration-python-main/examples/full_usage_example.py).

For a complete web-ready implementation, check out our [Django Example Project](file:///c:/Users/magka/Desktop/paymobx-integration-python-main/examples/django_example/).

## Example: Full Card Payment Flow

```python
client = PaymobxClient(api_key="your_key")

# 1. Create Order
order = client.create_order(amount_cents=15000, currency="USD")

# 2. Generate Key with partial billing data
billing = {"first_name": "Magka", "email": "user@example.com"}
token = client.generate_payment_key(
    amount_cents=15000,
    order_id=order["id"],
    integration_id=1234,
    billing_data=billing,
    currency="USD"
)

# 3. Get Iframe URL
url = client.get_iframe_url(iframe_id=5678, payment_token=token)
print(f"Direct user to: {url}")
```

## Example: Full Mobile Wallet Payment Flow

```python
client = PaymobxClient(api_key="your_key")

# 1. Create Order
order = client.create_order(amount_cents=10000, currency="EGP")

# 2. Generate Key
token = client.generate_payment_key(
    amount_cents=10000,
    order_id=order["id"],
    integration_id=4321, # Your Wallet Integration ID
    billing_data={"first_name": "Magka"},
    currency="EGP"
)

# 3. Initiate Wallet Payment and get Redirection URL
redirection_url = client.initiate_wallet_payment(
    payment_token=token,
    wallet_number="01010101010"
)
print(f"Redirect user to: {redirection_url}")
```

## Django Integration

If you are using Django, we provide dedicated helpers to verify callbacks securely.

### 1. Transaction Processed Callback (Webhook)

```python
from paymobx.integrations.django import is_valid_callback

@csrf_exempt
def processed_callback(request):
    if is_valid_callback(request, settings.PAYMOBX_HMAC):
        # Transaction is valid, update your database
        data = json.loads(request.body)
        if data['obj']['success']:
             # Success!
             pass
    return HttpResponse(status=200)
```

### 2. Transaction Response (Redirect)

```python
from paymobx.integrations.django import is_valid_response

def payment_success(request):
    if is_valid_response(request, settings.PAYMOBX_HMAC):
        # Securely verified redirect
        return render(request, 'success.html')
    return render(request, 'failed.html')
```

## Error Handling


The library raises specific exceptions for easier debugging:
- `PaymobxAuthenticationError`: Issues with your `api_key`.
- `PaymobxRequestError`: API errors (contains `status_code` and full `response` object).
