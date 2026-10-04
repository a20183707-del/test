"""API local: originales privados, credenciales efímeras y resultados verificables."""
from __future__ import annotations

import copy
import asyncio
import csv
import io
from contextlib import asynccontextmanager, suppress
import hmac
import json
import os
import secrets
import threading
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import inputs
from .schema import ExtractionSchema
from .sessions import MAX_DOCUMENTS, MAX_SESSION_BYTES, SESSION_TTL_SECONDS, Session, SessionStore

COOKIE_NAME = "bsg_session"
MAX_REQUEST_BYTES = 25 * 1024 * 1024
ALLOWED_HOSTS = {"127.0.0.1:8765", "localhost:8765"}
HUMAN_SUPERVISION_THRESHOLD = 70
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIST = PROJECT_ROOT / "web" / "dist"
store = SessionStore()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async def expire_sessions() -> None:
        while True:
            await asyncio.sleep(30)
            store.expire()

    cleanup = asyncio.create_task(expire_sessions())
    try:
        yield
    finally:
        cleanup.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup
        store.clear()

app = FastAPI(title="BSG Extractor documental local", docs_url=None, redoc_url=None, openapi_url=None,
              lifespan=lifespan)


def _safe_error(message: str, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail=message)


def _session(request: Request) -> Session:
    session = store.get(request.cookies.get(COOKIE_NAME))
    if session is None:
        raise _safe_error("La sesión venció. Recarga la aplicación e ingresa de nuevo la clave.", 401)
    return session


