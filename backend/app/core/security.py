"""JWT verification (OWASP A07/A08). Verifies the Supabase-signed access token
and exposes the verified claims. Claims are NEVER trusted unless the signature
checks out — this is what prevents a client from forging company_id."""
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

_bearer = HTTPBearer(auto_error=False)

# Supabase signs user access tokens with an asymmetric key (ES256) and publishes
# the public key via JWKS. We fetch + cache it and verify the signature — a
# client cannot forge company_id without the private key it never sees.
_settings = get_settings()
_jwk_client = jwt.PyJWKClient(
    f"{_settings.supabase_url}/auth/v1/.well-known/jwks.json", cache_keys=True
)


@dataclass
class CurrentUser:
    id: str
    email: Optional[str]
    company_id: Optional[str]
    is_super_admin: bool
    roles: list[str]
    claims: dict          # full verified payload, re-injected as request.jwt.claims


def get_current_user(
    cred: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> CurrentUser:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(cred.credentials)
        payload = jwt.decode(
            cred.credentials,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}")

    return CurrentUser(
        id=payload.get("sub"),
        email=payload.get("email"),
        company_id=payload.get("company_id"),
        is_super_admin=bool(payload.get("is_super_admin", False)),
        roles=list(payload.get("roles") or []),
        claims=payload,
    )


def require_roles(*allowed: str):
    """Dependency factory: 403 unless the user has one of the allowed roles
    (super_admin always allowed). RBAC — OWASP A01."""
    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.is_super_admin or any(r in user.roles for r in allowed):
            return user
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    return checker
