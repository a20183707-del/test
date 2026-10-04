"""Pipeline acotado; un fallo de documento nunca interrumpe los siguientes."""
from __future__ import annotations

import copy
import time
import uuid
from typing import Any, Callable, Protocol

from pydantic import ValidationError

from .providers import ProviderError
from .reviewer import (ReviewValidationError, check_review, check_verification,
                       neutral_questions)
from .schema import (AttemptLog, BatchMetrics, BatchReport, DocumentResult,
                     ExtractionSchema, PipelineEvent, ProviderCall, ProviderResponse, ProviderRole,
                     ReviewVerdict, SourceDocument, TokenUsage, VerificationResult,
                     utc_now)
from .validation import (InvalidJSONError, RecordValidationError, compare_reference,
                         safe_validation_messages, validate_business_rules,
                         validate_output, validate_record)


class Extractor(Protocol):
    mode: str
    model: str

    def extract(self, document: SourceDocument, schema: ExtractionSchema, *,
                attempt: int, feedback: list[str]) -> ProviderResponse: ...


class Reviewer(Protocol):
    mode: str
    model: str

    def review(self, document: SourceDocument, record: dict[str, Any], schema: ExtractionSchema,
               *, attempt: int) -> ProviderResponse: ...

    def verify(self, document: SourceDocument, schema: ExtractionSchema,
               questions: list[dict[str, str]], *, attempt: int) -> ProviderResponse: ...


def aggregate_usage(usages: list[TokenUsage]) -> TokenUsage:
    sent = [usage for usage in usages if usage.total_calls > 0]
    names = ("input_tokens", "output_tokens", "thinking_tokens", "cached_tokens", "total_tokens", "estimated_input_tokens")
    totals = {}
    for name in names:
        values = [getattr(usage, name) for usage in sent]
        totals[name] = sum(values) if values and all(value is not None for value in values) else None
    calls = sum(usage.total_calls for usage in sent)
    measured = sum(usage.measured_calls for usage in sent)
    return TokenUsage(**totals, source="provider" if measured else "unavailable",
                      complete=bool(calls) and all(usage.complete for usage in sent),
                      measured_calls=measured, total_calls=calls)


def _messages(error: Exception) -> list[str]:
    if isinstance(error, ValidationError):
        return safe_validation_messages(error)
    if isinstance(error, RecordValidationError):
        return error.messages
    if isinstance(error, (InvalidJSONError, ProviderError, ReviewValidationError)):
        return [str(error)]
    return ["Error interno aislado. Revisa la configuración o el documento; el lote continúa."]


