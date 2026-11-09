class PaymobxError(Exception):
    """Base exception for all paymobx errors."""


class PaymobxAuthenticationError(PaymobxError):
    """Raised when authentication with Paymob fails (bad key / 401)."""


class PaymobxRequestError(PaymobxError):
    """Raised when an API request to Paymob fails (non-2xx)."""

    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class PaymobxValidationError(PaymobxError):
    """Raised when client-side validation fails before the request is sent."""