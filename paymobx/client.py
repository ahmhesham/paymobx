import requests
from .exceptions import PaymobxAuthenticationError, PaymobxRequestError

class PaymobxClient:
    """
    A professional client for interacting with the paymobx API.
    """
    BASE_URL = "https://accept.paymob.com/api"

    def __init__(self, api_key: str, timeout: int = 10):
        """
        Args:
            api_key (str): Your paymobx API key.
            timeout (int): Request timeout in seconds. Defaults to 10.
        """
        self.api_key = api_key
        self.timeout = timeout
        self._auth_token = None

    def _authenticate(self) -> str:
        response = requests.post(
            f"{self.BASE_URL}/auth/tokens",
            json={"api_key": self.api_key},
            timeout=self.timeout
        )
        if response.status_code != 201:
            raise PaymobxAuthenticationError(f"Failed to authenticate: {response.text}")
        
        self._auth_token = response.json().get("token")
        return self._auth_token

    def create_order(self, amount_cents: int, currency: str, items: list = None, delivery_needed: bool = False) -> dict:
        if not self._auth_token:
            self._authenticate()

        payload = {
            "auth_token": self._auth_token,
            "delivery_needed": delivery_needed,
            "amount_cents": amount_cents,
            "currency": currency,
            "items": items or [],
        }
        response = requests.post(
            f"{self.BASE_URL}/ecommerce/orders", 
            json=payload,
            timeout=self.timeout
        )
        
        if response.status_code != 201:
            raise PaymobxRequestError(f"Failed to create order: {response.text}", status_code=response.status_code, response=response)
        
        return response.json()

    def generate_payment_key(self, amount_cents: int, order_id: str, integration_id: int, billing_data: dict, currency: str, expiration: int = 3600) -> str:
        if not self._auth_token:
            self._authenticate()

        defaults = {
            "first_name": "NA",
            "last_name": "NA",
            "email": "NA",
            "phone_number": "NA",
            "apartment": "NA",
            "floor": "NA",
            "street": "NA",
            "building": "NA",
            "shipping_method": "NA",
            "postal_code": "NA",
            "city": "NA",
            "country": "NA",
            "state": "NA"
        }
        final_billing_data = {**defaults, **billing_data}

        payload = {
            "auth_token": self._auth_token,
            "amount_cents": amount_cents,
            "expiration": expiration,
            "order_id": order_id,
            "billing_data": final_billing_data,
            "currency": currency,
            "integration_id": integration_id,
        }
        response = requests.post(
            f"{self.BASE_URL}/acceptance/payment_keys", 
            json=payload,
            timeout=self.timeout
        )
        
        if response.status_code != 201:
            raise PaymobxRequestError(f"Failed to generate payment key: {response.text}", status_code=response.status_code, response=response)
        
        return response.json().get("token")

    def initiate_wallet_payment(self, payment_token: str, wallet_number: str) -> str:
        payload = {
            "source": {
                "identifier": wallet_number,
                "subtype": "WALLET"
            },
            "payment_token": payment_token
        }
        response = requests.post(
            f"{self.BASE_URL}/acceptance/payments/pay", 
            json=payload,
            timeout=self.timeout
        )
        
        if response.status_code != 200:
            raise PaymobxRequestError(f"Failed to initiate wallet payment: {response.text}", status_code=response.status_code, response=response)
        
        return response.json().get("iframe_redirection_url")

    def get_iframe_url(self, iframe_id: int, payment_token: str) -> str:
        return f"https://accept.paymobsolutions.com/api/acceptance/iframes/{iframe_id}?payment_token={payment_token}"
