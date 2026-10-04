import io
import json
import urllib.error

import pytest

from bsg_extractor.inputs import from_text
from bsg_extractor.providers import GeminiProvider, ProviderError, validate_api_key
from bsg_extractor.reviewer import GeminiReviewer
from bsg_extractor.schema import ExtractionSchema, FieldSpec, ReviewVerdict, SourceDocument, VerificationResult
from pydantic import ValidationError


class Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, size):
        return self.payload[:size]


def envelope(text='{"valor":42}', finish="STOP"):
    return {"candidates": [{"content": {"parts": [{"text": "NO REVELAR", "thought": True}, {"text": text}]}, "finishReason": finish}],
            "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20,
                              "thoughtsTokenCount": 5, "totalTokenCount": 125}}


def schema():
    return ExtractionSchema(title="Campos pedidos", fields=[FieldSpec(name="valor", type="number")])


def test_native_schema_and_key_only_in_header_and_usage():
    captured = []

    def open_request(request, timeout):
        captured.append(request)
        return Response(envelope())

    provider = GeminiProvider("hidden_test_key", opener=open_request)
    response = provider.extract(from_text("valor:42"), schema())
    request = captured[0]
    body = json.loads(request.data)
    assert "hidden_test_key" not in request.full_url
    assert "hidden_test_key" not in request.data.decode()
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseJsonSchema"]["additionalProperties"] is False
    assert response.text == '{"valor":42}'
    assert response.usage.total_tokens == 125
    assert response.usage.thinking_tokens == 5
    assert response.usage.estimated_input_tokens is not None


@pytest.mark.parametrize("status,code,retryable", [(403, "authentication", False), (404, "model_not_found", False),
                                                 (429, "rate_limit", False), (503, "http_503", True)])
def test_http_errors_are_sanitized_and_do_not_retry(status, code, retryable):
    calls = []

    def fail(request, timeout):
        calls.append(request)
        raise urllib.error.HTTPError(request.full_url, status, "hidden_test_key", {}, io.BytesIO(b"PRIVATE_SOURCE hidden_test_key"))

    with pytest.raises(ProviderError) as raised:
        GeminiProvider("hidden_test_key", opener=fail).extract(from_text("Fuente"), schema())
    assert len(calls) == 1
    assert raised.value.code == code
    assert raised.value.retryable is retryable
    assert "hidden_test_key" not in str(raised.value)
    assert "PRIVATE_SOURCE" not in str(raised.value)


def test_google_project_denial_is_distinct_from_key_failure_and_never_exposes_details():
    payload = {"error": {"code": 403, "status": "PERMISSION_DENIED",
                         "message": "Your project has been denied access. Please contact support.",
                         "details": [{"private_source": "PRIVATE_SOURCE", "credential": "hidden_test_key"}]}}
    calls = []

    def fail(request, timeout):
        calls.append(request)
        raise urllib.error.HTTPError(request.full_url, 403, "hidden_test_key", {},
                                     io.BytesIO(json.dumps(payload).encode()))

    with pytest.raises(ProviderError) as raised:
        GeminiProvider("hidden_test_key", opener=fail).extract(from_text("Fuente"), schema())
    assert len(calls) == 1
    assert raised.value.code == "project_access_denied"
    assert raised.value.retryable is False
    assert "proyecto" in str(raised.value) and "soporte" in str(raised.value)
    assert "credencial" not in str(raised.value)
    assert "hidden_test_key" not in str(raised.value)
    assert "PRIVATE_SOURCE" not in str(raised.value)


def test_403_body_read_is_bounded_and_unrecognized_messages_are_sanitized():
    sizes = []

    class BoundedBody(io.BytesIO):
        def read(self, size=-1):
            sizes.append(size)
            return super().read(size)

    payload = {"error": {"status": "PERMISSION_DENIED", "message": "hidden_test_key PRIVATE_SOURCE " + "x" * 20000}}

    def fail(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, "hidden_test_key", {}, BoundedBody(json.dumps(payload).encode()))

    with pytest.raises(ProviderError) as raised:
        GeminiProvider("hidden_test_key", opener=fail).extract(from_text("Fuente"), schema())
    assert sizes == [16 * 1024 + 1]
    assert raised.value.code == "authentication"
    assert "hidden_test_key" not in str(raised.value)
    assert "PRIVATE_SOURCE" not in str(raised.value)


