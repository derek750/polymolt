"""REST router for the LMSR YES/NO prediction market.

Endpoints:
    GET  /market/state   — current market snapshot
    POST /market/order   — place a dollar-denominated YES/NO order
    POST /market/reset   — reset market to initial state
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.market.state import get_market, reset_market, apply_order

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market", tags=["market"])


# ------------------------------------------------------------------
# Request / response schemas
# ------------------------------------------------------------------

class OrderRequest(BaseModel):
    side: str = Field(..., pattern="^(YES|NO)$", description="YES or NO")
    dollars: float = Field(..., gt=0, description="Dollar amount to wager")
    market_id: Optional[str] = None


class ResetRequest(BaseModel):
    market_id: Optional[str] = None
    question: Optional[str] = None
    b: Optional[float] = Field(None, gt=0, description="Liquidity parameter")
    starting_price: float = Field(0.5, gt=0.0, lt=1.0)


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.get("/state")
def market_state(market_id: str | None = None):
    """Return the current LMSR market snapshot."""
    return get_market(market_id).snapshot()


@router.post("/order")
def place_order(req: OrderRequest):
    """Place a dollar-denominated order on the YES/NO market."""
    result = apply_order(
        side=req.side,
        dollars=req.dollars,
        market_id=req.market_id,
    )
    logger.info(
        "Order executed: side=%s dollars=%.2f -> price_yes=%.4f",
        req.side,
        req.dollars,
        result["market"]["price_yes"],
    )
    return result


@router.post("/reset")
def reset(req: ResetRequest):
    """Reset the market to a fresh initial state."""
    market = reset_market(
        market_id=req.market_id,
        question=req.question,
        b=req.b,
        starting_price=req.starting_price,
    )
    logger.info("Market reset: id=%s price_yes=%.4f", market.id, market.price_yes)
    return market.snapshot()
