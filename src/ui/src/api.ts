import type { Criticality, Recommendation, ResolutionForm, TicketForm } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = "Please check the form: " + body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch { /* keep default */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const getRecommendations = (t: TicketForm) =>
  request<Recommendation>("/api/recommendations", { method: "POST", body: JSON.stringify(t) });

export const submitResolution = (t: TicketForm, criticality: Criticality, r: ResolutionForm) =>
  request<{ jobId: string; status: string }>(`/api/tickets/${encodeURIComponent(t.ticketId)}/resolution`, {
    method: "POST",
    body: JSON.stringify({
      assetId: t.assetId,
      assetType: t.assetType,
      issue: t.issue,
      loggedDate: t.loggedDate,
      criticality,
      fixApplied: r.fixApplied,
      rootCause: r.rootCause,
      partsReplaced: r.partsReplaced,
      timeToResolveHours: r.timeToResolveHours === "" ? null : Number(r.timeToResolveHours),
      technician: r.technician,
    }),
  });

export const getEnrichmentStatus = (jobId: string) =>
  request<{ status: "checking" | "done" }>(`/api/enrichment/${jobId}`);
