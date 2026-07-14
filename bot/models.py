"""Pydantic models for TradePilot requests and responses."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderRequest(BaseModel):
    """Validated order payload used by the business layer."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    side: str
    order_type: str = Field(alias="type")
    quantity: Decimal
    price: Decimal | None = None
    time_in_force: str | None = Field(default="GTC", alias="timeInForce")

    @field_validator("symbol", "side", "order_type")
    @classmethod
    def normalize_uppercase(cls, value: str) -> str:
        return value.strip().upper()


class OrderResponse(BaseModel):
    """Normalized order response shown in the CLI."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    order_id: int = Field(alias="orderId")
    status: str
    executed_quantity: Decimal = Field(alias="executedQty")
    average_price: Decimal | None = Field(default=None, alias="avgPrice")
    client_order_id: str = Field(alias="clientOrderId")
    transaction_time: datetime = Field(alias="updateTime")
    side: str | None = None
    order_type: str | None = Field(default=None, alias="type")
    raw: dict[str, Any] | None = None

    @field_validator("transaction_time", mode="before")
    @classmethod
    def parse_transaction_time(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    @field_validator("executed_quantity", "average_price", mode="before")
    @classmethod
    def parse_decimal(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))