def test_usage_retained_on_incomplete_response():
    with pytest.raises(ProviderError) as raised:
        GeminiProvider("hidden_test_key", opener=lambda *args, **kw: Response(envelope(finish="MAX_TOKENS"))).extract(from_text("Fuente"), schema())
    assert raised.value.usage.total_tokens == 125


def test_absent_usage_is_unknown_not_zero():
    payload = envelope()
    payload.pop("usageMetadata")
    response = GeminiProvider("hidden_test_key", opener=lambda *args, **kw: Response(payload)).extract(from_text("Fuente"), schema())
    assert response.usage.source == "unavailable"
    assert response.usage.total_tokens is None
    assert response.usage.estimated_input_tokens is not None
    assert not response.usage.complete


def test_current_key_formats_support_period_and_reject_whitespace_without_echo():
    credential = "AQ.synthetic.key_for_test_123"
    assert validate_api_key(credential) == credential
    provider = GeminiProvider(credential, opener=lambda *args, **kw: Response(envelope()))
    assert provider.extract(from_text("Fuente"), schema()).usage.total_tokens == 125
    for invalid in (" " + credential, credential + "\n", credential + "\t", "short", "x" * 513):
        with pytest.raises(ProviderError) as raised:
            validate_api_key(invalid)
        assert credential not in str(raised.value)
        assert raised.value.usage.total_calls == 0


def test_source_preparation_failure_is_not_a_sent_api_call():
    captured = []
    provider = GeminiProvider("hidden_test_key", opener=lambda *args, **kw: captured.append(args))
    invalid = SourceDocument(id="doc", name="archivo.pdf", mime="application/pdf", text="vista sin archivo")
    with pytest.raises(ProviderError) as raised:
        provider.extract(invalid, schema())
    assert raised.value.code == "invalid_document"
    assert raised.value.usage.total_calls == 0
    assert not captured


def test_verification_reads_original_without_candidate_or_suggested_values():
    captured = []

    def open_request(request, timeout):
        captured.append(json.loads(request.data))
        return Response(envelope('{"fields":[]}'))

    reviewer = GeminiReviewer("hidden_test_key", opener=open_request)
    reviewer.review(from_text("valor original:42"), {"valor": 999999}, schema())
    reviewer.verify(from_text("valor original:42"), schema(), [{"field": "valor", "type": "number", "question": "¿Qué valor aparece explícitamente?"}])
    assert "999999" in json.dumps(captured[0])
    assert "999999" not in json.dumps(captured[1])
    assert "original:42" in json.dumps(captured[1])


def test_reviewer_native_schema_omits_rejected_maxitems_but_local_limit_remains():
    captured = []

    def open_request(request, timeout):
        captured.append(json.loads(request.data))
        return Response(envelope('{"fields":[]}'))

    reviewer = GeminiReviewer("hidden_test_key", opener=open_request)
    reviewer.review(from_text("valor original:42"), {"valor": 42}, schema())
    reviewer.verify(from_text("valor original:42"), schema(), [{"field": "valor", "question": "¿Qué valor consta?"}])
    for body in captured:
        native = body["generationConfig"]["responseJsonSchema"]
        assert "maxItems" not in native["properties"]["fields"]
        assert native["properties"]["fields"]["items"]["additionalProperties"] is False

    field = {"field": "valor", "status": "supported", "evidence": "42", "location": "texto",
             "problem": None, "severity": "none", "proposed_value": 42, "verification_question": "¿Qué valor consta?"}
    verdict = {"decision": "approved", "fields": [field] * 41, "reason": "Verificado", "should_retry": False}
    with pytest.raises(ValidationError):
        ReviewVerdict.model_validate(verdict)
    verification = {"fields": [{"field": "valor", "observed_value": 42, "evidence": "42", "location": "texto",
                                 "answer": "42", "answerable": True}] * 41}
    with pytest.raises(ValidationError):
        VerificationResult.model_validate(verification)
