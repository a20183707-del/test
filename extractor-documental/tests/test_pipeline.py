import csv
import io
import json

import pytest

from bsg_extractor.inputs import from_text
from bsg_extractor.pipeline import aggregate_usage, batch_metrics, process_batch
from bsg_extractor.providers import ProviderError
from bsg_extractor.reports import report_csv, report_json
from bsg_extractor.schema import (ExtractionSchema, FieldReview, FieldSpec,
                                      ProviderResponse, ReviewVerdict, TokenUsage,
                                      VerificationField, VerificationResult)


def schema():
    return ExtractionSchema(title="Dato pedido por usuario", fields=[FieldSpec(name="valor", type="number")])


def response(value):
    text = value if isinstance(value, str) else value.model_dump_json() if hasattr(value, "model_dump_json") else json.dumps(value)
    return ProviderResponse(text=text, model="prueba_inyectada",
                            usage=TokenUsage(source="unavailable", total_calls=0))


def verdict(value, status="supported", decision="approved", retry=False, evidence="valor:42"):
    return ReviewVerdict(decision=decision, fields=[
        FieldReview(field="valor", status=status, evidence=evidence, location="línea 1",
                    problem=None if status == "supported" else "Contraste pendiente",
                    severity="none" if status == "supported" else "high",
                    proposed_value=None if status == "supported" else 42,
                    verification_question="¿Qué valor aparece en la fuente?")],
        reason="Contraste documentado", should_retry=retry)


class InjectedExtractor:
    mode = "test_injected"
    model = "prueba_inyectada"

    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = []

    def extract(self, document, requested_schema, *, attempt, feedback):
        self.calls.append((document.id, attempt))
        values = self.outputs[document.id]
        value = values[min(attempt - 1, len(values) - 1)]
        if isinstance(value, Exception):
            raise value
        return response(value)


class InjectedReviewer:
    mode = "test_injected"
    model = "revisor_inyectado"

    def __init__(self, outputs=None):
        self.outputs = outputs
        self.calls = 0
        self.verify_calls = 0
        self.questions = []

    def review(self, document, record, requested_schema, *, attempt):
        self.calls += 1
        return response(self.outputs[min(attempt - 1, len(self.outputs) - 1)] if self.outputs else verdict(record["valor"]))

    def verify(self, document, requested_schema, questions, *, attempt):
        self.verify_calls += 1
        self.questions = questions
        return response(VerificationResult(fields=[VerificationField(field="valor", observed_value=42,
                        evidence="valor:42", location="línea 1", answer="Valor explícito", answerable=True)]))


def test_invalid_json_exhaustion_isolated_and_success_next_document():
    first = from_text("valor:42", document_id="bad")
    second = from_text("valor:42", document_id="good")
    extractor = InjectedExtractor({"bad": ["{invalid"], "good": [{"valor": 42}]})
    reviewer = InjectedReviewer()
    events = []
    report = process_batch([first, second], schema(), extractor, reviewer, on_event=events.append)
    assert [item.status for item in report.results] == ["fallido", "exitoso"]
    assert report.results[0].attempts == 3
    assert report.results[0].review_calls == 0
    assert report.metrics.success_rate == 50
    assert report.metrics.real_success_rate is None
    assert report.mode == "test_injected"
    assert report.usage.total_tokens is None
    assert sum(event.stage == "completed" for event in events) == 2
    assert events[-1].snapshot["result"]["status"] == "exitoso"
    assert "Gemini" not in " ".join(event.detail for event in events)


def test_discrepancy_independent_verification_and_preserved_versions():
    source = from_text("valor:42", document_id="doc")
    extractor = InjectedExtractor({"doc": [{"valor": 99}, {"valor": 42}]})
    reviewer = InjectedReviewer([verdict(99, "contradicted", "needs_review", True), verdict(42)])
    result = process_batch([source], schema(), extractor, reviewer).results[0]
    assert result.status == "exitoso"
    assert result.record == {"valor": 42}
    assert result.attempts == 2
    assert result.review_calls == 3
    assert result.attempt_log[0].record_after == {"valor": 99}
    assert result.attempt_log[1].record_before == {"valor": 99}
    assert result.attempt_log[0].reviewer_verdict.fields[0].proposed_value == 42
    assert result.attempt_log[0].independent_verification.fields[0].observed_value == 42
    assert "99" not in json.dumps(reviewer.questions)


