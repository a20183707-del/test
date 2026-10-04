import { Check, LoaderCircle, CircleAlert } from "lucide-react";
import type {
  Batch,
  ProviderCall,
  Session,
  SourceDocument,
  TokenUsage,
} from "../types";
const stages = [
  ["reading", "Lectura"],
  ["extracting", "Extracción"],
  ["validating", "Validación"],
  ["reviewing", "Revisor"],
  ["completed", "Resultado"],
];
const number = (value: unknown) =>
  typeof value === "number" ? value.toLocaleString("es-PE") : "—";
export const tokenTotal = (
  usage: TokenUsage | undefined,
  entries: ProviderCall[] = [],
) => {
  if (usage?.total_tokens != null)
    return `${usage.complete === false ? "≥ " : ""}${number(usage.total_tokens)}`;
  const measured = entries.filter(
    (entry) => entry.status !== "not_sent" && entry.usage.total_tokens != null,
  );
  return measured.length
    ? `≥ ${number(measured.reduce((total, entry) => total + (entry.usage.total_tokens ?? 0), 0))}`
    : "—";
};
const roles = {
  extraction: "Extracción",
  review: "Revisor",
  verification: "Comprobación",
};
function TokenHistory({
  entries,
  documents,
}: {
  entries: ProviderCall[];
  documents: SourceDocument[];
}) {
  let cumulative = 0,
    missing = false,
    known = false;
  return (
    <div className="token-history">
      <h3>Histórico de la sesión</h3>
      {entries.length ? (
        <ol>
          {entries.map((entry) => {
            if (
              entry.status !== "not_sent" &&
              entry.usage.total_tokens != null
            ) {
              cumulative += entry.usage.total_tokens;
              known = true;
            }
            if (entry.status !== "not_sent" && !entry.usage.complete)
              missing = true;
            const total = cumulative;
            const incomplete = missing;
            const measured = known;
            return (
              <li key={entry.id}>
                <details>
                  <summary>
                    <span>
                      <strong>{roles[entry.role]}</strong>
                      <small>
                        Intento {entry.attempt} ·{" "}
                        {new Date(entry.started_at).toLocaleTimeString("es-PE")}
                      </small>
                    </span>
                    <span>
                      {tokenTotal(entry.usage)}
                      <small>
                        Acum.{" "}
                        {measured
                          ? (incomplete ? "≥ " : "") +
                            total.toLocaleString("es-PE")
                          : "—"}
                      </small>
                    </span>
                  </summary>
                  <p>
                    {documents.find((d) => d.id === entry.document_id)?.name ??
                      entry.document_id}
                  </p>
                  <p>
                    {entry.model} · {entry.elapsed_ms} ms
                  </p>
                  <p>
                    Entrada: {number(entry.usage.input_tokens)} · Salida:{" "}
                    {number(entry.usage.output_tokens)} · Razonamiento:{" "}
                    {number(entry.usage.thinking_tokens)} · Caché:{" "}
                    {number(entry.usage.cached_tokens)}
                  </p>
                  <p>
                    {entry.status === "not_sent"
                      ? "Solicitud no enviada"
                      : entry.status === "error"
                        ? `Error: ${entry.error_code ?? "proveedor"}`
                        : "Respuesta recibida"}
                    {!entry.usage.complete && entry.status !== "not_sent"
                      ? " · Conteo incompleto o no informado por el proveedor."
                      : ""}
                  </p>
                </details>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="help">Aún no hay llamadas registradas.</p>
      )}
    </div>
  );
}
export default function FlowPanel({
  batch,
  selected,
  documents,
  session,
}: {
  batch: Batch | null;
  selected: string;
  documents: SourceDocument[];
  session: Session | null;
}) {
  const events = batch?.events.filter((e) => e.document_id === selected) ?? [],
    last = events.at(-1),
    result = batch?.results.find((r) => r.document_id === selected);
  const source = documents.find((d) => d.id === selected);
  const estimate =
    source?.text && source.mime !== "application/pdf"
      ? Math.ceil(source.text.length / 4)
      : null;
  const index = stages.findIndex(([id]) => id === last?.stage),
    reattempts = events.filter((e) => e.stage === "retrying");
  const usage = batch?.session_usage ?? session?.total_usage;
  const history =
    batch?.session_usage_history ??
    session?.usage_history ??
    batch?.usage_history ??
    [];
  const calls =
    batch?.usage_history?.filter((call) => call.document_id === selected) ?? [];
  const extractionFailed =
    calls.filter((call) => call.role === "extraction").at(-1)?.status ===
    "error";
  const reviewFailed =
    calls.filter((call) => call.role !== "extraction").at(-1)?.status ===
    "error";
  return (
    <aside className="rail">
      <section className="panel flow-panel">
        <h2>Flujo de análisis</h2>
        <ol className="stepper">
          {stages.map(([id, label], i) => {
            const visited = events.some((e) => e.stage === id);
            const active = !result && id === last?.stage;
            const done = visited && (!!result || index > i);
            const failed =
              !!result &&
              visited &&
              ((id === "extracting" && extractionFailed) ||
                (id === "reviewing" && reviewFailed));
            return (
              <li
                key={id}
                className={`${done ? "done" : ""} ${active ? "active" : ""} ${failed ? "step-error" : ""}`}
              >
                <span className="step-dot">
                  {failed ? (
                    <CircleAlert size={16} />
                  ) : done ? (
                    <Check size={16} />
                  ) : active ? (
                    <LoaderCircle size={16} className="spin" />
                  ) : (
                    i + 1
                  )}
                </span>
                <div>
                  <strong>{label}</strong>
                  <small>
                    {failed
                      ? "Terminó con error"
                      : active
                        ? "En curso"
                        : done
                          ? id === "completed"
                            ? "Terminado"
                            : "Ejecutado"
                          : result
                            ? "No ejecutado"
                            : "En espera"}
                  </small>
                </div>
              </li>
            );
          })}
        </ol>
        {reattempts.length ? (
          <div className="retry-info">
            <CircleAlert size={16} />
            {reattempts.length} reintento(s) registrado(s)
          </div>
        ) : null}
        {last ? (
          <p className="flow-detail" aria-live="polite">
            {last.detail}
          </p>
        ) : null}
        {result ? (
          <span className={`status ${result.status}`}>
            {result.status === "exitoso"
              ? "Extracción exitosa"
              : result.status === "parcial"
                ? "Revisión humana requerida"
                : "No se pudo procesar"}
          </span>
        ) : null}
      </section>
      <section className="panel tokens-panel">
        <h2>Consumo de tokens</h2>
        <dl>
          <div>
            <dt>Estimación del texto de entrada</dt>
            <dd>{number(estimate)}</dd>
          </div>
          <div>
            <dt>Acumulado real de la sesión</dt>
            <dd aria-live="polite">{tokenTotal(usage, history)}</dd>
          </div>
          <div>
            <dt>Consumo del lote actual</dt>
            <dd className="small-number">
              {tokenTotal(batch?.usage, batch?.usage_history)}
            </dd>
          </div>
        </dl>
        <p className="help">
          Se actualiza al finalizar cada llamada. «≥» indica consumo
          parcialmente informado. La estimación (caracteres ÷ 4) sólo incluye el
          texto, excluye instrucciones, esquema, revisión y reintentos. PDF e
          imágenes requieren conteo del proveedor.
        </p>
        <TokenHistory entries={history} documents={documents} />
        <details className="limits-details">
          <summary>Límites del proceso</summary>
          <p>
            Máximo 3 extracciones y 6 llamadas del revisor por documento. Se
            conserva cada intento. Una falla no detiene el lote.
          </p>
        </details>
      </section>
      {events.length ? (
        <details className="panel event-log">
          <summary>Eventos del documento ({events.length})</summary>
          {events.map((event, i) => (
            <p key={i}>
              <time>
                {new Date(event.timestamp).toLocaleTimeString("es-PE")}
              </time>{" "}
              · {event.detail}
            </p>
          ))}
        </details>
      ) : null}
    </aside>
  );
}
