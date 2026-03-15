<div align="center">
  <img src="docs/logo.png" alt="Polymolt" width="200" />
  <h1>Polymolt</h1>
  <p>AI-powered prediction market where specialized agents bet on real-world claims<br>Multi-agent orchestration with RAG retrieval, LMSR pricing, and live Server-Sent Events (SSE) streaming</p>

</div>  

---

## Overview

Traditional search gives you ten blue links when you want a straight answer. Nobody has time for that.  
That's why we built **Polymolt**: a prediction market where AI agents with asymmetric knowledge debate yes/no claims about real-world locations, and the truth emerges from how they trade.

Polymolt combines RAG pipelines, LMSR market mechanics, and multi-agent orchestration to evaluate claims. Each agent has a unique persona, domain expertise, and risk profile. They retrieve evidence from Astra DB, reason independently using Gemini and OpenAI models, and place bets, surfacing a probability that reflects their collective knowledge. Think Polymarket, but the traders are AI agents with specialized knowledge.

---

## Features

- **AI prediction market** with LMSR scoring to derive fair value from agent trades
- **Specialized agents** with unique expertise: healthcare, finance, location analysis, deep reasoning
- **RAG-powered evidence retrieval** from Astra DB vector stores before each decision
- **Real-time Server-Sent Events (SSE)** for live market updates on every agent trade
- **Interactive map**: click any Toronto location to trigger agent evaluation
- **Live dashboard** with probability charts, trade feeds, and agent belief tracking
- **Multi-agent orchestration** routing questions to the most relevant domain specialists
- **Dynamic visualization** via interactive globe, animated stock lines, and live charts
- **Shock events**: inject crisis or recovery scenarios mid-simulation; agents react within rounds
- **Railtracks**

---

## Architecture

**Prediction Pipeline**  
User Question → RAG Retrieval (Astra DB) → Agent Reasoning (Gemini/OpenAI) → LMSR Bet Sizing → Market Price Update → Frontend Dashboard

**Market Engine**  
Agent Belief → Confidence Scoring → Bet Size Calculation → LMSR Cost Function → Price History Update → SSE broadcast

**Orchestration Pipeline**  
Question Intake → Domain Classification → Agent Selection → Parallel RAG + Reasoning → Bet Collection → Fair Value Computation

<div align="center">
  <img src="docs/techstack.png" alt="Tech stack diagram" />
</div>

---

## Tech Stack

| Category | Technologies |
|---------|--------------|
| AI & ML | OpenAI GPT, Google Gemini, Langflow |
| Backend | Python, FastAPI, SSE (Server-Sent Events), Uvicorn |
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Database | Astra DB (Vector DB), IBM DB2, Langflow |
| Visualization | Mapbox GL, Recharts, COBE Globe |
| Communication | Server-Sent Events (SSE), REST API |

---

## How It Works

1. User clicks a location on the map or submits a yes/no claim.
2. Orchestrator classifies the question domain and selects relevant agents.
3. Each agent retrieves evidence from Astra DB collections via RAG.
4. Agents reason independently using their specialized system prompts.
5. Agents place YES/NO bets weighted by confidence and domain relevance.
6. LMSR engine computes the fair probability from all agent bets.
7. Market price updates in real time via SSE to the dashboard.
8. Trade feed shows each agent's reasoning, direction, and price impact.
9. Users can inject shock events to test how agents respond under pressure.

---

## Getting Started

### Prerequisites

- **Node.js** 18+
- **Python** 3.11+
- **API keys** (see Environment Variables below):
  - [OpenAI](https://platform.openai.com/api-keys) — GPT-4o-mini for agent reasoning
  - [Google Gemini](https://aistudio.google.com/apikey) — embeddings and optional chat
  - [DataStax Astra DB](https://astra.datastax.com/) — vector database for RAG retrieval
  - [Mapbox](https://account.mapbox.com/access-tokens/) — interactive map
  - [Upstash Redis](https://console.upstash.com/) *(optional)* — response caching

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/e-yang6/polymolt.git
cd polymolt
```

```bash
# 2. Backend
cd backend
python -m pip install -r requirements.txt
cp .env.example .env          # then fill in your API keys (see below)
python -m uvicorn main:app --reload --port 8000
```

```bash
# 3. Frontend (new terminal)
cd frontend
npm install
# Create .env.local:
echo 'NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token_here' > .env.local
npm run dev
```

```bash
# 4. Open http://localhost:3000
```

### Environment Variables

The backend reads from `backend/.env`. Copy the example and fill in your keys:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT-4o-mini agent reasoning |
| `GOOGLE_API_KEY` | Yes | Google Gemini API key for embeddings |
| `ASTRA_DB_API_ENDPOINT` | Yes | Astra DB endpoint for agent RAG collection |
| `ASTRA_DB_APPLICATION_TOKEN` | Yes | Astra DB token for agent RAG collection |
| `ASTRA_DB_ORCHESTRATOR_API_ENDPOINT` | Yes | Astra DB endpoint for orchestrator news RAG |
| `ASTRA_DB_ORCHESTRATOR_APPLICATION_TOKEN` | Yes | Astra DB token for orchestrator news RAG |
| `UPSTASH_REDIS_REST_URL` | No | Upstash Redis URL for caching |
| `UPSTASH_REDIS_REST_TOKEN` | No | Upstash Redis token for caching |
| `DB2_DSN` | No | IBM Db2 connection string for persistent storage |

The frontend reads from `frontend/.env.local`:

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_MAPBOX_TOKEN` | Yes | Mapbox GL access token for the interactive map |

---

## Project Structure

```
polymolt/
├── backend/                  # FastAPI server (Python 3.11+)
│   ├── main.py               # App entrypoint — mounts /ai, /db, /market routers
│   ├── app/
│   │   ├── ai/               # RAG pipeline, orchestrator, SSE streaming, bet sizing
│   │   ├── agents/           # Agent definitions — persona, expertise, risk profiles
│   │   ├── market/           # LMSR engine, market state, simulation
│   │   ├── db/               # IBM Db2 persistence layer
│   │   ├── models/           # OpenAI + Gemini wrappers (chat & embeddings)
│   │   ├── data/             # Toronto open-data scrapers (TTC, parks, libraries)
│   │   ├── config.py         # Environment variable loader
│   │   └── cache.py          # Upstash Redis caching
│   ├── Dockerfile            # Cloud Run deployment
│   └── requirements.txt
├── frontend/                 # Next.js 16 + React 19 + Tailwind CSS
│   ├── app/                  # Pages: landing, dashboard, map, agents
│   ├── components/           # UI: map, market panel, trade feed, globe
│   ├── lib/                  # Hooks, context providers, utilities
│   └── types/                # TypeScript type definitions
└── docs/                     # Design docs, diagrams, task breakdowns
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

- **Devpost**: coming soon
