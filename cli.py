"""Command line interface for TradePilot."""

from __future__ import annotations

import argparse
import sys
from colorama import Fore, Style, init
from pydantic import ValidationError as PydanticValidationError

from bot.client import BinanceClient
from bot.exceptions import BinanceAPIException, NetworkException, ValidationError
from bot.logging_config import setup_logging
from bot.models import OrderRequest
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
    parser.add_argument("--symbol", required=True, help="Trading pair, for example BTCUSDT")
    parser.add_argument("--side", required=True, help="BUY or SELL")
    parser.add_argument("--type", required=True, dest="order_type", help="MARKET or LIMIT")
    parser.add_argument("--quantity", required=True, help="Order quantity")
    parser.add_argument("--price", help="Limit price")
    return parser.parse_args()


def _build_request(args: argparse.Namespace) -> OrderRequest:
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
    rows = [
        ("Order ID", str(response.order_id)),
        ("Status", response.status),
        ("Executed Qty", format_decimal(response.executed_quantity)),
        ("Avg Price", format_response_price(response.average_price, response.status)),
        ("Client Order ID", response.client_order_id),
        ("Transaction Time", format_timestamp(response.transaction_time)),
    ]
    print()
    print(banner("TradePilot", "Order Response"))
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
