class PaymobxError(Exception):
    """Base exception for paymobx errors."""
    pass

class PaymobxAuthenticationError(PaymobxError):
    """Raised when authentication with paymobx fails."""
    pass

class PaymobxRequestError(PaymobxError):
    """Raised when an API request to paymobx fails."""
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
