import type { Memory } from "../types";
import { MemoryCard } from "./MemoryCard";
import "./Timeline.css";

interface Props {
  memories: Memory[];
  expandedId: string | null;
  onToggle: (hash: string) => void;
}

export function Timeline({ memories, expandedId, onToggle }: Props) {
  // Newest first (reverse chronological — newest at top)
  const sorted = [...memories].reverse();

  if (sorted.length === 0) {
    return <p className="timeline__empty">No memories loaded.</p>;
  }

  return (
    <ol className="timeline">
      {sorted.map((mem) => (
        <li key={mem.commit_hash} className="timeline__item">
          <div className="timeline__dot" />
          <div className="timeline__content">
            <MemoryCard
              memory={mem}
              expanded={expandedId === mem.commit_hash}
              onToggle={() => onToggle(mem.commit_hash)}
            />
          </div>
        </li>
      ))}
    </ol>
  );
}
