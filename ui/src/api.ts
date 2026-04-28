import type { Memory, SearchResult } from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export interface GraphNodeData {
  id: string;
  commit_hash: string;
  commit_message: string;
  decision_type: string;
  reason: string;
  tradeoffs: {
    chosen?: string;
    rejected?: string | string[];
    known_downsides?: string;
  };
  tags: string[];
}

export interface GraphLinkData {
  source: string;
  target: string;
}

export interface GraphResponse {
  nodes: GraphNodeData[];
  links: GraphLinkData[];
}

export async function fetchMemories(repo: string): Promise<Memory[]> {
  const res = await fetch(`${BASE}/memory?repo=${encodeURIComponent(repo)}`);
  if (!res.ok) throw new Error(`/memory returned ${res.status}`);
  return res.json();
}

export async function searchMemories(
  query: string,
  repo: string,
  topK = 3
): Promise<SearchResult[]> {
  const params = new URLSearchParams({
    query,
    repo,
    top_k: String(topK),
  });
  const res = await fetch(`${BASE}/search?${params}`);
  if (!res.ok) throw new Error(`/search returned ${res.status}`);
  return res.json();
}

export async function fetchGraph(repo: string): Promise<GraphResponse> {
  const res = await fetch(`${BASE}/graph?repo=${encodeURIComponent(repo)}`);
  if (!res.ok) throw new Error(`/graph returned ${res.status}`);
  return res.json();
}

export async function postMemory(memory: Memory): Promise<Memory> {
  const res = await fetch(`${BASE}/memory`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(memory),
  });
  if (!res.ok) throw new Error(`POST /memory returned ${res.status}`);
  return res.json();
}
