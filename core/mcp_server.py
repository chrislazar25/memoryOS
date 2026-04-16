"""
mcp_server.py — MemoryOS MCP server.

Exposes MemoryOS as a tool + resource to any MCP-compatible coding agent
(Claude Code, Cursor, etc.).  The FastAPI server (core/server.py) must be
running on localhost:8000 before clients connect.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO REGISTER THIS SERVER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Claude Code (~/.claude/claude_desktop_config.json  or  claude mcp add):

    {
      "mcpServers": {
        "memoryos": {
          "command": "python",
          "args": ["<absolute-path-to>/core/mcp_server.py"]
        }
      }
    }

  Or via the CLI:
    claude mcp add memoryos python <absolute-path-to>/core/mcp_server.py

Cursor (Settings → MCP → Add Server):

    Name:    memoryos
    Command: python
    Args:    <absolute-path-to>/core/mcp_server.py

In both cases, start the FastAPI server first:
    uvicorn core.server:app --port 8000

Run standalone (for testing):
    python core/mcp_server.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import sqlite3
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from mcp.server import FastMCP

BASE_URL = "http://localhost:8000"

mcp = FastMCP("memoryos")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get(path: str, params: dict | None = None) -> dict | list:
    """Make a GET request to the FastAPI server and return parsed JSON."""
    url = BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach MemoryOS server at {BASE_URL}. "
            f"Start it with: uvicorn core.server:app --port 8000\n"
            f"Detail: {exc}"
        ) from exc


def _format_result(i: int, r: dict) -> str:
    """Format a single search result as readable text for an agent."""
    short = r["commit_hash"][:7]
    lines = [
        f"#{i}  [{short}]  {r['commit_message']}",
        f"    score:         {r['score']:.4f}",
        f"    decision_type: {r['decision_type']}",
        "",
        "    Reason:",
    ]
    for line in textwrap.wrap(r["reason"], width=72,
                               initial_indent="      ",
                               subsequent_indent="      "):
        lines.append(line)

    t = r.get("tradeoffs", {})

    chosen = t.get("chosen", "")
    if chosen:
        lines.append("")
        lines.extend(
            textwrap.wrap(f"Chosen: {chosen}", width=72,
                          initial_indent="    ", subsequent_indent="      ")
        )

    rejected = t.get("rejected", "")
    if isinstance(rejected, list):
        rejected = "; ".join(rejected)
    if rejected:
        lines.extend(
            textwrap.wrap(f"Rejected: {rejected}", width=72,
                          initial_indent="    ", subsequent_indent="      ")
        )

    downsides = t.get("known_downsides", "")
    if downsides:
        lines.extend(
            textwrap.wrap(f"Downsides: {downsides}", width=72,
                          initial_indent="    ", subsequent_indent="      ")
        )

    lines.append("")
    lines.append(f"    Tags: {', '.join(r.get('tags', []))}")
    lines.append("\u2500" * 68)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

@mcp.tool()
def search_memory(query: str, repo: str, top_k: int = 3) -> str:
    """
    Search MemoryOS for the engineering decisions behind code changes.

    Returns the most relevant memories ranked by TF-IDF cosine similarity.
    Each memory records *why* a change was made — the reasoning, tradeoffs,
    and context that git commit messages don't capture.

    Args:
        query:  Natural language question, e.g. "why did we switch away from JWT?"
        repo:   Repository name as stored in MemoryOS, e.g. "demo-api"
        top_k:  Maximum number of results to return (default 3, max 20)
    """
    top_k = max(1, min(top_k, 20))
    results = _get("/search", {"query": query, "repo": repo, "top_k": top_k})

    if not results:
        return (
            f'No memories found for repo "{repo}". '
            "Has it been ingested? Check memoryos://repos."
        )

    header = f'MemoryOS search \u2014 repo: "{repo}"  query: "{query}"\n'
    header += "=" * 68 + "\n"
    body = "\n".join(_format_result(i, r) for i, r in enumerate(results, 1))
    return header + body


# ---------------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------------

@mcp.resource("memoryos://repos")
def list_repos() -> str:
    """
    List all repositories that have been ingested into MemoryOS.

    Returns a plain-text list of repo names, one per line.
    Use a repo name with the search_memory tool.
    """
    db = Path(__file__).parent / "memories.db"
    if not db.exists():
        return "No memories ingested yet."

    try:
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT DISTINCT repo FROM memories ORDER BY repo"
        ).fetchall()
        conn.close()
    except sqlite3.Error as exc:
        return f"Could not read database: {exc}"

    repos = [r[0] for r in rows]
    if not repos:
        return "No memories ingested yet."

    lines = ["Ingested repositories:\n"]
    for name in repos:
        lines.append(f"  \u2022 {name}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
