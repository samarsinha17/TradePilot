"""Custom exceptions used across TradePilot."""


class ValidationError(Exception):
    """Raised when CLI or order payload validation fails."""


class BinanceAPIException(Exception):
    """Raised when Binance returns an API-level error."""


class NetworkException(Exception):
    """Raised when the transport layer cannot reach Binance."""
