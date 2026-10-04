import { Download, FileCheck, Save } from "lucide-react";
import { useEffect, useState } from "react";
import type { Batch, DocumentResult, ExtractionSchema, HumanReview } from "../types";
const printable = (value: unknown) =>
  value === null
    ? "null"
    : typeof value === "string"
      ? value
      : JSON.stringify(value);
const reviewLabels: Record<string, string> = {
  approved: "Aprobado",
  needs_review: "Revisión humana",
  rejected: "Rechazado",
  supported: "Sustentado",
  missing: "Ausente",
  contradicted: "Contradictorio",
  uncertain: "Incierto",
};
export default function ResultsPanel({
  batch,
  result,
  schema,
  onHumanReview,
  busy,
  reviewRequest,
}: {
  batch: Batch | null;
  result: DocumentResult | undefined;
  schema: ExtractionSchema;
  onHumanReview: (
    data: Record<string, unknown>,
    note: string,
  ) => Promise<HumanReview>;
  busy: boolean;
  reviewRequest: number;
}) {
  const [tab, setTab] = useState("Datos obtenidos"),
    [editing, setEditing] = useState(false),
    [correction, setCorrection] = useState(""),
    [note, setNote] = useState(""),
    [localError, setLocalError] = useState(""),
    [savedMessage, setSavedMessage] = useState("");
  useEffect(() => {
    setEditing(false);
    setCorrection(JSON.stringify(result?.record ?? Object.fromEntries(schema.fields.map((field) => [field.name, null])), null, 2));
    setNote("");
    setLocalError("");
    setSavedMessage("");
  }, [result?.document_id, schema.fields]);
  useEffect(() => {
    if (reviewRequest) {
      setTab("Revisor");
      setEditing(true);
      document
        .querySelector(".results-panel")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [reviewRequest]);
  const save = async () => {
    setLocalError("");
    setSavedMessage("");
    try {
      if (note.trim().length < 3)
        throw new Error("Escribe un motivo y evidencia de al menos 3 caracteres para registrar la revisión.");
      const data: unknown = JSON.parse(correction);
      if (data === null || Array.isArray(data) || typeof data !== "object")
        throw new Error("La corrección debe ser un objeto JSON.");
      const review = await onHumanReview(data as Record<string, unknown>, note);
      setSavedMessage(`Revisión registrada · ${review.id}. Consulta la auditoría debajo.`);
      setEditing(false);
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : "JSON inválido.");
    }
  };
  const verdict = result?.reviewer_verdict;
  const humanReviews = batch?.human_reviews?.filter((review) => review.document_id === result?.document_id) ?? [];
  return (
    <section
      className="panel results-panel"
      aria-label="Resultados de extracción"
    >
      <div className="result-top">
        <div className="tabs" role="tablist">
          {["Datos obtenidos", "Revisor", "Intentos", "JSON"].map((label) => (
            <button
              key={label}
              id={`tab-${label}`}
              role="tab"
              aria-selected={tab === label}
              aria-controls="result-content"
              tabIndex={tab === label ? 0 : -1}
              onKeyDown={(e) => {
                const tabs = ["Datos obtenidos", "Revisor", "Intentos", "JSON"];
                if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                  e.preventDefault();
                  const next =
                    tabs[
                      (tabs.indexOf(tab) + (e.key === "ArrowRight" ? 1 : 3)) % 4
                    ];
                  setTab(next);
                  document.getElementById(`tab-${next}`)?.focus();
                }
              }}
              onClick={() => setTab(label)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div id="result-content" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {!result ? (
          <div className="empty result-empty">
            <FileCheck size={32} />
            <p>
              {batch?.status === "running"
                ? "Analizando documentos…"
                : "Los resultados aparecerán aquí."}
            </p>
            <small>
              {batch?.status === "running"
                ? "Los estados se actualizan con eventos del servidor."
                : "Confirma los campos y analiza el lote."}
            </small>
          </div>
        ) : (
          <>
            <div className="result-summary">
              <span className={`status ${result.status}`}>{result.status}</span>
              <span>
                {result.attempts} intento(s) · {result.review_calls} llamada(s)
                de revisión
              </span>
            </div>
            {tab === "Datos obtenidos" ? (
              <>
                <div className="result-table-wrap">
                  <table className="result-table">
                    <thead>
                      <tr>
                        <th>Campo</th>
                        <th>Valor</th>
                        <th>Evidencia del revisor</th>
                      </tr>
                    </thead>
                    <tbody>
                      {schema.fields.map((field) => {
                        const review = verdict?.fields.find(
                          (f) => f.field === field.name,
                        );
                        return (
                          <tr key={field.name}>
                            <th scope="row">{field.name}</th>
                            <td>
                              <code
                                className={
                                  result.record?.[field.name] === null
                                    ? "null-value"
                                    : ""
                                }
                              >
                                {result.record
                                  ? printable(result.record[field.name])
                                  : "—"}
                              </code>
                            </td>
                            <td>
                              {review?.evidence ?? "Sin evidencia verificable"}
                              {review?.location ? (
                                <small>{review.location}</small>
                              ) : null}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <ul className="reasons">
                  {result.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </>
            ) : null}
            {tab === "Revisor" ? (
              verdict ? (
                <div className="review-findings">
                  <h3>{reviewLabels[verdict.decision] ?? verdict.decision}</h3>
                  <p>{verdict.reason}</p>
                  {verdict.fields.map((field, i) => (
                    <details key={i} open={field.status !== "supported"}>
                      <summary>
                        <strong>{field.field}</strong>
                        <span className={`review-status ${field.status}`}>
                          {reviewLabels[field.status] ?? field.status}
                        </span>
                      </summary>
                      <dl>
                        <div>
                          <dt>Dato obtenido</dt>
                          <dd>
                            <code>
                              {printable(result.record?.[field.field] ?? null)}
                            </code>
                          </dd>
                        </div>
                        <div>
                          <dt>Evidencia y ubicación</dt>
                          <dd>
                            {field.evidence ?? "Sin evidencia"} ·{" "}
                            {field.location ?? "Sin ubicación"}
                          </dd>
                        </div>
                        <div>
                          <dt>Comprobación neutral</dt>
                          <dd>{field.verification_question}</dd>
                        </div>
                        {field.problem ? (
                          <div>
                            <dt>Problema · {field.severity}</dt>
                            <dd>{field.problem}</dd>
                          </div>
                        ) : null}
                        {field.status !== "supported" ? (
                          <div>
                            <dt>Propuesta (sin aplicar)</dt>
                            <dd>
                              <code>{printable(field.proposed_value)}</code>
                            </dd>
                          </div>
                        ) : null}
                      </dl>
                    </details>
                  ))}
                </div>
              ) : (
                <p className="help">
                  El revisor no pudo completar una revisión válida. Consulta los
                  motivos.
                </p>
              )
            ) : null}
            {tab === "Intentos" ? (
              <ol className="attempts">
                {result.attempt_log.map((attempt, i) => (
                  <li key={i}>
                    <h3>
                      Intento {attempt.attempt} <span>{attempt.outcome}</span>
                    </h3>
                    {attempt.error_type ? (
                      <p className="inline-warning">{attempt.error_type}</p>
                    ) : null}
                    {attempt.messages?.map((m, j) => (
                      <p key={j}>{m}</p>
                    ))}
                    <details>
                      <summary>Versión y comprobaciones registradas</summary>
                      <pre>{JSON.stringify(attempt, null, 2)}</pre>
                    </details>
                  </li>
                ))}
              </ol>
            ) : null}
            {tab === "JSON" ? (
              <pre className="json-output">
                {JSON.stringify(result.record, null, 2)}
              </pre>
            ) : null}
            {result.human_review_required && batch?.status === "completed" ? (
              <div className="human-review">
                <button onClick={() => { setEditing(!editing); setLocalError(""); setSavedMessage(""); }} disabled={busy}>
                  {editing ? "Cerrar revisión" : "Registrar revisión humana"}
                </button>
                {editing ? (
                  <div>
                    <label>
                      Corrección propuesta (JSON)
                      <textarea
                        rows={8}
                        value={correction}
                        onChange={(e) => setCorrection(e.target.value)}
                      />
                    </label>
                    <label>
                      Motivo y evidencia (obligatorio)
                      <textarea
                        rows={2}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        maxLength={2000}
                        disabled={busy}
                      />
                    </label>
                    <p className="help">
                      La corrección se valida y se registra aparte. La tasa
                      automática y las versiones se conservan. Escribe un motivo de al menos 3 caracteres.
                    </p>
                    {localError ? (
                      <p role="alert" className="inline-warning">
                        {localError}
                      </p>
                    ) : null}
                    <button
                      className="primary"
                      disabled={busy}
                      onClick={() => void save()}
                    >
                      <Save size={16} />
                      {busy ? "Registrando…" : "Registrar revisión"}
                    </button>
                  </div>
                ) : null}
              </div>
            ) : null}
            {savedMessage ? <p className="review-confirmation" role="status">{savedMessage}</p> : null}
            {humanReviews.length ? (
              <section className="human-audit" aria-label="Auditoría de revisiones humanas">
                <h3>Auditoría humana · {humanReviews.length} revisión(es)</h3>
                <p className="help">Registro de esta sesión. Descarga el reporte JSON o CSV para conservarlo al cerrar o reiniciar.</p>
                {humanReviews.map((review, index) => (
                <details className="human-history" key={review.id} open={index === humanReviews.length - 1}>
                  <summary>
                    Revisión humana ·{" "}
                    {new Date(review.timestamp).toLocaleString("es-PE")} ·{" "}
                    {review.validation.status}
                  </summary>
                  <p className="review-receipt">ID: {review.id} · Autor: {review.actor}</p>
                  <p>{review.note}</p>
                  <h4>Resultado automático original</h4>
                  <pre>{JSON.stringify(review.original_record, null, 2)}</pre>
                  <h4>Corrección humana registrada</h4>
                  <pre>{JSON.stringify(review.proposed_record, null, 2)}</pre>
                  {review.validation.reasons.length ? <ul className="reasons">{review.validation.reasons.map((reason, i) => <li key={i}>{reason}</li>)}</ul> : null}
                </details>
                ))}
              </section>
            ) : null}
          </>
        )}
      </div>
      {batch?.status === "completed" ? (
        <div className="export-row">
          <span>Reporte del lote</span>
          <a
            className="button"
            href={`/api/batches/${batch.id}/export?format=json`}
            download
          >
            <Download size={15} />
            JSON
          </a>
          <a
            className="button"
            href={`/api/batches/${batch.id}/export?format=csv`}
            download
          >
            <Download size={15} />
            CSV
          </a>
        </div>
      ) : null}
    </section>
  );
}
