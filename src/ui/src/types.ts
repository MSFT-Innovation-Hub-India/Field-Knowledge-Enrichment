export type AssetType = "battery" | "station";
export type Criticality = "urgent" | "priority" | "normal";

export interface Recommendation {
  ticketId: string;
  criticality: { suggested: Criticality; basis: string };
  probableCause: string;
  recommendedActions: { order: number; text: string; sopId?: string | null; section?: string | null }[];
  safetyWarnings: string[];
  pastHistory: { ticketId?: string | null; assetId?: string | null; date?: string | null; summary: string; resolution: string }[];
  sources: { sopId?: string | null; title?: string | null; section?: string | null; origin: "seed" | "field_enrichment" }[];
  noRelevantKnowledge: boolean;
}

export interface TicketForm {
  assetId: string;
  assetType: AssetType;
  ticketId: string;
  issue: string;
  loggedDate: string;
}

export interface ResolutionForm {
  fixApplied: string;
  rootCause: string;
  partsReplaced: string;
  timeToResolveHours: string;
  technician: string;
}
