"""Command line interface for TradePilot."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from colorama import Fore, Style, init
from pydantic import ValidationError as PydanticValidationError

from bot.client import BinanceClient
from bot.exceptions import BinanceAPIException, NetworkException, ValidationError
from bot.logging_config import setup_logging
from bot.models import OrderRequest, OrderResponse
from bot.orders import place_limit_order, place_market_order
from bot.utils import (
    banner,
    format_decimal,
    format_response_price,
    format_timestamp,
    render_card,
)
from bot.validators import (
    validate_order_rules,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TradePilot - Binance USDT-M Futures Testnet trading bot"
    )
    parser.add_argument("--demo", action="store_true", help="Run a safe interactive demo without placing orders")
    parser.add_argument("--symbol", help="Trading pair, for example BTCUSDT")
    parser.add_argument("--side", help="BUY or SELL")
    parser.add_argument("--type", dest="order_type", help="MARKET or LIMIT")
    parser.add_argument("--quantity", help="Order quantity")
    parser.add_argument("--price", help="Limit price")
    return parser.parse_args()


def _build_request(args: argparse.Namespace) -> OrderRequest:
    if not args.demo:
        missing = [name for name in ("symbol", "side", "order_type", "quantity") if getattr(args, name) is None]
        if missing:
            raise ValidationError(f"Missing required arguments: {', '.join(missing)}.")

    symbol = validate_symbol(args.symbol)
    side = validate_side(args.side)
    order_type = validate_order_type(args.order_type)
    quantity = validate_quantity(args.quantity)
    price = validate_price(args.price)
    validate_order_rules(order_type, price)

    return OrderRequest(
        symbol=symbol,
        side=side,
        type=order_type,
        quantity=quantity,
        price=price,
    )


def _prompt_value(prompt: str, *, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def _prompt_validated(prompt: str, validator, *, default: str | None = None, allow_blank: bool = False) -> str:
    while True:
        value = _prompt_value(prompt, default=default)
        if allow_blank and not value:
            return ""
        try:
            validator(value)
            return value
        except ValidationError as exc:
            print(f"{Fore.YELLOW}{exc}{Style.RESET_ALL}")


def _run_demo_flow() -> int:
    print()
    print(banner("TradePilot", "Demo Mode"))
    print("Safe interactive walkthrough. No Binance order will be placed.")
    print()

    symbol = validate_symbol(_prompt_validated("Enter symbol", validate_symbol, default="BTCUSDT"))
    side = validate_side(_prompt_validated("Enter side", validate_side, default="BUY"))
    order_type = validate_order_type(_prompt_validated("Enter order type", validate_order_type, default="MARKET"))
    quantity = validate_quantity(_prompt_validated("Enter quantity", validate_quantity, default="0.001"))
    price_value = ""
    if order_type == "LIMIT":
        price_value = _prompt_validated("Enter price", validate_price, allow_blank=False)
    price = validate_price(price_value) if price_value else None
    validate_order_rules(order_type, price)

    request = OrderRequest(
        symbol=symbol,
        side=side,
        type=order_type,
        quantity=quantity,
        price=price,
    )

    print()
    print(f"{Style.BRIGHT}Validation complete. Here is the order preview:{Style.RESET_ALL}")
    _print_request(request)

    confirm = _prompt_value("Continue with simulated execution? (y/n)", default="y").lower()
    if confirm not in {"y", "yes"}:
        print()
        print(f"{Fore.YELLOW}Demo cancelled. No order was placed.{Style.RESET_ALL}")
        return 0

    simulated_response = OrderResponse(
        orderId=9000000001 if order_type == "MARKET" else 9000000002,
        symbol=request.symbol,
        status="FILLED" if order_type == "MARKET" else "NEW",
        executedQty=request.quantity if order_type == "MARKET" else Decimal("0"),
        avgPrice=price if price is not None else None,
        clientOrderId=f"demo-{uuid4().hex[:12]}",
        updateTime=datetime.now(timezone.utc),
        side=request.side,
        type=request.order_type,
        raw={"mode": "demo", "simulated": True},
    )

    print()
    print(f"{Style.BRIGHT}{Fore.CYAN}Simulation complete. No Binance API call was made.{Style.RESET_ALL}")
    _print_response(simulated_response)
    print()
    print(f"{Style.BRIGHT}{Fore.GREEN}Demo completed successfully.{Style.RESET_ALL}")
    return 0


def _print_request(request: OrderRequest) -> None:
    # Small helper to keep the CLI output readable.
    rows = [
        ("Symbol", request.symbol),
        ("Side", request.side),
        ("Order Type", request.order_type),
        ("Quantity", format_decimal(request.quantity)),
        (
            "Price",
            format_decimal(request.price) if request.price is not None else "N/A",
        ),
    ]
    print()
    print(banner("TradePilot", "Trading Request"))
    print(render_card("Order Details", rows))


def _print_response(response) -> None:
    # Binance snapshot after the follow-up query.
    banner_subtitle = "Demo Response" if getattr(response, "raw", None) and response.raw.get("mode") == "demo" else "Order Response"
    rows = [
        ("Order ID", str(response.order_id)),
        ("Status", response.status),
        ("Executed Qty", format_decimal(response.executed_quantity)),
        ("Avg Price", format_response_price(response.average_price, response.status)),
        ("Client Order ID", response.client_order_id),
        ("Transaction Time", format_timestamp(response.transaction_time)),
    ]
    print()
    print(banner("TradePilot", banner_subtitle))
    print(render_card("Execution Details", rows))


def main() -> int:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    init(autoreset=True)
    setup_logging()

    try:
        args = _parse_args()
        if args.demo:
            return _run_demo_flow()

        request = _build_request(args)

        logger_name = f"tradepilot.{request.order_type.lower()}"
        from bot.logging_config import get_logger

        logger = get_logger(logger_name, request.order_type)
        client = BinanceClient(logger)

        _print_request(request)

        if request.order_type == "MARKET":
            response = place_market_order(client, request, logger)
        else:
            response = place_limit_order(client, request, logger)

        _print_response(response)
        print()
        print(f"{Style.BRIGHT}{Fore.GREEN}Order completed successfully.{Style.RESET_ALL}")
        return 0
    except (ValidationError, PydanticValidationError) as exc:
        print()
        print(f"{Fore.RED}{Style.BRIGHT}Order failed.{Style.RESET_ALL}")
        print(f"{Fore.RED}{exc}{Style.RESET_ALL}")
        return 1
    except (BinanceAPIException, NetworkException) as exc:
        print()
        print(f"{Fore.RED}{Style.BRIGHT}Order failed.{Style.RESET_ALL}")
        print(f"{Fore.RED}Order could not be completed: {exc}{Style.RESET_ALL}")
        return 1
    except Exception as exc:  # pragma: no cover - defensive fallback
        print()
        print(f"{Fore.RED}{Style.BRIGHT}Order failed.{Style.RESET_ALL}")
        print(f"{Fore.RED}Unexpected error: {exc}{Style.RESET_ALL}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
