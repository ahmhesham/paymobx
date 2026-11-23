import requests
from typing import Any, Dict, Optional

from .exceptions import (
    PaymobxRequestError,
    PaymobxValidationError,
)


class PaymentOperationsMixin:
    """
    Mixin for ``PaymobxClient`` that adds payment lifecycle operations:

    - Refund / Void / Capture
    - Transaction inquiry (by transaction ID or order ID / merchant reference)
    - Payment links (QuickLinks)
    - Saved cards / MOTO
    - Subscription plans

    All methods use the legacy ``api_key`` authentication flow (``auth_token``),
    which is obtained lazily via ``self._authenticate()`` from ``PaymobxClient``.
    """

    def _post_accept_action(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Authenticated POST to an Accept API endpoint.

        Reuses ``self._authenticate()`` from ``PaymobxClient`` and injects
        ``auth_token`` into the request body automatically.
        """
        if not self._auth_token:
            self._authenticate()

        payload = {**payload, "auth_token": self._auth_token}

        response = requests.post(
            f"{self.base_url}{endpoint}",
            json=payload,
            timeout=self.timeout,
        )
        if response.status_code not in (200, 201):
            raise PaymobxRequestError(
                f"Action failed ({endpoint}): {response.text}",
                status_code=response.status_code,
                response=response,
            )
        return response.json()

    def refund_transaction(
        self,
        transaction_id: str,
        amount_cents: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Refund a transaction (full or partial).

        Endpoint: ``POST /api/acceptance/void_refund/refund``

        Args:
            transaction_id: Paymob transaction ID to refund.
            amount_cents:   If ``None``, full refund. Otherwise partial refund
                            for the given amount (in smallest currency unit).
        """
        payload: Dict[str, Any] = {"transaction_id": transaction_id}
        if amount_cents is not None:
            if amount_cents <= 0:
                raise PaymobxValidationError("amount_cents must be a positive integer.")
            payload["amount_cents"] = amount_cents
        return self._post_accept_action("/acceptance/void_refund/refund", payload)

    def void_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """
        Void a transaction (cancel before settlement, usually same-day).

        Endpoint: ``POST /api/acceptance/void_refund/void``
        """
        return self._post_accept_action(
            "/acceptance/void_refund/void",
            {"transaction_id": transaction_id},
        )

    def capture_transaction(
        self,
        transaction_id: str,
        amount_cents: int,
    ) -> Dict[str, Any]:
        """
        Capture funds from a previously authorized (Auth/Cap) transaction.

        Endpoint: ``POST /api/acceptance/capture``

        Args:
            transaction_id: Transaction ID from the authorization step.
            amount_cents:   Amount to capture (can be partial).
        """
        if amount_cents <= 0:
            raise PaymobxValidationError("amount_cents must be a positive integer.")
        return self._post_accept_action(
            "/acceptance/capture",
            {"transaction_id": transaction_id, "amount_cents": amount_cents},
        )

    def get_transaction_by_id(self, transaction_id: str) -> Dict[str, Any]:
        """
        Retrieve transaction details by Paymob transaction ID.

        Endpoint: ``GET /api/acceptance/transactions/{transaction_id}``
        """
        if not self._auth_token:
            self._authenticate()

        response = requests.get(
            f"{self.base_url}/acceptance/transactions/{transaction_id}",
            params={"auth_token": self._auth_token},
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise PaymobxRequestError(
                f"Inquiry failed: {response.text}",
                status_code=response.status_code,
                response=response,
            )
        return response.json()

    def get_transaction_by_order_id(
        self,
        order_id: Optional[str] = None,
        merchant_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve the latest transaction linked to a Paymob Order ID or to your
        own merchant reference (the ``special_reference`` you sent when creating
        the intention / order).

        Endpoint: ``POST /api/ecommerce/orders/transaction_inquiry``

        At least one of ``order_id`` or ``merchant_order_id`` is required.
        """
        if not order_id and not merchant_order_id:
            raise PaymobxValidationError(
                "Provide at least one of order_id or merchant_order_id."
            )
        payload: Dict[str, Any] = {}
        if order_id:
            payload["order_id"] = order_id
        if merchant_order_id:
            payload["merchant_order_id"] = merchant_order_id
        return self._post_accept_action(
            "/ecommerce/orders/transaction_inquiry", payload
        )

    def create_payment_link(
        self,
        amount_cents: int,
        currency: str,
        integration_id: int,
        full_name: str,
        phone_number: str,
        email: Optional[str] = None,
        description: Optional[str] = None,
        expires_at: Optional[str] = None,
        notification_url: Optional[str] = None,
        redirection_url: Optional[str] = None,
        reference_id: Optional[str] = None,
        is_live: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a Paymob-hosted payment link (QuickLink).

        Endpoint: ``POST /api/ecommerce/payment-links``

        Returns the raw Paymob response (which includes the link ``id`` you can
        redirect the customer to).
        """
        if amount_cents <= 0:
            raise PaymobxValidationError("amount_cents must be a positive integer.")

        payload: Dict[str, Any] = {
            "amount_cents": amount_cents,
            "currency": currency,
            "payment_methods": [integration_id],
            "full_name": full_name,
            "phone_number": phone_number,
            "is_live": is_live,
        }
        if email:
            payload["email"] = email
        if description:
            payload["description"] = description
        if expires_at:
            payload["expires_at"] = expires_at
        if notification_url:
            payload["notification_url"] = notification_url
        if redirection_url:
            payload["redirection_url"] = redirection_url
        if reference_id:
            payload["reference_id"] = reference_id

        return self._post_accept_action("/ecommerce/payment-links", payload)

    def pay_with_saved_card(
        self,
        payment_token: str,
        card_token: str,
        subtype: str = "TOKEN",
    ) -> Dict[str, Any]:
        """
        Charge a saved card using the headless payment endpoint (MOTO).

        Endpoint: ``POST /api/acceptance/payments/pay``

        Args:
            payment_token: MOTO payment key (from your MOTO integration).
            card_token:    Saved card token (obtained from a previous
                           successful transaction).
            subtype:       Paymob source subtype. Defaults to ``"TOKEN"``.
                           Use ``"CARD"`` if your integration expects it.
        """
        payload = {
            "source": {"identifier": card_token, "subtype": subtype},
            "payment_token": payment_token,
        }
        return self._post_accept_action("/acceptance/payments/pay", payload)

    def create_subscription_plan(
        self,
        plan_name: str,
        amount_cents: int,
        frequency: str,
        moto_integration_id: int,
        webhook_url: str,
        **extra_plan_params: Any,
    ) -> Dict[str, Any]:
        """
        Create a recurring subscription plan (requires a MOTO integration ID).

        Endpoint: ``POST /api/acceptance/subscription-plans``

        Args:
            plan_name:            Human-readable plan name.
            amount_cents:         Amount charged per cycle.
            frequency:            e.g. ``"MONTHLY"`` or ``"WEEKLY"``.
            moto_integration_id:  MOTO integration ID from the dashboard.
            webhook_url:          URL Paymob will call on each billing cycle.
            **extra_plan_params:  Any additional Paymob plan parameters.
        """
        if amount_cents <= 0:
            raise PaymobxValidationError("amount_cents must be a positive integer.")
        if not moto_integration_id:
            raise PaymobxValidationError("moto_integration_id is required.")

        payload: Dict[str, Any] = {
            "name": plan_name,
            "amount_cents": amount_cents,
            "frequency": frequency,
            "integration_id": moto_integration_id,
            "webhook_url": webhook_url,
            **extra_plan_params,
        }
        return self._post_accept_action("/acceptance/subscription-plans", payload)