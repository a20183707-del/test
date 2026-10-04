"""Seguridad y contratos del servidor local; no realizan llamadas a Gemini."""
from __future__ import annotations

import json
import threading
import time

from fastapi.testclient import TestClient
import pytest

from bsg_extractor import server
from bsg_extractor.sessions import SessionStore

SCHEMA = {"title": "Documento general", "fields": [{"name": "titulo", "type": "string", "required": True},
                                                         {"name": "cantidad", "type": "number", "required": False}]}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(server, "store", SessionStore())
    with TestClient(server.app, base_url="http://127.0.0.1:8765") as test_client:
        session = test_client.get("/api/session")
        test_client.headers["X-CSRF-Token"] = session.json()["csrf_token"]
        test_client.headers["Origin"] = "http://127.0.0.1:8765"
        yield test_client


def test_session_http_only_strict_and_secret_never_returned(client, caplog):
    response = client.get("/api/session")
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert response.json()["has_api_key"] is False
    assert response.json()["schema"] is None
    dummy_secret = "offline-dummy-secret-only"
    response = client.post("/api/key", json={"api_key": dummy_secret})
    assert response.status_code == 200
    assert dummy_secret not in response.text
    assert dummy_secret not in client.get("/api/session").text
    assert dummy_secret not in caplog.text
    assert client.get("/api/session").json()["has_api_key"] is True
    assert client.delete("/api/key").json()["has_api_key"] is False


def test_environment_key_fallback_never_exposes_secret(client, monkeypatch, caplog):
    dummy_environment_secret = "offline-dummy-environment-secret"
    monkeypatch.setenv("GEMINI_API_KEY", dummy_environment_secret)
    response = client.get("/api/session")
    assert response.json()["has_api_key"] is True and response.json()["key_source"] == "environment"
    assert dummy_environment_secret not in response.text
    response = client.delete("/api/key")
    assert response.json()["has_api_key"] is True
    assert dummy_environment_secret not in response.text and dummy_environment_secret not in caplog.text


@pytest.mark.parametrize("host", ["evil.example:8765", "localhost.evil.example:8765", "127.0.0.1:9999", "0.0.0.0:8765"])
def test_dns_rebinding_hosts_rejected(client, host):
    assert client.get("/api/session", headers={"Host": host}).status_code == 403


