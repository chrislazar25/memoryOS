import type { Memory, SearchResult } from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

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
