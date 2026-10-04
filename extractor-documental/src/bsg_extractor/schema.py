"""Contratos explícitos para documentos, extracción, revisión y reportes."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Status = Literal["exitoso", "parcial", "fallido"]
Stage = Literal["reading", "extracting", "validating", "reviewing", "retrying", "completed"]
ProviderRole = Literal["extraction", "review", "verification"]
Scalar = str | int | float | bool | None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class SourceDocument(StrictModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False, validate_assignment=True)

    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=240)
    mime: str
    text: str | None = None
    data: bytes | None = Field(default=None, exclude=True, repr=False)
    sha256: str = ""
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FieldSpec(StrictModel):
    name: str = Field(min_length=1, max_length=64)
    type: Literal["string", "number", "integer", "date", "enum", "boolean"]
    description: str = Field(default="", max_length=1500)
    required: bool = True
    enum_values: list[str] = Field(default_factory=list, max_length=30)
    minimum: float | None = Field(default=None, allow_inf_nan=False)
    maximum: float | None = Field(default=None, allow_inf_nan=False)

    @field_validator("name")
    @classmethod
    def safe_name(cls, value: str) -> str:
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*", value):
            raise ValueError("Usa nombres de campo con letras, números y guion bajo; empieza por una letra.")
        return value

    @model_validator(mode="after")
    def coherent_rules(self) -> FieldSpec:
        if self.type == "enum" and (not self.enum_values or any(not x.strip() or len(x) > 200 for x in self.enum_values)):
            raise ValueError("Un campo categórico requiere opciones no vacías, de hasta 200 caracteres.")
        if len(set(self.enum_values)) != len(self.enum_values):
            raise ValueError("Las opciones categóricas deben ser únicas.")
        if self.type != "enum" and self.enum_values:
            raise ValueError("Las opciones sólo corresponden a campos categóricos.")
        if self.type not in ("number", "integer") and (self.minimum is not None or self.maximum is not None):
            raise ValueError("Los límites sólo corresponden a campos numéricos.")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("El mínimo no puede superar al máximo.")
        return self


class ExtractionSchema(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    fields: list[FieldSpec] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def unique_fields(self) -> ExtractionSchema:
        if len({f.name.casefold() for f in self.fields}) != len(self.fields):
            raise ValueError("Los nombres de campo deben ser únicos.")
        return self

    def json_schema(self) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        for field in self.fields:
            value: dict[str, Any] = {"type": "string" if field.type in ("date", "enum") else field.type}
            if field.type == "date":
                value["format"] = "date"
            if field.type == "enum":
                value["enum"] = field.enum_values
            if field.minimum is not None:
                value["minimum"] = field.minimum
            if field.maximum is not None:
                value["maximum"] = field.maximum
            properties[field.name] = {
                "anyOf": [value, {"type": "null"}],
                "description": field.description + (" Obligatorio; ausencia se representa con null." if field.required else " Opcional; ausencia se representa con null."),
            }
        return {"type": "object", "title": self.title, "properties": properties,
                "required": [field.name for field in self.fields], "additionalProperties": False}


class TokenUsage(StrictModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    thinking_tokens: int | None = Field(default=None, ge=0)
    cached_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_input_tokens: int | None = Field(default=None, ge=0)
    source: Literal["provider", "unavailable", "estimate"] = "unavailable"
    complete: bool = False
    measured_calls: int = 0
    total_calls: int = 1


class ProviderResponse(StrictModel):
    text: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    model: str
    elapsed_ms: int = 0


class ProviderCall(StrictModel):
    id: str
    document_id: str
    attempt: int
    role: ProviderRole
    model: str
    started_at: datetime
    elapsed_ms: int = Field(ge=0)
    usage: TokenUsage
    status: Literal["completed", "error", "not_sent"]
    error_code: str | None = None


class FieldReview(StrictModel):
    field: str
    status: Literal["supported", "missing", "contradicted", "uncertain"]
    evidence: str | None
    location: str | None
    problem: str | None
    severity: Literal["none", "low", "medium", "high", "critical"]
    proposed_value: Scalar
    verification_question: str


class ReviewVerdict(StrictModel):
    decision: Literal["approved", "needs_review", "rejected"]
    fields: list[FieldReview] = Field(max_length=40)
    reason: str
    should_retry: bool


class VerificationField(StrictModel):
    field: str
    observed_value: Scalar
    evidence: str | None
    location: str | None
    answer: str
    answerable: bool


class VerificationResult(StrictModel):
    fields: list[VerificationField] = Field(max_length=40)


class ValidationResult(StrictModel):
    status: Status
    reasons: list[str]
    missing_fields: list[str]


class AttemptLog(StrictModel):
    attempt: int
    outcome: str
    error_type: str | None = None
    messages: list[str] = Field(default_factory=list)
    elapsed_ms: int = 0
    record_before: dict[str, Scalar] | None = None
    record_after: dict[str, Scalar] | None = None
    reviewer_verdict: ReviewVerdict | None = None
    independent_verification: VerificationResult | None = None
    usage: TokenUsage = Field(default_factory=lambda: TokenUsage(total_calls=0))


class PipelineEvent(StrictModel):
    document_id: str
    stage: Stage
    attempt: int
    timestamp: datetime = Field(default_factory=utc_now)
    detail: str
    snapshot: dict[str, Any] | None = None


class DocumentResult(StrictModel):
    document_id: str
    source_name: str
    status: Status
    record: dict[str, Scalar] | None
    attempts: int
    review_calls: int
    reasons: list[str]
    attempt_log: list[AttemptLog]
    reviewer_verdict: ReviewVerdict | None = None
    human_review_required: bool = False
    usage: TokenUsage = Field(default_factory=lambda: TokenUsage(total_calls=0))
    source_sha256: str = ""
    reference_accuracy: dict[str, Any] | None = None
    provider_calls: list[ProviderCall] = Field(default_factory=list)


class BatchMetrics(StrictModel):
    total: int
    successful: int
    partial: int
    failed: int
    success_rate: float | None
    partial_rate: float | None
    failure_rate: float | None
    total_attempts: int
    real_documents: int
    real_successful: int
    real_success_rate: float | None
    synthetic_documents: int
    undeclared_documents: int = 0
    rate_definition: str = "Documentos exitosos / documentos procesados × 100; no es confianza ni exactitud."


class BatchReport(StrictModel):
    schema_version: str = "2.0.0"
    mode: str
    provider: str
    reviewer: str
    schema_definition: ExtractionSchema
    started_at: datetime
    completed_at: datetime
    max_attempts: int
    max_review_calls: int
    results: list[DocumentResult]
    metrics: BatchMetrics
    events: list[PipelineEvent]
    usage: TokenUsage
    provider_calls: list[ProviderCall] = Field(default_factory=list)
