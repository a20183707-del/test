import { FileText, Upload, Plus, Trash2 } from "lucide-react";
import { useRef, useState } from "react";
import type { DocumentResult, SourceDocument } from "../types";
interface Props {
  documents: SourceDocument[];
  selected: string;
  select: (id: string) => void;
  upload: (files: FileList | File[]) => Promise<boolean>;
  paste: (name: string, text: string) => Promise<boolean>;
  remove: (id: string) => Promise<boolean>;
  busy: boolean;
  results: DocumentResult[];
}
export default function DocumentsPanel({
  documents,
  selected,
  select,
  upload,
  paste,
  remove,
  busy,
  results,
}: Props) {
  const input = useRef<HTMLInputElement>(null),
    [pasting, setPasting] = useState(false),
    [text, setText] = useState(""),
    [name, setName] = useState("Texto libre"),
    [dragging, setDragging] = useState(false);
  const document = documents.find((d) => d.id === selected);
  return (
    <section
      className="panel documents-panel"
      aria-label="Documentos de entrada"
    >
      <div className="section-title">
        <h2>1. Documentos</h2>
        <span className="count">{documents.length}</span>
      </div>
      <div className="button-pair">
        <button disabled={busy} onClick={() => input.current?.click()}>
          <Upload size={16} />
          Cargar archivos
        </button>
        <button disabled={busy} onClick={() => setPasting(!pasting)}>
          <FileText size={16} />
          Pegar texto
        </button>
      </div>
      <input
        ref={input}
        type="file"
        multiple
        accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp"
        className="visually-hidden"
        aria-label="Seleccionar documentos"
        onChange={(e) => {
          if (e.target.files?.length) void upload(e.target.files);
          e.target.value = "";
        }}
      />
      {pasting ? (
        <form
          className="paste-form"
          onSubmit={async (e) => {
            e.preventDefault();
            if (await paste(name, text)) {
              setText("");
              setPasting(false);
            }
          }}
        >
          <label>
            Nombre del documento
            <input
              value={name}
              maxLength={120}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label>
            Contenido
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              required
              maxLength={300000}
              rows={7}
              placeholder="Pega un contrato, correo, CV u otro texto…"
            />
          </label>
          <button className="primary" disabled={busy || !text.trim()}>
            <Plus size={16} />
            Agregar documento
          </button>
        </form>
      ) : null}
      {documents.length === 0 ? (
        <div
          className={`dropzone ${dragging ? "dragging" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            if (!busy && e.dataTransfer.files.length)
              void upload(e.dataTransfer.files);
          }}
        >
          <Upload size={30} />
          <strong>Arrastra tus documentos aquí</strong>
          <span>PDF, DOCX, TXT o imágenes</span>
          <small>Hasta 12 MiB por archivo. Cualquier dominio.</small>
        </div>
      ) : (
        <ul className="document-list">
          {documents.map((d) => {
            const result = results.find((r) => r.document_id === d.id);
            return (
              <li key={d.id}>
                <button
                  className={`document-row ${d.id === selected ? "selected" : ""}`}
                  onClick={() => select(d.id)}
                >
                  <FileText size={18} />
                  <span>
                    <strong>{d.name}</strong>
                    <small>
                      {d.mime.split("/").pop()} · {(d.size / 1024).toFixed(1)}{" "}
                      KB
                    </small>
                  </span>
                  <span className={`status ${result?.status ?? ""}`}>
                    {result?.status ?? "En espera"}
                  </span>
                </button>
                <button
                  className="icon-button remove-document"
                  aria-label={`Eliminar ${d.name}`}
                  disabled={busy}
                  onClick={() => void remove(d.id)}
                >
                  <Trash2 size={14} />
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <div className="original">
        <h3>Documento original</h3>
        {!document ? (
          <div className="empty source-empty">
            <FileText size={36} />
            <p>Carga el primer documento.</p>
          </div>
        ) : (
          <>
            <p className="source-name">{document.name}</p>
            {document.mime.startsWith("image/") ? (
              <img
                src={
                  document.preview_url ?? `/api/documents/${document.id}/source`
                }
                alt={`Documento original: ${document.name}`}
                className="source-image"
              />
            ) : document.mime === "application/pdf" ? (
              <>
                <iframe
                  title="PDF original"
                  src={
                    document.preview_url ??
                    `/api/documents/${document.id}/source`
                  }
                />
                <a
                  href={`/api/documents/${document.id}/source`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Abrir PDF original
                </a>
                <p className="help">
                  La vista PDF utiliza el visor del navegador.
                </p>
                {document.text ? (
                  <details>
                    <summary>Texto leído del PDF</summary>
                    <pre className="source-text">{document.text}</pre>
                  </details>
                ) : null}
              </>
            ) : (
              <>
                {document.mime.includes("wordprocessingml") ? (
                  <p className="help">
                    Texto leído del DOCX, sin formato.{" "}
                    <a
                      href={`/api/documents/${document.id}/source?download=true`}
                      download
                    >
                      Descargar original
                    </a>
                  </p>
                ) : null}
                <pre className="source-text">
                  {document.text ?? "El texto de la fuente no está disponible."}
                </pre>
              </>
            )}
            {document.warnings.map((w, i) => (
              <p className="inline-warning" key={i}>
                {w}
              </p>
            ))}
          </>
        )}
      </div>
      {documents.length ? (
        <p className="privacy-note">
          Los documentos se eliminan al cerrar la sesión desde Configuración o
          tras 60 minutos de inactividad.
        </p>
      ) : null}
    </section>
  );
}
