import { useEffect, useRef, useState } from "react";
import { KeyRound, X } from "lucide-react";
import type { Session } from "../types";
interface Props {
  session: Session | null;
  busy: boolean;
  close: () => void;
  save: (key: string, models: Session["models"]) => Promise<boolean>;
  remove: () => Promise<boolean>;
  closeSession: () => Promise<boolean>;
  error: string;
}
export default function SettingsDialog({
  session,
  busy,
  close,
  save,
  remove,
  closeSession,
  error,
}: Props) {
  const dialog = useRef<HTMLDialogElement>(null),
    key = useRef<HTMLInputElement>(null),
    [models, setModels] = useState(
      session?.models ?? {
        extractor: "gemini-3.5-flash-lite",
        reviewer: "gemini-3.8-flash",
      },
    );
  useEffect(() => {
    dialog.current?.showModal();
    return () => {
      dialog.current?.close();
    };
  }, []);
  return (
    <dialog ref={dialog} onCancel={close} className="settings-dialog">
      <div className="dialog-heading">
        <h2>
          <KeyRound size={20} />
          Configurar Gemini
        </h2>
        <button
          className="icon-button"
          aria-label="Cerrar configuración"
          onClick={close}
        >
          <X size={20} />
        </button>
      </div>
      <p>
        La clave se entrega al servidor local y permanece en memoria durante la
        sesión.
      </p>
      {error ? (
        <p role="alert" className="inline-warning">
          {error}
        </p>
      ) : null}
      <form
        autoComplete="off"
        onSubmit={async (e) => {
          e.preventDefault();
          const input = key.current;
          const value = input?.value ?? "";
          if (input) input.value = "";
          if (await save(value, models)) close();
        }}
      >
        <label>
          API key
          <input
            ref={key}
            type="password"
            autoComplete="new-password"
            placeholder={
              session?.has_api_key
                ? "Ya hay una clave en la sesión"
                : "Ingresa tu API key de Gemini"
            }
            spellCheck={false}
            required
            maxLength={256}
          />
        </label>
        <p className="help">
          No se guarda en Git, archivos, registros ni en el almacenamiento del
          navegador.
        </p>
        <details>
          <summary>Modelos y límites</summary>
          <label>
            Extractor
            <input
              value={models.extractor}
              required
              onChange={(e) =>
                setModels({ ...models, extractor: e.target.value })
              }
            />
          </label>
          <label>
            Revisor independiente
            <input
              value={models.reviewer}
              required
              onChange={(e) =>
                setModels({ ...models, reviewer: e.target.value })
              }
            />
          </label>
          <p className="help">
            Contextos nuevos, sin historial compartido. Hasta 3 extracciones y 6
            llamadas de revisión por documento. La disponibilidad del modelo se
            comprueba al llamar al proveedor.
          </p>
        </details>
        <div className="dialog-actions">
          <button type="submit" className="primary" disabled={busy}>
            Guardar en memoria
          </button>
          {session?.has_api_key ? (
            <button
              type="button"
              disabled={busy}
              onClick={async () => {
                if (await remove()) close();
              }}
            >
              Eliminar clave de sesión
            </button>
          ) : null}
        </div>
      </form>
      <button
        disabled={busy}
        onClick={async () => {
          if (await closeSession()) close();
        }}
      >
        Cerrar y borrar sesión
      </button>
      <p className="help">
        Los documentos analizados se envían a Gemini. La revisión no certifica
        autenticidad ni ejecuta acciones externas.
      </p>
    </dialog>
  );
}
