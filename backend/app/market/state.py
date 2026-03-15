"""In-memory market store.

Manages one or more LmsrMarket instances keyed by market_id.
A default market is created on import so the API is immediately usable.
"""

from __future__ import annotations

import math
from typing import Any

from app.market.lmsr_engine import LmsrMarket

DEFAULT_MARKET_ID = "default"
DEFAULT_QUESTION = "Is this region sustainable?"
DEFAULT_B = 100.0
DEFAULT_STARTING_PRICE = 0.5

_markets: dict[str, LmsrMarket] = {}


def _init_market(
    market_id: str,
    question: str = DEFAULT_QUESTION,
    b: float = DEFAULT_B,
    starting_price: float = DEFAULT_STARTING_PRICE,
) -> LmsrMarket:
    p = max(0.01, min(0.99, starting_price))
    q_yes = b * math.log(p / (1 - p))
    market = LmsrMarket(
        id=market_id,
        question=question,
        b=b,
        q_yes=q_yes,
        q_no=0.0,
    )
    _markets[market_id] = market
    return market


def get_market(market_id: str | None = None) -> LmsrMarket:
    mid = market_id or DEFAULT_MARKET_ID
    if mid not in _markets:
        _init_market(mid)
    return _markets[mid]


def reset_market(
    market_id: str | None = None,
    question: str | None = None,
    b: float | None = None,
    starting_price: float = DEFAULT_STARTING_PRICE,
) -> LmsrMarket:
    mid = market_id or DEFAULT_MARKET_ID
    q = question or _markets.get(mid, LmsrMarket(id=mid, question=DEFAULT_QUESTION)).question
    lb = b or _markets.get(mid, LmsrMarket(id=mid, question=DEFAULT_QUESTION)).b
    return _init_market(mid, question=q, b=lb, starting_price=starting_price)


def apply_order(
    side: str,
    dollars: float,
    market_id: str | None = None,
) -> dict[str, Any]:
    """Execute a dollar-denominated order and return trade receipt + market snapshot."""
    market = get_market(market_id)
    receipt = market.execute_dollar_order(side, dollars)
    return {
        "trade": receipt,
        "market": market.snapshot(),
    }
