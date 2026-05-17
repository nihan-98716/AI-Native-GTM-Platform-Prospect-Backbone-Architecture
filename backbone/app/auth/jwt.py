from __future__ import annotations

import time

import jwt
from jwt import InvalidTokenError

from app.contracts.api.auth import TokenClaims
from app.core.config import Settings
from app.observability.runtime import ObservabilityRuntime, get_observability_runtime


class TokenValidationError(ValueError):
    pass


class Hs256TokenVerifier:
    def __init__(self, settings: Settings, observability: ObservabilityRuntime | None = None) -> None:
        self._settings = settings
        self._obs = observability or get_observability_runtime()

    def verify(self, token: str) -> TokenClaims:
        started = time.perf_counter()
        try:
            payload = jwt.decode(
                token,
                key=self._settings.jwt_secret,
                algorithms=["HS256"],
                audience=self._settings.jwt_audience,
                issuer=self._settings.jwt_issuer,
                options={"require": ["sub", "tenant_id", "exp", "iat"]},
            )
        except InvalidTokenError as exc:
            self._obs.emit_operation(
                service="auth.jwt.verify",
                status="error",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            raise TokenValidationError("Invalid bearer token.") from exc
        claims = TokenClaims.model_validate(payload)
        self._obs.emit_operation(
            service="auth.jwt.verify",
            status="ok",
            duration_ms=int((time.perf_counter() - started) * 1000),
            tenant_id=claims.tenant_id,
        )
        return claims