def _process_document(document: SourceDocument, schema: ExtractionSchema, extractor: Extractor,
                      reviewer: Reviewer, emit: Callable[..., None], max_attempts: int,
                      max_review_calls: int,
                      register_call: Callable[[ProviderCall], TokenUsage]) -> DocumentResult:
    logs: list[AttemptLog] = []
    usages: list[TokenUsage] = []
    provider_calls: list[ProviderCall] = []
    record: dict[str, Any] | None = None
    verdict: ReviewVerdict | None = None
    reasons: list[str] = []
    feedback: list[str] = []
    status = "fallido"
    review_calls = 0
    emit(document.id, "reading", 0, "Fuente original preparada para análisis.")
    if not document.text and not document.data:
        reasons = ["No se dispone del documento original."]
    else:
        for attempt in range(1, max_attempts + 1):
            started = time.monotonic()
            log = AttemptLog(attempt=attempt, outcome="started", record_before=copy.deepcopy(record))
            attempt_usages: list[TokenUsage] = []
            retry = False
            phase = "extraction"

            def invoke(role: ProviderRole, model: str,
                       call: Callable[[], ProviderResponse]) -> ProviderResponse:
                call_started_at = utc_now()
                call_started = time.monotonic()
                response: ProviderResponse | None = None
                failure: Exception | None = None
                try:
                    response = call()
                    return response
                except Exception as error:
                    failure = error
                    raise
                finally:
                    usage = (response.usage if response is not None else failure.usage
                             if isinstance(failure, ProviderError) else TokenUsage())
                    error_code = (failure.code if isinstance(failure, ProviderError)
                                  else type(failure).__name__ if failure else None)
                    entry = ProviderCall(id=uuid.uuid4().hex, document_id=document.id,
                                         attempt=attempt, role=role,
                                         model=response.model if response is not None else model,
                                         started_at=call_started_at,
                                         elapsed_ms=round((time.monotonic() - call_started) * 1000),
                                         usage=usage,
                                         status="completed" if response is not None else "not_sent" if usage.total_calls == 0 else "error",
                                         error_code=error_code)
                    provider_calls.append(entry)
                    attempt_usages.append(usage)
                    usages.append(usage)
                    batch_usage = register_call(entry)
                    emit(document.id, "extracting" if role == "extraction" else "reviewing", attempt,
                         "Llamada terminada; consumo actualizado." if entry.status == "completed"
                         else "Llamada no enviada." if entry.status == "not_sent"
                         else "Llamada terminó con error; consumo disponible actualizado.",
                         {"token_entry": entry.model_dump(mode="json"),
                          "usage": aggregate_usage(usages).model_dump(mode="json"),
                          "batch_usage": batch_usage.model_dump(mode="json")})

            try:
                emit(document.id, "extracting", attempt, "El extractor aplica el esquema confirmado.")
                response = invoke("extraction", extractor.model,
                                  lambda: extractor.extract(document, schema, attempt=attempt, feedback=feedback))
                emit(document.id, "validating", attempt, "Validación local de JSON, tipos, formatos y restricciones.")
                candidate = validate_record(response.text, schema)
                record = copy.deepcopy(candidate)
                verdict = None
                log.record_after = copy.deepcopy(candidate)
                local = validate_business_rules(candidate, schema)
                reasons = list(local.reasons)
                status = local.status
                phase = "review"
                if review_calls >= max_review_calls:
                    raise ProviderError("Se agotó el límite de llamadas del revisor.", code="review_limit", retryable=False,
                                        usage=TokenUsage(total_calls=0))
                emit(document.id, "reviewing", attempt, "Revisor: contraste independiente con la fuente original.",
                     {"record": candidate, "review_calls": review_calls + 1})
                review_calls += 1
                review_response = invoke("review", reviewer.model,
                                         lambda: reviewer.review(document, candidate, schema, attempt=attempt))
                verdict = check_review(validate_output(review_response.text, ReviewVerdict), document, candidate, schema)
                log.reviewer_verdict = verdict
                questions = neutral_questions(verdict, candidate, schema)
                if questions:
                    if review_calls >= max_review_calls:
                        raise ProviderError("No hay presupuesto para comprobar las discrepancias de forma independiente.",
                                            code="review_limit", retryable=False, usage=TokenUsage(total_calls=0))
                    emit(document.id, "reviewing", attempt,
                         "Comprobación neutral de discrepancias: nueva lectura original sin candidato.",
                         {"review_calls": review_calls + 1, "questions": questions})
                    review_calls += 1
                    verified_response = invoke("verification", reviewer.model,
                                               lambda: reviewer.verify(document, schema, questions, attempt=attempt))
                    verification = check_verification(validate_output(verified_response.text, VerificationResult), questions, document)
                    log.independent_verification = verification
                    for item in verification.fields:
                        if item.answerable and item.observed_value != candidate[item.field]:
                            proposal = {**candidate, item.field: item.observed_value}
                            try:
                                validate_record(proposal, schema)
                            except RecordValidationError:
                                continue
                            retry = True
                if verdict.decision == "approved" and local.status == "exitoso":
                    status = "exitoso"
                    reasons = ["JSON y reglas locales válidos; todos los campos contrastados por el revisor."]
                    log.outcome = "approved"
                else:
                    status = "fallido" if verdict.decision == "rejected" or local.status == "fallido" else "parcial"
                    reasons.append(verdict.reason)
                    reasons.extend(f"{item.field}: {item.problem or item.status}" for item in verdict.fields
                                   if item.status in ("contradicted", "uncertain"))
                    retry = retry or (verdict.should_retry and bool(questions))
                    log.outcome = "needs_review" if status == "parcial" else "rejected"
                    feedback = [f"Comprueba de nuevo {item['field']}: {item['question']}" for item in questions]
            except Exception as error:
                messages = _messages(error)
                log.error_type = error.code if isinstance(error, ProviderError) else type(error).__name__
                log.messages = messages
                log.outcome = "review_error" if phase == "review" else "extraction_error"
                reasons = messages
                # Un candidato válido se conserva, pero jamás se aprueba sin revisión.
                status = "parcial" if record is not None and any(v is not None for v in record.values()) else "fallido"
                retry = not isinstance(error, ProviderError) or error.retryable
                feedback = messages
                if not isinstance(error, (ProviderError, ValidationError, RecordValidationError,
                                          InvalidJSONError, ReviewValidationError)):
                    retry = False
            log.elapsed_ms = round((time.monotonic() - started) * 1000)
            log.usage = aggregate_usage(attempt_usages)
            logs.append(log)
            if status == "exitoso" or not retry:
                break
            if attempt < max_attempts:
                emit(document.id, "retrying", attempt, "Nueva extracción acotada; se conserva la versión anterior.",
                     {"record": record, "reasons": reasons})
            else:
                reasons.append("Se agotaron los 3 intentos de extracción." if max_attempts == 3 else f"Se agotaron los {max_attempts} intentos de extracción.")
    reference = document.metadata.get("reference")
    accuracy = (compare_reference(record, reference,
                                  reference_source=str(document.metadata.get("reference_source", "Referencia proporcionada")),
                                  independent_human_review=document.metadata.get("reference_reviewed") is True)
                if isinstance(reference, dict) else None)
    result = DocumentResult(document_id=document.id, source_name=document.name, status=status,
                            record=record, attempts=len(logs), review_calls=review_calls,
                            reasons=list(dict.fromkeys([*document.warnings, *reasons])), attempt_log=logs,
                            reviewer_verdict=verdict, human_review_required=status != "exitoso",
                            usage=aggregate_usage(usages), source_sha256=document.sha256,
                            reference_accuracy=accuracy, provider_calls=provider_calls)
    emit(document.id, "completed", len(logs), f"Documento terminado: {status}.",
         {"result": result.model_dump(mode="json")})
    return result


