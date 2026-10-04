"""Validación independiente del modelo: sintaxis, esquema y reglas de negocio."""

from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .schema import PaymentRecord, ValidationResult

ModelT = TypeVar("ModelT", bound=BaseModel)


class InvalidJSONError(ValueError):
    """La salida no es un objeto JSON estricto."""


def _reject_nonfinite(value: str) -> None:
    raise InvalidJSONError("JSON contiene un número no finito")


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidJSONError("JSON contiene claves repetidas")
        result[key] = value
    return result


def validate_output(output: str | dict[str, Any] | ModelT, model: type[ModelT]) -> ModelT:
    """No rescata texto entre fences ni rellena claves faltantes silenciosamente."""
    if isinstance(output, BaseModel):
        # Se vuelve a validar incluso si el proveedor devuelve un modelo construido.
        output = output.model_dump(mode="json")
    if isinstance(output, str):
        try:
            output = json.loads(output, parse_constant=_reject_nonfinite, object_pairs_hook=_unique_keys)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InvalidJSONError("La respuesta no es JSON válido") from exc
    if not isinstance(output, dict):
        raise InvalidJSONError("La respuesta debe ser un objeto JSON")
    return model.model_validate(output)


def safe_validation_messages(error: ValidationError) -> list[str]:
    """Feedback útil sin registrar valores completos ni el texto de respuestas."""
    return [
        f"{'.'.join(map(str, item['loc'])) or 'documento'}: {item['type']}"
        for item in error.errors(include_url=False, include_context=False, include_input=False)
    ]


def validate_business_rules(record: PaymentRecord) -> ValidationResult:
    """La fecha del depósito no prueba el periodo ni la identidad de la unidad."""
    essential = ("fecha_pago", "monto", "moneda", "numero_operacion", "codigo_unidad")
    missing = [name for name in essential if getattr(record, name) is None]
    reasons = [f"Falta dato esencial verificable: {name}." for name in missing]
    reasons.extend(f"Advertencia de extracción: {warning}" for warning in record.advertencias if warning.strip())
    usable = any(getattr(record, name) is not None for name in ("fecha_pago", "monto", "numero_operacion", "codigo_unidad"))
    if not usable:
        return ValidationResult(status="fallido", reasons=["No se recuperaron datos de pago utilizables.", *reasons], missing_fields=missing)
    if reasons:
        return ValidationResult(status="parcial", reasons=reasons, missing_fields=missing)
    return ValidationResult(status="exitoso", reasons=["Datos esenciales presentes y validación independiente superada."], missing_fields=[])
