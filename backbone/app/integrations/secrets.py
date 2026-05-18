from __future__ import annotations

import base64
import hashlib
import json

from app.contracts.integrations import IntegrationCredentials
from app.integrations.errors import IntegrationConfigurationError
from app.core.config import get_settings

try:  # pragma: no cover - optional dependency
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover - optional dependency
    Fernet = None


class IntegrationCredentialCodec:
    def __init__(self, secret: str | None = None) -> None:
        resolved_secret = secret or get_settings().jwt_secret
        if Fernet is None:
            self._fernet = None
            self._secret = resolved_secret
            return
        key = base64.urlsafe_b64encode(hashlib.sha256(resolved_secret.encode("utf-8")).digest())
        self._fernet = Fernet(key)
        self._secret = resolved_secret

    def encrypt(self, credentials: IntegrationCredentials) -> bytes:
        payload = json.dumps(credentials.model_dump(mode="json"), sort_keys=True).encode("utf-8")
        if self._fernet is not None:
            return self._fernet.encrypt(payload)
        return base64.urlsafe_b64encode(payload)

    def decrypt(self, payload: bytes | None) -> IntegrationCredentials | None:
        if not payload:
            return None
        try:
            raw = self._fernet.decrypt(payload) if self._fernet is not None else base64.urlsafe_b64decode(payload)
            decoded = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: PERF203 - explicit crypto decode failure
            raise IntegrationConfigurationError("Failed to decode integration credentials.") from exc
        return IntegrationCredentials.model_validate(decoded)

