import hmac
import hashlib

def verify_hmac(request_data: dict, hmac_secret: str, hmac_received: str) -> bool:
    """
    Verifies HMAC for POST callbacks (Processed callbacks).
    """
    fields = [
        ('obj', 'amount_cents'), ('obj', 'created_at'), ('obj', 'currency'),
        ('obj', 'error_occured'), ('obj', 'has_parent_transaction'), ('obj', 'id'),
        ('obj', 'integration_id'), ('obj', 'is_3d_secure'), ('obj', 'is_auth'),
        ('obj', 'is_capture'), ('obj', 'is_refunded'), ('obj', 'is_standalone_payment'),
        ('obj', 'is_voided'), ('obj', 'order', 'id'), ('obj', 'owner'),
        ('obj', 'pending'), ('obj', 'source_data', 'pan'), ('obj', 'source_data', 'sub_type'),
        ('obj', 'source_data', 'type'), ('obj', 'success'),
    ]

    def _extract(data, keys):
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, '')
            else:
                return ''
        return data

    msg = ""
    for path in fields:
        val = _extract(request_data, path)
        if isinstance(val, bool):
            val = "true" if val else "false"
        msg += str(val)

    gen = hmac.new(hmac_secret.encode(), msg.encode(), hashlib.sha512).hexdigest()
    return hmac.compare_digest(gen, hmac_received)

def verify_response_hmac(query_params: dict, hmac_secret: str, hmac_received: str) -> bool:
    """
    Verifies HMAC for GET callbacks (Response callbacks).
    """
    fields = [
        'amount_cents', 'created_at', 'currency', 'error_occured',
        'has_parent_transaction', 'id', 'integration_id', 'is_3d_secure',
        'is_auth', 'is_capture', 'is_refunded', 'is_standalone_payment',
        'is_voided', 'order', 'owner', 'pending', 'source_data.pan',
        'source_data.sub_type', 'source_data.type', 'success',
    ]

    msg = ""
    for field in fields:
        val = query_params.get(field, "")
        if isinstance(val, bool):
            val = "true" if val else "false"
        msg += str(val)

    gen = hmac.new(hmac_secret.encode(), msg.encode(), hashlib.sha512).hexdigest()
    return hmac.compare_digest(gen, hmac_received)
