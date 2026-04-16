# MemoryOS

A persistent memory layer for coding agents. Solves the problem that coding agents can read your code but have no memory of why it is the way it is.

## Core thesis
Git records what changed. Nobody records why. MemoryOS is that missing layer.

## Stack
- Python — core engine (ingest, store, retrieval)
- FastAPI — API server
- SQLite — storage (v1), swap to Postgres later
- TF-IDF — retrieval (v1), swap to embeddings later
- React/TypeScript — UI
- MCP — agent integration layer

## Project structure
- /demo-repo — crafted git repo with memory_reasons.json (the demo narrative)
- /core — Python memory engine
- /ui — React frontend
- /core/mcp_server.py — MCP server

## Key conventions
- Every commit in demo-repo has a corresponding entry in memory_reasons.json
- memory_reasons.json is the structured "why" that git doesn't capture
- Retrieval always returns: message, reason, tradeoffs, tags, commit hash
- Never auto-commit. Always wait for user review.

## Memory primitives (v1)
- decision_type: design_choice | design_change | performance | security_incident_response
- Every memory has: commit_hash, reason, tradeoffs, tags