def _serializable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serializable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        payload = json.loads(await request.body(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError):
        raise _safe_error("El cuerpo debe contener JSON válido.") from None
    if not isinstance(payload, dict):
        raise _safe_error("Se esperaba un objeto JSON.")
    return payload


def _schema(raw: Any) -> ExtractionSchema:
    try:
        return ExtractionSchema.model_validate(raw)
    except (ValidationError, ValueError, TypeError):
        raise _safe_error("El esquema no es válido. Revisa nombres, tipos, campos y categorías.") from None


def _credential(session: Session) -> str:
    from .providers import ProviderError, validate_api_key

    key = session.api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise _safe_error("Ingresa una API key de Gemini en Configuración antes de analizar.", 409)
    try:
        return validate_api_key(key)
    except (ValueError, TypeError, ProviderError):
        raise _safe_error("La API key no tiene un formato válido. Reingrésala en Configuración.", 409) from None


def _usage_total(history: list[dict[str, Any]]) -> dict[str, Any]:
    from .pipeline import aggregate_usage
    from .schema import TokenUsage

    return _serializable(aggregate_usage([TokenUsage.model_validate(entry["usage"]) for entry in history]))


def _session_usage(session: Session) -> dict[str, Any]:
    return _usage_total(session.usage_history)


@app.middleware("http")
async def local_security(request: Request, call_next: Any) -> Response:
    """Host + Origin + CSRF: bloquea DNS rebinding y solicitudes de sitios externos."""
    host = request.headers.get("host", "").lower()
    origin = request.headers.get("origin")
    if host not in ALLOWED_HOSTS:
        return JSONResponse({"detail": "Host no permitido. Abre http://127.0.0.1:8765."}, status_code=403)
    if origin is not None and origin != f"http://{host}":
        return JSONResponse({"detail": "Origen externo no permitido."}, status_code=403)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        session = store.get(request.cookies.get(COOKIE_NAME))
        csrf = request.headers.get("x-csrf-token", "")
        if session is None or not hmac.compare_digest(csrf, session.csrf_token):
            return JSONResponse({"detail": "Token de sesión no válido. Recarga la aplicación."}, status_code=403)
    length = request.headers.get("content-length")
    if length is not None:
        try:
            if int(length) > MAX_REQUEST_BYTES or int(length) < 0:
                return JSONResponse({"detail": "La solicitud supera 25 MiB."}, status_code=413)
        except ValueError:
            return JSONResponse({"detail": "Longitud de solicitud inválida."}, status_code=400)
    # Leer por bloques evita que una solicitud chunked sin Content-Length exceda el límite.
    if request.method in {"POST", "PUT", "PATCH"}:
        chunks: list[bytes] = []
        received = 0
        async for chunk in request.stream():
            received += len(chunk)
            if received > MAX_REQUEST_BYTES:
                return JSONResponse({"detail": "La solicitud supera 25 MiB."}, status_code=413)
            chunks.append(chunk)
        request._body = b"".join(chunks)
    try:
        response = await call_next(request)
    except Exception:
        # Evita que Uvicorn registre trazas de excepciones con datos de la petición.
        response = JSONResponse({"detail": "No se pudo completar la operación local."}, status_code=500)
    response.headers.update({
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "SAMEORIGIN",
        "Referrer-Policy": "no-referrer",
        "Cross-Origin-Resource-Policy": "same-origin",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-src 'self' blob:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'self'",
    })
    return response


@app.exception_handler(RequestValidationError)
async def request_validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
    # No devolver input ni trazas; una petición puede contener una credencial.
    return JSONResponse({"detail": "Parámetros de solicitud no válidos."}, status_code=422)


@app.exception_handler(Exception)
async def unexpected_error(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse({"detail": "No se pudo completar la operación local."}, status_code=500)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "application": "bsg-extractor", "version": "1.1.0"}


@app.get("/api/session")
def session_info(request: Request) -> JSONResponse:
    session = store.get(request.cookies.get(COOKIE_NAME))
    if session is None:
        try:
            session = store.create()
        except ValueError as error:
            raise _safe_error(str(error), 429) from None
    with session.lock:
        usage_history = copy.deepcopy(session.usage_history)
        total_usage = _usage_total(usage_history)
    response = JSONResponse({
        "csrf_token": session.csrf_token,
        "has_api_key": bool(session.api_key or os.environ.get("GEMINI_API_KEY", "").strip()),
        "key_source": "session" if session.api_key else "environment" if os.environ.get("GEMINI_API_KEY") else None,
        "session_expires_in": SESSION_TTL_SECONDS,
        "models": {"extractor": session.extractor_model, "reviewer": session.reviewer_model},
        "schema": _serializable(session.schema),
        "latest_batch_id": next(reversed(session.batches), None),
        "usage_history": usage_history,
        "total_usage": total_usage,
        "limits": {"max_documents": MAX_DOCUMENTS, "max_document_bytes": inputs.MAX_DOCUMENT_BYTES,
                   "max_session_bytes": MAX_SESSION_BYTES, "max_attempts": 3, "max_review_calls": 6},
    })
    response.set_cookie(COOKIE_NAME, session.id, httponly=True, samesite="strict", secure=False,
                        max_age=SESSION_TTL_SECONDS, path="/")
    return response


@app.delete("/api/session")
def delete_session(request: Request) -> Response:
    session = _session(request)
    store.delete(session.id)
    response = JSONResponse({"deleted": True})
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


@app.post("/api/key")
async def set_key(request: Request) -> dict[str, Any]:
    from .providers import ProviderError, validate_api_key, validate_model

    payload = await _json_body(request)
    key = payload.get("api_key")
    try:
        key = validate_api_key(key)
    except (ValueError, TypeError, ProviderError):
        raise _safe_error("La API key no tiene un formato válido.") from None
    session = _session(request)
    try:
        extractor = validate_model(payload.get("extractor", session.extractor_model))
        reviewer = validate_model(payload.get("reviewer", session.reviewer_model))
    except (ValueError, TypeError):
        raise _safe_error("Identificador de modelo Gemini no válido.") from None
    with session.lock:
        session.api_key = key
        session.extractor_model = extractor
        session.reviewer_model = reviewer
    return {"has_api_key": True, "models": {"extractor": extractor, "reviewer": reviewer}}


@app.delete("/api/key")
def delete_key(request: Request) -> dict[str, Any]:
    session = _session(request)
    with session.lock:
        session.api_key = None
    return {"has_api_key": bool(os.environ.get("GEMINI_API_KEY", "").strip()), "session_key_deleted": True}


def _document_view(document: Any, original: bytes) -> dict[str, Any]:
    text = document.text
    estimate = max(1, (len(text) + 3) // 4) if text and document.mime in {"text/plain", inputs.DOCX_MIME} else None
    return {"id": document.id, "name": document.name, "mime": document.mime,
            "size": len(original), "sha256": document.sha256, "warnings": document.warnings,
            "text": text, "preview_url": f"/api/documents/{document.id}/source",
            "token_estimate": {"input_tokens": estimate, "estimated": estimate is not None,
                               "requires_provider_count": estimate is None,
                               "basis": "Heurística local caracteres/4; no es un conteo de Gemini." if estimate is not None
                               else "El contenido multimodal requiere conteo del proveedor; no hay una estimación local fiable."}}


def _register_documents(session: Session, items: list[tuple[Any, bytes]]) -> list[dict[str, Any]]:
    with session.lock:
        if len(session.documents) + len(items) > MAX_DOCUMENTS:
            raise _safe_error("Máximo 20 documentos por sesión.", 413)
        if sum(map(len, session.originals.values())) + sum(len(data) for _, data in items) > MAX_SESSION_BYTES:
            raise _safe_error("La sesión supera 96 MiB. Elimina documentos antes de continuar.", 413)
        for document, data in items:
            session.documents[document.id] = document
            session.originals[document.id] = data
        return [_document_view(document, data) for document, data in items]


@app.post("/api/documents/text")
async def add_text(request: Request) -> dict[str, Any]:
    payload = await _json_body(request)
    text = payload.get("text")
    name = payload.get("name", "Texto libre")
    if not isinstance(text, str) or not isinstance(name, str) or not 1 <= len(name.strip()) <= 180:
        raise _safe_error("Indica un nombre y texto válido.")
    try:
        document = inputs.from_text(text, name=name.strip(), document_id=secrets.token_hex(12))
    except (ValueError, UnicodeError) as error:
        raise _safe_error(str(error)) from None
    return {"documents": _register_documents(_session(request), [(document, text.encode("utf-8"))])}


@app.post("/api/documents")
async def upload_documents(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("multipart/form-data") or len(content_type) > 300:
        raise _safe_error("Carga archivos mediante multipart/form-data.")
    # El parser email trabaja en memoria: evita que UploadFile escriba originales a temp.
    try:
        envelope = b"Content-Type: " + content_type.encode("ascii", errors="strict") + b"\r\nMIME-Version: 1.0\r\n\r\n" + await request.body()
        message = BytesParser(policy=policy.default).parsebytes(envelope)
        if not message.is_multipart() or message.defects:
            raise ValueError("Carga multipart no válida.")
        items: list[tuple[Any, bytes]] = []
        for part in message.iter_parts():
            filename = part.get_filename()
            if filename is None:
                continue
            if len(items) >= MAX_DOCUMENTS:
                raise ValueError("Máximo 20 archivos por carga.")
            name = filename.replace("\\", "/").split("/")[-1].strip()
            if not name or len(name) > 180 or any(ord(char) < 32 for char in name):
                raise ValueError("Nombre de archivo no válido.")
            data = part.get_payload(decode=True)
            if not isinstance(data, bytes):
                raise ValueError("Contenido de archivo no válido.")
            document = inputs.read_document(data, name, document_id=secrets.token_hex(12))
            items.append((document, data))
        if not items:
            raise ValueError("Selecciona al menos un archivo.")
    except (ValueError, UnicodeError) as error:
        raise _safe_error(str(error)) from None
    return {"documents": _register_documents(_session(request), items)}


@app.get("/api/documents")
def list_documents(request: Request) -> dict[str, Any]:
    session = _session(request)
    with session.lock:
        return {"documents": [_document_view(document, session.originals[document_id])
                              for document_id, document in session.documents.items()]}


@app.delete("/api/documents/{document_id}")
def remove_document(document_id: str, request: Request) -> dict[str, bool]:
    session = _session(request)
    with session.lock:
        if any(batch["status"] == "running" for batch in session.batches.values()):
            raise _safe_error("Espera a que termine el lote antes de eliminar originales.", 409)
        if document_id not in session.documents:
            raise _safe_error("Documento no encontrado.", 404)
        session.documents.pop(document_id)
        session.originals.pop(document_id)
    return {"deleted": True}


@app.get("/api/documents/{document_id}/source")
def document_source(document_id: str, request: Request, download: bool = False) -> Response:
    session = _session(request)
    with session.lock:
        document = session.documents.get(document_id)
        if document is None:
            raise _safe_error("Documento no encontrado en esta sesión.", 404)
        if document.mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" and not download:
            return Response(document.text or "", media_type="text/plain")
        mime = document.mime
        disposition = "attachment" if download else "inline"
        # Nombre generado, sin incluir datos de usuario en cabeceras.
        return Response(session.originals[document_id], media_type=mime,
                        headers={"Content-Disposition": f'{disposition}; filename="documento-{document_id}"'})


@app.put("/api/schema")
async def save_schema(request: Request) -> dict[str, Any]:
    payload = await _json_body(request)
    schema = _schema(payload.get("schema", payload))
    session = _session(request)
    with session.lock:
        session.schema = schema
    return {"schema": _serializable(schema)}


def _empty_metrics(total: int) -> dict[str, Any]:
    return {"total": total, "processed": 0, "successful": 0, "partial": 0, "failed": 0,
            "success_rate": None, "partial_rate": None, "failure_rate": None, "total_attempts": 0}


def _execute_batch(session: Session, batch_id: str, documents: list[Any], schema: Any,
                   api_key: str, extractor_model: str, reviewer_model: str, max_attempts: int) -> None:
    def on_event(event: Any) -> None:
        with session.lock:
            batch = session.batches.get(batch_id)
            if batch is None:
                raise RuntimeError("La sesión del lote venció.")
            batch["events"].append(_serializable(event))
            snapshot = getattr(event, "snapshot", None)
            if isinstance(snapshot, dict) and "token_entry" in snapshot:
                entry = _serializable(snapshot["token_entry"])
                if not any(item["id"] == entry["id"] for item in batch["usage_history"]):
                    batch["usage_history"].append(entry)
                    session.usage_history.append({**entry, "batch_id": batch_id})
                batch["usage"] = _serializable(snapshot.get("batch_usage", batch["usage"]))
            if isinstance(snapshot, dict) and "result" in snapshot:
                result = _serializable(snapshot["result"])
                batch["results"] = [item for item in batch["results"] if item["document_id"] != result["document_id"]] + [result]
                batch["metrics"] = _progress_metrics(len(documents), batch["results"])
                batch["supervision"] = _supervision(batch["metrics"])

    try:
        from .pipeline import process_batch
        from .providers import GeminiProvider, ProviderError
        from .reviewer import GeminiReviewer
        from .schema import TokenUsage

        def ensure_session_active() -> None:
            if store.get(session.id, touch=False) is None or not (
                session.api_key == api_key or os.environ.get("GEMINI_API_KEY", "") == api_key
            ):
                raise ProviderError("La credencial fue borrada o la sesión venció. No se realizan más llamadas.",
                                    code="session_expired", retryable=False, usage=TokenUsage(total_calls=0))

        class SessionProvider:
            def __init__(self, provider: Any):
                self.provider = provider
                self.mode = provider.mode
                self.model = provider.model

            def extract(self, *args: Any, **kwargs: Any) -> Any:
                ensure_session_active()
                return self.provider.extract(*args, **kwargs)

            def review(self, *args: Any, **kwargs: Any) -> Any:
                ensure_session_active()
                return self.provider.review(*args, **kwargs)

            def verify(self, *args: Any, **kwargs: Any) -> Any:
                ensure_session_active()
                return self.provider.verify(*args, **kwargs)

        report = process_batch(documents, schema, SessionProvider(GeminiProvider(api_key, model=extractor_model)),
                               SessionProvider(GeminiReviewer(api_key, model=reviewer_model)), on_event=on_event,
                               max_attempts=max_attempts, max_review_calls=6)
        report_data = _serializable(report)
        with session.lock:
            batch = session.batches.get(batch_id)
            if batch is not None:
                batch.update(status="completed", mode=report_data["mode"], results=report_data["results"], metrics=report_data["metrics"],
                             usage=report_data.get("usage", {}), report=report_data)
                batch["supervision"] = _supervision(batch["metrics"], completed=True)
    except Exception:
        # No guardar str(error): SDKs o excepciones inesperadas podrían incluir headers.
        with session.lock:
            batch = session.batches.get(batch_id)
            if batch is not None:
                batch.update(status="failed", error="No se pudo completar el lote. Revisa la conexión y la configuración.")
                batch["supervision"] = _supervision(batch["metrics"], completed=True)
    finally:
        api_key = ""


def _progress_metrics(total: int, results: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = _empty_metrics(total)
    metrics["processed"] = len(results)
    for result in results:
        key = {"exitoso": "successful", "parcial": "partial", "fallido": "failed"}.get(result["status"])
        if key:
            metrics[key] += 1
        metrics["total_attempts"] += result.get("attempts", 0)
    if results:
        metrics.update(success_rate=100 * metrics["successful"] / len(results),
                       partial_rate=100 * metrics["partial"] / len(results),
                       failure_rate=100 * metrics["failed"] / len(results))
    return metrics


def _supervision(metrics: dict[str, Any], *, completed: bool = False) -> dict[str, Any]:
    processed = metrics.get("processed", metrics.get("successful", 0) + metrics.get("partial", 0) + metrics.get("failed", 0))
    rate = metrics.get("success_rate")
    required = rate is not None and rate < HUMAN_SUPERVISION_THRESHOLD and (processed >= 3 or completed and processed > 0)
    reason = (f"La tasa de éxito automático es {rate:.1f}%, por debajo del umbral de {HUMAN_SUPERVISION_THRESHOLD}%. "
              "Revisa los documentos parciales y fallidos antes de utilizar los resultados.") if required else None
    return {"required": required, "reason": reason, "threshold": HUMAN_SUPERVISION_THRESHOLD,
            "processed": processed, "success_rate": rate}


@app.post("/api/batches", status_code=202)
async def start_batch(request: Request) -> dict[str, Any]:
    from .providers import validate_model

    payload = await _json_body(request)
    session = _session(request)
    document_ids = payload.get("document_ids")
    if not isinstance(document_ids, list) or not document_ids or len(document_ids) > MAX_DOCUMENTS or not all(isinstance(item, str) for item in document_ids) or len(set(document_ids)) != len(document_ids):
        raise _safe_error("Selecciona entre 1 y 20 documentos sin duplicados.")
    attempts = payload.get("max_attempts", 3)
    if isinstance(attempts, bool) or not isinstance(attempts, int) or not 1 <= attempts <= 3:
        raise _safe_error("El máximo de intentos debe estar entre 1 y 3.")
    schema = _schema(payload.get("schema", _serializable(session.schema)))
    try:
        extractor_model = validate_model(payload.get("extractor_model", session.extractor_model))
        reviewer_model = validate_model(payload.get("reviewer_model", session.reviewer_model))
    except (ValueError, TypeError):
        raise _safe_error("Identificador de modelo Gemini no válido.") from None
    api_key = _credential(session)
    with session.lock:
        if any(batch["status"] == "running" for batch in session.batches.values()):
            raise _safe_error("Ya hay un lote en ejecución en esta sesión.", 409)
        if len(session.batches) >= 10:
            raise _safe_error("Máximo 10 lotes por sesión. Exporta los resultados y abre una nueva sesión.", 413)
        if any(document_id not in session.documents for document_id in document_ids):
            raise _safe_error("Hay documentos que no pertenecen a esta sesión.", 404)
        documents = [session.documents[document_id] for document_id in document_ids]
        batch_id = secrets.token_hex(12)
        session.batches[batch_id] = {"id": batch_id, "status": "running", "mode": "gemini", "events": [],
                                     "results": [], "metrics": _empty_metrics(len(documents)), "usage": _usage_total([]),
                                     "usage_history": [], "supervision": _supervision(_empty_metrics(len(documents))),
                                     "report": None, "human_reviews": [], "error": None,
                                     "started_at": datetime.now(timezone.utc).isoformat(), "schema": _serializable(schema)}
        session.schema = schema
    threading.Thread(target=_execute_batch, args=(session, batch_id, documents, schema, api_key,
                                                  extractor_model, reviewer_model, attempts), daemon=True).start()
    return {"id": batch_id, "status": "running", "mode": "gemini"}


def _batch(session: Session, batch_id: str) -> dict[str, Any]:
    batch = session.batches.get(batch_id)
    if batch is None:
        raise _safe_error("Lote no encontrado en esta sesión.", 404)
    return batch


@app.get("/api/batches/{batch_id}")
def batch_status(batch_id: str, request: Request) -> dict[str, Any]:
    session = _session(request)
    with session.lock:
        response = copy.deepcopy(_batch(session, batch_id))
        response["session_usage"] = _session_usage(session)
        response["session_usage_history"] = copy.deepcopy(session.usage_history)
        return response


@app.get("/api/batches/{batch_id}/export")
def export_batch(batch_id: str, request: Request, format: str = "json") -> Response:
    if format not in {"json", "csv"}:
        raise _safe_error("Formato de exportación no admitido.")
    session = _session(request)
    with session.lock:
        batch = _batch(session, batch_id)
        if batch["report"] is None:
            raise _safe_error("Espera a que termine el lote para exportarlo.", 409)
        report_data = copy.deepcopy(batch["report"])
        report_data["human_reviews"] = copy.deepcopy(batch["human_reviews"])
        report_data["usage_history"] = copy.deepcopy(batch.get("usage_history", []))
        report_data["supervision"] = copy.deepcopy(batch.get("supervision"))
    if format == "json":
        body = json.dumps(report_data, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")
        mime = "application/json"
    else:
        from .reports import report_csv
        from .schema import BatchReport
        base_report = {key: value for key, value in report_data.items() if key not in {"human_reviews", "usage_history", "supervision"}}
        csv_report = report_csv(BatchReport.model_validate(base_report))
        source_rows = csv.reader(io.StringIO(csv_report))
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow([*next(source_rows), "human_reviews", "supervision_required", "supervision_reason"])
        supervision = report_data.get("supervision") or {}
        for row in source_rows:
            reviews = [item for item in report_data["human_reviews"] if item["document_id"] == row[0]]
            writer.writerow([*row, json.dumps(reviews, ensure_ascii=False, allow_nan=False),
                             supervision.get("required", False), supervision.get("reason") or ""])
        body = ("\ufeff" + output.getvalue()).encode("utf-8")
        mime = "text/csv; charset=utf-8"
    return Response(body, media_type=mime,
                    headers={"Content-Disposition": f'attachment; filename="bsg-{batch_id}.{format}"'})


@app.post("/api/batches/{batch_id}/review")
async def human_review(batch_id: str, request: Request) -> dict[str, Any]:
    from .validation import InvalidJSONError, RecordValidationError, validate_business_rules, validate_record

    payload = await _json_body(request)
    document_id, data, note = payload.get("document_id"), payload.get("corrected_data"), payload.get("note")
    if not isinstance(document_id, str) or not isinstance(data, dict) or not isinstance(note, str) or not 3 <= len(note.strip()) <= 2000:
        raise _safe_error("Indica el documento, objeto de datos corregidos y una nota de revisión (3–2000 caracteres).")
    session = _session(request)
    with session.lock:
        batch = _batch(session, batch_id)
        if batch["status"] != "completed":
            raise _safe_error("Completa el lote antes de registrar una revisión humana.", 409)
        original = next((item for item in batch["results"] if item["document_id"] == document_id), None)
        if original is None:
            raise _safe_error("Documento no encontrado en el lote.", 404)
        schema = _schema(batch["schema"])
        try:
            validated = validate_record(data, schema)
        except (InvalidJSONError, RecordValidationError):
            raise _safe_error("Los datos corregidos no cumplen el esquema. Revisa claves, tipos, fechas y categorías.", 422) from None
        validation_data = _serializable(validate_business_rules(validated, schema))
        review = {"id": secrets.token_hex(12), "document_id": document_id,
                  "timestamp": datetime.now(timezone.utc).isoformat(), "actor": "usuario_local",
                  "original_record": copy.deepcopy(original.get("record")), "proposed_record": data,
                  "note": note.strip(), "validation": validation_data,
                  "changes_pipeline_success": False}
        batch["human_reviews"].append(review)
    return {"review": review, "validation": validation_data}


@app.get("/")
def frontend() -> Response:
    index = WEB_DIST / "index.html"
    if index.is_file():
        return FileResponse(index)
    return Response("Interfaz aún sin compilar. Ejecuta iniciar.bat desde la carpeta del proyecto.",
                    media_type="text/plain", status_code=503)


@app.get("/favicon.svg")
def favicon() -> Response:
    path = WEB_DIST / "favicon.svg"
    if path.is_file():
        return FileResponse(path, media_type="image/svg+xml")
    return Response(status_code=404)


if (WEB_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")
