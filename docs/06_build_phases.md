# Build Phases

## Phase 1 — Scaffold + MVP
**Goal**: Working local app with live market, agents, trade feed, and agent cards.

Deliverables:
- Next.js frontend scaffold with Tailwind
- FastAPI backend with Server-Sent Events (SSE) support
- 9 agents defined with seeded behavior traits
- 3 seeded demo regions with evidence
- LMSR market maker
- Simulation loop running in background task
- SSE stream for live market updates
- Frontend: probability display, live chart, trade feed, agent grid, agent detail drawer
- App starts and runs without errors

**Success criteria**: Select a region, watch probability update in real time, click an agent to see reasoning.

---

## Phase 2 — Market Realism
**Goal**: Agents behave more distinctly; market dynamics are more interesting.

Deliverables:
- Agent belief persistence across rounds (no full reset per round)
- Momentum awareness (agents observe price direction)
- Position limits (cap net position per agent)
- Confidence decay (belief erodes without new confirming evidence)
- Contrarian behavior for select agents
- Stronger template reasoning tied to specific evidence items
- Region profiles tuned to produce distinct market behaviors

**Success criteria**: Industrial Delta (contested region) shows visible disagreement and volatility. Scandinavia converges smoothly.

---

## Phase 3 — RAG/Langflow Architecture
**Goal**: Clean integration seams for real retrieval and LLM reasoning.

Deliverables:
- `CategoryRetriever` interface with TODO stubs
- `AgentReasoner` interface with TODO stubs
- `LangflowClient` stub
- Seeded evidence replaced by `get_evidence(region, category)` function call (easy to swap)
- Agent categories mapped to corpus names
- Architecture document updated with actual code shapes
- Optional: simple LLM call via OpenAI API for reasoning generation (if API key available)

**Success criteria**: A developer can swap `get_seeded_evidence()` for a vector store call with minimal changes.

---

## Phase 4 — UI Polish
**Goal**: Dashboard feels like a real prediction market product.

Deliverables:
- Polymarket-inspired chart styling (dark, minimal, clean)
- Compact agent cards with clear hierarchy
- Animated trade entries (slide in)
- Belief vs. market price gap visualizer in agent drawer
- Category badge colors applied throughout
- Behavior trait bars with labels
- Probability color shift (green vs red based on threshold)
- Optional: behavior-study view (overlay showing all agent beliefs vs market price)

**Success criteria**: Demo looks polished enough for a hackathon presentation.

---

## Phase 5 — Demo Readiness
**Goal**: Stable, self-contained local demo.

Deliverables:
- Reset button that restarts market simulation
- Auto-select default region on load
- Market starts trading within 3 seconds
- All 3 seeded regions behave distinctly and are selectable
- No console errors, no broken states
- README quickstart verified
- Optional: scenario presets (e.g., "shock event" that injects negative evidence mid-simulation)

**Success criteria**: Anyone can clone, run two commands, and present a live demo in < 5 minutes.
