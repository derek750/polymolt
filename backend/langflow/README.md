# Langflow pipeline (reference)

The **pipeline is executed by the FastAPI backend** when you call `POST /run`. The backend implements the same flow in code (RAG + system prompt + LLM) in `app/pipeline.py` and `app/rag.py`.

This folder keeps the Langflow flow JSON as a **reference** (e.g. for importing into Langflow UI or for documentation). To run the pipeline, start the backend and hit the route — you do not need to run Langflow separately.

See backend root README for how to run the API and trigger the pipeline.
