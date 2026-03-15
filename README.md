# Polymolt
AI-powered prediction market where specialized agents bet on real-world claims  
Multi-agent orchestration with RAG retrieval, LMSR pricing, and live WebSocket trading  

---

## Overview

Traditional search gives you ten blue links when you want a straight answer. Nobody has time for that.  
That's why we built **Polymolt**: a prediction market where AI agents with asymmetric knowledge debate yes/no claims about real-world locations — and the truth emerges from how they trade.

Polymolt combines RAG pipelines, LMSR market mechanics, and multi-agent orchestration to evaluate claims. Each agent has a unique persona, domain expertise, and risk profile. They retrieve evidence from Astra DB, reason independently using Gemini and OpenAI models, and place bets — surfacing a probability that reflects their collective knowledge. Think Polymarket, but the traders are AI agents with specialized knowledge.

---

## Features

- **AI prediction market** with LMSR scoring to derive fair value from agent trades
- **Specialized agents** with unique expertise — healthcare, finance, location analysis, deep reasoning
- **RAG-powered evidence retrieval** from Astra DB vector stores before each decision
- **Real-time WebSocket streaming** for live market updates on every agent trade
- **Interactive map** — click any Toronto location to trigger agent evaluation
- **Live dashboard** with probability charts, trade feeds, and agent belief tracking
- **Multi-agent orchestration** routing questions to the most relevant domain specialists
- **Dynamic visualization** via interactive globe, animated stock lines, and live charts
- **Shock events** — inject crisis or recovery scenarios mid-simulation; agents react within rounds

---

## Architecture

**Prediction Pipeline**  
User Question → RAG Retrieval (Astra DB) → Agent Reasoning (Gemini/OpenAI) → LMSR Bet Sizing → Market Price Update → Frontend Dashboard

**Market Engine**  
Agent Belief → Confidence Scoring → Bet Size Calculation → LMSR Cost Function → Price History Update → WebSocket Broadcast

**Orchestration Pipeline**  
Question Intake → Domain Classification → Agent Selection → Parallel RAG + Reasoning → Bet Collection → Fair Value Computation

---

## Tech Stack

| Category | Technologies |
|---------|--------------|
| AI & ML | OpenAI GPT, Google Gemini, Langflow |
| Backend | Python, FastAPI, WebSockets, Uvicorn |
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Database | Astra DB (Vector DB), IBM DB2, Langflow |
| Visualization | Mapbox GL, Recharts, COBE Globe |
| Communication | WebSockets, REST API |

---

## How It Works

1. User clicks a location on the map or submits a yes/no claim.
2. Orchestrator classifies the question domain and selects relevant agents.
3. Each agent retrieves evidence from Astra DB collections via RAG.
4. Agents reason independently using their specialized system prompts.
5. Agents place YES/NO bets weighted by confidence and domain relevance.
6. LMSR engine computes the fair probability from all agent bets.
7. Market price updates in real time via WebSocket to the dashboard.
8. Trade feed shows each agent's reasoning, direction, and price impact.
9. Users can inject shock events to test how agents respond under pressure.

---

## Getting Started

**Prerequisites**: Node 18+, Python 3.11+, an OpenAI API key, and a Mapbox access token.

```bash
# 1. Clone and enter
cd polymolt

# 2. Backend
cd backend
python -m pip install -r requirements.txt
export OPENAI_API_KEY=your_key_here
python -m uvicorn main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install

# Create .env.local with your Mapbox token:
# NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token_here
# Get your token from https://account.mapbox.com/access-tokens/

npm run dev

# 4. Open http://localhost:3000
```

---

## Future Roadmap

- More agents with environmental, legal, and education expertise
- Live data ingestion for real-time news and evidence feeds
- Persistent agent memory for evolving beliefs across sessions
- Multi-question markets running simultaneously
- Mobile app for on-the-go location-based predictions

---

## Team

| Member |
|--------|
| Derek Lau |
| Jeffrey Wong |
| Sihao Wu |
| Ethan Yang |

---

## Links

- Devpost submission: coming soon!
