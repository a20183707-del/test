import {
  AlertCircle,
  ArrowRight,
  Settings,
  LoaderCircle,
  CheckCircle2,
} from "lucide-react";
import { useState } from "react";
import DocumentsPanel from "./components/DocumentsPanel";
import SchemaEditor from "./components/SchemaEditor";
import FlowPanel, { tokenTotal } from "./components/FlowPanel";
import ResultsPanel from "./components/ResultsPanel";
import SettingsDialog from "./components/SettingsDialog";
import { useWorkspace } from "./useWorkspace";
export default function App() {
  const workspace = useWorkspace(),
    [settings, setSettings] = useState(false),
    [reviewRequest, setReviewRequest] = useState(0);
  const {
    session,
    documents,
    selected,
    schema,
    batch,
    busy,
    running,
    error,
    notice,
    confirmed,
  } = workspace;
  const processed = batch?.results.length ?? 0,
    successful =
      batch?.results.filter((r) => r.status === "exitoso").length ?? 0,
    partial = batch?.results.filter((r) => r.status === "parcial").length ?? 0,
    failed = batch?.results.filter((r) => r.status === "fallido").length ?? 0;
  const rate = processed
    ? `${((successful / processed) * 100).toLocaleString("es-PE", { maximumFractionDigits: 1 })}%`
    : "Sin ejecutar";
  const result = batch?.results.find((r) => r.document_id === selected),
    blocked =
      busy ||
      running ||
      !session?.has_api_key ||
      !confirmed ||
      documents.length === 0;
  const nextStep = !documents.length
    ? "Carga o pega documentos para comenzar."
    : !schema.fields.length
      ? "Define sólo los campos que necesitas extraer."
      : !confirmed
        ? "Revisa y confirma los campos antes de analizar."
        : !session?.has_api_key
          ? "Configura Gemini para realizar el análisis."
          : "Todo listo para analizar con Gemini y el revisor.";
  return (
    <>
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">BSG</span>
          <span>Extractor documental</span>
        </div>
        <button onClick={() => setSettings(true)}>
          <Settings size={17} />
          Configurar Gemini
          {session?.has_api_key ? (
            <span className="key-dot" aria-label="Clave configurada" />
          ) : null}
        </button>
      </header>
      <main>
        <div className="intro">
          <h1>De documentos a datos verificables</h1>
          <p>
            Define los campos. Extrae con Gemini. Contrasta con un revisor
            independiente.
          </p>
        </div>
        <div className="overview">
          <button
            className="primary analyze-button"
            disabled={blocked}
            onClick={() => void workspace.analyze()}
          >
            {running ? (
              <LoaderCircle size={18} className="spin" />
            ) : (
              <ArrowRight size={18} />
            )}{" "}
            {running ? "Analizando lote…" : "Analizar documentos"}
          </button>
          <div className="metric">
            <span>Éxito del lote</span>
            <strong>{rate}</strong>
            {processed ? (
              <small>
                {successful} exitosos · {partial} parciales · {failed} fallidos
              </small>
            ) : null}
          </div>
          <div className="metric">
            <span>Documentos procesados</span>
            <strong>
              {processed}
              {batch ? ` / ${batch.metrics?.total ?? documents.length}` : ""}
            </strong>
          </div>
          <div className="metric">
            <span>Tokens de la sesión</span>
            <strong>
              {tokenTotal(
                batch?.session_usage ?? session?.total_usage,
                batch?.session_usage_history ?? session?.usage_history,
              )}
            </strong>
          </div>
        </div>
        <p className="next-step">
          {nextStep}
          {processed
            ? " Éxito = exitosos / procesados. No mide confianza ni exactitud."
            : ""}
        </p>
        {error || batch?.error ? (
          <div className="message error" role="alert">
            <AlertCircle size={18} />
            <span>{error || batch?.error}</span>
          </div>
        ) : null}
        {notice ? (
          <div className="message success" role="status">
            <CheckCircle2 size={18} />
            <span>{notice}</span>
          </div>
        ) : null}
        {batch?.supervision?.required ? (
          <div className="supervision-banner" role="alert">
            <AlertCircle size={20} />
            <div>
              <strong>Se necesita supervisión humana</strong>
              <p>{batch.supervision.reason}</p>
            </div>
            <button
              onClick={() => {
                const target = batch.results.find(
                  (r) => r.status !== "exitoso",
                );
                if (target) {
                  workspace.setSelected(target.document_id);
                  setReviewRequest((n) => n + 1);
                }
              }}
            >
              Supervisar resultados
            </button>
          </div>
        ) : null}
        <div className="workspace">
          <DocumentsPanel
            key={session?.csrf_token ?? "initial"}
            documents={documents}
            selected={selected}
            select={workspace.setSelected}
            upload={workspace.upload}
            paste={workspace.paste}
            remove={workspace.removeDocument}
            busy={busy || running}
            results={batch?.results ?? []}
          />
          <div className="center-column">
            <SchemaEditor
              schema={schema}
              update={workspace.updateSchema}
              confirmed={confirmed}
              busy={busy || running}
              confirm={workspace.confirm}
            />
            <ResultsPanel
              batch={batch}
              result={result}
              schema={batch?.schema ?? schema}
              onHumanReview={workspace.humanReview}
              busy={busy || running}
              reviewRequest={reviewRequest}
            />
          </div>
          <FlowPanel
            batch={batch}
            selected={selected}
            documents={documents}
            session={session}
          />
        </div>
      </main>
      <footer className="app-footer">
        Sesión local · Los archivos y resultados permanecen locales hasta que
        analizas con Gemini.
      </footer>
      {settings ? (
        <SettingsDialog
          session={session}
          busy={busy || running}
          close={() => setSettings(false)}
          save={workspace.saveKey}
          remove={workspace.removeKey}
          closeSession={workspace.closeSession}
          error={error}
        />
      ) : null}
    </>
  );
}
