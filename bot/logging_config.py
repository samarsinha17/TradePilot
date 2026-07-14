"""Logging configuration for TradePilot."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
GENERAL_LOG = LOG_DIR / "trading_bot.log"
MARKET_LOG = LOG_DIR / "market_order.log"
LIMIT_LOG = LOG_DIR / "limit_order.log"

_LOGGING_READY = False


def _build_formatter() -> logging.Formatter:
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_logging() -> None:
    global _LOGGING_READY
    if _LOGGING_READY:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    formatter = _build_formatter()

    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    console.setFormatter(formatter)
    root.addHandler(console)

    general_handler = RotatingFileHandler(GENERAL_LOG, maxBytes=512_000, backupCount=3, encoding="utf-8")
    general_handler.setLevel(logging.INFO)
    general_handler.setFormatter(formatter)
    root.addHandler(general_handler)

    _LOGGING_READY = True


def get_logger(name: str, order_type: str | None = None) -> logging.Logger:
    setup_logging()
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    target_file = MARKET_LOG if order_type == "MARKET" else LIMIT_LOG if order_type == "LIMIT" else None
    if target_file is None:
        return logger

    handler_marker = f"file:{target_file}"
    if any(getattr(handler, "name", None) == handler_marker for handler in logger.handlers):
        return logger

    file_handler = RotatingFileHandler(target_file, maxBytes=256_000, backupCount=2, encoding="utf-8")
    file_handler.name = handler_marker
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(_build_formatter())
    logger.addHandler(file_handler)
    logger.propagate = True
    return logger
