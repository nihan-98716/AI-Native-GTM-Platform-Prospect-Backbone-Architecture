from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.auth.jwt import Hs256TokenVerifier, TokenValidationError
from app.auth.rbac import AuthorizationError, RbacAuthorizer
from app.contracts.api.auth import TokenClaims
from app.core.config import Settings


def build_settings() -> Settings:
    return Settings(
        app_name="gtm-backbone",
        environment="test",
        database_url="postgresql+psycopg://gtm:gtm@localhost:5432/gtm",
        jwt_secret="unit-test-secret-with-32-byte-minimum",
        jwt_audience="gtm-api",
        jwt_issuer="gtm-local",
        cors_origins=["http://localhost:3000"],
        rate_limit_per_minute=120,
        auto_seed_on_startup=False,
        seed_dir="..\\data",
    )


def build_token(settings: Settings, **overrides) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "sub": "user-1",
        "tenant_id": "tenant-1",
        "roles": ["seller"],
        "permissions": ["accounts:read"],
        "aud": settings.jwt_audience,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    payload.update(overrides)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def test_hs256_token_verifier_accepts_valid_claims():
    settings = build_settings()
    verifier = Hs256TokenVerifier(settings=settings)
    claims = verifier.verify(build_token(settings))
    assert claims.sub == "user-1"
    assert claims.tenant_id == "tenant-1"


def test_hs256_token_verifier_rejects_invalid_issuer():
    settings = build_settings()
    verifier = Hs256TokenVerifier(settings=settings)
    token = build_token(settings, iss="unexpected-issuer")
    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_hs256_token_verifier_rejects_invalid_audience():
    settings = build_settings()
    verifier = Hs256TokenVerifier(settings=settings)
    token = build_token(settings, aud="wrong-audience")
    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_hs256_token_verifier_rejects_expired_token():
    settings = build_settings()
    verifier = Hs256TokenVerifier(settings=settings)
    now = datetime.now(tz=UTC)
    token = jwt.encode(
        {
            "sub": "user-1",
            "tenant_id": "tenant-1",
            "roles": ["seller"],
            "permissions": ["accounts:read"],
            "aud": settings.jwt_audience,
            "iss": settings.jwt_issuer,
            "iat": int((now - timedelta(minutes=20)).timestamp()),
            "exp": int((now - timedelta(minutes=10)).timestamp()),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_hs256_token_verifier_rejects_missing_required_claims():
    settings = build_settings()
    verifier = Hs256TokenVerifier(settings=settings)
    now = datetime.now(tz=UTC)
    token = jwt.encode(
        {
            "sub": "user-1",
            "roles": ["seller"],
            "permissions": ["accounts:read"],
            "aud": settings.jwt_audience,
            "iss": settings.jwt_issuer,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_rbac_requires_permission():
    authorizer = RbacAuthorizer()
    claims = TokenClaims(sub="u1", tenant_id="t1", permissions=["accounts:*"])
    authorizer.require(claims, "accounts:read")

    denied = TokenClaims(sub="u2", tenant_id="t1", permissions=["signals:read"])
    with pytest.raises(AuthorizationError):
        authorizer.require(denied, "accounts:read")

