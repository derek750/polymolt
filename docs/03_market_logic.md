# Market Logic

## Market Question
**"Is this region sustainable?"**

The market operates as a binary prediction market. The probability P represents the market's current estimate that the region is sustainable.

---

## Market Mechanism: LMSR-Inspired

We use a **Logarithmic Market Scoring Rule (LMSR)**-inspired mechanism.

Key properties:
- Each trade shifts the probability based on trade size and liquidity parameter b
- Larger trades move the market more
- The mechanism is bounded: probability stays in (0, 1)
- Market maker absorbs all trades (no counterparty required)

### Probability Update Formula

```
# LMSR cost function
cost(q) = b * ln(e^(q_yes/b) + e^(q_no/b))

# After a BUY of size s:
q_yes += s
# After a SELL of size s:
q_no += s

# Market probability
P = e^(q_yes/b) / (e^(q_yes/b) + e^(q_no/b))
```

Where:
- `q_yes`: total YES quantity
- `q_no`: total NO quantity
- `b`: liquidity parameter (controls price sensitivity; higher b = slower movement)

### Initial State

```python
b = 50.0          # liquidity parameter — tune for desired volatility
q_yes = 50.0      # start at 50/50
q_no = 50.0
initial_price = 0.5
```

---

## Why LMSR?

- **Bounded**: probability never reaches exactly 0 or 1
- **Continuous**: small trades have small effects, large trades have large effects
- **No counterparty needed**: market maker always accepts trades
- **Interpretable**: the probability has a clean mathematical meaning
- **Not a formula**: the result depends on the sequence and size of trades

This is the key point: the final probability is path-dependent. If Climate Agent trades first, the market behaves differently than if Master Generalist trades first.

---

## Trade Sizing

```python
def compute_trade_size(agent, market_price):
    belief_gap = abs(agent.current_belief - market_price)
    evidence_factor = mean([e['strength'] for e in agent.evidence_used]) if agent.evidence_used else 0.5
    base_size = agent.betting_power * agent.confidence * agent.risk_tolerance * 10
    size = base_size * belief_gap * evidence_factor
    return max(size, 0.1)   # minimum trade size
```

Effect on market:
- **Master Generalist** (2.0x) can move the market ~2x as much as a specialist
- **High confidence + high gap** = large move
- **Weak evidence** = dampened trade, even for a strong belief

---

## Market State Object

```python
@dataclass
class MarketState:
    region_id: str
    question: str
    b: float                    # liquidity parameter
    q_yes: float
    q_no: float
    price_history: list[float]  # one entry per trade
    trade_log: list[TradeEntry]
    round_number: int
    is_running: bool
```

---

## Trade Log Entry

```python
@dataclass
class TradeEntry:
    timestamp: str
    agent_id: str
    agent_name: str
    direction: Literal["BUY", "SELL"]
    size: float
    price_before: float
    price_after: float
    reasoning: str
    evidence_titles: list[str]
```

---

## Simulation Loop

The orchestrator runs a continuous loop:

```
for each round:
    shuffle agent order (adds randomness)
    for each agent (filtered by update_frequency):
        agent reads evidence
        agent forms private belief
        agent computes trade
        if trade size > threshold:
            apply LMSR update
            log trade
            broadcast via SSE
        sleep(interval)
```

Round interval is configurable (default: 1.5s between agent trades).

---

## Market Behavior Goals

| Region Profile | Expected Behavior |
|----------------|-------------------|
| Strongly sustainable | Early convergence to 70–85%, minor oscillation |
| Weakly sustainable | Convergence to 20–35%, specialists agree |
| Contested (mixed) | Persistent 40–60% range, visible disagreement, volatile |

Mechanisms that produce disagreement:
- Specialists with domain-specific negative evidence push against generalist optimism
- Stubbornness prevents rapid convergence
- Contrarian agents (if present) actively resist consensus
- Evidence asymmetry means agents can rationally hold different beliefs indefinitely

---

## No Direct Formula

**What this is NOT:**
```python
# WRONG — this is not how Polymolt works
sustainability_score = (
    0.2 * climate_score +
    0.15 * energy_score +
    0.15 * water_score +
    0.2 * infra_score +
    0.15 * social_score +
    0.15 * governance_score
)
```

**What this IS:**
- Each agent processes its own evidence
- Each agent forms its own belief
- Each agent trades based on the gap between belief and market price
- The market price moves in response to those trades
- The final probability is the emergent result of all those individual decisions

---

## Liquidity and Reset

- On region change: reset `q_yes = q_no = b` (return to 50%)
- `b` can be tuned per region for different market depth
- History is cleared on reset

---

## Future: Real Market Dynamics

Phase 2 additions:
- Agent memory (beliefs persist across rounds, not reset)
- Momentum tracking (agents observe price velocity)
- Position limits (agents can't go infinitely long/short)
- Confidence decay (agents reduce conviction over time without new evidence)
