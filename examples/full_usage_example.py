from paymobx import PaymobxClient, verify_hmac, verify_response_hmac
from paymobx.integrations.django import is_valid_callback, is_valid_response

# --------------------------------------------------------------------------
# 1. INITIALIZATION
# --------------------------------------------------------------------------
API_KEY = "your_api_key_here"
client = PaymobxClient(api_key=API_KEY)


# --------------------------------------------------------------------------
# 2. CORE PAYMENT FLOW (Order -> Payment Key)
# --------------------------------------------------------------------------

# STEP A: Create an Order
# currency is required for clarity and international support
order = client.create_order(
    amount_cents=10000, 
    currency="EGP",
    items=[{"name": "Item 1", "amount_cents": 10000, "description": "Custom item description"}],
    delivery_needed=False
)
order_id = order['id']


# STEP B: Generate Payment Key
# Billing data is flexible. Mandatory fields missing from your dict 
# will be automatically filled with "NA" by the library.
billing_data = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone_number": "+201012345678"
}

payment_token = client.generate_payment_key(
    amount_cents=10000,
    order_id=order_id,
    integration_id=123456,  # Replace with your Integration ID
    billing_data=billing_data,
    currency="EGP"
)


# --------------------------------------------------------------------------
# 3. SPECIFIC PAYMENT METHODS
# --------------------------------------------------------------------------

# OPTION 1: Card Payments (Iframe)
iframe_url = client.get_iframe_url(iframe_id=112233, payment_token=payment_token)
print(f"Card payment URL: {iframe_url}")


# OPTION 2: Mobile Wallets (Vodafone Cash, etc.)
redirection_url = client.initiate_wallet_payment(
    payment_token=payment_token,
    wallet_number="01010101010"
)
print(f"Wallet redirection URL: {redirection_url}")

