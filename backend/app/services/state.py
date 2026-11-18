"""Shared runtime state (price cache + market data source)."""

from __future__ import annotations

from dataclasses import dataclass

from app.market import MarketDataSource, PriceCache


@dataclass
class AppState:
    cache: PriceCache
    source: MarketDataSource