def test_fabricated_evidence_cannot_be_approved():
    source = from_text("valor:42", document_id="doc")
    reviewer = InjectedReviewer([verdict(99, evidence="La fuente dice 99")])
    extractor = InjectedExtractor({"doc": [{"valor": 99}]})
    result = process_batch([source], schema(), extractor, reviewer, max_attempts=1).results[0]
    assert result.status == "parcial"
    assert result.reviewer_verdict.decision == "needs_review"
    assert result.record == {"valor": 99}  # propuesta 42 no modifica silenciosamente datos
    assert result.human_review_required


def test_reviewer_limit_is_independent_and_never_bypassed():
    source = from_text("valor:42", document_id="doc")
    reviewer = InjectedReviewer([verdict(99, "contradicted", "needs_review", True)])
    result = process_batch([source], schema(), InjectedExtractor({"doc": [{"valor": 99}]}),
                           reviewer, max_review_calls=1).results[0]
    assert result.review_calls == 1
    assert reviewer.verify_calls == 0
    assert result.attempts == 1
    assert result.status == "parcial"


def test_three_extractions_and_six_review_calls_are_absolute_limits():
    source = from_text("valor:42", document_id="doc")
    extractor = InjectedExtractor({"doc": [{"valor": 99}]})
    reviewer = InjectedReviewer([verdict(99, "contradicted", "needs_review", True)])
    result = process_batch([source], schema(), extractor, reviewer).results[0]
    assert result.attempts == len(extractor.calls) == 3
    assert result.review_calls == 6
    assert reviewer.calls == reviewer.verify_calls == 3
    assert result.record == {"valor": 99}
    assert result.status == "parcial"


def test_authentication_failure_does_not_retry_and_batch_continues():
    docs = [from_text("valor:42", document_id="first"), from_text("valor:42", document_id="second")]
    extractor = InjectedExtractor({"first": [ProviderError("Credencial rechazada", retryable=False)], "second": [{"valor": 42}]})
    results = process_batch(docs, schema(), extractor, InjectedReviewer()).results
    assert results[0].attempts == 1
    assert results[1].status == "exitoso"


def test_required_absence_stays_null_without_impossible_retries():
    requested = ExtractionSchema(title="Datos", fields=[FieldSpec(name="nombre", type="string"), FieldSpec(name="valor", type="number")])
    source = from_text("nombre:Ejemplo", document_id="doc")
    extractor = InjectedExtractor({"doc": [{"nombre": "Ejemplo", "valor": None}]})

    class MissingReviewer(InjectedReviewer):
        def review(self, document, record, requested_schema, *, attempt):
            fields = [FieldReview(field="nombre", status="supported", evidence="nombre:Ejemplo", location="línea 1", problem=None,
                                   severity="none", proposed_value=None, verification_question="¿Qué nombre aparece?"),
                      FieldReview(field="valor", status="missing", evidence=None, location=None, problem="No existe en fuente",
                                   severity="high", proposed_value=None, verification_question="¿Qué valor aparece?")]
            return response(ReviewVerdict(decision="needs_review", fields=fields, reason="Dato ausente", should_retry=True))

    result = process_batch([source], requested, extractor, MissingReviewer()).results[0]
    assert result.status == "parcial"
    assert result.attempts == 1
    assert result.record["valor"] is None


def test_malformed_reviewer_never_approves_and_total_calls_bounded():
    source = from_text("valor:42", document_id="doc")
    reviewer = InjectedReviewer([ReviewVerdict(decision="approved", fields=[], reason="sin comprobación", should_retry=False)])
    result = process_batch([source], schema(), InjectedExtractor({"doc": [{"valor": 42}]}), reviewer).results[0]
    assert result.status == "parcial"
    assert result.attempts == 3
    assert result.review_calls == 3
    assert result.record == {"valor": 42}


