import { useCallback, useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { DecisionType } from "../types";
import type { GraphNodeData, GraphLinkData, GraphResponse } from "../api";
import { fetchGraph, postMemory } from "../api";
import { Badge } from "./Badge";
import "./GraphView.css";

// react-force-graph-2d mutates nodes with x/y during simulation
type LiveNode = GraphNodeData & { x: number; y: number };

interface LiveGraph {
  nodes: GraphNodeData[];
  links: GraphLinkData[];
}

const NODE_COLORS: Record<string, string> = {
  design_choice: "#3B82F6",
  design_change: "#F97316",
  performance: "#22C55E",
  security_incident_response: "#EF4444",
  incident: "#EF4444",
  spec: "#A855F7",
};

function colorOf(node: GraphNodeData): string {
  return NODE_COLORS[node.decision_type] ?? "#8b949e";
}

function radiusOf(node: GraphNodeData): number {
  if (node.decision_type === "spec") return 10;
  if (node.decision_type === "incident" || node.decision_type === "security_incident_response") return 8;
  return 6;
}

function normalizeRejected(r: string | string[] | undefined): string {
  if (!r) return "";
  return Array.isArray(r) ? r.join(" · ") : r;
}

interface SpecForm {
  title: string;
  intent: string;
  constraints: string;
  tradeoffs: string;
}

const EMPTY_FORM: SpecForm = { title: "", intent: "", constraints: "", tradeoffs: "" };

interface Props {
  repo: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const FG = ForceGraph2D as React.ComponentType<any>;

export function GraphView({ repo }: Props) {
  const [graph, setGraph] = useState<LiveGraph>({ nodes: [], links: [] });
  const [selected, setSelected] = useState<GraphNodeData | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<SpecForm>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const canvasRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const [dims, setDims] = useState({ width: 800, height: 600 });

  useEffect(() => {
    fetchGraph(repo)
      .then((data: GraphResponse) => setGraph(data))
      .catch(() => {});
  }, [repo]);

  useEffect(() => {
    if (!fgRef.current || graph.nodes.length === 0) return;
    fgRef.current.d3Force("charge").strength(-200);
    fgRef.current.d3Force("link").distance(80);
  }, [graph]);

  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0]?.contentRect;
      if (r) setDims({ width: r.width, height: r.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const handleNodeClick = useCallback((node: object) => {
    setSelected(node as GraphNodeData);
  }, []);

  async function handleSpecSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const created = await postMemory({
        repo,
        commit_hash: `spec-${Date.now()}`,
        commit_message: form.title,
        decision_type: "spec" as DecisionType,
        reason: form.intent,
        tradeoffs: {
          chosen: form.tradeoffs || undefined,
          known_downsides: form.constraints || undefined,
        },
        tags: ["spec"],
      });
      const newNode: GraphNodeData = {
        id: created.commit_hash,
        commit_hash: created.commit_hash,
        commit_message: created.commit_message,
        decision_type: created.decision_type,
        reason: created.reason,
        tradeoffs: created.tradeoffs,
        tags: created.tags,
      };
      setGraph((prev) => ({ nodes: [...prev.nodes, newNode], links: prev.links }));
      setShowModal(false);
      setForm(EMPTY_FORM);
    } catch (_err) {
      // keep modal open so user can retry
    } finally {
      setSubmitting(false);
    }
  }

  function renderNode(node: object, ctx: CanvasRenderingContext2D, globalScale: number) {
    const n = node as LiveNode;
    const r = radiusOf(n);
    const color = colorOf(n);

    // Soft glow ring
    ctx.beginPath();
    ctx.arc(n.x, n.y, r + 3, 0, 2 * Math.PI);
    ctx.fillStyle = color + "22";
    ctx.fill();

    // Filled circle
    ctx.beginPath();
    ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    // Truncated label below node
    const raw = n.commit_message ?? "";
    const label = raw.length > 40 ? raw.slice(0, 40) + "…" : raw;
    const fontSize = Math.max(12 / globalScale, 2);
    ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillStyle = "rgba(201,209,217,0.8)";
    ctx.fillText(label, n.x, n.y + r + 4 / globalScale);
  }

  function paintPointerArea(node: object, color: string, ctx: CanvasRenderingContext2D) {
    const n = node as LiveNode;
    ctx.beginPath();
    ctx.arc(n.x, n.y, radiusOf(n) + 4, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
  }

  return (
    <div className="gv">
      {/* Toolbar */}
      <div className="gv__toolbar">
        <button className="gv__add-spec" onClick={() => setShowModal(true)}>
          + Add Spec
        </button>
        <div className="gv__legend">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <span key={type} className="gv__legend-item">
              <span className="gv__legend-dot" style={{ background: color }} />
              <span className="gv__legend-label">{type.replace(/_/g, " ")}</span>
            </span>
          ))}
        </div>
      </div>

      {/* Graph + Side Panel */}
      <div className="gv__body">
        <div className="gv__canvas" ref={canvasRef}>
          <FG
            ref={fgRef}
            graphData={graph}
            width={dims.width}
            height={dims.height}
            backgroundColor="#0d1117"
            nodeCanvasObject={renderNode}
            nodeCanvasObjectMode={() => "replace"}
            nodePointerAreaPaint={paintPointerArea}
            nodeLabel={(n: object) => (n as GraphNodeData).commit_message}
            onNodeClick={handleNodeClick}
            linkColor={() => "rgba(255,255,255,0.12)"}
            linkWidth={1}
            cooldownTicks={150}
          />
        </div>

        {selected && (
          <aside className="gv__panel">
            <div className="gv__panel-top">
              <div className="gv__panel-meta">
                <code className="gv__hash">{selected.commit_hash.slice(0, 7)}</code>
                <Badge type={selected.decision_type as DecisionType} />
              </div>
              <button
                className="gv__close-btn"
                onClick={() => setSelected(null)}
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <h3 className="gv__panel-title">{selected.commit_message}</h3>

            <section className="gv__section">
              <h4 className="gv__section-title">Reason</h4>
              <p className="gv__body-text">{selected.reason}</p>
            </section>

            {(selected.tradeoffs.chosen || selected.tradeoffs.rejected || selected.tradeoffs.known_downsides) && (
              <section className="gv__section">
                <h4 className="gv__section-title">Tradeoffs</h4>
                {selected.tradeoffs.chosen && (
                  <div className="gv__tradeoff">
                    <span className="gv__tradeoff-label gv__tradeoff-label--chosen">chosen</span>
                    <span className="gv__body-text">{selected.tradeoffs.chosen}</span>
                  </div>
                )}
                {selected.tradeoffs.rejected && (
                  <div className="gv__tradeoff">
                    <span className="gv__tradeoff-label gv__tradeoff-label--rejected">rejected</span>
                    <span className="gv__body-text">{normalizeRejected(selected.tradeoffs.rejected)}</span>
                  </div>
                )}
                {selected.tradeoffs.known_downsides && (
                  <div className="gv__tradeoff">
                    <span className="gv__tradeoff-label gv__tradeoff-label--downsides">downsides</span>
                    <span className="gv__body-text">{selected.tradeoffs.known_downsides}</span>
                  </div>
                )}
              </section>
            )}

            {selected.tags.length > 0 && (
              <section className="gv__section">
                <div className="gv__tags">
                  {selected.tags.map((tag) => (
                    <span key={tag} className="gv__tag">{tag}</span>
                  ))}
                </div>
              </section>
            )}
          </aside>
        )}
      </div>

      {/* Add Spec Modal */}
      {showModal && (
        <div
          className="gv__overlay"
          onClick={() => setShowModal(false)}
          role="dialog"
          aria-modal="true"
        >
          <div className="gv__modal" onClick={(e) => e.stopPropagation()}>
            <div className="gv__modal-header">
              <h3>Add Spec</h3>
              <button className="gv__close-btn" onClick={() => setShowModal(false)} aria-label="Close">✕</button>
            </div>

            <form className="gv__form" onSubmit={handleSpecSubmit}>
              <label className="gv__field">
                <span className="gv__field-label">Title</span>
                <input
                  className="gv__input"
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  required
                  placeholder="e.g. Use TF-IDF for retrieval"
                />
              </label>

              <label className="gv__field">
                <span className="gv__field-label">Intent</span>
                <textarea
                  className="gv__input gv__textarea"
                  value={form.intent}
                  onChange={(e) => setForm((f) => ({ ...f, intent: e.target.value }))}
                  required
                  placeholder="Why are we doing this?"
                  rows={3}
                />
              </label>

              <label className="gv__field">
                <span className="gv__field-label">Constraints</span>
                <textarea
                  className="gv__input gv__textarea"
                  value={form.constraints}
                  onChange={(e) => setForm((f) => ({ ...f, constraints: e.target.value }))}
                  placeholder="Known limits or downsides"
                  rows={2}
                />
              </label>

              <label className="gv__field">
                <span className="gv__field-label">Tradeoffs</span>
                <textarea
                  className="gv__input gv__textarea"
                  value={form.tradeoffs}
                  onChange={(e) => setForm((f) => ({ ...f, tradeoffs: e.target.value }))}
                  placeholder="What was chosen over what?"
                  rows={2}
                />
              </label>

              <div className="gv__form-actions">
                <button
                  type="button"
                  className="gv__btn gv__btn--ghost"
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="gv__btn gv__btn--primary"
                  disabled={submitting}
                >
                  {submitting ? "Saving…" : "Add Spec"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
