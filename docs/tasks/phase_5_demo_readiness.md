# Phase 5 Tasks — Demo Readiness

## Goal
The app should be stable, self-contained, and presentable in a hackathon demo.

## Tasks

### D5.1 — Reset Flow
- [ ] "Reset Market" button in header
- [ ] Calls `POST /market/{region_id}/reset`
- [ ] Backend: resets MarketState, restarts simulation loop, broadcasts market_reset message
- [ ] Frontend: clears chart, clears trade feed, resets agent states
- [ ] Animation: brief flash/transition on reset

### D5.2 — Auto-Start
- [ ] Default region (Scandinavia) loads on app open
- [ ] Market starts trading within 3 seconds of SSE connect
- [ ] No manual "Start" button required

### D5.3 — Region Switching
- [ ] Switching region stops current simulation
- [ ] Starts new simulation with new evidence
- [ ] Chart and trade feed clear
- [ ] Agent beliefs reinitialize
- [ ] Smooth transition (no broken state)

### D5.4 — Stability
- [ ] No unhandled exceptions in backend
- [ ] SSE reconnects automatically if disconnected
- [ ] Backend handles multiple concurrent SSE connections gracefully
- [ ] Market loop does not crash on edge cases (empty evidence, no trades)

### D5.5 — Documentation
- [ ] README quickstart verified end-to-end
- [ ] CLAUDE.md updated with final phase status
- [ ] All TODO stubs present and clearly labeled

### D5.6 — Seeded Scenarios
- [ ] All 3 regions produce distinct, recognizable behavior
- [ ] Optional: "shock event" endpoint: `POST /market/{region_id}/shock`
  - Injects a set of strong negative evidence items
  - Agents respond within 2–3 rounds
  - Market visibly drops
- [ ] Optional: "recovery event": inject positive evidence

### D5.7 — Final QA
- [ ] Clone fresh → install → run → demo in < 5 minutes
- [ ] No TypeScript errors
- [ ] No Python errors
- [ ] Chart renders for all 3 regions
- [ ] Agent drawer works for all 9 agents

## Demo Script
1. Open app → Scandinavia loads → probability converges upward
2. Narrate: "Each agent has different knowledge. The market probability emerges from their trades."
3. Click Climate Agent → show reasoning and evidence
4. Switch to Industrial Delta → market becomes contested, probability oscillates
5. Explain: "These agents genuinely disagree — different evidence sets, different interpretations"
6. Click Master Generalist → show broad knowledge, but lower conviction
7. Reset → fresh start
8. Optional: trigger shock event → watch market react
