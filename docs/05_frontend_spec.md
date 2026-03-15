# Frontend Specification

## Stack
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Recharts (for probability chart)
- Server-Sent Events (SSE) via EventSource in custom hook

---

## Layout Overview

```
┌─────────────────────────────────────────────────────────┐
│  HEADER: Polymolt logo | Region selector | Status badge  │
├──────────────────────────────┬──────────────────────────┤
│                              │                          │
│   MARKET PANEL               │   TRADE FEED             │
│   ─ Current probability      │   ─ Scrolling trade log  │
│   ─ Live chart               │   ─ Agent / dir / size   │
│   ─ Region description       │   ─ Before → After prob  │
│                              │   ─ Short explanation    │
│                              │                          │
├──────────────────────────────┴──────────────────────────┤
│                                                         │
│   AGENT GRID (3x3)                                      │
│   ─ 9 agent cards                                       │
│   ─ Click to open detail panel                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
│   AGENT DETAIL DRAWER (slides in from right on click)   │
```

---

## Component Tree

```
app/
  layout.tsx          # Root layout, font, global styles
  page.tsx            # Main dashboard page

components/
  header/
    Header.tsx        # Logo, region selector, connection status
    RegionSelector.tsx

  market/
    MarketPanel.tsx   # Container for probability + chart
    ProbabilityDisplay.tsx  # Big number + trend indicator
    ProbabilityChart.tsx    # Recharts line chart

  trades/
    TradeFeed.tsx     # Scrollable trade log container
    TradeEntry.tsx    # Individual trade row

  agents/
    AgentGrid.tsx     # 3x3 grid of agent cards
    AgentCard.tsx     # Individual card with name, type, position
    AgentDrawer.tsx   # Detail panel/drawer

  shared/
    CategoryBadge.tsx # Colored tag for sustainability category
    BehaviorTraits.tsx # Trait bars visualization
```

---

## Data Flow

```
SSE (GET http://localhost:8000/market/{region_id}/stream)
  ↓
useMarket() hook (lib/useMarket.ts)
  ↓
  ├── marketState (price, history, region)
  ├── trades (ordered list)
  └── agents (9 agent objects with latest state)
  ↓
Components consume from context or props
```

---

## SSE Event Types

```typescript
// Incoming from backend (SSE data payloads)
type SSEMessage =
  | { type: "market_update"; data: MarketUpdate }
  | { type: "trade"; data: TradeEntry }
  | { type: "agent_update"; data: AgentUpdate }
  | { type: "market_reset"; data: MarketState }
  | { type: "connected"; data: { region_id: string } }
```

---

## TypeScript Types

```typescript
// types/market.ts
interface MarketState {
  regionId: string
  regionName: string
  question: string
  currentPrice: number        // 0–1
  priceHistory: number[]
  roundNumber: number
  isRunning: boolean
}

// types/trade.ts
interface TradeEntry {
  id: string
  timestamp: string
  agentId: string
  agentName: string
  agentType: "specialist" | "hybrid" | "master"
  direction: "BUY" | "SELL"
  size: number
  priceBefore: number
  priceAfter: number
  reasoning: string
  evidenceTitles: string[]
}

// types/agent.ts
interface Agent {
  id: string
  name: string
  agentType: "specialist" | "hybrid" | "master"
  categories: string[]
  bettingPower: number
  confidence: number
  riskTolerance: number
  stubbornness: number
  herdSensitivity: number
  updateFrequency: number
  currentBelief: number
  currentPosition: number
  lastReasoning: string
  evidenceUsed: EvidenceItem[]
  tradeHistory: TradeEntry[]
}

// types/evidence.ts
interface EvidenceItem {
  id: string
  category: string
  title: string
  summary: string
  sentiment: "positive" | "negative" | "mixed"
  strength: number   // 0–1
}
```

---

## Visual Design

### Color Palette
- Background: `slate-950` (near black)
- Surface: `slate-900`
- Border: `slate-800`
- Accent: `emerald-500` (sustainable/bullish)
- Warning: `rose-500` (unsustainable/bearish)
- Neutral: `slate-400`

### Agent Type Colors
- Specialist: `blue-500`
- Hybrid: `violet-500`
- Master: `amber-500`

### Category Colors
1. Climate: `emerald-400`
2. Energy: `yellow-400`
3. Water: `cyan-400`
4. Infrastructure: `orange-400`
5. Social: `pink-400`
6. Governance: `purple-400`

### Chart
- Line color: dynamic (green above 50%, red below)
- Grid: `slate-800`
- Tooltip: dark with probability + trade info

---

## Agent Detail Drawer

Content sections:
1. **Header**: name, type badge, betting power
2. **Knowledge**: category tags (colored)
3. **Belief**: current belief vs market price (visual gap indicator)
4. **Traits**: horizontal bars for each behavioral trait
5. **Latest Reasoning**: paragraph text
6. **Evidence Used**: card list with category, title, sentiment, strength
7. **Trade History**: last 5 trades in compact format

---

## Responsive Behavior
- Desktop first (1280px+)
- Tablet: hide trade feed to sidebar, collapse agent grid to 2 columns
- No mobile requirement for MVP
