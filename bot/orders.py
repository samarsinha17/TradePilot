"""Business logic for placing Binance futures orders."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

from .client import BinanceClient
from .exceptions import BinanceAPIException, NetworkException
from .models import OrderRequest, OrderResponse
from .utils import format_decimal


def _build_payload(request: OrderRequest) -> dict[str, Any]:
    # Keeping payload assembly separate makes future order types easier to add.
    payload: dict[str, Any] = {
        "symbol": request.symbol,
        "side": request.side,
        "type": request.order_type,
        "quantity": format_decimal(request.quantity),
    }
    if request.order_type == "LIMIT":
        payload["timeInForce"] = request.time_in_force or "GTC"
        payload["price"] = format_decimal(request.price)
    return payload


def _build_response(response: dict[str, Any]) -> OrderResponse:
    return OrderResponse.model_validate(
        {
            **response,
            "raw": response,
        }
    )


def _refresh_order_snapshot(client: BinanceClient, order_response: dict[str, Any], logger: logging.Logger) -> dict[str, Any]:
    """Fetch Binance's latest view of the order after submission."""

    order_id = int(order_response["orderId"])
    symbol = str(order_response["symbol"])
    try:
        refreshed = client.get_futures_order(symbol=symbol, order_id=order_id)
    except (BinanceAPIException, NetworkException) as exc:
        logger.warning("Order refresh skipped | order_id=%s | reason=%s", order_id, exc)
        return order_response

    logger.info("Order refresh completed | order_id=%s | response=%s", order_id, refreshed)
    return refreshed


def place_market_order(client: BinanceClient, request: OrderRequest, logger: logging.Logger) -> OrderResponse:
    """Place a MARKET futures order."""

    payload = _build_payload(request)
    logger.info("Submitting market order | payload=%s", payload)
    started_at = perf_counter()
    response = client.place_futures_order(payload)
    response = _refresh_order_snapshot(client, response, logger)
    elapsed = round((perf_counter() - started_at) * 1000, 2)
    logger.info("Market order completed | status=SUCCESS | execution_ms=%s | response=%s", elapsed, response)
    return _build_response(response)


def place_limit_order(client: BinanceClient, request: OrderRequest, logger: logging.Logger) -> OrderResponse:
    """Place a LIMIT futures order with GTC time-in-force."""

    payload = _build_payload(request)
    logger.info("Submitting limit order | payload=%s", payload)
    started_at = perf_counter()
    response = client.place_futures_order(payload)
    response = _refresh_order_snapshot(client, response, logger)
    elapsed = round((perf_counter() - started_at) * 1000, 2)
    logger.info("Limit order completed | status=SUCCESS | execution_ms=%s | response=%s", elapsed, response)
    return _build_response(response)
