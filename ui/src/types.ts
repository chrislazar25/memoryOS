export type DecisionType =
  | "design_choice"
  | "design_change"
  | "performance"
  | "security_incident_response";

export interface Tradeoffs {
  chosen?: string;
  rejected?: string | string[];
  known_downsides?: string;
}

export interface Memory {
  id?: number;
  repo?: string;
  commit_hash: string;
  commit_message: string;
  decision_type: DecisionType;
  reason: string;
  tradeoffs: Tradeoffs;
  tags: string[];
  created_at?: string;
}

export interface SearchResult extends Memory {
  score: number;
}
