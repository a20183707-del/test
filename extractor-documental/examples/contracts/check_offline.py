"""Verifica fixtures y pipeline con respuestas inyectadas; nunca llama a Gemini.

El extractor devuelve los valores elaborados en references.json. El revisor es
también un fixture determinista. Esta prueba no mide comprensión ni exactitud
de un modelo y no reemplaza una revisión humana independiente.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from bsg_extractor.inputs import read_document
from bsg_extractor.pipeline import process_batch
from bsg_extractor.reports import report_csv, report_json
from bsg_extractor.schema import (
    ExtractionSchema, FieldReview, ProviderResponse, ReviewVerdict, TokenUsage,
)
from bsg_extractor.validation import validate_business_rules, validate_record

FIXTURES = Path(__file__).resolve().parent
PROJECT = FIXTURES.parents[1]
EVIDENCE_PATTERNS = {
    "contract_id": ["CONTRATO", "CONTRACTUAL"],
    "client": ["Cliente:"],
    "supplier": ["Proveedor:"],
    "start_date": ["Inicio:", "Vigencia desde", "Fecha de inicio:"],
    "end_date": ["Inicio:", "Vigencia desde"],
    "monthly_fee": ["Tarifa mensual:", "Cuota mensual acordada:"],
    "currency": ["Tarifa mensual:", "Cuota mensual acordada:", "Moneda contractual:"],
    "service_type": ["Servicio contratado:", "El servicio es", "Servicio:"],
    "auto_renewal": ["Renovación automática:", "Se descarta la renovación automática:"],
}


class FixtureExtractor:
    mode = "test_injected"
    model = "fixture_reference_injected"

    def __init__(self, references: dict):
        self.references = references

    def extract(self, document, schema, **kwargs):
        return ProviderResponse(text=json.dumps(self.references[document.name]),
                                model=self.model, usage=TokenUsage(total_calls=0))


class FixtureReviewer:
    mode = "test_injected"
    model = "fixture_review_injected"

    def review(self, document, record, schema, **kwargs):
        fields = []
        for spec in schema.fields:
            value = record[spec.name]
            evidence = next((line for line in document.text.splitlines()
                             if any(pattern.casefold() in line.casefold()
                                    for pattern in EVIDENCE_PATTERNS[spec.name])), None) if value is not None else None
            fields.append(FieldReview(
                field=spec.name, status="supported" if value is not None else "missing",
                evidence=evidence, location="Texto sintético de prueba" if evidence else None,
                problem=None if value is not None else "Dato ausente o ambiguo en la referencia elaborada",
                severity="none" if value is not None else "medium" if spec.required else "low",
                proposed_value=value,
                verification_question="¿Qué valor explícito consta en el texto sintético?",
            ))
        missing = any(spec.required and record[spec.name] is None for spec in schema.fields)
        decision = "rejected" if all(value is None for value in record.values()) else "needs_review" if missing else "approved"
        verdict = ReviewVerdict(
            decision=decision, fields=fields, should_retry=False,
            reason="Revisor inyectado de software con referencia elaborada; no es revisión humana ni ejecución Gemini.",
        )
        return ProviderResponse(text=verdict.model_dump_json(), model=self.model,
                                usage=TokenUsage(total_calls=0))

    def verify(self, *args, **kwargs):
        raise AssertionError("Este escenario no necesita verificación neutral; las discrepancias se prueban por separado.")


def main() -> None:
    schema = ExtractionSchema.model_validate(json.loads((FIXTURES / "schema.fields.json").read_text(encoding="utf-8")))
    references = json.loads((FIXTURES / "references.json").read_text(encoding="utf-8"))
    notes = json.loads((FIXTURES / "reference-notes.json").read_text(encoding="utf-8"))
    expected = {item["filename"]: item["expected_deterministic_status"] for item in notes["documents"]}
    assert len(references) == 5 and len(schema.fields) >= 6
    assert {"number", "date", "enum"} <= {field.type for field in schema.fields}
    results, documents = [], []
    for index, (name, record) in enumerate(references.items(), 1):
        document = read_document((FIXTURES / name).read_bytes(), name,
                                 document_id=f"synthetic-contract-{index}",
                                 metadata={"synthetic": True, "reference_reviewed": False})
        assert "EJEMPLO SINTÉTICO" in document.text
        assert set(record) == {field.name for field in schema.fields}
        outcome = validate_business_rules(validate_record(record, schema), schema)
        assert outcome.status == expected[name]
        documents.append(document)
        results.append({"document": name, "source_sha256": document.sha256,
                        "reference_validation_status": outcome.status,
                        "missing_required_fields": outcome.missing_fields})
    assert len({document.sha256 for document in documents}) == len(documents)
    report = process_batch(documents, schema, FixtureExtractor(references), FixtureReviewer())
    assert [result.status for result in report.results] == list(expected.values())
    assert report.mode == "test_injected" and report.metrics.real_documents == 0
    assert report.usage.total_calls == 0 and all(result.reference_accuracy is None for result in report.results)
    evidence = PROJECT / "docs"
    evidence.mkdir(exist_ok=True)
    summary = {
        "check": "synthetic_fixture_integrity_and_reference_validation",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(), "provider_calls": 0,
        "documents": len(documents), "fields_per_reference": len(schema.fields),
        "reference_kind": "elaborated_by_Codex_not_independently_reviewed",
        "independent_human_review": False, "real_Gemini_extraction": False, "results": results,
    }
    (evidence / "FIXTURE_VALIDATION.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (evidence / "SYNTHETIC_BATCH_REPORT.json").write_text(report_json(report) + "\n", encoding="utf-8")
    (evidence / "SYNTHETIC_BATCH_REPORT.csv").write_text(report_csv(report), encoding="utf-8", newline="")
    print("Verificación offline ejecutada: 5 contratos sintéticos; 0 llamadas externas.")
    print("Referencias elaboradas: 2 completos, 2 parciales, 1 fallido; no mide exactitud de Gemini.")


if __name__ == "__main__":
    main()
