from typing import Protocol

from app.contracts.api.auth import TokenClaims


class TokenVerifier(Protocol):
    def verify(self, token: str) -> TokenClaims:
        ...


class Authorizer(Protocol):
    def require(self, claims: TokenClaims, required_permission: str) -> None:
        ...

