# Product Requirements

## Core Question
**"Is this region sustainable?"**

The market probability at any moment is the product's answer. It is not computed — it is discovered through agent trading.

---

## Functional Requirements

### Region Selection
- User can select from seeded demo regions
- Region selector visible in header
- Selecting a region resets the market and starts a new simulation

### Market Display
- Large, prominent current probability percentage
- Live chart: probability over time (Polymarket-style)
- Chart updates after every trade
- Y-axis: 0–100%, X-axis: trade index or time
- Chart should feel alive — smooth, reactive

### Trade Feed
Every trade entry shows:
- Timestamp
- Agent name (with agent type indicator)
- Direction: BUY (bullish) or SELL (bearish)
- Trade size (in units)
- Probability before trade
- Probability after trade
- Short natural-language explanation (1–2 sentences)

### Agent Cards
Grid of 9 agent cards visible at all times. Each card shows:
- Agent name
- Agent type (Specialist / Hybrid / Master)
- Current position (net long/short)
- Last trade summary
- Knowledge breadth indicator (category count)

### Agent Detail Panel
Clicking an agent card opens a drawer/panel showing:
- Name, type, betting power
- Accessible categories (tagged list)
- Current belief (private probability estimate)
- Behavior traits: confidence, risk tolerance, stubbornness, herd sensitivity, update frequency
- Latest reasoning (1–2 paragraphs of evidence-based logic)
- Evidence used (list of evidence items with category tag)
- Recent trade history (last 5 trades)
- Belief evolution chart (if feasible in Phase 1, otherwise Phase 4)

### Real-Time Updates
- Server-Sent Events (SSE) connection from frontend to backend
- Backend streams market updates to frontend
- Frontend receives and renders without full page reload
- Trade feed auto-scrolls to latest

### Region Profiles
Each seeded region has:
- Name and description
- Pre-seeded evidence per category (4–6 items per category)
- Expected initial agent beliefs

---

## Non-Functional Requirements

### Performance
- Trade loop runs every 2–4 seconds per agent (configurable)
- SSE latency < 100ms on local
- Chart renders smoothly up to 500 data points

### Code Quality
- No file over 400 lines
- Modular: one concern per file
- Clear TODO stubs for RAG/Langflow integration points

### Demo Readiness
- App starts with `npm run dev` + `uvicorn main:app`
- Default region loads automatically
- Market begins trading within 3 seconds of load
- Reset button to restart simulation

---

## Out of Scope (MVP)
- Real user accounts or wallets
- Real money or token economics
- Live data fetching (all evidence is seeded)
- Persistent database (in-memory state)
- Authentication
- Mobile layout (desktop-first)
