# Phase 1 Tasks — Scaffold + MVP

## Backend Tasks

### B1.1 — Project scaffold
- [ ] Create `backend/` directory structure
- [ ] Create `backend/requirements.txt`
- [ ] Create `backend/main.py` (FastAPI app entry point)
- [ ] Create `backend/app/__init__.py`

### B1.2 — Data layer
- [ ] Create `backend/app/data/regions.py` — 3 seeded region definitions
- [ ] Create `backend/app/data/evidence.py` — seeded evidence per region per category
- [ ] Evidence format: `{id, category, title, summary, sentiment, strength}`

### B1.3 — Agent system
- [ ] Create `backend/app/agents/agent_config.py` — 9 agent definitions with traits
- [ ] Create `backend/app/agents/belief_engine.py` — belief formation logic
- [ ] Create `backend/app/agents/trade_engine.py` — trade size/direction logic
- [ ] Create `backend/app/agents/reasoning.py` — template-based reasoning generator

### B1.4 — Market logic
- [ ] Create `backend/app/market/lmsr.py` — LMSR probability update functions
- [ ] Create `backend/app/market/market_state.py` — MarketState dataclass + trade log
- [ ] Create `backend/app/market/trade_models.py` — TradeEntry dataclass

### B1.5 — Orchestrator
- [ ] Create `backend/app/core/orchestrator.py` — simulation loop
- [ ] Create `backend/app/core/state.py` — global app state (current market, agents)
- [ ] Simulation loop: shuffle agents → form beliefs → compute trades → apply LMSR → log → broadcast

### B1.6 — API
- [ ] Create SSE stream endpoint `GET /market/{region_id}/stream` for live market updates
- [ ] Create `backend/app/api/regions.py` — REST GET `/regions`
- [ ] Create `backend/app/api/market.py` — REST GET `/market/{region_id}`
- [ ] Register all routers in `main.py`

---

## Frontend Tasks

### F1.1 — Project scaffold
- [ ] Create Next.js app in `frontend/` with TypeScript + Tailwind
- [ ] Configure Tailwind dark theme
- [ ] Install dependencies: recharts, lucide-react

### F1.2 — Types
- [ ] Create `frontend/src/types/market.ts`
- [ ] Create `frontend/src/types/agent.ts`
- [ ] Create `frontend/src/types/trade.ts`
- [ ] Create `frontend/src/types/evidence.ts`

### F1.3 — SSE hook
- [ ] Create `frontend/src/lib/useMarket.ts` — SSE (EventSource) hook
- [ ] Handle: connect, disconnect, reconnect
- [ ] Parse event types: market_update, trade, agent_update, market_reset

### F1.4 — Components
- [ ] `Header.tsx` with region selector
- [ ] `ProbabilityDisplay.tsx` — large number display
- [ ] `ProbabilityChart.tsx` — Recharts line chart
- [ ] `TradeFeed.tsx` + `TradeEntry.tsx`
- [ ] `AgentGrid.tsx` + `AgentCard.tsx`
- [ ] `AgentDrawer.tsx` — detail panel
- [ ] `CategoryBadge.tsx`

### F1.5 — Main page
- [ ] Wire up all components in `app/page.tsx`
- [ ] Connect useMarket hook
- [ ] Pass data to all components

---

## Acceptance Criteria

- [ ] Backend starts without errors: `uvicorn main:app --reload --port 8000`
- [ ] Frontend starts without errors: `npm run dev`
- [ ] SSE stream connects successfully
- [ ] Market begins updating within 3 seconds of page load
- [ ] Trade feed shows real-time entries
- [ ] Probability chart updates live
- [ ] All 9 agent cards visible
- [ ] Click agent card → detail drawer opens with reasoning
- [ ] Region selector changes the simulation
