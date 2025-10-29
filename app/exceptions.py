"""
Custom exception classes for the Vehicle Rental web app.

These exceptions provide precise error types that controllers can catch
to render friendly messages instead of generic 500 errors.
"""


class VehicleNotFoundError(Exception):
    """Raised when a vehicle ID cannot be found in the system."""

    def __init__(self, message: str = "Error: vehicle not found") -> None:
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:  # pragma: no cover
        return self.message


class UserNotFoundError(Exception):
    """Raised when a user/renter ID cannot be found in the system."""

    def __init__(self, message: str = "Error: user not found") -> None:
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:  # pragma: no cover
        return self.message


class RentalNotFoundError(Exception):
    """Raised when a rental record cannot be found in the system."""

    def __init__(self, message: str = "Error: rental not found") -> None:
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:  # pragma: no cover
        return self.message


class InvalidDateRangeError(Exception):
    """Raised when start date is after end date or an invalid date is provided."""

    def __init__(self, message: str = "Error: invalid date range") -> None:
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:  # pragma: no cover
        return self.message


class VehicleUnavailableError(Exception):
    """Raised when a vehicle is not available for the requested dates."""

    def __init__(self, message: str = "Error: vehicle is not available") -> None:
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:  # pragma: no cover
        return self.message


class PaymentProcessingError(Exception):
    """Raised when payment or invoice generation fails."""

    def __init__(self, message: str = "Error: payment processing failed") -> None:
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:  # pragma: no cover
        return self.message
