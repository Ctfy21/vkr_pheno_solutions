import httpx
from functools import lru_cache
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt, jwk
from jose.utils import base64url_decode
from app.config import KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID

security = HTTPBearer()

_jwks_cache: dict = {}


async def _get_keycloak_public_keys() -> dict:
    """Fetch JWKS from Keycloak and cache."""
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


def _find_key(jwks: dict, kid: str) -> dict:
    for key in jwks.get("keys", []):
        if key["kid"] == kid:
            return key
    raise HTTPException(status_code=401, detail="Key not found in JWKS")


async def decode_keycloak_token(token: str) -> dict:
    """Validate and decode a Keycloak JWT."""
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token header")

    jwks = await _get_keycloak_public_keys()
    key_data = _find_key(jwks, header["kid"])
    public_key = jwk.construct(key_data)

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[header.get("alg", "RS256")],
            audience="account",
            options={"verify_aud": False},
        )
    except JWTError as e:
        # Invalidate cache and retry once
        global _jwks_cache
        _jwks_cache = {}
        try:
            jwks = await _get_keycloak_public_keys()
            key_data = _find_key(jwks, header["kid"])
            public_key = jwk.construct(key_data)
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[header.get("alg", "RS256")],
                audience="account",
                options={"verify_aud": False},
            )
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    return payload


def extract_roles(payload: dict) -> List[str]:
    """Extract realm roles from Keycloak token payload."""
    realm_access = payload.get("realm_access", {})
    return realm_access.get("roles", [])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current user from Keycloak JWT."""
    payload = await decode_keycloak_token(credentials.credentials)
    roles = extract_roles(payload)

    # Map to user object compatible with existing code
    user = {
        "_id": payload.get("sub", ""),
        "email": payload.get("email", ""),
        "name": payload.get("preferred_username", payload.get("name", "")),
        "role": "admin" if "admin" in roles else "researcher" if "researcher" in roles else "observer",
        "roles": roles,
        "organizationId": "",
    }
    return user


def require_role(required_role: str):
    """Dependency factory: require a specific role."""
    async def _check(user: dict = Depends(get_current_user)):
        if required_role not in user.get("roles", []):
            raise HTTPException(status_code=403, detail=f"Role '{required_role}' required")
        return user
    return _check
