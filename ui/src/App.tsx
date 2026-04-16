import { useEffect, useState } from "react";
import type { Memory } from "./types";
import { fetchMemories } from "./api";
import { Timeline } from "./components/Timeline";
import { QueryPanel } from "./components/QueryPanel";
import "./App.css";

const REPO = "demo-api";

type LoadStatus = "loading" | "ready" | "error";

export default function App() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loadStatus, setLoadStatus] = useState<LoadStatus>("loading");
  const [loadError, setLoadError] = useState("");
  const [expandedHash, setExpandedHash] = useState<string | null>(null);

  useEffect(() => {
    fetchMemories(REPO)
      .then((data) => {
        setMemories(data);
        setLoadStatus("ready");
      })
      .catch((err) => {
        setLoadError(err instanceof Error ? err.message : "Failed to load");
        setLoadStatus("error");
      });
  }, []);

  function handleToggle(hash: string) {
    setExpandedHash((prev) => (prev === hash ? null : hash));
  }

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__header-inner">
          <div className="app__title-group">
            <span className="app__logo">⬡</span>
            <h1 className="app__title">MemoryOS</h1>
          </div>
          <span className="app__repo">{REPO}</span>
        </div>
      </header>

      <main className="app__main">
        {/* ── OVERVIEW ── */}
        <section className="app__section">
          <h2 className="app__section-title">Overview</h2>

          {loadStatus === "loading" && (
            <div className="app__loading">
              <span className="app__loading-spinner" />
              <span>Loading memories…</span>
            </div>
          )}

          {loadStatus === "error" && (
            <div className="app__load-error">
              <strong>Could not load memories.</strong>
              <span>{loadError}</span>
              <span className="app__load-hint">
                Is the API running?{" "}
                <code>uvicorn core.server:app --port 8000</code>
              </span>
            </div>
          )}

          {loadStatus === "ready" && (
            <Timeline
              memories={memories}
              expandedId={expandedHash}
              onToggle={handleToggle}
            />
          )}
        </section>

        {/* ── QUERY ── */}
        <QueryPanel repo={REPO} />
      </main>
    </div>
  );
}
