import { useState, useRef, type FormEvent } from "react";
import type { SearchResult } from "../types";
import { searchMemories } from "../api";
import { MemoryCard } from "./MemoryCard";
import "./QueryPanel.css";

interface Props {
  repo: string;
}

type Status = "idle" | "loading" | "error";

export function QueryPanel({ repo }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [expandedHash, setExpandedHash] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;

    setStatus("loading");
    setResults([]);
    setExpandedHash(null);
    setErrorMsg("");

    try {
      const data = await searchMemories(q, repo, 3);
      setResults(data);
      setStatus("idle");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Search failed");
      setStatus("error");
    }
  }

  function toggle(hash: string) {
    setExpandedHash((prev) => (prev === hash ? null : hash));
  }

  return (
    <section className="query-panel">
      <h2 className="query-panel__title">Query</h2>

      <form className="query-panel__form" onSubmit={handleSubmit}>
        <div className="query-panel__input-row">
          <input
            ref={inputRef}
            className="query-panel__input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything about this codebase…"
            disabled={status === "loading"}
            autoComplete="off"
            spellCheck={false}
          />
          <button
            className="query-panel__submit"
            type="submit"
            disabled={status === "loading" || !query.trim()}
          >
            {status === "loading" ? (
              <span className="query-panel__spinner" />
            ) : (
              <SearchIcon />
            )}
          </button>
        </div>
      </form>

      {status === "error" && (
        <p className="query-panel__error">{errorMsg}</p>
      )}

      {results.length > 0 && (
        <div className="query-panel__results">
          <p className="query-panel__results-meta">
            {results.length} result{results.length !== 1 ? "s" : ""} for "{query}"
          </p>
          <div className="query-panel__result-list">
            {results.map((r) => (
              <MemoryCard
                key={r.commit_hash}
                memory={r}
                expanded={expandedHash === r.commit_hash}
                onToggle={() => toggle(r.commit_hash)}
              />
            ))}
          </div>
        </div>
      )}

      {status === "idle" && results.length === 0 && query && (
        <p className="query-panel__empty">No results found.</p>
      )}
    </section>
  );
}

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
