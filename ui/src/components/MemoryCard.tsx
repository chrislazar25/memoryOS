import { useState } from "react";
import type { Memory, SearchResult } from "../types";
import { Badge } from "./Badge";
import "./MemoryCard.css";

interface Props {
  memory: Memory | SearchResult;
  expanded: boolean;
  onToggle: () => void;
}

function isSearchResult(m: Memory | SearchResult): m is SearchResult {
  return "score" in m;
}

function normalizeRejected(r: string | string[] | undefined): string {
  if (!r) return "";
  return Array.isArray(r) ? r.join(" · ") : r;
}

export function MemoryCard({ memory, expanded, onToggle }: Props) {
  const short = memory.commit_hash.slice(0, 7);
  const score = isSearchResult(memory) ? memory.score : null;

  return (
    <div
      className={`card ${expanded ? "card--expanded" : ""}`}
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onToggle()}
    >
      {/* ── collapsed header ── */}
      <div className="card__header">
        <div className="card__header-left">
          <code className="card__hash">{short}</code>
          <Badge type={memory.decision_type} />
          {score !== null && (
            <span className="card__score">{score.toFixed(3)}</span>
          )}
        </div>
        <span className="card__chevron">{expanded ? "▲" : "▼"}</span>
      </div>

      <p className="card__message">{memory.commit_message}</p>

      <p className="card__reason-preview">
        {expanded ? "" : memory.reason.slice(0, 120) + (memory.reason.length > 120 ? "…" : "")}
      </p>

      {/* ── expanded detail ── */}
      {expanded && (
        <div className="card__detail" onClick={(e) => e.stopPropagation()}>
          <section className="card__section">
            <h4 className="card__section-title">Reason</h4>
            <p className="card__body">{memory.reason}</p>
          </section>

          {memory.tradeoffs && (
            <section className="card__section">
              <h4 className="card__section-title">Tradeoffs</h4>
              {memory.tradeoffs.chosen && (
                <div className="card__tradeoff">
                  <span className="card__tradeoff-label card__tradeoff-label--chosen">chosen</span>
                  <span className="card__body">{memory.tradeoffs.chosen}</span>
                </div>
              )}
              {memory.tradeoffs.rejected && (
                <div className="card__tradeoff">
                  <span className="card__tradeoff-label card__tradeoff-label--rejected">rejected</span>
                  <span className="card__body">{normalizeRejected(memory.tradeoffs.rejected)}</span>
                </div>
              )}
              {memory.tradeoffs.known_downsides && (
                <div className="card__tradeoff">
                  <span className="card__tradeoff-label card__tradeoff-label--downsides">downsides</span>
                  <span className="card__body">{memory.tradeoffs.known_downsides}</span>
                </div>
              )}
            </section>
          )}

          {memory.tags.length > 0 && (
            <section className="card__section">
              <div className="card__tags">
                {memory.tags.map((tag) => (
                  <span key={tag} className="card__tag">{tag}</span>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