def test_empty_batch_has_no_success_percentage():
    report = process_batch([], schema(), InjectedExtractor({}), InjectedReviewer())
    assert report.metrics.success_rate is None
    assert report.metrics.real_success_rate is None


@pytest.mark.parametrize("attempts,reviews", [(4, 6), (3, 7), (0, 6), (True, 6)])
def test_limits_are_enforced(attempts, reviews):
    with pytest.raises(ValueError):
        process_batch([], schema(), InjectedExtractor({}), InjectedReviewer(), max_attempts=attempts, max_review_calls=reviews)


def test_reports_have_provenance_history_and_csv_formula_protection():
    source = from_text("valor:42", name="=SUM(A1:A2)", document_id="doc")
    source.metadata = {"reference": {"valor": 42.0}, "reference_source": "Referencia sintética de test", "synthetic": True}
    report = process_batch([source], schema(), InjectedExtractor({"doc": [{"valor": 42}]}), InjectedReviewer())
    exported = json.loads(report_json(report))
    assert exported["results"][0]["reference_accuracy"]["accuracy_percent"] == 100
    assert not exported["results"][0]["reference_accuracy"]["independent_human_review"]
    rows = list(csv.reader(io.StringIO(report_csv(report))))
    assert rows[1][1].startswith("'=")
    assert "reviewer_findings" in rows[0]
    assert "provider_calls" in rows[0]
    assert len(exported["provider_calls"]) == 2
    assert exported["results"][0]["provider_calls"] == exported["provider_calls"]


def measured_usage(total):
    return TokenUsage(input_tokens=total - 3, output_tokens=2, thinking_tokens=1,
                      cached_tokens=0, total_tokens=total, estimated_input_tokens=total - 3,
                      source="provider", complete=True, measured_calls=1, total_calls=1)


def test_incremental_ledger_updates_after_every_call_before_next_stage_and_document():
    docs = [from_text("valor:42", document_id="one"), from_text("valor:42", document_id="two")]
    events = []

    class MeasuredExtractor(InjectedExtractor):
        def extract(self, document, requested_schema, *, attempt, feedback):
            if document.id == "two":
                # El consumo del primer documento ya salió durante el lote.
                assert [event.snapshot["batch_usage"]["total_tokens"] for event in events
                        if event.snapshot and "token_entry" in event.snapshot] == [10, 30]
            returned = super().extract(document, requested_schema, attempt=attempt, feedback=feedback)
            returned.usage = measured_usage(10)
            return returned

    class MeasuredReviewer(InjectedReviewer):
        def review(self, document, record, requested_schema, *, attempt):
            # La extracción se registra antes de entrar a revisar.
            assert events[-2].stage == "validating"
            returned = super().review(document, record, requested_schema, attempt=attempt)
            returned.usage = measured_usage(20)
            return returned

    report = process_batch(docs, schema(), MeasuredExtractor({"one": [{"valor": 42}], "two": [{"valor": 42}]}),
                           MeasuredReviewer(), on_event=events.append)
    incremental = [event for event in events if event.snapshot and "token_entry" in event.snapshot]
    assert [event.snapshot["batch_usage"]["total_tokens"] for event in incremental] == [10, 30, 40, 60]
    assert [event.snapshot["usage"]["total_tokens"] for event in incremental] == [10, 30, 10, 30]
    assert [event.stage for event in incremental] == ["extracting", "reviewing", "extracting", "reviewing"]
    assert [entry.role for entry in report.provider_calls] == ["extraction", "review", "extraction", "review"]
    assert len({entry.id for entry in report.provider_calls}) == 4
    assert all(entry.elapsed_ms >= 0 and entry.status == "completed" for entry in report.provider_calls)
    assert report.usage.total_tokens == 60
    assert report.usage.measured_calls == 4


