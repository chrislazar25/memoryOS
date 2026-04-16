# MemoryOS

> Coding agents can read your code. They have no memory of why it is the way it is.

Git records what changed. MemoryOS records why — and makes it queryable by any agent or developer.

---

## The problem

Every time a coding agent starts a new session, it starts blind. It can read your codebase but has no access to the decisions that shaped it. Why did you switch from JWT to sessions? Why is Redis here? Why is the rate limit set to 10 req/min?

That context lives in the head of your colleague who switched teams, a Teams chat you're not a part of, and these days by an agent whose context window is 90% full and can't triage why.

MemoryOS is the missing layer between your git history and your agent's context window.

---

## What it does

- Stores structured "why" alongside every commit — reason, tradeoffs, what was rejected
- Makes that memory queryable in natural language
- Exposes it via REST API and MCP so any coding agent can retrieve it as context
- Visualizes your repo's decision history so you can understand a codebase at a glance

---

## Demo

![MemoryOS UI](docs/screenshot.png)

Ask: *"why did we switch from JWT?"*

MemoryOS returns:
- The exact commit
- The incident that triggered it (contractor account couldn't be locked out for 45 min)
- What was rejected (JWT + denylist)
- Known downsides of the decision made

No digging through PRs. No asking a teammate. No re-explaining to your agent.

---

## Running locally

**1. Ingest demo data**

Use the copy tracked in the main repo (works everywhere), or the narrative repo under `demo-repo/` if you have it checked out:

```bash
cd core
python ingest.py ../seed-data/memory_reasons.json
# or: python ingest.py ../demo-repo/memory_reasons.json
```

**2. Start the API server**

```bash
uvicorn core.server:app --port 8000
```

**3. Start the UI**

```bash
cd ui
npm install && npm run dev
```

Open `http://localhost:5173` — the demo repo is preloaded.

If your API is running on `localhost:8000`, set:

```bash
# PowerShell
$env:VITE_API_BASE_URL="http://localhost:8000"
npm run dev
```

**4. Query via API directly**

```bash
curl "http://localhost:8000/search?query=why+did+we+add+rate+limiting&repo=demo-api"
```

---

## MCP integration

MemoryOS exposes a `search_memory` tool via MCP. Add this to your Cursor or Claude Code config:

```json
{
  "mcpServers": {
    "memoryos": {
      "command": "python",
      "args": ["core/mcp_server.py"]
    }
  }
}
```

Your agent can now call `search_memory` to retrieve context before making changes.

---

## Deployment

Use:
- **Vercel** for the frontend (`ui/`)
- **Render** for the backend (`core.server:app`)

### Zero-friction hosting: `seed-data/` vs `demo-repo/`

The crafted narrative may live under `demo-repo/`. If `demo-repo/` is its **own git repository**, GitHub often does **not** include its files inside the parent MemoryOS repo clone. Render then fails with `FileNotFoundError: ... demo-repo/memory_reasons.json`.

**Fix used here:** a deploy-safe copy lives at [`seed-data/memory_reasons.json`](seed-data/memory_reasons.json), committed in the main repo. [`core/seed_demo.py`](core/seed_demo.py) loads, in order:

1. `MEMORYOS_SEED_PATH` (optional override)
2. `seed-data/memory_reasons.json`
3. `demo-repo/memory_reasons.json` (fallback for local dev)

You can keep using `demo-repo/` as a separate repo for experiments; sync content into `seed-data/` when the narrative changes (see [`seed-data/README.md`](seed-data/README.md)).

### Render (free tier, no persistent disk)

[`render.yaml`](render.yaml) configures:

- `plan: free` (no persistent disk)
- `MEMORYOS_DB_PATH=/tmp/memories.db` (ephemeral SQLite)
- `startCommand: python core/seed_demo.py && uvicorn core.server:app --host 0.0.0.0 --port $PORT` (seed on every boot so cold starts and redeploys stay demo-ready)

What ephemeral storage means:

- Data can reset on restarts, cold starts, or redeploys.
- Fine for portfolio/demo; not for durable production data (a future v2 path is a hosted DB like Postgres).

### No-friction deploy checklist

**Backend (Render)**

1. Push this repo to GitHub (ensure `seed-data/memory_reasons.json` is in the tree).
2. New **Blueprint** (or Web Service) from the repo; confirm it reads `render.yaml`.
3. After deploy, open **Environment** and confirm `MEMORYOS_DB_PATH` is `/tmp/memories.db`.
4. Smoke-test:
   - `GET https://<your-service>.onrender.com/memory?repo=demo-api`
   - `GET https://<your-service>.onrender.com/search?query=jwt&repo=demo-api`

**Frontend (Vercel)**

1. Import the same repo; set **Root Directory** to `ui`.
2. Set `VITE_API_BASE_URL=https://<your-service>.onrender.com` (no trailing slash).
3. Deploy and open the Vercel URL; timeline and search should hit Render.

Local UI env template: [`ui/.env.example`](ui/.env.example).

### Troubleshooting

| Symptom | Likely cause | Fix |
|--------|----------------|-----|
| `FileNotFoundError: ... demo-repo/memory_reasons.json` on Render | Nested `demo-repo` not in parent repo checkout | Ensure `seed-data/memory_reasons.json` is committed and pushed; redeploy. |
| Empty timeline / no search results | DB empty or wiped (`/tmp`) | Redeploy or wait for restart — startup runs `seed_demo.py` again; or run `python core/seed_demo.py` in Render **Shell**. |
| Browser CORS or wrong API host | Frontend still pointing at localhost | Set `VITE_API_BASE_URL` on Vercel to your Render URL and redeploy the frontend. |

### Later: durable production data

For real persistence beyond demo tier, plan a move from file SQLite to **Postgres** (or Render disk on a paid plan). The current setup optimizes for **zero friction** on free Render + Vercel.

---

## Architecture

```
memory_reasons.json → ingest → SQLite → TF-IDF retrieval → FastAPI → UI / MCP
```

**Project structure**

```
memoryos/
├── demo-repo/          optional nested git repo (narrative); may not ship on GitHub
├── seed-data/          memory_reasons.json copy for deploy + seed_demo.py
├── render.yaml         Render backend service definition
├── core/
│   ├── store.py        SQLite layer
│   ├── ingest.py       reads reasons file, stores memory
│   ├── retrieval.py    TF-IDF semantic search
│   ├── server.py       FastAPI REST API
│   ├── seed_demo.py    demo seed (seed-data first, then demo-repo)
│   └── mcp_server.py   MCP server for agent integration
└── ui/                 React + TypeScript
```

---

## v1 vs what's coming

**v1 (this repo)**
- Manual `memory_reasons.json` — developer writes the why
- TF-IDF retrieval
- Timeline UI + natural language query
- REST API + MCP

**v2**
- Auto-capture — agent commits, MemoryOS intercepts, structured reason extracted automatically
- Neural embeddings replacing TF-IDF
- Graph UI — entities, relationships, decisions as nodes and edges
- Parallel agent support — multiple agents share one memory layer, no conflicts

---

## Why this isn't solved by mem0 or Graphiti

Both are built for conversational agents. Their memory primitive is extracting facts from dialogue.

A coding agent's world is different — it's decisions with tradeoffs, failures that revealed design constraints, branches representing parallel realities. None of that maps to conversation facts.

MemoryOS is built around coding-native memory primitives: `decision`, `incident`, `tradeoff`, `invariant`. The unit of memory is a commit, not a message.

---

## Status

Early. v1 proves the retrieval thesis. If you're building coding agents and want to talk, open an issue or reach out.
