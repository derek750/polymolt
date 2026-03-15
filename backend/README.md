# PolyMolt Backend

FastAPI app that runs the **RAG + specialized system-prompt agent** pipeline when you call the route.

## Run the backend

```bash
cd backend
python -m pip install -r requirements.txt
export OPENAI_API_KEY=your_key_here
python -m uvicorn main:app --reload --port 8000
```

## Routes

- **/**, **/health** — App info and health.
- **/ai/run** — Run the pipeline (POST). **/ai/agents** — List agents (GET).
- **/db/health** — Database router placeholder (GET); add DB routes in `app/api/database.py` later.

## Trigger the pipeline

**POST /ai/run** — the pipeline runs on every call.

```bash
curl -X POST http://localhost:8000/ai/run \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the main climate risks for Scandinavia?"}'
```

Optional body fields:

- **message** (required): User question or message.
- **system_prompt** (optional): Override the default agent system prompt (e.g. "You are a policy expert. Answer only from the context.").
- **use_rag** (optional, default `true`): If `true`, the query is embedded and the vector store is searched for context; if `false`, only system prompt + message are sent to the LLM.

Response:

```json
{ "response": "..." }
```

## Environment

- **OPENAI_API_KEY** (required for pipeline): Used for embeddings (RAG) and chat (LLM).
- **EMBED_MODEL** (optional): Default `text-embedding-3-small`.
- **CHAT_MODEL** (optional): Default `gpt-4o-mini`.

## RAG (two Astra DBs)

The app uses **two DataStax Astra DB** vector stores (via `astrapy`):

| DB | Purpose | Collection | Ingest script |
|----|---------|------------|---------------|
| **Agents** | Guidelines / sample context for agents | `sample_rag` | `ingest_sample.py` |
| **Orchestrator** | Scraped news for orchestrator | `news_rag` | `ingest_news.py` |

- **Agents RAG (guidelines):** `ASTRA_DB_API_ENDPOINT`, `ASTRA_DB_APPLICATION_TOKEN`. Optional: `ASTRA_DB_KEYSPACE` (default `default_keyspace`), `ASTRA_EMBED_DIMENSION` (default `1536`).
- **Orchestrator RAG (news):** `ASTRA_DB_ORCHESTRATOR_API_ENDPOINT`, `ASTRA_DB_ORCHESTRATOR_APPLICATION_TOKEN`. Optional: `ASTRA_DB_ORCHESTRATOR_KEYSPACE` (default `default_keyspace`).

If a DB is not configured or no documents have been added for that collection, RAG returns no context for that path. To add documents: `add_documents(texts, ids=..., collection_name=..., metadatas=...)`; use `collection_name="sample_rag"` for agents, `collection_name="news_rag"` for orchestrator (ingest scripts set this automatically).

## IBM Db2 — saving orchestrate responses

Each **POST /ai/orchestrate** response is saved to Db2 under one question: the question row, one **orchestrate_runs** row (topic_reasoning, deep_analysis, assigned_agent_id, expertise_rationale, rag_context, full_response JSON), and **stakeholder_responses** for every initial_bet (phase=`initial_bet`) and every triggered_agent (phase=`triggered`, with choice_reasoning, context, analysis in raw_payload).

1. **Set DB2_DSN** in `.env` (see `.env.example`).
2. **Create tables** (and add `phase` / `orchestrate_runs` if you already have questions): run the SQL in **`scripts/db2_orchestrate_schema.sql`** in your Db2 database.

### How to verify data is saved

- **List recent questions (with yes/no counts):**
  ```bash
  curl -s http://localhost:8000/db/questions | jq
  ```
- **Get one question and all AI responses (initial_bets + triggered, with phase and reasoning):**
  ```bash
  curl -s http://localhost:8000/db/questions/1 | jq
  ```
  Replace `1` with a question `id` from the list.
- **Get the full orchestrate run for a question (topic_reasoning, deep_analysis, full_response JSON):**
  ```bash
  curl -s http://localhost:8000/db/questions/1/orchestrate | jq
  ```

You can also query Db2 directly (e.g. IBM Cloud console → Query editor): `SELECT * FROM questions`, `SELECT * FROM stakeholder_responses WHERE question_id = 1`, `SELECT * FROM orchestrate_runs WHERE question_id = 1`.

## Layout

- **main.py** — FastAPI app; mounts routers from `app/api/`.
- **app/ai/router.py** — AI router (`/ai`): POST /ai/run, POST /ai/orchestrate, GET /ai/agents, etc.
- **app/db/router.py** — DB router (`/db`): POST /db/questions, GET /db/questions, GET /db/questions/{id}, GET /db/questions/{id}/orchestrate.
- **app/ai/pipeline.py** — Builds prompt (system + RAG context + message), calls LLM, returns response.
- **app/ai/rag.py** — Embeddings + Astra DB vector retrieval.
- **app/config.py** — Env config.
- **scripts/db2_orchestrate_schema.sql** — Db2 DDL for orchestrate_runs and phase column.
- **langflow_pipeline/** — Reference flow JSON (same logic as the code).
