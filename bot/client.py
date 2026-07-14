"""Binance Futures testnet client wrapper."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any
from time import perf_counter

from dotenv import load_dotenv

from .exceptions import BinanceAPIException, NetworkException, ValidationError
from .validators import validate_symbol

TESTNET_BASE_URL = "https://testnet.binancefuture.com"


@dataclass(frozen=True)
class BinanceCredentials:
    """API credentials loaded from environment variables."""

    api_key: str
    api_secret: str


def load_credentials() -> BinanceCredentials:
    """Load and validate Binance credentials from .env."""

    load_dotenv()
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key:
        raise ValidationError("Missing BINANCE_API_KEY in .env.")
    if not api_secret:
        raise ValidationError("Missing BINANCE_API_SECRET in .env.")
    return BinanceCredentials(api_key=api_key, api_secret=api_secret)


class BinanceClient:
    """Thin wrapper around python-binance for Futures testnet trading."""

    def __init__(self, logger: logging.Logger, base_url: str = TESTNET_BASE_URL) -> None:
        self.logger = logger
        self.base_url = base_url.rstrip("/")
        credentials = load_credentials()

        try:
            from binance.client import Client
        except ImportError as exc:  # pragma: no cover - dependency is installed by the user
            raise RuntimeError(
                "python-binance is required. Install dependencies with pip install -r requirements.txt."
            ) from exc

        self.client = Client(credentials.api_key, credentials.api_secret)
        # Futures testnet needs the base URL adjusted explicitly.
        self.client.FUTURES_URL = f"{self.base_url}/fapi"

    @staticmethod
    def _friendly_message(exc: Exception) -> str:
        message = str(exc).strip()
        lowered = message.lower()
        # Binance SDK error messages can be a little inconsistent, so keep the mapping forgiving.
        if "api-key" in lowered or "invalid api-key" in lowered or "permission" in lowered:
            return "Authentication failed. Please verify your Binance Testnet API key and secret."
        if "timed out" in lowered or "timeout" in lowered:
            return "The request timed out while contacting Binance."
        if "connection" in lowered or "network" in lowered:
            return "Network error while reaching Binance."
        return message or exc.__class__.__name__

    def place_futures_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Submit a signed futures order request."""

        symbol = payload.get("symbol", "")
        validate_symbol(symbol)

        endpoint = f"{self.base_url}/fapi/order"
        started_at = perf_counter()
        self.logger.info("API request | endpoint=%s | payload=%s", endpoint, payload)

        try:
            from binance.exceptions import BinanceAPIException as BinanceLibraryAPIException
            from binance.exceptions import BinanceRequestException

            response = self.client.futures_create_order(**payload)
        except BinanceLibraryAPIException as exc:
            elapsed = round((perf_counter() - started_at) * 1000, 2)
            self.logger.exception(
                "Binance API error | endpoint=%s | status=FAILED | execution_ms=%s | payload=%s",
                endpoint,
                elapsed,
                payload,
            )
            raise BinanceAPIException(self._friendly_message(exc)) from exc
        except BinanceRequestException as exc:
            elapsed = round((perf_counter() - started_at) * 1000, 2)
            self.logger.exception(
                "Network error | endpoint=%s | status=FAILED | execution_ms=%s | payload=%s",
                endpoint,
                elapsed,
                payload,
            )
            raise NetworkException(self._friendly_message(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            elapsed = round((perf_counter() - started_at) * 1000, 2)
            self.logger.exception(
                "Unexpected client error | endpoint=%s | status=FAILED | execution_ms=%s | payload=%s",
                endpoint,
                elapsed,
                payload,
            )
            raise NetworkException(self._friendly_message(exc)) from exc

        elapsed = round((perf_counter() - started_at) * 1000, 2)
        self.logger.info(
            "API response | endpoint=%s | status=SUCCESS | execution_ms=%s | response=%s",
            endpoint,
            elapsed,
            response,
        )
        return response

    def get_futures_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Fetch the latest Binance snapshot for an existing futures order."""

        validate_symbol(symbol)

        endpoint = f"{self.base_url}/fapi/order"
        started_at = perf_counter()
        request_payload = {"symbol": symbol, "orderId": order_id}
        self.logger.info("API request | endpoint=%s | payload=%s", endpoint, request_payload)

        try:
            from binance.exceptions import BinanceAPIException as BinanceLibraryAPIException
            from binance.exceptions import BinanceRequestException

            response = self.client.futures_get_order(symbol=symbol, orderId=order_id)
        except BinanceLibraryAPIException as exc:
            elapsed = round((perf_counter() - started_at) * 1000, 2)
            self.logger.exception(
                "Binance API error | endpoint=%s | status=FAILED | execution_ms=%s | payload=%s",
                endpoint,
                elapsed,
                request_payload,
            )
            raise BinanceAPIException(self._friendly_message(exc)) from exc
        except BinanceRequestException as exc:
            elapsed = round((perf_counter() - started_at) * 1000, 2)
            self.logger.exception(
                "Network error | endpoint=%s | status=FAILED | execution_ms=%s | payload=%s",
                endpoint,
                elapsed,
                request_payload,
            )
            raise NetworkException(self._friendly_message(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            elapsed = round((perf_counter() - started_at) * 1000, 2)
            self.logger.exception(
                "Unexpected client error | endpoint=%s | status=FAILED | execution_ms=%s | payload=%s",
                endpoint,
                elapsed,
                request_payload,
            )
            raise NetworkException(self._friendly_message(exc)) from exc

        elapsed = round((perf_counter() - started_at) * 1000, 2)
        self.logger.info(
            "API response | endpoint=%s | status=SUCCESS | execution_ms=%s | response=%s",
            endpoint,
            elapsed,
            response,
        )
        return response
