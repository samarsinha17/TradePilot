"""Input validation helpers."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from .exceptions import ValidationError

_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")
_ALLOWED_SIDES = {"BUY", "SELL"}
_ALLOWED_TYPES = {"MARKET", "LIMIT"}


def _coerce_decimal(value: object, field_name: str) -> Decimal:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError(f"{field_name} must be a valid number.") from exc

    if decimal_value <= 0:
        raise ValidationError(f"{field_name} must be greater than 0.")
    return decimal_value


def validate_symbol(symbol: str) -> str:
    symbol_value = symbol.strip().upper()
    if not _SYMBOL_PATTERN.fullmatch(symbol_value):
        raise ValidationError("Symbol must contain only uppercase letters and numbers.")
    if not symbol_value.endswith("USDT"):
        raise ValidationError("Symbol must be a USDT-M futures pair, for example BTCUSDT.")
    return symbol_value


def validate_side(side: str) -> str:
    side_value = side.strip().upper()
    if side_value not in _ALLOWED_SIDES:
        raise ValidationError("Side must be either BUY or SELL.")
    return side_value


def validate_order_type(order_type: str) -> str:
    order_type_value = order_type.strip().upper()
    if order_type_value not in _ALLOWED_TYPES:
        raise ValidationError("Order type must be either MARKET or LIMIT.")
    return order_type_value


def validate_quantity(quantity: object) -> Decimal:
    return _coerce_decimal(quantity, "Quantity")


def validate_price(price: object | None) -> Decimal | None:
    if price is None:
        return None
    return _coerce_decimal(price, "Price")


def validate_order_rules(order_type: str, price: Decimal | None) -> None:
    if order_type == "LIMIT" and price is None:
        raise ValidationError("LIMIT orders require a price.")
    if order_type == "MARKET" and price is not None:
        raise ValidationError("MARKET orders must not include a price.")
