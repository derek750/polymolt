"""LMSR (Logarithmic Market Scoring Rule) engine for a binary YES/NO market.

Cost function:  C(q) = b * ln(exp(q_yes/b) + exp(q_no/b))
Price of YES:   p_yes = exp(q_yes/b) / (exp(q_yes/b) + exp(q_no/b))
Trade cost:     cost = C(q + delta) - C(q)

The `size_for_dollars` solver finds the share delta whose LMSR cost equals
a given dollar budget, using bisection search.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LmsrMarket:
    """Represents a single binary LMSR market."""

    id: str
    question: str
    b: float = 100.0
    q_yes: float = 0.0
    q_no: float = 0.0
    trade_count: int = 0
    price_history: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.price_history:
            self.price_history = [self.price_yes]

    # ------------------------------------------------------------------
    # Core LMSR maths
    # ------------------------------------------------------------------

    def _cost(self, q_yes: float, q_no: float) -> float:
        """LMSR cost function C(q) = b * ln(exp(q_yes/b) + exp(q_no/b)).

        Uses log-sum-exp trick to avoid overflow.
        """
        m = max(q_yes, q_no) / self.b
        return self.b * (m + math.log(
            math.exp(q_yes / self.b - m) + math.exp(q_no / self.b - m)
        ))

    @property
    def cost(self) -> float:
        return self._cost(self.q_yes, self.q_no)

    @property
    def price_yes(self) -> float:
        exp_y = math.exp(self.q_yes / self.b)
        exp_n = math.exp(self.q_no / self.b)
        return exp_y / (exp_y + exp_n)

    @property
    def price_no(self) -> float:
        return 1.0 - self.price_yes

    # ------------------------------------------------------------------
    # Trade cost for arbitrary share deltas
    # ------------------------------------------------------------------

    def trade_cost(self, delta_yes: float = 0.0, delta_no: float = 0.0) -> float:
        """Dollar cost to move quantities by (delta_yes, delta_no)."""
        return (
            self._cost(self.q_yes + delta_yes, self.q_no + delta_no)
            - self._cost(self.q_yes, self.q_no)
        )

    # ------------------------------------------------------------------
    # Order sizing: dollars -> shares
    # ------------------------------------------------------------------

    def size_for_dollars(
        self,
        side: str,
        dollars: float,
        *,
        tol: float = 1e-6,
        max_iter: int = 200,
    ) -> float:
        """Find share quantity `delta` such that LMSR cost ≈ `dollars`.

        Uses bisection on the monotonically increasing cost function.
        """
        if dollars <= 0:
            return 0.0

        side = side.upper()
        if side not in ("YES", "NO"):
            raise ValueError(f"side must be 'YES' or 'NO', got '{side}'")

        lo, hi = 0.0, dollars * 10.0

        # Expand upper bound until it brackets the target cost
        for _ in range(50):
            if side == "YES":
                c = self.trade_cost(delta_yes=hi)
            else:
                c = self.trade_cost(delta_no=hi)
            if c >= dollars:
                break
            hi *= 2.0
        else:
            return hi  # extreme edge case — return upper bound

        for _ in range(max_iter):
            mid = (lo + hi) / 2.0
            if side == "YES":
                c = self.trade_cost(delta_yes=mid)
            else:
                c = self.trade_cost(delta_no=mid)

            if abs(c - dollars) < tol:
                return mid
            if c < dollars:
                lo = mid
            else:
                hi = mid

        return (lo + hi) / 2.0

    # ------------------------------------------------------------------
    # Execute trades
    # ------------------------------------------------------------------

    def execute_trade(
        self,
        side: str,
        delta: float,
    ) -> dict[str, Any]:
        """Apply a share-denominated trade. Returns trade receipt."""
        side = side.upper()
        price_before = self.price_yes

        if side == "YES":
            cost = self.trade_cost(delta_yes=delta)
            self.q_yes += delta
        elif side == "NO":
            cost = self.trade_cost(delta_no=delta)
            self.q_no += delta
        else:
            raise ValueError(f"side must be 'YES' or 'NO', got '{side}'")

        price_after = self.price_yes
        self.trade_count += 1
        self.price_history.append(price_after)

        return {
            "trade_id": uuid.uuid4().hex[:8],
            "side": side,
            "shares": round(delta, 6),
            "cost_dollars": round(cost, 6),
            "price_yes_before": round(price_before, 6),
            "price_yes_after": round(price_after, 6),
        }

    def execute_dollar_order(
        self,
        side: str,
        dollars: float,
    ) -> dict[str, Any]:
        """Convenience: convert a dollar budget into shares, then trade."""
        delta = self.size_for_dollars(side, dollars)
        receipt = self.execute_trade(side, delta)
        receipt["requested_dollars"] = round(dollars, 6)
        return receipt

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        return {
            "market_id": self.id,
            "question": self.question,
            "b": self.b,
            "q_yes": round(self.q_yes, 6),
            "q_no": round(self.q_no, 6),
            "price_yes": round(self.price_yes, 6),
            "price_no": round(self.price_no, 6),
            "trade_count": self.trade_count,
            "price_history": [round(p, 6) for p in self.price_history[-200:]],
        }

    def reset(self, starting_price: float = 0.5) -> None:
        """Reset quantities so price_yes equals starting_price."""
        p = max(0.01, min(0.99, starting_price))
        self.q_yes = self.b * math.log(p / (1 - p))
        self.q_no = 0.0
        self.trade_count = 0
        self.price_history = [self.price_yes]