def batch_metrics(results: list[DocumentResult], documents: list[SourceDocument], mode: str) -> BatchMetrics:
    total = len(results)
    successful = sum(result.status == "exitoso" for result in results)
    partial = sum(result.status == "parcial" for result in results)
    failed = total - successful - partial
    sources = {doc.id: doc for doc in documents}
    synthetic = sum(sources[result.document_id].metadata.get("synthetic") is True for result in results)
    # La procedencia se declara explícitamente; ejecutar Gemini no la establece.
    real = [result for result in results if sources[result.document_id].metadata.get("synthetic") is False]
    real_successful = sum(result.status == "exitoso" for result in real)
    rate = lambda value: round(value / total * 100, 2) if total else None
    return BatchMetrics(total=total, successful=successful, partial=partial, failed=failed,
                        success_rate=rate(successful), partial_rate=rate(partial), failure_rate=rate(failed),
                        total_attempts=sum(result.attempts for result in results),
                        real_documents=len(real), real_successful=real_successful,
                        real_success_rate=round(real_successful / len(real) * 100, 2) if real and mode == "gemini" else None,
                        synthetic_documents=synthetic,
                        undeclared_documents=total - synthetic - len(real))


def process_batch(documents: list[SourceDocument], schema: ExtractionSchema, extractor: Extractor,
                  reviewer: Reviewer, on_event: Callable[[PipelineEvent], None] | None = None,
                  max_attempts: int = 3, max_review_calls: int = 6) -> BatchReport:
    if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
        raise ValueError("El límite de extracción debe estar entre 1 y 3 intentos.")
    if type(max_review_calls) is not int or not 1 <= max_review_calls <= 6:
        raise ValueError("El límite del revisor debe estar entre 1 y 6 llamadas.")
    if len(documents) > 100 or len({doc.id for doc in documents}) != len(documents):
        raise ValueError("Usa hasta 100 documentos con identificadores únicos.")
    started = utc_now()
    events: list[PipelineEvent] = []
    provider_calls: list[ProviderCall] = []

    def register_call(entry: ProviderCall) -> TokenUsage:
        provider_calls.append(entry)
        return aggregate_usage([call.usage for call in provider_calls])

    def emit(document_id: str, stage: str, attempt: int, detail: str,
             snapshot: dict[str, Any] | None = None) -> None:
        event = PipelineEvent(document_id=document_id, stage=stage, attempt=attempt, detail=detail, snapshot=snapshot)
        events.append(event)
        if on_event:
            try:
                on_event(event)
            except Exception:
                # El reporte conserva el evento aunque una vista deje de estar conectada.
                pass

    results = [_process_document(doc, schema, extractor, reviewer, emit, max_attempts, max_review_calls, register_call)
               for doc in documents]
    mode = "gemini" if extractor.mode == "gemini" and reviewer.mode == "gemini" else "test_injected"
    return BatchReport(mode=mode, provider=extractor.model, reviewer=reviewer.model,
                       schema_definition=schema, started_at=started, completed_at=utc_now(),
                       max_attempts=max_attempts, max_review_calls=max_review_calls, results=results,
                       metrics=batch_metrics(results, documents, mode), events=events,
                       usage=aggregate_usage([result.usage for result in results]),
                       provider_calls=provider_calls)
