// The chat timeline is a single ordered list of these. Live actions (chat,
// pace, conformance, doctor) all append to the same timeline so the demo reads
// as one continuous session.
import type {
  Budget,
  ConformanceResult,
  Governance,
  LastCall,
  Span,
} from "./features";
import type { PaceCallRow, ReserveReached } from "./components/results";

export interface Inspector {
  budget: Budget | null;
  lastCall: LastCall | null;
  span: Span | null;
}

export type Message =
  | { kind: "user"; id: string; text: string }
  | {
      kind: "assistant";
      id: string;
      text: string;
      streaming: boolean;
      inspector: Inspector | null;
    }
  | {
      kind: "governance";
      id: string;
      gov: Governance;
      inspector: Inspector | null;
    }
  | { kind: "note"; id: string; icon: string; title: string; body: string }
  | {
      kind: "pace";
      id: string;
      reserve: number;
      calls: PaceCallRow[];
      reserveReached: ReserveReached | null;
      budget: Budget | null;
      running: boolean;
    }
  | {
      kind: "conformance";
      id: string;
      result: ConformanceResult | null;
      running: boolean;
    }
  | { kind: "doctor"; id: string; output: string; running: boolean };

export function newId(): string {
  return Math.random().toString(36).slice(2, 10);
}
