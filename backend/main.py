"""
PolyMolt backend — FastAPI app.
Routers: /ai (pipeline), /db (database), /market (prediction market).
Deploys to GCP Cloud Run (reads PORT from env).
"""

import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.config import ALLOWED_ORIGINS  # noqa: E402 — must be after load_dotenv
from app.ai.router import router as ai_router
from app.db.router import router as db_router
from app.market.router import router as market_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PolyMolt API",
    description="Backend for the PolyMolt app",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)
app.include_router(db_router)
app.include_router(market_router)


@app.get("/")
def root():
    return {"name": "PolyMolt API", "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
def health():
    from app.cache import redis_health
    return {"status": "ok", "redis": redis_health()}
