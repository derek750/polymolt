"""
PolyMolt backend — FastAPI app.
Routers: /ai (pipeline), /db (database placeholder).
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import pipeline_router, database_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PolyMolt API",
    description="Backend for the PolyMolt app",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_router)
app.include_router(database_router)


@app.get("/")
def root():
    return {"name": "PolyMolt API", "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