def test_cross_origin_and_csrf_rejected(client):
    assert client.post("/api/key", json={"api_key": "dummy-secret"}, headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/api/key", json={"api_key": "dummy-secret"}, headers={"Origin": "http://localhost:8765"}).status_code == 403
    assert client.post("/api/key", json={"api_key": "dummy-secret"}, headers={"X-CSRF-Token": "incorrect"}).status_code == 403
    assert "access-control-allow-origin" not in client.get("/api/health").headers


def test_text_original_in_memory_and_private_to_session(client):
    text = "Documento de investigación\nCantidad: 4"
    response = client.post("/api/documents/text", json={"name": "Investigación", "text": text})
    assert response.status_code == 200
    document = response.json()["documents"][0]
    assert len(document["sha256"]) == 64 and document["token_estimate"]["estimated"]
    assert client.get(document["preview_url"]).text == text
    with TestClient(server.app, base_url="http://127.0.0.1:8765") as other:
        other.get("/api/session")
        assert other.get(document["preview_url"]).status_code == 404


def test_uploads_preserve_original_and_strip_path(client):
    response = client.post("/api/documents", files=[("files", ("../../local.txt", b"Fuente original", "text/plain"))])
    assert response.status_code == 200
    document = response.json()["documents"][0]
    assert document["name"] == "local.txt"
    assert client.get(document["preview_url"]).content == b"Fuente original"
    assert client.get("/api/documents").json()["documents"][0]["id"] == document["id"]
    assert client.delete("/api/documents/" + document["id"]).status_code == 200
    assert client.get(document["preview_url"]).status_code == 404


def test_unsupported_and_empty_input_rejected(client):
    assert client.post("/api/documents", files={"files": ("malicious.html", b"<script>evil</script>", "text/html")}).status_code == 400
    assert client.post("/api/documents/text", json={"text": "  "}).status_code == 400
    assert client.post("/api/documents/text", content="{not json}", headers={"Content-Type": "application/json"}).status_code == 400


def test_document_count_and_request_limit(client, monkeypatch):
    for number in range(20):
        assert client.post("/api/documents/text", json={"text": f"Documento {number}"}).status_code == 200
    assert client.post("/api/documents/text", json={"text": "Documento 21"}).status_code == 413
    monkeypatch.setattr(server, "MAX_REQUEST_BYTES", 12)
    assert client.post("/api/documents/text", json={"text": "Demasiado largo"}).status_code == 413


def test_schema_custom_and_analysis_without_key(client):
    saved = client.put("/api/schema", json={"schema": SCHEMA})
    assert saved.status_code == 200 and saved.json()["schema"]["title"] == "Documento general"
    document_id = client.post("/api/documents/text", json={"text": "Título: informe"}).json()["documents"][0]["id"]
    response = client.post("/api/batches", json={"document_ids": [document_id], "schema": SCHEMA})
    assert response.status_code == 409
    assert "API key" in response.json()["detail"]
    assert client.post("/api/schema/propose", json={"instructions": "Título y cantidad"}).status_code == 404


def test_models_validated_and_saved_with_key(client):
    response = client.post("/api/key", json={"api_key": "dummy-secret-test", "extractor": "gemini-3.5-flash-lite", "reviewer": "gemini-3.8-flash"})
    assert response.status_code == 200
    assert client.get("/api/session").json()["models"]["reviewer"] == "gemini-3.8-flash"
    assert client.post("/api/key", json={"api_key": "dummy-secret-test", "extractor": "../../evil"}).status_code == 400


def test_key_format_allows_point_and_rejects_header_injection(client, caplog):
    dummy_key = "AQ.offline-dummy-secret-test"
    response = client.post("/api/key", json={"api_key": dummy_key})
    assert response.status_code == 200 and dummy_key not in response.text
    for invalid in [" leading-space-key", "trailing-space-key ", "key\nHeader:value", "key/invalid-format"]:
        response = client.post("/api/key", json={"api_key": invalid})
        assert response.status_code == 400 and invalid not in response.text
    assert dummy_key not in caplog.text


def test_expiration_and_explicit_deletion_wipe_memory():
    sessions = SessionStore(ttl=10)
    session = sessions.create()
    session.api_key = "dummy-secret-test"
    session.originals["a"] = b"documento privado"
    session.expires_at = time.monotonic() - 1
    assert sessions.get(session.id) is None
    assert session.api_key is None and session.originals == {}
    session = sessions.create()
    session.api_key = "dummy-secret-test"
    sessions.delete(session.id)
    assert session.api_key is None


def test_progress_success_is_processed_denominator():
    metrics = server._progress_metrics(20, [{"status": "exitoso", "attempts": 1}, {"status": "parcial", "attempts": 2}])
    assert metrics["success_rate"] == 50 and metrics["processed"] == 2 and metrics["total"] == 20
    assert server._empty_metrics(20)["success_rate"] is None


def test_supervision_threshold_uses_actual_processed_documents():
    assert server._supervision(server._empty_metrics(20))["required"] is False
    before_three = server._progress_metrics(20, [{"status": "exitoso", "attempts": 1}, {"status": "parcial", "attempts": 1}])
    assert server._supervision(before_three)["required"] is False
    assert server._supervision(before_three, completed=True)["required"] is True
    below_threshold = server._progress_metrics(20, [{"status": "exitoso", "attempts": 1}, {"status": "exitoso", "attempts": 1}, {"status": "fallido", "attempts": 1}])
    supervision = server._supervision(below_threshold)
    assert supervision["required"] is True and supervision["processed"] == 3 and supervision["threshold"] == 70
    assert server._supervision({"processed": 10, "success_rate": 70})["required"] is False


def test_human_review_preserves_original_and_success_metrics(client):
    session = server.store.get(client.cookies[server.COOKIE_NAME])
    result = {"document_id": "doc-a", "status": "parcial", "record": {"titulo": None, "cantidad": 4}, "attempts": 1}
    session.batches["batch-a"] = {"status": "completed", "results": [result], "schema": SCHEMA, "human_reviews": [],
                                  "metrics": {"success_rate": 0}, "report": {"results": [result]}}
    invalid = client.post("/api/batches/batch-a/review", json={"document_id": "doc-a", "corrected_data": {"titulo": "Revisión", "cantidad": "cuatro"}, "note": "Lectura humana de la fuente"})
    assert invalid.status_code == 422
    response = client.post("/api/batches/batch-a/review", json={"document_id": "doc-a", "corrected_data": {"titulo": "Revisión", "cantidad": 4}, "note": "Lectura humana de la fuente"})
    assert response.status_code == 200
    assert response.json()["review"]["changes_pipeline_success"] is False
    assert result["record"]["titulo"] is None and session.batches["batch-a"]["metrics"]["success_rate"] == 0
    exported = client.get("/api/batches/batch-a/export?format=json")
    assert exported.status_code == 200
    assert json.loads(exported.content)["human_reviews"][0]["original_record"]["titulo"] is None


def test_background_batch_contract_with_explicit_injected_providers(client, monkeypatch):
    """La inyección sólo existe en esta prueba; no hay modo simulación en la API."""
    from bsg_extractor import providers, reviewer
    from bsg_extractor.schema import ProviderResponse, TokenUsage

    class InjectedExtractor:
        mode = "test_injected"
        model = "offline-test-extractor"

        def __init__(self, *args, **kwargs):
            pass

        def extract(self, *args, **kwargs):
            return ProviderResponse(text='{"titulo":"Estudio", "cantidad":4}', model=self.model,
                                    usage=TokenUsage(total_calls=0))

    class InjectedReviewer(InjectedExtractor):
        model = "offline-test-reviewer"

        def review(self, *args, **kwargs):
            fields = [{"field": name, "status": "supported", "evidence": evidence, "location": "texto",
                       "problem": None, "severity": "none", "proposed_value": None,
                       "verification_question": "Comprobar en fuente"}
                      for name, evidence in [("titulo", "Estudio"), ("cantidad", "4")]]
            text = json.dumps({"decision": "approved", "fields": fields, "reason": "Prueba offline inyectada",
                               "should_retry": False})
            return ProviderResponse(text=text, model=self.model, usage=TokenUsage(total_calls=0))

    monkeypatch.setattr(providers, "GeminiProvider", InjectedExtractor)
    monkeypatch.setattr(reviewer, "GeminiReviewer", InjectedReviewer)
    client.post("/api/key", json={"api_key": "offline-dummy-secret-test"})
    document_id = client.post("/api/documents/text", json={"text": "Estudio\nCantidad: 4"}).json()["documents"][0]["id"]
    response = client.post("/api/batches", json={"document_ids": [document_id], "schema": SCHEMA})
    assert response.status_code == 202
    batch_id = response.json()["id"]
    for _ in range(50):
        batch = client.get("/api/batches/" + batch_id).json()
        if batch["status"] != "running":
            break
        time.sleep(0.01)
    assert batch["status"] == "completed" and batch["mode"] == "test_injected"
    assert batch["report"]["metrics"]["real_success_rate"] is None
    assert batch["results"][0]["record"]["cantidad"] == 4
    assert batch["events"][-1]["snapshot"]["result"]["status"] == "exitoso"
    for export_format in ["json", "csv"]:
        exported = client.get(f"/api/batches/{batch_id}/export?format={export_format}")
        assert exported.status_code == 200
        assert "test_injected" in exported.text
        assert "offline-dummy-secret-test" not in exported.text
    assert client.get(f"/api/batches/{batch_id}/export?format=html").status_code == 400


def test_background_setup_exception_finishes_batch(client, monkeypatch):
    from bsg_extractor import providers

    def injected_constructor_failure(*args, **kwargs):
        raise RuntimeError("Injected constructor failure (offline test)")

    monkeypatch.setattr(providers, "GeminiProvider", injected_constructor_failure)
    client.post("/api/key", json={"api_key": "offline-dummy-secret-test"})
    document_id = client.post("/api/documents/text", json={"text": "Documento original"}).json()["documents"][0]["id"]
    response = client.post("/api/batches", json={"document_ids": [document_id], "schema": SCHEMA})
    batch_id = response.json()["id"]
    for _ in range(50):
        batch = client.get("/api/batches/" + batch_id).json()
        if batch["status"] != "running":
            break
        time.sleep(0.01)
    assert batch["status"] == "failed"
    assert "constructor failure" not in batch["error"]


def test_deleting_key_stops_future_model_calls(client, monkeypatch):
    from bsg_extractor import providers, reviewer
    from bsg_extractor.schema import ProviderResponse, TokenUsage

    started, release = threading.Event(), threading.Event()
    calls = {"extract": 0, "review": 0}

    class InjectedExtractor:
        mode = "test_injected"
        model = "offline-test"

        def __init__(self, *args, **kwargs):
            pass

        def extract(self, *args, **kwargs):
            calls["extract"] += 1
            started.set()
            assert release.wait(timeout=2)
            return ProviderResponse(text='{"titulo":"Estudio", "cantidad":4}', model=self.model,
                                    usage=TokenUsage(total_calls=0))

    class InjectedReviewer(InjectedExtractor):
        def review(self, *args, **kwargs):
            calls["review"] += 1
            raise AssertionError("No debe llamarse al revisor después del borrado de la clave")

    monkeypatch.setattr(providers, "GeminiProvider", InjectedExtractor)
    monkeypatch.setattr(reviewer, "GeminiReviewer", InjectedReviewer)
    client.post("/api/key", json={"api_key": "offline-dummy-secret-test"})
    ids = [client.post("/api/documents/text", json={"text": "Estudio\nCantidad: 4"}).json()["documents"][0]["id"] for _ in range(2)]
    batch_id = client.post("/api/batches", json={"document_ids": ids, "schema": SCHEMA}).json()["id"]
    assert started.wait(timeout=1)
    assert client.delete("/api/key").status_code == 200
    release.set()
    for _ in range(50):
        batch = client.get("/api/batches/" + batch_id).json()
        if batch["status"] != "running":
            break
        time.sleep(0.01)
    assert batch["status"] == "completed"
    assert calls == {"extract": 1, "review": 0}
    assert [item["status"] for item in batch["results"]] == ["parcial", "fallido"]
    assert batch["usage"]["total_calls"] == 0  # Las dos llamadas canceladas nunca salieron al proveedor.


def test_incremental_usage_history_and_session_total_across_batches(client, monkeypatch):
    """Métricas inyectadas en pytest únicamente: valida publicación tras cada llamada."""
    from bsg_extractor import providers, reviewer
    from bsg_extractor.schema import ProviderResponse, TokenUsage

    review_started, release_review = threading.Event(), threading.Event()

    class InjectedExtractor:
        mode = "test_injected"
        model = "offline-test-extractor"

        def __init__(self, *args, **kwargs):
            pass

        def extract(self, *args, **kwargs):
            return ProviderResponse(text='{"titulo":"Estudio", "cantidad":4}', model=self.model,
                                    usage=TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15,
                                                     source="provider", complete=True, measured_calls=1, total_calls=1))

    class InjectedReviewer(InjectedExtractor):
        model = "offline-test-reviewer"

        def review(self, *args, **kwargs):
            review_started.set()
            assert release_review.wait(timeout=2)
            fields = [{"field": name, "status": "supported", "evidence": evidence, "location": "texto",
                       "problem": None, "severity": "none", "proposed_value": None,
                       "verification_question": "Comprobar en fuente"}
                      for name, evidence in [("titulo", "Estudio"), ("cantidad", "4")]]
            text = json.dumps({"decision": "approved", "fields": fields, "reason": "Prueba offline inyectada",
                               "should_retry": False})
            return ProviderResponse(text=text, model=self.model,
                                    usage=TokenUsage(input_tokens=20, output_tokens=10, total_tokens=30,
                                                     source="provider", complete=True, measured_calls=1, total_calls=1))

    monkeypatch.setattr(providers, "GeminiProvider", InjectedExtractor)
    monkeypatch.setattr(reviewer, "GeminiReviewer", InjectedReviewer)
    client.post("/api/key", json={"api_key": "offline-dummy-secret-test"})
    document_id = client.post("/api/documents/text", json={"text": "Estudio\nCantidad: 4"}).json()["documents"][0]["id"]
    first_batch = client.post("/api/batches", json={"document_ids": [document_id], "schema": SCHEMA}).json()["id"]
    assert review_started.wait(timeout=1)
    batch = client.get("/api/batches/" + first_batch).json()
    assert batch["status"] == "running" and batch["metrics"]["processed"] == 0
    assert batch["usage"]["total_tokens"] == 15 and len(batch["usage_history"]) == 1
    session = client.get("/api/session").json()
    assert session["total_usage"]["total_tokens"] == 15
    assert session["usage_history"][0]["batch_id"] == first_batch
    release_review.set()
    for _ in range(50):
        batch = client.get("/api/batches/" + first_batch).json()
        if batch["status"] != "running":
            break
        time.sleep(0.01)
    assert batch["status"] == "completed" and batch["usage"]["total_tokens"] == 45
    assert [item["role"] for item in batch["usage_history"]] == ["extraction", "review"]
    assert batch["supervision"]["required"] is False
    second_batch = client.post("/api/batches", json={"document_ids": [document_id], "schema": SCHEMA}).json()["id"]
    for _ in range(50):
        second = client.get("/api/batches/" + second_batch).json()
        if second["status"] != "running":
            break
        time.sleep(0.01)
    session = client.get("/api/session").json()
    assert second["status"] == "completed" and second["session_usage"]["total_tokens"] == 90
    assert session["total_usage"]["total_tokens"] == 90 and len(session["usage_history"]) == 4
    assert len({item["id"] for item in session["usage_history"]}) == 4
    report = client.get(f"/api/batches/{first_batch}/export?format=json").json()
    assert len(report["usage_history"]) == 2


def test_session_usage_unknown_if_any_sent_call_has_no_metadata(client):
    session = server.store.get(client.cookies[server.COOKIE_NAME])
    session.usage_history = [{"id": "known", "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15,
                                                        "source": "provider", "complete": True,
                                                        "total_calls": 1, "measured_calls": 1}},
                             {"id": "unknown", "usage": {"total_calls": 1, "measured_calls": 0}}]
    response = client.get("/api/session").json()
    assert response["total_usage"]["total_tokens"] is None
    assert response["total_usage"]["complete"] is False
    assert response["usage_history"][0]["usage"]["total_tokens"] == 15
