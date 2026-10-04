"""Validación local estricta e independiente de las promesas del proveedor."""
from __future__ import annotations

import json
import math
import re
from datetime import date
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .schema import ExtractionSchema, ValidationResult

ModelT = TypeVar("ModelT", bound=BaseModel)


class InvalidJSONError(ValueError):
    pass


class RecordValidationError(ValueError):
    def __init__(self, messages: list[str]):
        super().__init__("; ".join(messages))
        self.messages = messages


def _reject_nonfinite(value: str) -> None:
    raise InvalidJSONError("JSON contiene un número no finito.")


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidJSONError("JSON contiene claves repetidas.")
        result[key] = value
    return result


def parse_object(output: str | dict[str, Any] | BaseModel) -> dict[str, Any]:
    if isinstance(output, BaseModel):
        output = output.model_dump(mode="json")
    if isinstance(output, str):
        try:
            output = json.loads(output, parse_constant=_reject_nonfinite, object_pairs_hook=_unique_keys)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise InvalidJSONError("La respuesta no es JSON válido.") from None
    if not isinstance(output, dict):
        raise InvalidJSONError("La respuesta debe ser un objeto JSON.")
    return output


def validate_output(output: str | dict[str, Any] | ModelT, model: type[ModelT]) -> ModelT:
    return model.model_validate(parse_object(output))


def safe_validation_messages(error: ValidationError) -> list[str]:
    return [f"{'.'.join(map(str, item['loc'])) or 'documento'}: {item['type']}"
            for item in error.errors(include_url=False, include_context=False, include_input=False)]


def validate_record(output: str | dict[str, Any], schema: ExtractionSchema) -> dict[str, Any]:
    record = parse_object(output)
    names = {field.name for field in schema.fields}
    errors: list[str] = []
    if set(record) - names:
        errors.append("La respuesta contiene campos no definidos en el esquema.")
    for field in schema.fields:
        if field.name not in record:
            errors.append(f"{field.name}: falta la clave; usa null para un dato ausente.")
            continue
        value = record[field.name]
        if value is None:
            continue
        valid = False
        if field.type in ("string", "enum", "date"):
            valid = isinstance(value, str) and bool(value.strip())
            if valid and field.type == "enum":
                valid = value in field.enum_values
            if valid and field.type == "date":
                try:
                    valid = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)) and date.fromisoformat(value).isoformat() == value
                except ValueError:
                    valid = False
        elif field.type == "boolean":
            valid = isinstance(value, bool)
        elif field.type in ("number", "integer"):
            valid = type(value) in (int, float) and (field.type != "integer" or type(value) is int)
            try:
                valid = valid and math.isfinite(value)
            except OverflowError:
                valid = False
            if valid and field.minimum is not None:
                valid = value >= field.minimum
            if valid and field.maximum is not None:
                valid = value <= field.maximum
        if not valid:
            errors.append(f"{field.name}: tipo, formato o restricción {field.type} inválidos.")
        elif isinstance(value, str) and len(value) > 10000:
            errors.append(f"{field.name}: valor demasiado largo.")
    if errors:
        raise RecordValidationError(errors)
    return record


def validate_business_rules(record: dict[str, Any], schema: ExtractionSchema) -> ValidationResult:
    missing = [f.name for f in schema.fields if f.required and record.get(f.name) is None]
    reasons = [f"Falta dato obligatorio verificable: {name}." for name in missing]
    if not any(value is not None for value in record.values()):
        return ValidationResult(status="fallido", reasons=["No se recuperaron datos utilizables.", *reasons], missing_fields=missing)
    return ValidationResult(status="parcial" if missing else "exitoso", reasons=reasons, missing_fields=missing)


def compare_reference(record: dict[str, Any] | None, reference: dict[str, Any], *,
                      reference_source: str = "Referencia proporcionada",
                      independent_human_review: bool = False) -> dict[str, Any]:
    """Referencia explícita con su procedencia; nunca se infiere del modelo."""
    def equivalent(obtained: Any, expected: Any) -> bool:
        if type(obtained) in (int, float) and type(expected) in (int, float):
            return obtained == expected
        return type(obtained) is type(expected) and obtained == expected

    fields = [{"field": name, "matches": record is not None and name in record and equivalent(record[name], value)}
              for name, value in reference.items()]
    correct = sum(item["matches"] for item in fields)
    return {"compared_fields": len(fields), "correct_fields": correct,
            "accuracy_percent": round(correct / len(fields) * 100, 2) if fields else None,
            "fields": fields, "reference_source": reference_source,
            "independent_human_review": independent_human_review}
