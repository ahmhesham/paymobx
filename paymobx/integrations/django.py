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