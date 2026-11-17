import type { Criticality, Recommendation } from "./types";

export const CRITICALITY_LABEL: Record<Criticality, string> = {
  urgent: "▲ Urgent",
  priority: "● Priority",
  normal: "○ Normal",
};

export function CriticalityBadge({ value }: { value: Criticality }) {
  return <span className={`badge crit-${value}`}>{CRITICALITY_LABEL[value]}</span>;
}

function Origin({ origin }: { origin: "seed" | "field_enrichment" }) {
  return origin === "field_enrichment" ? <span className="badge field">Field-derived</span> : <span className="badge seed">SOP</span>;
}

export default function RecommendationsPanel({ rec }: { rec: Recommendation }) {
  if (rec.noRelevantKnowledge) {
    return (
      <div className="notice">
        <strong>No relevant knowledge found.</strong>
        <p>{rec.probableCause || "No matching SOP or past incident was found for this asset type."}</p>
        <p className="muted">Apply your judgement. Whatever fix you record below will help build the knowledge base.</p>
      </div>
    );
  }

  const isField = (section?: string | null) => (section ?? "").toLowerCase().startsWith("field");

  return (
    <div className="recs">
      <div className="row">
        <span className="muted">Suggested criticality</span>
        <CriticalityBadge value={rec.criticality.suggested} />
        <span className="muted small">{rec.criticality.basis}</span>
      </div>

      {rec.safetyWarnings.length > 0 && (
        <section className="warn">
          <h3>Safety</h3>
          <ul>{rec.safetyWarnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </section>
      )}

      {rec.probableCause && (
        <section>
          <h3>Probable cause</h3>
          <p>{rec.probableCause}</p>
        </section>
      )}

      <section>
        <h3>Recommended actions</h3>
        <ol>
          {rec.recommendedActions.map((a) => (
            <li key={a.order}>
              {a.text}
              {a.sopId && (
                <span className="cite">
                  {" "}[{a.sopId}{a.section ? ` · ${a.section}` : ""}]
                  {isField(a.section) && <span className="badge field">Field-derived</span>}
                </span>
              )}
            </li>
          ))}
        </ol>
      </section>

      {rec.pastHistory.length > 0 && (
        <section>
          <h3>Past history</h3>
          <ul className="history">
            {rec.pastHistory.map((h, i) => (
              <li key={i}>
                <strong>{h.ticketId ?? "Incident"}</strong>
                <span className="muted small"> {[h.assetId, h.date].filter(Boolean).join(" · ")}</span>
                <div>{h.summary}</div>
                {h.resolution && <div className="muted">Resolution: {h.resolution}</div>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {rec.sources.length > 0 && (
        <section>
          <h3>Sources</h3>
          <ul className="sources">
            {rec.sources.map((s, i) => (
              <li key={i}>
                <Origin origin={s.origin} /> {s.sopId} {s.section ? `· ${s.section}` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
