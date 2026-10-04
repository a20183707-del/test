import { Plus, Trash2, Check } from "lucide-react";
import type { ExtractionSchema, FieldSpec, FieldType } from "../types";
interface Props {
  schema: ExtractionSchema;
  update: (schema: ExtractionSchema) => void;
  confirmed: boolean;
  busy: boolean;
  confirm: () => Promise<boolean>;
}
const typeLabels: Record<FieldType, string> = {
  string: "Texto",
  number: "Número",
  integer: "Entero",
  date: "Fecha",
  enum: "Categoría",
  boolean: "Sí / No",
};
export default function SchemaEditor({
  schema,
  update,
  confirmed,
  busy,
  confirm,
}: Props) {
  const change = (index: number, patch: Partial<FieldSpec>) =>
    update({
      ...schema,
      fields: schema.fields.map((f, i) =>
        i === index ? { ...f, ...patch } : f,
      ),
    });
  if (confirmed) {
    return (
      <section className="panel schema-panel">
        <div className="section-title">
          <h2>2. Campos confirmados</h2>
          <span className="confirmed">
            <Check size={14} />
            {schema.fields.length} campos
          </span>
        </div>
        <p className="help">
          {schema.fields.map((field) => field.name).join(" · ")}
        </p>
        <button disabled={busy} onClick={() => update({ ...schema })}>
          Editar campos
        </button>
      </section>
    );
  }
  return (
    <section className="panel schema-panel">
      <div className="section-title">
        <h2>2. Qué quieres extraer</h2>
        {confirmed ? (
          <span className="confirmed">
            <Check size={14} />
            Confirmado
          </span>
        ) : null}
      </div>
      <p className="help">
        Agrega sólo los campos que necesitas. Elige el tipo y si son
        obligatorios.
      </p>
      <div className="schema-actions">
        <button
          disabled={busy || schema.fields.length >= 40}
          onClick={() =>
            update({
              ...schema,
              fields: [
                ...schema.fields,
                {
                  name: "",
                  type: "string",
                  description: "",
                  required: true,
                  enum_values: [],
                },
              ],
            })
          }
        >
          <Plus size={16} />
          Agregar campo
        </button>
      </div>
      {schema.fields.length ? (
        <>
          <div className="fields">
            <div className="field-head">
              <span>Campo</span>
              <span>Tipo</span>
              <span>Obligatorio</span>
              <span />
            </div>
            {schema.fields.map((field, i) => (
              <div className="field" key={i}>
                <div className="field-line">
                  <input
                    aria-label={`Nombre del campo ${i + 1}`}
                    value={field.name}
                    placeholder="nombre_del_campo"
                    disabled={busy}
                    maxLength={64}
                    onChange={(e) => change(i, { name: e.target.value })}
                  />
                  <select
                    aria-label={`Tipo del campo ${i + 1}`}
                    value={field.type}
                    disabled={busy}
                    onChange={(e) =>
                      change(i, {
                        type: e.target.value as FieldType,
                        enum_values: [],
                        minimum: null,
                        maximum: null,
                      })
                    }
                  >
                    {Object.entries(typeLabels).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <input
                    aria-label={`Campo ${i + 1} obligatorio`}
                    type="checkbox"
                    checked={field.required}
                    disabled={busy}
                    onChange={(e) => change(i, { required: e.target.checked })}
                  />
                  <button
                    className="icon-button"
                    aria-label={`Eliminar campo ${i + 1}`}
                    disabled={busy}
                    onClick={() =>
                      update({
                        ...schema,
                        fields: schema.fields.filter((_, idx) => idx !== i),
                      })
                    }
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
                {field.type === "enum" ? (
                  <input
                    className="enum-input"
                    aria-label={`Categorías del campo ${i + 1}`}
                    placeholder="Categorías separadas por coma"
                    value={field.enum_values.join(", ")}
                    disabled={busy}
                    onChange={(e) =>
                      change(i, {
                        enum_values: e.target.value
                          .split(",")
                          .map((s) => s.trim()),
                      })
                    }
                  />
                ) : null}
                <details className="field-details">
                  <summary>Precisar este campo</summary>
                  <label>
                    Qué significa
                    <input
                      value={field.description}
                      maxLength={500}
                      disabled={busy}
                      onChange={(e) =>
                        change(i, { description: e.target.value })
                      }
                    />
                  </label>
                  {field.type === "number" || field.type === "integer" ? (
                    <div className="button-pair">
                      <label>
                        Mínimo
                        <input
                          type="number"
                          value={field.minimum ?? ""}
                          disabled={busy}
                          onChange={(e) =>
                            change(i, {
                              minimum:
                                e.target.value === ""
                                  ? null
                                  : Number(e.target.value),
                            })
                          }
                        />
                      </label>
                      <label>
                        Máximo
                        <input
                          type="number"
                          value={field.maximum ?? ""}
                          disabled={busy}
                          onChange={(e) =>
                            change(i, {
                              maximum:
                                e.target.value === ""
                                  ? null
                                  : Number(e.target.value),
                            })
                          }
                        />
                      </label>
                    </div>
                  ) : null}
                </details>
              </div>
            ))}
          </div>
          <div className="confirm-row">
            <p className="help">
              Dato ausente = <code>null</code>. No se inventa.
            </p>
            <button
              className={confirmed ? "" : "primary"}
              disabled={
                busy ||
                confirmed ||
                schema.fields.some(
                  (f) =>
                    !f.name.trim() ||
                    (f.type === "enum" && !f.enum_values.some((v) => v.trim())),
                )
              }
              onClick={() => void confirm()}
            >
              <Check size={16} />
              {confirmed ? "Esquema confirmado" : "Confirmar campos"}
            </button>
          </div>
        </>
      ) : (
        <div className="empty schema-empty">
          <p>Aún no hay campos definidos.</p>
          <small>Agregar campo es el siguiente paso.</small>
        </div>
      )}
    </section>
  );
}
