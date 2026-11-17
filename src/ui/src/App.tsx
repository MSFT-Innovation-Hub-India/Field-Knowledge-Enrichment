import { useEffect, useRef, useState } from "react";
import { getEnrichmentStatus, getRecommendations, submitResolution } from "./api";
import RecommendationsPanel, { CRITICALITY_LABEL } from "./RecommendationsPanel";
import type { AssetType, Criticality, Recommendation, ResolutionForm, TicketForm } from "./types";

const today = () => new Date().toISOString().slice(0, 10);
const emptyTicket = (): TicketForm => ({ assetId: "", assetType: "battery", ticketId: "", issue: "", loggedDate: today() });
const emptyFix = (): ResolutionForm => ({ fixApplied: "", rootCause: "", partsReplaced: "", timeToResolveHours: "", technician: "" });

type RecState = { kind: "idle" } | { kind: "loading" } | { kind: "error"; message: string } | { kind: "ready"; rec: Recommendation };
type EnrichState = "none" | "submitting" | "checking" | "done" | "error";

export default function App() {
  const [ticket, setTicket] = useState<TicketForm>(emptyTicket);
  const [criticality, setCriticality] = useState<Criticality>("normal");
  const [recState, setRecState] = useState<RecState>({ kind: "idle" });
  const [fix, setFix] = useState<ResolutionForm>(emptyFix);
  const [enrich, setEnrich] = useState<EnrichState>("none");
  const [enrichError, setEnrichError] = useState("");
  const poll = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearInterval(poll.current), []);

  const ticketValid = [ticket.assetId, ticket.ticketId, ticket.issue, ticket.loggedDate].every((v) => v.trim().length > 0);
  const missing = [
    !ticket.assetId.trim() && "Asset ID",
    !ticket.ticketId.trim() && "Ticket ID",
    !ticket.loggedDate.trim() && "Date of issue logged",
    !ticket.issue.trim() && "Nature of issue",
  ].filter(Boolean) as string[];
  const fixValid = ticketValid && fix.fixApplied.trim().length > 0;

  const setT = <K extends keyof TicketForm>(k: K, v: TicketForm[K]) => setTicket((t) => ({ ...t, [k]: v }));
  const setF = <K extends keyof ResolutionForm>(k: K, v: ResolutionForm[K]) => setFix((f) => ({ ...f, [k]: v }));

  async function onRecommend() {
    setRecState({ kind: "loading" });
    try {
      const rec = await getRecommendations({ ...ticket, assetId: ticket.assetId.trim(), ticketId: ticket.ticketId.trim() });
      setCriticality(rec.criticality.suggested);
      setRecState({ kind: "ready", rec });
    } catch (e) {
      setRecState({ kind: "error", message: (e as Error).message });
    }
  }

  async function onSubmitFix() {
    setEnrich("submitting");
    setEnrichError("");
    try {
      const { jobId } = await submitResolution(ticket, criticality, fix);
      setEnrich("checking");
      const started = Date.now();
      window.clearInterval(poll.current);
      poll.current = window.setInterval(async () => {
        try {
          const { status } = await getEnrichmentStatus(jobId);
          if (status === "done") {
            window.clearInterval(poll.current);
            setEnrich("done");
          } else if (Date.now() - started > 180_000) {
            window.clearInterval(poll.current);
            setEnrich("done");
          }
        } catch {
          window.clearInterval(poll.current);
          setEnrich("done");
        }
      }, 2000);
    } catch (e) {
      setEnrich("error");
      setEnrichError((e as Error).message);
    }
  }

  function onNewTicket() {
    window.clearInterval(poll.current);
    setTicket(emptyTicket());
    setFix(emptyFix());
    setCriticality("normal");
    setRecState({ kind: "idle" });
    setEnrich("none");
  }

  return (
    <div className="page">
      <header>
        <h1>Field Knowledge Enrichment</h1>
        <p className="muted">Raise a ticket, get SOP-based recommendations, then record what actually fixed it.</p>
      </header>

      <div className="grid">
        <section className="card">
          <h2>Ticket</h2>
          <div className="field">
            <span className="lbl" id="asset-type-label">Asset type</span>
            <div className="segmented" role="radiogroup" aria-labelledby="asset-type-label">
              {(["battery", "station"] as AssetType[]).map((t) => (
                <button key={t} type="button" role="radio" aria-checked={ticket.assetType === t}
                  className={ticket.assetType === t ? "on" : ""} onClick={() => setT("assetType", t)}>
                  {t === "battery" ? "Battery" : "Station"}
                </button>
              ))}
            </div>
          </div>
          <label>Asset ID <span className="req">*</span>
            <input value={ticket.assetId} maxLength={64} onChange={(e) => setT("assetId", e.target.value)}
              placeholder={ticket.assetType === "battery" ? "e.g. INSMOMAH0809A061E913" : "e.g. WMQISXM1V1-02614"} />
          </label>
          <label>Ticket ID <span className="req">*</span>
            <input value={ticket.ticketId} maxLength={64} onChange={(e) => setT("ticketId", e.target.value)} placeholder="e.g. INC-2026-11201" />
          </label>
          <label>Date of issue logged
            <input type="date" value={ticket.loggedDate} onChange={(e) => setT("loggedDate", e.target.value)} />
          </label>
          <label>Nature of issue <span className="req">*</span>
            <textarea rows={5} maxLength={2000} value={ticket.issue} onChange={(e) => setT("issue", e.target.value)}
              placeholder="Describe what was observed, error codes, slot, readings…" />
          </label>
          <label>Criticality
            <select value={criticality} onChange={(e) => setCriticality(e.target.value as Criticality)}>
              {(Object.keys(CRITICALITY_LABEL) as Criticality[]).map((c) => <option key={c} value={c}>{CRITICALITY_LABEL[c]}</option>)}
            </select>
          </label>
          <div className="actions">
            <button className="primary" disabled={!ticketValid || recState.kind === "loading"} onClick={onRecommend}>
              {recState.kind === "loading" ? "Getting recommendations…" : "Get recommendations"}
            </button>
            <button type="button" onClick={onNewTicket}>New ticket</button>
          </div>
          {!ticketValid && <p className="hint">Required to continue: {missing.join(", ")}.</p>}
        </section>

        <section className="card">
          <h2>Recommendations</h2>
          {recState.kind === "idle" && <p className="muted">Fill in the ticket and choose <em>Get recommendations</em>. Recommended actions, past history and sources appear here.</p>}
          {recState.kind === "loading" && <div className="loading"><span className="spinner" /> Searching the knowledge base…</div>}
          {recState.kind === "error" && (
            <div className="error" role="alert">
              {recState.message}
              <div><button onClick={onRecommend}>Retry</button></div>
            </div>
          )}
          {recState.kind === "ready" && <RecommendationsPanel rec={recState.rec} />}
        </section>
      </div>

      <section className="card fix">
        <h2>Fix applied</h2>
        <p className="muted">Record what actually fixed the issue. Your input helps improve the knowledge base for the next technician.</p>
        <label>Fixes applied
          <textarea rows={5} maxLength={4000} value={fix.fixApplied} onChange={(e) => setF("fixApplied", e.target.value)}
            placeholder="What did you find, replace, measure or change? What was the outcome?" />
        </label>
        <div className="row3">
          <label>Root cause <span className="muted">(optional)</span>
            <input value={fix.rootCause} maxLength={1000} onChange={(e) => setF("rootCause", e.target.value)} />
          </label>
          <label>Parts replaced <span className="muted">(optional)</span>
            <input value={fix.partsReplaced} maxLength={500} onChange={(e) => setF("partsReplaced", e.target.value)} />
          </label>
          <label>Time to resolve, hours <span className="muted">(optional)</span>
            <input type="number" min={0} step={0.25} value={fix.timeToResolveHours} onChange={(e) => setF("timeToResolveHours", e.target.value)} />
          </label>
        </div>
        <div className="actions">
          <button className="primary" disabled={!fixValid || enrich === "submitting" || enrich === "checking"} onClick={onSubmitFix}>
            Submit resolution
          </button>
          {enrich === "submitting" && <span className="status"><span className="spinner" /> Saving…</span>}
          {enrich === "checking" && <span className="status" role="status"><span className="spinner" /> Ticket saved. Checking whether this can enrich the knowledge base…</span>}
          {enrich === "done" && <span className="status ok" role="status">✓ Done. Thank you.</span>}
          {enrich === "error" && <span className="status bad" role="alert">{enrichError || "Could not save. Please try again."}</span>}
        </div>
      </section>
    </div>
  );
}
