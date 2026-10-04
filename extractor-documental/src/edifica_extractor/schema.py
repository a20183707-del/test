"""Contratos compartidos. Los valores ausentes se representan con null."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Status = Literal["exitoso", "parcial", "fallido"]
Stage = Literal[
    "queued", "reading", "extracting", "validating", "judging", "retrying", "completed", "failed"
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DocumentInput:
    """Fuente primaria local. metadata nunca reemplaza la evidencia del recibo."""

    document_id: str
    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path))
        if not self.document_id.strip():
            raise ValueError("document_id no puede estar vacío")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class PaymentRecord(StrictModel):
    """Esquema nativo: todas las claves requeridas, valores desconocidos nulos."""

    banco: str | None = Field(description="Banco o aplicación identificados explícitamente en el comprobante.")
    fecha_pago: date | None = Field(description="Fecha inequívoca del pago en YYYY-MM-DD. Si es ambigua: null.")
    monto: float | None = Field(gt=0, allow_inf_nan=False, description="Monto positivo del pago. Excluye comisiones; no calcular ni corregir.")
    moneda: Literal["PEN", "USD"] | None = Field(description="Moneda explícita: PEN para soles, USD para dólares; desconocida: null.")
    numero_operacion: str | None = Field(description="Identificador de operación tal como se lee, conservando ceros iniciales.")
    codigo_unidad: str | None = Field(description="Departamento o unidad explícitos en el documento. No deducir del pagador, archivo o metadatos.")
    periodo: str | None = Field(description="Periodo o mes de mantenimiento mencionado explícitamente. No deducir de la fecha.")
    mensaje: str | None = Field(description="Mensaje o concepto literal de la transferencia, cuando sea visible.")
    cuenta_origen_ultimos4: str | None = Field(pattern=r"^\d{4}$", description="Únicamente los cuatro últimos dígitos visibles y verificables de la cuenta de origen.")
    cuenta_destino_ultimos4: str | None = Field(pattern=r"^\d{4}$", description="Únicamente los cuatro últimos dígitos visibles y verificables de la cuenta de destino.")
    tipo_documento: Literal["transferencia", "deposito", "yape", "plin", "otro"] | None
    beneficiario: str | None = Field(description="Nombre del receptor tal como aparece; no inferir ni identificar mediante fuentes externas.")
    advertencias: list[str] = Field(description="Ambigüedades, contradicciones, texto ilegible o evidencia insuficiente; [] si no hay.")

    @field_validator(
        "banco", "numero_operacion", "codigo_unidad", "periodo", "mensaje", "beneficiario",
        "cuenta_origen_ultimos4", "cuenta_destino_ultimos4", mode="before"
    )
    @classmethod
    def empty_text_is_null(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("fecha_pago", mode="before")
    @classmethod
    def require_unambiguous_date(cls, value: Any) -> Any:
        if value is None or (isinstance(value, date) and not isinstance(value, datetime)):
            return value
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Use una fecha ISO inequívoca YYYY-MM-DD o null si la fuente es ambigua")
        return value

    @field_validator("monto", mode="before")
    @classmethod
    def amount_must_be_number(cls, value: Any) -> Any:
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError("El monto debe ser un número JSON, sin símbolos ni separadores de miles")
        return value


class JudgeFinding(StrictModel):
    campo: str
    gravedad: Literal["baja", "media", "alta", "critica"]
    descripcion: str
    evidencia: str | None
    sugerencia: str
    pregunta_verificacion: str


class JudgeVerdict(StrictModel):
    decision: Literal["approved", "needs_review", "rejected"]
    hallazgos: list[JudgeFinding]
    motivo: str
    reextraer: bool


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
    record_before: PaymentRecord | None = None
    record_after: PaymentRecord | None = None
    judge_verdict: JudgeVerdict | None = None


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
    record: PaymentRecord | None
    attempts: int
    reasons: list[str]
    attempt_log: list[AttemptLog]
    judge_verdict: JudgeVerdict | None = None
    human_review_required: bool = False


class BatchMetrics(StrictModel):
    total: int
    successful: int
    partial: int
    failed: int
    success_rate: float
    partial_rate: float
    failure_rate: float
    total_attempts: int


class BatchReport(StrictModel):
    schema_version: str = "1.0.0"
    mode: str
    provider: str
    judge: str | None
    started_at: datetime
    completed_at: datetime
    max_attempts: int
    results: list[DocumentResult]
    metrics: BatchMetrics
    events: list[PipelineEvent]

