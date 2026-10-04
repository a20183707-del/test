import pytest
from pydantic import ValidationError

from bsg_extractor.schema import ExtractionSchema, FieldSpec
from bsg_extractor.validation import (InvalidJSONError, RecordValidationError,
                                          compare_reference, validate_business_rules,
                                          validate_record)


def schema():
    return ExtractionSchema(title="Documento personalizado", fields=[
        FieldSpec(name="nombre", type="string"),
        FieldSpec(name="valor", type="number", minimum=1),
        FieldSpec(name="fecha", type="date"),
        FieldSpec(name="categoria", type="enum", enum_values=["A", "B"]),
        FieldSpec(name="activo", type="boolean"),
        FieldSpec(name="cantidad", type="integer", required=False),
    ])


def valid_record():
    return {"nombre": "Ejemplo", "valor": 42, "fecha": "2026-10-04",
            "categoria": "A", "activo": True, "cantidad": None}


@pytest.mark.parametrize("output", ['{"nombre": "a", "nombre": "b"}', '{"valor": NaN}', '[]', '```json\n{}\n```'])
def test_rejects_non_strict_json(output):
    with pytest.raises(InvalidJSONError):
        validate_record(output, schema())


@pytest.mark.parametrize("field,value", [("valor", "42"), ("valor", True), ("valor", -1),
                                        ("fecha", "04/10/2026"), ("fecha", "2026-02-30"),
                                        ("categoria", "C"), ("activo", 1), ("cantidad", 2.0)])
def test_types_and_formats_are_independent(field, value):
    record = {**valid_record(), field: value}
    with pytest.raises(RecordValidationError):
        validate_record(record, schema())


def test_missing_key_and_null_have_different_meanings():
    record = valid_record()
    del record["fecha"]
    with pytest.raises(RecordValidationError):
        validate_record(record, schema())
    record["fecha"] = None
    assert validate_business_rules(validate_record(record, schema()), schema()).status == "parcial"


def test_optional_null_is_complete_and_extra_key_is_invalid():
    assert validate_business_rules(valid_record(), schema()).status == "exitoso"
    with pytest.raises(RecordValidationError):
        validate_record({**valid_record(), "no_solicitado": "dato"}, schema())


def test_schema_duplicate_names_and_enum_rules():
    with pytest.raises(ValidationError):
        ExtractionSchema(title="x", fields=[FieldSpec(name="Campo", type="string"), FieldSpec(name="campo", type="string")])
    with pytest.raises(ValidationError):
        FieldSpec(name="categoria", type="enum")


def test_reference_comparison_numbers_but_not_booleans_and_provenance():
    reference = compare_reference({"valor": 42.0, "activo": 1}, {"valor": 42, "activo": True},
                                  reference_source="Archivo de referencia de pruebas")
    assert reference["accuracy_percent"] == 50
    assert reference["independent_human_review"] is False
    assert reference["reference_source"] == "Archivo de referencia de pruebas"
