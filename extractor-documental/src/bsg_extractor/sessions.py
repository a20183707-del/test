"""Sesiones locales limitadas; secretos, originales y resultados sólo en memoria."""
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any

SESSION_TTL_SECONDS = 60 * 60
MAX_SESSIONS = 8
MAX_DOCUMENTS = 20
MAX_SESSION_BYTES = 96 * 1024 * 1024


@dataclass
class Session:
    id: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    csrf_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    expires_at: float = field(default_factory=lambda: time.monotonic() + SESSION_TTL_SECONDS)
    api_key: str | None = field(default=None, repr=False)
    documents: dict[str, Any] = field(default_factory=dict, repr=False)
    originals: dict[str, bytes] = field(default_factory=dict, repr=False)
    batches: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)
    usage_history: list[dict[str, Any]] = field(default_factory=list, repr=False)
    schema: Any = None
    extractor_model: str = "gemini-3.5-flash-lite"
    reviewer_model: str = "gemini-3.8-flash"
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def wipe(self) -> None:
        """Elimina referencias; Python no ofrece borrado criptográfico de strings."""
        with self.lock:
            self.api_key = None
            self.documents.clear()
            self.originals.clear()
            self.batches.clear()
            self.usage_history.clear()
            self.schema = None


class SessionStore:
    def __init__(self, ttl: int = SESSION_TTL_SECONDS, max_sessions: int = MAX_SESSIONS):
        self.ttl = ttl
        self.max_sessions = max_sessions
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    def get(self, session_id: str | None, *, touch: bool = True) -> Session | None:
        with self._lock:
            self._prune()
            session = self._sessions.get(session_id or "")
            if session is not None and touch:
                session.expires_at = time.monotonic() + self.ttl
            return session

    def create(self) -> Session:
        with self._lock:
            self._prune()
            if len(self._sessions) >= self.max_sessions:
                raise ValueError("Hay demasiadas sesiones locales abiertas. Cierra alguna o espera su vencimiento.")
            session = Session(expires_at=time.monotonic() + self.ttl)
            self._sessions[session.id] = session
            return session

    def delete(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session is not None:
                session.wipe()

    def expire(self) -> None:
        with self._lock:
            self._prune()

    def clear(self) -> None:
        with self._lock:
            for session in self._sessions.values():
                session.wipe()
            self._sessions.clear()

    def _prune(self) -> None:
        expired = [key for key, session in self._sessions.items() if session.expires_at <= time.monotonic()]
        for key in expired:
            session = self._sessions.pop(key)
            session.wipe()
