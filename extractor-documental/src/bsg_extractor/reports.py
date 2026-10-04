"""Exportaciones locales trazables; el CSV neutraliza fórmulas de hojas de cálculo."""
from __future__ import annotations

import csv
import io
import json

from .schema import BatchReport


def report_json(report: BatchReport) -> str:
    return report.model_dump_json(indent=2)


def _csv_safe(value: object) -> object:
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def report_csv(report: BatchReport) -> str:
    output = io.StringIO(newline="")
    names = [field.name for field in report.schema_definition.fields]
    writer = csv.writer(output)
    writer.writerow(["document_id", "source_name", "source_sha256", "mode", "status", "attempts", "review_calls",
                     "reasons", "reviewer_decision", "reviewer_findings", "independent_verifications",
                     "input_tokens", "output_tokens", "thinking_tokens", "total_tokens", "usage_complete", "provider_calls",
                     "reference_accuracy", *["data." + name for name in names]])
    for result in report.results:
        verifications = [log.independent_verification.model_dump(mode="json") for log in result.attempt_log
                         if log.independent_verification]
        row = [result.document_id, result.source_name, result.source_sha256, report.mode, result.status,
               result.attempts, result.review_calls, " | ".join(result.reasons),
               result.reviewer_verdict.decision if result.reviewer_verdict else "sin_revision",
               result.reviewer_verdict.model_dump_json() if result.reviewer_verdict else "",
               json.dumps(verifications, ensure_ascii=False),
               result.usage.input_tokens, result.usage.output_tokens, result.usage.thinking_tokens,
               result.usage.total_tokens, result.usage.complete,
               json.dumps([call.model_dump(mode="json") for call in result.provider_calls], ensure_ascii=False),
               json.dumps(result.reference_accuracy, ensure_ascii=False) if result.reference_accuracy else "",
               *[(result.record or {}).get(name) for name in names]]
        writer.writerow([_csv_safe(value) for value in row])
    return output.getvalue()
