"""Formatting and output helpers."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Iterable

BOX_WIDTH = 62
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def format_decimal(value: Decimal | float | int | None) -> str:
    if value is None:
        return "N/A"
    decimal_value = Decimal(str(value))
    normalized = decimal_value.normalize()
    text = format(normalized, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def format_timestamp(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def format_response_price(value: Decimal | float | int | None, status: str | None = None) -> str:
    """Show N/A for prices Binance has not populated yet."""

    if value is None:
        return "N/A"

    status_value = (status or "").upper()
    decimal_value = Decimal(str(value))
    if decimal_value == 0 and status_value not in {"FILLED", "PARTIALLY_FILLED"}:
        return "N/A"
    return format_decimal(decimal_value)


def render_card(title: str, rows: Iterable[tuple[str, str]]) -> str:
    lines = [f"╭{'─' * (BOX_WIDTH - 2)}╮"]
    centered = f" {title} ".center(BOX_WIDTH - 2, " ")
    lines.append(f"│{centered}│")
    lines.append(f"├{'─' * (BOX_WIDTH - 2)}┤")
    for key, value in rows:
        content = f"{key:<18} {value}"
        visible = ANSI_RE.sub("", content)
        if len(visible) > BOX_WIDTH - 4:
            visible = visible[: BOX_WIDTH - 7] + "..."
        padding = BOX_WIDTH - 4 - len(visible)
        lines.append(f"│ {content}{' ' * max(padding, 0)} │")
    lines.append(f"╰{'─' * (BOX_WIDTH - 2)}╯")
    return "\n".join(lines)


def banner(title: str, subtitle: str | None = None) -> str:
    lines = [
        "╭" + "─" * (BOX_WIDTH - 2) + "╮",
        f"│{title.center(BOX_WIDTH - 2)}│",
    ]
    if subtitle:
        lines.append(f"│{subtitle.center(BOX_WIDTH - 2)}│")
    lines.append("╰" + "─" * (BOX_WIDTH - 2) + "╯")
    return "\n".join(lines)
