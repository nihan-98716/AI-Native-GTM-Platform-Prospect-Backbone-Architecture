from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_claims, get_db_session
from app.contracts.api.auth import TokenClaims
from app.contracts.responses.envelope import SuccessEnvelope
from app.core.config import get_settings
from app.models.identity import User
from app.models.tenant import Tenant

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=SuccessEnvelope)
def me(claims: TokenClaims = Depends(get_current_claims)) -> SuccessEnvelope:
    return SuccessEnvelope(data=claims.model_dump())


@router.get("/bootstrap")
def bootstrap(session: Session = Depends(get_db_session)) -> dict[str, str]:
    settings = get_settings()
    tenant = session.execute(select(Tenant).order_by(Tenant.created_at.asc())).scalars().first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No seed tenant available.")
    user = session.execute(
        select(User)
        .where(User.tenant_id == tenant.id, User.status == "active")
        .order_by(User.created_at.asc())
    ).scalars().first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No seed user available.")

    now = datetime.now(tz=UTC)
    permissions = list(user.permissions or []) if isinstance(user.permissions, list) else list((user.permissions or {}).keys())
    token = jwt.encode(
        {
            "sub": str(user.id),
            "tenant_id": str(tenant.id),
            "roles": list(user.roles or []),
            "permissions": permissions,
            "aud": settings.jwt_audience,
            "iss": settings.jwt_issuer,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=4)).timestamp()),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    return {
        "token": token,
        "tenantDisplayName": tenant.name,
        "profileDisplayName": user.full_name,
    }

