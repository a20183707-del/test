import { useCallback, useEffect, useState } from "react";
import { initializeSession, post, request } from "./api";
import type { Batch, ExtractionSchema, Session, SourceDocument } from "./types";
export function useWorkspace() {
  const [session, setSession] = useState<Session | null>(null),
    [documents, setDocuments] = useState<SourceDocument[]>([]),
    [selected, setSelected] = useState("");
  const [schema, setSchema] = useState<ExtractionSchema>({
      title: "Extracción personalizada",
      fields: [],
    }),
    [confirmed, setConfirmed] = useState(false),
    [batch, setBatch] = useState<Batch | null>(null);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    const raw = await request<
      SourceDocument[] | { documents: SourceDocument[] }
    >("/api/documents");
    const docs = Array.isArray(raw) ? raw : raw.documents;
    setDocuments(docs);
    setSelected((prev) =>
      docs.some((d) => d.id === prev) ? prev : (docs[0]?.id ?? ""),
    );
  }, []);
  useEffect(() => {
    let live = true;
    initializeSession()
      .then(async (s) => {
        if (live) {
          setSession(s);
          if (s.schema) {
            setSchema(s.schema);
            setConfirmed(true);
          }
          if (s.latest_batch_id)
            setBatch(await request<Batch>(`/api/batches/${s.latest_batch_id}`));
        }
        return refresh();
      })
      .catch((e) => {
        if (live) setError(e.message);
      });
    return () => {
      live = false;
    };
  }, [refresh]);
  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ocurrió un error.");
      return false;
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    if (!batch || batch.status !== "running") return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const next = await request<Batch>(`/api/batches/${batch.id}`);
        if (!stopped) {
          setBatch(next);
          if (next.status === "running") timer = setTimeout(poll, 700);
        }
      } catch (e) {
        if (!stopped) {
          setError(
            e instanceof Error ? e.message : "No se pudo actualizar el lote.",
          );
          timer = setTimeout(poll, 2500);
        }
      }
    };
    timer = setTimeout(poll, 300);
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [batch?.id, batch?.status]);
  const upload = (files: FileList | File[]) =>
    run(async () => {
      const form = new FormData();
      Array.from(files).forEach((file) => form.append("files", file));
      await request("/api/documents", { method: "POST", body: form });
      await refresh();
      setNotice("Documentos cargados. Aún no se han enviado a Gemini.");
    });
  const paste = (name: string, text: string) =>
    run(async () => {
      await post("/api/documents/text", { name, text });
      await refresh();
      setNotice("Texto agregado como documento.");
    });
  const updateSchema = (value: ExtractionSchema) => {
    setSchema(value);
    setConfirmed(false);
  };
  const confirm = () =>
    run(async () => {
      await request("/api/schema", {
        method: "PUT",
        body: JSON.stringify({ schema }),
      });
      setConfirmed(true);
      setNotice("Esquema confirmado. Puedes analizar el lote.");
    });
  const analyze = () =>
    run(async () => {
      const created = await post<Partial<Batch> & { id: string }>(
        "/api/batches",
        { document_ids: documents.map((d) => d.id), schema, max_attempts: 3 },
      );
      setBatch({
        status: "running",
        mode: "gemini",
        events: [],
        results: [],
        metrics: null,
        usage: {},
        ...created,
      });
    });
  const saveKey = (api_key: string, models: Session["models"]) =>
    run(async () => {
      await post("/api/key", { api_key, ...models });
      setSession(await initializeSession());
      setNotice("Credencial disponible en la memoria de esta sesión.");
    });
  const removeKey = () =>
    run(async () => {
      await request("/api/key", { method: "DELETE" });
      setSession(await initializeSession());
      setNotice("Credencial de sesión eliminada.");
    });
  const humanReview = (corrected_data: Record<string, unknown>, note: string) =>
    run(async () => {
      if (!batch) return;
      await post(`/api/batches/${batch.id}/review`, {
        document_id: selected,
        corrected_data,
        note,
      });
      setBatch(await request<Batch>(`/api/batches/${batch.id}`));
      setNotice(
        "Revisión humana registrada; se conserva el resultado automático.",
      );
    });
  const removeDocument = (id: string) =>
    run(async () => {
      await request(`/api/documents/${id}`, { method: "DELETE" });
      await refresh();
    });
  const closeSession = () =>
    run(async () => {
      await request("/api/session", { method: "DELETE" });
      setSession(await initializeSession());
      setDocuments([]);
      setSelected("");
      setBatch(null);
      setSchema({ title: "Extracción personalizada", fields: [] });
      setConfirmed(false);
      setNotice(
        "Sesión cerrada. Clave, documentos y resultados eliminados de memoria.",
      );
    });
  return {
    session,
    documents,
    selected,
    setSelected,
    schema,
    updateSchema,
    confirmed,
    batch,
    error,
    notice,
    busy,
    running: batch?.status === "running",
    upload,
    paste,
    confirm,
    analyze,
    saveKey,
    removeKey,
    humanReview,
    removeDocument,
    closeSession,
  };
}
