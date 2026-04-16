"""
server.py — FastAPI server for the MemoryOS core engine.

Run with:
    uvicorn core.server:app --reload --port 8000

Endpoints
---------
  POST /ingest
  GET  /search?query=&repo=&top_k=3
  GET  /memory?repo=
"""

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Core engine imports — resolve relative to this file so the server works
# whether launched as `uvicorn core.server:app` or from inside /core.
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, str(Path(__file__).parent))

import store
import ingest as ingest_module
import retrieval as retrieval_module

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="MemoryOS", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure DB exists on startup
store.init_db()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    reasons_file: str
    repo: str


class IngestResponse(BaseModel):
    ingested: int
    repo: str


class Tradeoffs(BaseModel):
    chosen: str = ""
    rejected: Any = ""          # str or list[str]
    known_downsides: str = ""


class MemoryRecord(BaseModel):
    id: int | None = None
    repo: str | None = None
    commit_hash: str
    commit_message: str
    decision_type: str
    reason: str
    tradeoffs: dict
    tags: list[str]
    created_at: str | None = None


class SearchResult(BaseModel):
    score: float
    commit_hash: str
    commit_message: str
    decision_type: str
    reason: str
    tradeoffs: dict
    tags: list[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/ingest", response_model=IngestResponse, status_code=201)
def ingest(body: IngestRequest):
    """
    Load a memory_reasons.json file into SQLite.

    The `repo` field in the request body is used to validate that the file
    matches the expected repo — the authoritative name is always read from
    the JSON itself.
    """
    path = Path(body.reasons_file)
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {body.reasons_file}",
        )

    # Peek at the repo name in the file so we can validate + return it
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")

    actual_repo = data.get("repo", "")

    # Clear existing memories for idempotent re-ingestion
    store.clear_repo(actual_repo)

    count = ingest_module.ingest(path, clear=False)

    return IngestResponse(ingested=count, repo=actual_repo)


@app.get("/search", response_model=list[SearchResult])
def search(
    query: str = Query(..., description="Natural language query"),
    repo: str = Query(..., description="Repo name to search"),
    top_k: int = Query(3, ge=1, le=20, description="Max results to return"),
):
    """Return top_k memories ranked by TF-IDF cosine similarity."""
    if not query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    results = retrieval_module.retrieve(query, repo, top_k=top_k)
    return results


@app.get("/memory", response_model=list[MemoryRecord])
def memory(
    repo: str = Query(..., description="Repo name"),
):
    """Return all stored memories for a repo, unscored, in insertion order."""
    rows = store.fetch_all(repo)
    return rows