def test_error_usage_is_registered_once_and_kept_when_json_or_review_is_invalid():
    source = from_text("valor:42", document_id="doc")
    failure = ProviderError("Respuesta incompleta", code="incomplete_response", retryable=False, usage=measured_usage(15))
    events = []
    report = process_batch([source], schema(), InjectedExtractor({"doc": [failure]}), InjectedReviewer(), on_event=events.append)
    assert len(report.provider_calls) == 1
    entry = report.provider_calls[0]
    assert entry.status == "error"
    assert entry.error_code == "incomplete_response"
    assert entry.usage.total_tokens == report.usage.total_tokens == 15
    assert report.results[0].attempt_log[0].usage.total_tokens == 15
    assert next(event.snapshot["batch_usage"]["total_tokens"] for event in events
                if event.snapshot and "token_entry" in event.snapshot) == 15


def test_invalid_json_response_retains_measured_call_in_history():
    source = from_text("valor:42", document_id="doc")

    class InvalidMeasuredExtractor(InjectedExtractor):
        def extract(self, document, requested_schema, *, attempt, feedback):
            return ProviderResponse(text="{invalid", model=self.model, usage=measured_usage(8))

    report = process_batch([source], schema(), InvalidMeasuredExtractor({}), InjectedReviewer(), max_attempts=1)
    assert report.results[0].status == "fallido"
    assert report.provider_calls[0].status == "completed"  # llamada terminada, JSON inválido en la siguiente etapa
    assert report.usage.total_tokens == 8


def test_missing_metadata_leaves_aggregate_unknown_and_not_sent_does_not_contaminate():
    measured = measured_usage(12)
    unavailable = TokenUsage()
    not_sent = TokenUsage(total_calls=0)
    assert aggregate_usage([measured, not_sent]).total_tokens == 12
    combined = aggregate_usage([measured, unavailable])
    assert combined.total_tokens is None
    assert combined.input_tokens is None
    assert combined.source == "provider"
    assert not combined.complete
    assert combined.total_calls == 2 and combined.measured_calls == 1


def test_local_session_failure_history_says_not_sent_with_unknown_consumption():
    source = from_text("valor:42", document_id="doc")
    failure = ProviderError("Sesión expirada", code="session_expired", retryable=False, usage=TokenUsage(total_calls=0))
    report = process_batch([source], schema(), InjectedExtractor({"doc": [failure]}), InjectedReviewer())
    assert report.provider_calls[0].status == "not_sent"
    assert report.usage.total_calls == 0
    assert report.usage.total_tokens is None


@pytest.mark.parametrize("mode", ["gemini", "test_injected"])
def test_source_provenance_requires_explicit_boolean_independently_of_provider_mode(mode):
    documents = [from_text("valor:42", document_id=f"doc_{index}") for index in range(7)]
    declarations = [True, False, None, "true", "false", 1, 0]
    for document, declaration in zip(documents, declarations):
        document.metadata["synthetic"] = declaration
    report = process_batch(documents, schema(), InjectedExtractor({doc.id: [{"valor": 42}] for doc in documents}), InjectedReviewer())
    metrics = batch_metrics(report.results, documents, mode)
    assert metrics.synthetic_documents == 1
    assert metrics.real_documents == 1
    assert metrics.undeclared_documents == 5
    assert metrics.real_success_rate == (100 if mode == "gemini" else None)
    assert metrics.total == metrics.synthetic_documents + metrics.real_documents + metrics.undeclared_documents


def test_authentication_failures_on_uploaded_undeclared_fixtures_do_not_become_real_sources():
    documents = [from_text("EJEMPLO SINTÉTICO valor:42", document_id=f"upload_{index}") for index in range(5)]
    failure = ProviderError("Credencial rechazada", code="authentication", retryable=False)
    report = process_batch(documents, schema(), InjectedExtractor({doc.id: [failure] for doc in documents}), InjectedReviewer())
    metrics = batch_metrics(report.results, documents, "gemini")
    assert metrics.total == metrics.failed == metrics.undeclared_documents == 5
    assert metrics.success_rate == 0
    assert metrics.real_documents == metrics.synthetic_documents == 0
    assert metrics.real_success_rate is None
    assert all(result.review_calls == 0 for result in report.results)
