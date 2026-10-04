"""Regresiones de seguridad independientes; archivos y claves son fixtures locales."""
from __future__ import annotations

import io
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from bsg_extractor import providers
from bsg_extractor.inputs import from_text, read_document
from bsg_extractor.providers import GeminiProvider, ProviderError
from bsg_extractor.schema import ExtractionSchema, FieldSpec


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-le", "utf-16-be", "utf-32", "utf-32-le", "utf-32-be"])
def test_docx_dtd_and_entity_rejected_in_multibyte_xml(encoding):
    """Una entidad interna segura reproduce la evasión, sin XXE ni archivos externos."""
    xml = ('<?xml version="1.0"?>'
           '<!DOCTYPE w:document [<!ENTITY marker "INTERNAL_ENTITY_EXPANDED">]>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           '<w:body><w:p><w:r><w:t>&marker;</w:t></w:r></w:p></w:body></w:document>')
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", xml.encode(encoding))
    with pytest.raises(ValueError, match="declaraciones XML"):
        read_document(output.getvalue(), "multibyte-entity-fixture.docx")


def test_provider_redirect_does_not_forward_request_or_credential(monkeypatch):
    """HTTP fixture local verifica que una redirección no recibe una segunda petición."""
    observed = []

    class RedirectFixture(BaseHTTPRequestHandler):
        def do_POST(self):
            observed.append(("POST", self.path))
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.send_response(302)
            self.send_header("Location", "/redirected-destination")
            self.end_headers()

        def do_GET(self):
            observed.append(("GET", self.path))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *_):
            pass  # No registrar solicitudes, cabeceras ni fixtures de credenciales.

    server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectFixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setattr(providers, "API_BASE", f"http://127.0.0.1:{server.server_port}/models")
        schema = ExtractionSchema(title="Fixture", fields=[FieldSpec(name="value", type="number")])
        with pytest.raises(ProviderError) as raised:
            GeminiProvider("offline_dummy_key", timeout=2).extract(from_text("value:42"), schema)
        assert raised.value.code == "http_302"
        assert len(observed) == 1
        assert observed[0][0] == "POST"
        assert all(path != "/redirected-destination" for _, path in observed)
        assert "offline_dummy_key" not in str(raised.value)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
