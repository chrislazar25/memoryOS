import type { DecisionType } from "../types";
import "./Badge.css";

const LABELS: Record<DecisionType, string> = {
  design_choice: "design choice",
  design_change: "design change",
  performance: "performance",
  security_incident_response: "security incident",
};

interface Props {
  type: DecisionType;
}

export function Badge({ type }: Props) {
  return (
    <span className={`badge badge--${type}`}>
      {LABELS[type] ?? type}
    </span>
  );
}
