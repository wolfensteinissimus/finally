"""Pydantic schema for the structured LLM response."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TradeAction(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)

    @field_validator("ticker")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("side", mode="before")
    @classmethod
    def _lower(cls, v):
        return v.strip().lower() if isinstance(v, str) else v


class WatchlistChange(BaseModel):
    ticker: str
    action: Literal["add", "remove"]

    @field_validator("ticker")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("action", mode="before")
    @classmethod
    def _lower(cls, v):
        return v.strip().lower() if isinstance(v, str) else v


class ChatLLMResponse(BaseModel):
    message: str
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChange] = Field(default_factory=list)
