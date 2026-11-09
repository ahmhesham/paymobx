import requests
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

from .exceptions import (
    PaymobxAuthenticationError,
    PaymobxRequestError,
    PaymobxValidationError,
)


BILLING_DEFAULTS: Dict[str, str] = {
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
    "state": "NA",
}


class PaymobxClient:
    """
    A professional client for interacting with the Paymob API.

    Supports two authentication modes:

    1. Legacy (Order / Payment Key / Iframe / Wallet):
       - Requires ``api_key``

    2. Modern (Intention API + Unified Checkout, incl. Fawry/Kiosk):
       - Requires ``secret_key`` (Intention API)
       - Requires ``public_key`` (Unified Checkout URL)

    Both keys are found in the Paymob Dashboard -> Settings -> Developers.
    """

    BASE_URL = "https://accept.paymob.com/api"
    INTENTION_URL = "https://accept.paymob.com/v1/intention/"

    CHECKOUT_ENDPOINTS: Dict[str, str] = {
        "egypt": "https://eg.checkout.paymob.com/unifiedcheckout/",
        "uae":   "https://uae.checkout.paymob.com/unifiedcheckout/",
        "oman":  "https://om.checkout.paymob.com/unifiedcheckout/",
        "ksa":   "https://ksa.checkout.paymob.com/unifiedcheckout/",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        public_key: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        """
        Args:
            api_key:    Paymob API Key (legacy flow only).
            secret_key: Paymob Secret Key (required for Intention API).
            public_key: Paymob Public Key (required for Unified Checkout URL).
            timeout:    HTTP request timeout in seconds.
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.public_key = public_key
        self.timeout = timeout
        self._auth_token: Optional[str] = None

    # ------------------------------------------------------------------
    # MODERN FLOW — Intention API + Unified Checkout
    # ------------------------------------------------------------------

    def create_intention(
        self,
        amount_cents: int,
        currency: str,
        payment_methods: List[int],
        billing_data: Dict[str, Any],
        items: Optional[List[Dict[str, Any]]] = None,
        special_reference: Optional[str] = None,
        notification_url: Optional[str] = None,
        redirection_url: Optional[str] = None,
        expiration: int = 3600,
        extras: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a payment intention. Returns a dict containing ``client_secret``,
        which you then pass to :meth:`get_unified_checkout_url`.

        Args:
            amount_cents:       Amount in smallest currency unit (e.g. 10000 = 100.00).
            currency:           ISO currency code (EGP, USD, SAR, AED, OMR).
            payment_methods:    List of integration IDs. For Fawry/Kiosk, use the
                                Kiosk integration ID.
            billing_data:       Customer details. Missing fields are auto-filled with "NA".
            items:              Optional list of line items (``name``, ``amount_cents``, ...).
            special_reference:  Your internal order / reference ID.
            notification_url:   Public HTTPS URL for POST webhook (server-to-server).
            redirection_url:    Public HTTPS URL the user is redirected to after paying.
            expiration:         Intention expiry in seconds (default 3600).
            extras:             Optional custom metadata dict.

        Returns:
            dict: Paymob response containing ``client_secret`` and ``intention_order_id``.
        """
        if not self.secret_key:
            raise PaymobxAuthenticationError(
                "secret_key is required for create_intention(). "
                "Find it in Paymob Dashboard -> Settings -> Developers."
            )
        if amount_cents <= 0:
            raise PaymobxValidationError("amount_cents must be a positive integer.")
        if not payment_methods:
            raise PaymobxValidationError(
                "payment_methods must contain at least one integration ID."
            )

        final_billing = {**BILLING_DEFAULTS, **(billing_data or {})}

        payload: Dict[str, Any] = {
            "amount": amount_cents,
            "currency": currency,
            "payment_methods": payment_methods,
            "billing_data": final_billing,
            "items": items or [],
            "expiration": expiration,
        }
        if special_reference:
            payload["special_reference"] = special_reference
        if notification_url:
            payload["notification_url"] = notification_url
        if redirection_url:
            payload["redirection_url"] = redirection_url
        if extras:
            payload["extras"] = extras

        response = requests.post(
            self.INTENTION_URL,
            json=payload,
            headers={
                "Authorization": f"Token {self.secret_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )

        if response.status_code == 401:
            raise PaymobxAuthenticationError(
                f"Invalid secret_key: {response.text}"
            )
        if response.status_code not in (200, 201):
            raise PaymobxRequestError(
                f"Intention creation failed: {response.text}",
                status_code=response.status_code,
                response=response,
            )

        return response.json()

    def get_unified_checkout_url(
        self,
        client_secret: str,
        region: str = "egypt",
        public_key: Optional[str] = None,
    ) -> str:
        """
        Build the Paymob Unified Checkout redirect URL.

        Args:
            client_secret: ``client_secret`` returned from :meth:`create_intention`.
            region:        One of "egypt", "uae", "oman", "ksa". Default "egypt".
            public_key:    Override the client's public_key if needed.

        Returns:
            str: Full URL to redirect the customer to.
        """
        pub = public_key or self.public_key
        if not pub:
            raise PaymobxValidationError(
                "public_key is required. Pass it to PaymobxClient or as an argument."
            )
        base = self.CHECKOUT_ENDPOINTS.get((region or "egypt").lower())
        if not base:
            raise PaymobxValidationError(
                f"Unsupported region '{region}'. "
                f"Choose from {list(self.CHECKOUT_ENDPOINTS.keys())}."
            )
        query = urlencode({"publicKey": pub, "clientSecret": client_secret})
        return f"{base}?{query}"

    def create_fawry_intention(
        self,
        amount_cents: int,
        currency: str,
        kiosk_integration_id: int,
        billing_data: Dict[str, Any],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Convenience wrapper: creates an Intention restricted to a Fawry / Kiosk
        integration ID. All extra ``**kwargs`` are forwarded to
        :meth:`create_intention`.
        """
        return self.create_intention(
            amount_cents=amount_cents,
            currency=currency,
            payment_methods=[kiosk_integration_id],
            billing_data=billing_data,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # LEGACY FLOW — Order / Payment Key / Iframe / Wallet
    # ------------------------------------------------------------------

    def _authenticate(self) -> str:
        if not self.api_key:
            raise PaymobxAuthenticationError(
                "api_key is required for the legacy flow."
            )
        response = requests.post(
            f"{self.BASE_URL}/auth/tokens",
            json={"api_key": self.api_key},
            timeout=self.timeout,
        )
        if response.status_code != 201:
            raise PaymobxAuthenticationError(
                f"Failed to authenticate: {response.text}"
            )
        self._auth_token = response.json().get("token")
        return self._auth_token  # type: ignore[return-value]

    def create_order(
        self,
        amount_cents: int,
        currency: str,
        items: Optional[list] = None,
        delivery_needed: bool = False,
    ) -> dict:
        """Legacy: create an ecommerce order."""
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
            timeout=self.timeout,
        )
        if response.status_code != 201:
            raise PaymobxRequestError(
                f"Failed to create order: {response.text}",
                status_code=response.status_code,
                response=response,
            )
        return response.json()

    def generate_payment_key(
        self,
        amount_cents: int,
        order_id: str,
        integration_id: int,
        billing_data: dict,
        currency: str,
        expiration: int = 3600,
    ) -> str:
        """Legacy: generate a payment key (session token)."""
        if not self._auth_token:
            self._authenticate()

        final_billing_data = {**BILLING_DEFAULTS, **billing_data}

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
            timeout=self.timeout,
        )
        if response.status_code != 201:
            raise PaymobxRequestError(
                f"Failed to generate payment key: {response.text}",
                status_code=response.status_code,
                response=response,
            )
        return response.json().get("token")

    def initiate_wallet_payment(self, payment_token: str, wallet_number: str) -> str:
        """Legacy: initiate a mobile wallet payment and return the redirect URL."""
        payload = {
            "source": {"identifier": wallet_number, "subtype": "WALLET"},
            "payment_token": payment_token,
        }
        response = requests.post(
            f"{self.BASE_URL}/acceptance/payments/pay",
            json=payload,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise PaymobxRequestError(
                f"Failed to initiate wallet payment: {response.text}",
                status_code=response.status_code,
                response=response,
            )
        return response.json().get("iframe_redirection_url")

    def get_iframe_url(self, iframe_id: int, payment_token: str) -> str:
        """Legacy: build the iframe URL for card payments."""
        return (
            f"https://accept.paymob.com/api/acceptance/iframes/"
            f"{iframe_id}?payment_token={payment_token}"
        )