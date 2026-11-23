import json
from typing import Any

from ..utils import verify_hmac, verify_response_hmac


def is_valid_callback(request: Any, hmac_secret: str) -> bool:
    """
    Helper for Django POST callbacks (Transaction Processed webhook).
    Works with both legacy Order callbacks and modern Intention callbacks.
    """
    if request.method != "POST":
        return False
    try:
        data = json.loads(request.body)
        received = request.GET.get("hmac")
        return verify_hmac(data, hmac_secret, received)
    except (json.JSONDecodeError, AttributeError):
        return False


def is_valid_response(request: Any, hmac_secret: str) -> bool:
    """
    Helper for Django GET callbacks (Transaction Response redirect).
    """
    params = request.GET.dict()
    received = params.get("hmac")
    return verify_response_hmac(params, hmac_secret, received)


# ---------------------------------------------------------------------------
# Paid-status helpers
#
# These check HMAC *and* whether the payment succeeded, in one call.
# Use them when you only care about "should I fulfill this order?".
# ---------------------------------------------------------------------------

def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False


def is_paid_callback(request: Any, hmac_secret: str) -> bool:
    """
    Return True only if a POST webhook is genuine AND the payment succeeded.

    Covers both normal transaction callbacks and subscription callbacks —
    both store the success flag at ``obj.success``.
    """
    if request.method != "POST":
        return False
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, AttributeError):
        return False

    if not verify_hmac(payload, hmac_secret, request.GET.get("hmac")):
        return False

    obj = payload.get("obj") or {}
    return _truthy(obj.get("success"))


def is_paid_response(request: Any, hmac_secret: str) -> bool:
    """
    Return True only if a GET redirect is genuine AND the payment succeeded.
    """
    params = request.GET.dict()
    if not verify_response_hmac(params, hmac_secret, params.get("hmac")):
        return False
    return _truthy(params.get("success", ""))